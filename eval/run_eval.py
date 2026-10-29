"""Run eval/messages.jsonl through the real check pipeline (real Gemini key) and measure it.

    python eval/run_eval.py              # full run, writes eval/results.json and eval/results.summary.json
    python eval/run_eval.py --limit 5    # smoke run on the first 5 messages
    python eval/run_eval.py --report     # no model calls: recompute the summary and S1 what-ifs from results.json
    python eval/run_eval.py --out eval/results_run2.json --compare eval/results.json   # second run + stability

How it works
- GEMINI_API_KEY is parsed from ../../.env.railway (the main checkout) or --env-file, in process. It is never printed.
- Every message is scored as if first seen: it gets its own fresh temporary SQLite file, so the cache, ring links (S4)
  and script matches (S5) of other eval messages can't touch it. IDENTIFIER_SALT is a random value for this run.
- Each message goes through backend.pipeline.run_check, the function POST /api/check calls after input validation and
  rate limiting. We call validate_check_input ourselves and skip the rate limiter.
- At most 3 checks run at once. A 429 from Gemini pauses all workers, and a check whose claims step failed is retried
  (fresh database again) after a backoff. The first-attempt failure rate is kept in the summary too.
- The score what-ifs re-add the saved signal points with a different S1 weight; they never call the model.
"""
from __future__ import annotations

import argparse
import asyncio
import contextvars
import dataclasses
import json
import math
import os
import secrets
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

S1_WHAT_IF = (35, 40, 45, 50)
LANG_ORDER = ('en', 'hi', 'hinglish', 'mr', 'ta', 'te', 'kn', 'bn')


def default_env_file() -> Path:
    # The repo root, or the main checkout when this runs from a git worktree (.claude/worktrees/<name>).
    for base in (REPO, *REPO.parents):
        candidate = base / '.env.railway'
        if candidate.is_file():
            return candidate
    return REPO / '.env.railway'


def load_key(env_file: Path) -> None:
    """Set GEMINI_API_KEY from the env file. Nothing else from that file is loaded (no admin or payment keys)."""
    if not os.getenv('GEMINI_API_KEY', '').strip():
        if not env_file.is_file():
            raise SystemExit(f'No GEMINI_API_KEY in the environment and no env file at {env_file}')
        for line in env_file.read_text(encoding='utf-8').splitlines():
            name, sep, value = line.strip().partition('=')
            if sep and name.strip().removeprefix('export ').strip() == 'GEMINI_API_KEY':
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                    value = value[1:-1]
                os.environ['GEMINI_API_KEY'] = value.strip()
    if not os.getenv('GEMINI_API_KEY', '').strip():
        raise SystemExit('GEMINI_API_KEY not found')
    print('key: set', flush=True)


def load_messages(limit: int | None, only: set[str] | None) -> list[dict]:
    rows = [json.loads(line) for line in (HERE / 'messages.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if only:
        rows = [r for r in rows if r['id'] in only]
    return rows[:limit] if limit else rows


# ---------------------------------------------------------------- live run

class State:
    def __init__(self) -> None:
        self.calls: Counter = Counter()        # model call attempts by kind:model
        self.errors: Counter = Counter()       # failures by kind:reason
        self.cooldown_until = 0.0
        self.backoff = 10.0


async def run_live(messages: list[dict], concurrency: int, max_attempts: int) -> tuple[list[dict], dict]:
    # Settings for this process only. They must be set before backend modules are imported.
    tmp_root = Path(tempfile.mkdtemp(prefix='cbyp-eval-'))
    os.environ['IDENTIFIER_SALT'] = secrets.token_urlsafe(32)
    os.environ['IP_CHECKS_PER_HOUR'] = '1000000'
    os.environ['SQLITE_PATH'] = str(tmp_root / 'unused.db')
    for name in ('OPENAI_API_KEY', 'VIASOCKET_REPORT_WEBHOOK_URL', 'PHISHTANK_FEED_PATH', 'PUBLIC_BASE_URL'):
        os.environ.pop(name, None)  # Gemini only; no webhooks; S7 feed off, as in production today

    from google.genai import errors as genai_errors

    from backend import config, llm, pipeline
    from backend.extraction import normalize, regex_extract, source_text
    from backend.inputs import validate_check_input
    from backend.schemas import CheckRequest
    from backend import signals as signals_mod

    db_path: contextvars.ContextVar[Path | None] = contextvars.ContextVar('eval_db_path', default=None)
    trace: contextvars.ContextVar[dict | None] = contextvars.ContextVar('eval_trace', default=None)

    # One fresh SQLite file per check: run_check reads its path from get_settings(). A context variable
    # (copied into every task and thread the check starts) keeps concurrent checks apart.
    real_settings = config.get_settings

    def eval_settings() -> config.Settings:
        settings = real_settings()
        path = db_path.get()
        return dataclasses.replace(settings, sqlite_path=path) if path else settings

    pipeline.get_settings = eval_settings

    state = State()
    await llm.providers.initialize()
    if not llm.providers.ready or llm.providers.google is None:
        raise SystemExit('Gemini model discovery failed; nothing was run.')
    models = dict(llm.providers.models)
    print('models: ' + json.dumps(models), flush=True)

    # Count every model call and classify failures without changing behaviour.
    aio_models = llm.providers.google.aio.models

    def counted(kind: str, fn):
        async def wrapper(*args, **kwargs):
            model = kwargs.get('model', '?')
            state.calls[f'{kind}:{model}'] += 1
            rec = trace.get()
            if rec is not None:
                rec['calls'] += 1
            try:
                result = await fn(*args, **kwargs)
                state.backoff = 10.0
                return result
            except genai_errors.APIError as exc:
                reason = f'http_{exc.code}'
                state.errors[f'{kind}:{reason}'] += 1
                if rec is not None:
                    rec['errors'].append(reason)
                if exc.code == 429:
                    state.cooldown_until = max(state.cooldown_until, time.monotonic() + state.backoff)
                    state.backoff = min(120.0, state.backoff * 2)
                raise
            except asyncio.CancelledError:
                state.errors[f'{kind}:timeout'] += 1
                if rec is not None:
                    rec['errors'].append('timeout')
                raise
            except Exception as exc:
                state.errors[f'{kind}:{type(exc).__name__}'] += 1
                if rec is not None:
                    rec['errors'].append(type(exc).__name__)
                raise
        return wrapper

    aio_models.generate_content = counted('generate', aio_models.generate_content)
    aio_models.embed_content = counted('embed', aio_models.embed_content)

    # Keep what the model extracted (before and after quote verification) for the error analysis.
    real_structured = llm.providers.structured

    async def traced_structured(role, instruction, text, schema, media=None):
        result = await real_structured(role, instruction, text, schema, media)
        rec = trace.get()
        if rec is not None and role == 'extract':
            rec['claims_raw'] = [c.model_dump() for c in getattr(result, 'claims', [])]
        return result

    llm.providers.structured = traced_structured
    real_extract = llm.extract

    async def traced_extract(text):
        result = await real_extract(text)
        rec = trace.get()
        if rec is not None:
            rec['extraction'] = result.model_dump()
        return result

    llm.extract = traced_extract

    def s1_diagnosis(text: str, extraction: dict | None) -> dict:
        """The S1 conditions from backend/signals.py evaluate(), recomputed so misses can be explained."""
        clean = normalize(source_text(text))
        if extraction is None:  # the pipeline falls back to regex entities and no claims
            extraction = regex_extract(source_text(text)).model_dump()
        ents = extraction.get('entities', {})
        upis = ents.get('upi_ids', [])
        context = clean
        for upi in upis:
            context = context.replace(upi, ' ')
        match = signals_mod.INVESTMENT.search(context)
        claims = (extraction or {}).get('claims', [])
        return {
            'upi_ids': upis,
            'non_valid_upi': [u for u in upis if not u.split('@')[-1].startswith('valid')],
            'investment_regex': match.group(0) if match else None,
            'investment_claim': any(c['type'] in signals_mod.INVESTMENT_CLAIMS and normalize(c['quote']) in clean for c in claims),
            'payment_verb': bool(signals_mod.PAYMENT.search(clean)),
        }

    async def one_attempt(msg: dict, attempt: int) -> dict:
        db_file = tmp_root / f"{msg['id']}-a{attempt}.db"
        db_path.set(db_file)
        rec = {'calls': 0, 'errors': [], 'claims_raw': None, 'extraction': None}
        trace.set(rec)
        body = CheckRequest(lang=msg['lang'], anon_id=f"u_eval_{msg['id']}", ref=None, input={'text': msg['text']})
        inp = validate_check_input(body.input)
        started = time.perf_counter()
        result = await pipeline.run_check(body, inp, 'http://eval.local')
        wall_ms = round((time.perf_counter() - started) * 1000)
        return {
            'band': result.band, 'score': result.score,
            'signals': [{'id': s.id, 'points': s.points, 'kind': s.evidence.kind, 'evidence': s.evidence.text}
                        for s in result.signals],
            'unchecked': list(result.unchecked), 'latency_ms': result.latency_ms, 'wall_ms': wall_ms,
            'cached': result.cached, 'entities': [e.model_dump() for e in result.entities],
            'model_calls': rec['calls'], 'model_errors': rec['errors'],
            'claims_raw': rec['claims_raw'], 'extraction': rec['extraction'],
            's1_diag': s1_diagnosis(msg['text'], rec['extraction']),
        }

    sem = asyncio.Semaphore(concurrency)
    done = 0

    async def worker(msg: dict) -> dict:
        nonlocal done
        async with sem:
            first_unchecked = None
            attempts = []
            for attempt in range(1, max_attempts + 1):
                wait = state.cooldown_until - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                # Each attempt runs in its own context copy, so its db path and trace stay its own.
                ctx = contextvars.copy_context()
                out = await asyncio.create_task(one_attempt(msg, attempt), context=ctx)
                attempts.append({'unchecked': out['unchecked'], 'errors': out['model_errors'], 'calls': out['model_calls']})
                if first_unchecked is None:
                    first_unchecked = out['unchecked']
                if 'claims' not in out['unchecked']:
                    break
                await asyncio.sleep(5 * attempt)
            done += 1
            row = {k: msg[k] for k in ('id', 'label', 'lang', 'category', 'ident', 'source', 'text')}
            row.update(out)
            row['attempts'] = len(attempts)
            row['first_attempt_unchecked'] = first_unchecked
            row['attempt_log'] = attempts
            sig = ' '.join(f"{s['id']}+{s['points']}" for s in row['signals']) or '-'
            print(f"[{done}/{len(messages)}] {row['id']:7} {row['label']:8} -> {row['band']:16} {row['score']:3} "
                  f"{sig:28} unchecked={row['unchecked']} {row['latency_ms']}ms att={row['attempts']}", flush=True)
            return row

    try:
        rows = await asyncio.gather(*(worker(m) for m in messages))
    finally:
        await llm.providers.close()
        shutil.rmtree(tmp_root, ignore_errors=True)
    meta = {
        'measured_at': datetime.now(timezone.utc).isoformat(),
        'models': models,
        'concurrency': concurrency,
        'max_attempts': max_attempts,
        'model_calls': dict(state.calls), 'model_calls_total': sum(state.calls.values()),
        'model_errors': dict(state.errors),
        'method': ('backend.pipeline.run_check per message with validate_check_input; real Gemini; fresh temporary '
                   'SQLite per attempt (no cache, S4 or S5 from other eval messages); random IDENTIFIER_SALT; '
                   'phishing feed off; local machine, not production.'),
    }
    return list(rows), meta


# ---------------------------------------------------------------- analysis (no model calls)

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def band_for(total: int, high: int, caution: int) -> str:
    return 'high_risk' if total >= high else 'caution' if total >= caution else 'no_known_signals'


def rescore(row: dict, s1: int, high: int, caution: int) -> tuple[int, str]:
    total = sum(s1 if s['id'] == 'S1' else s['points'] for s in row['signals'])
    total = max(0, min(100, total))
    return total, band_for(total, high, caution)


def thresholds() -> tuple[int, int, int]:
    """S1 weight and band cut-offs as the code has them (backend/weights.py, backend/signals.py score())."""
    from backend import weights
    from backend.schemas import Evidence, Signal
    from backend.signals import score

    def band_of(points: int) -> str:
        return score([Signal(id='S6', label='x', points=points, evidence=Evidence(kind='quote', text='x', source_url=None))])[1]
    high = next(p for p in range(0, 101) if band_of(p) == 'high_risk')
    caution = next(p for p in range(0, 101) if band_of(p) == 'caution')
    return weights.S1, high, caution


def pct(k: int, n: int) -> str:
    return f'{k}/{n} ({100 * k / n:.0f}%)' if n else '0/0'


def percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    import numpy as np
    return round(float(np.percentile(values, q)))


def summarize(rows: list[dict], meta: dict) -> dict:
    s1_now, high, caution = thresholds()
    scams = [r for r in rows if r['label'] == 'scam']
    ords = [r for r in rows if r['label'] == 'ordinary']

    def bands(group: list[dict]) -> dict:
        c = Counter(r['band'] for r in group)
        n = len(group)
        flagged = c['high_risk'] + c['caution']
        return {'n': n, 'high_risk': c['high_risk'], 'caution': c['caution'], 'no_known_signals': c['no_known_signals'],
                'flagged': flagged, 'flagged_ci95': [round(x, 3) for x in wilson(flagged, n)],
                'high_risk_ci95': [round(x, 3) for x in wilson(c['high_risk'], n)]}

    def by(group: list[dict], key: str, order=None) -> dict:
        keys = order or sorted({r[key] for r in group})
        return {k: bands([r for r in group if r[key] == k]) for k in keys if any(r[key] == k for r in group)}

    text_lat = [r['latency_ms'] for r in rows]
    unchecked_final = Counter(u for r in rows for u in r['unchecked'])
    unchecked_first = Counter(u for r in rows for u in (r.get('first_attempt_unchecked') or r['unchecked']))
    domain_rows = [r for r in rows if (r.get('extraction') or {}).get('entities', {}).get('domains')
                   or any(e['type'] in ('domain', 'url') for e in r.get('entities', []))]
    signal_rates = {}
    for sid in ('S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7'):
        signal_rates[sid] = {'scam': sum(any(s['id'] == sid for s in r['signals']) for r in scams),
                             'ordinary': sum(any(s['id'] == sid for s in r['signals']) for r in ords)}
    what_if = {}
    for w in S1_WHAT_IF:
        sb = Counter(rescore(r, w, high, caution)[1] for r in scams)
        ob = Counter(rescore(r, w, high, caution)[1] for r in ords)
        what_if[str(w)] = {
            'scam_high_risk': sb['high_risk'], 'scam_caution': sb['caution'], 'scam_missed': sb['no_known_signals'],
            'scam_flagged': sb['high_risk'] + sb['caution'],
            'ord_caution': ob['caution'], 'ord_high_risk': ob['high_risk'], 'ord_flagged': ob['caution'] + ob['high_risk'],
            'n_scam': len(scams), 'n_ord': len(ords),
            'scam_high_risk_ids_gained': sorted(r['id'] for r in scams if rescore(r, w, high, caution)[1] == 'high_risk'
                                                and r['band'] != 'high_risk'),
            'ord_high_risk_ids': sorted(r['id'] for r in ords if rescore(r, w, high, caution)[1] == 'high_risk'),
        }
    errors_missed = sorted((r for r in scams if r['band'] == 'no_known_signals'), key=lambda r: (r['score'], r['id']))
    errors_fp = sorted((r for r in ords if r['band'] != 'no_known_signals'), key=lambda r: (-r['score'], r['id']))
    return {
        'n': len(rows), 'n_scam': len(scams), 'n_ordinary': len(ords),
        'code_settings': {'S1': s1_now, 'high_risk_at': high, 'caution_at': caution},
        'scam': bands(scams), 'ordinary': bands(ords),
        'scam_by_lang': by(scams, 'lang', LANG_ORDER), 'ordinary_by_lang': by(ords, 'lang', LANG_ORDER),
        'scam_by_category': by(scams, 'category'), 'scam_by_ident': by(scams, 'ident'),
        'ordinary_by_category': by(ords, 'category'),
        'latency_ms': {'p50': percentile(text_lat, 50), 'p95': percentile(text_lat, 95), 'max': max(text_lat) if text_lat else None,
                       'n': len(text_lat)},
        'unchecked_final': dict(unchecked_final), 'unchecked_first_attempt': dict(unchecked_first),
        'rows_with_domains': len(domain_rows),
        'retried_rows': sum(r.get('attempts', 1) > 1 for r in rows),
        'signal_fire_counts': signal_rates,
        'what_if_s1': what_if,
        'missed_scams': [{'id': r['id'], 'score': r['score'], 'signals': r['signals'], 'category': r['category'],
                          'ident': r['ident'], 'unchecked': r['unchecked'], 's1_diag': r.get('s1_diag')} for r in errors_missed],
        'flagged_ordinary': [{'id': r['id'], 'band': r['band'], 'score': r['score'], 'signals': r['signals'],
                              'category': r['category'], 's1_diag': r.get('s1_diag')} for r in errors_fp],
        'meta': {k: meta.get(k) for k in ('measured_at', 'models', 'model_calls_total', 'model_errors', 'concurrency')},
    }


def print_report(summary: dict) -> None:
    sc, od = summary['scam'], summary['ordinary']
    cs = summary['code_settings']
    print(f"\nCode settings: S1={cs['S1']}, high_risk >= {cs['high_risk_at']}, caution >= {cs['caution_at']}")
    print(f"Scams (n={sc['n']}): high_risk {pct(sc['high_risk'], sc['n'])}, caution {pct(sc['caution'], sc['n'])}, "
          f"missed {pct(sc['no_known_signals'], sc['n'])}; flagged {pct(sc['flagged'], sc['n'])} CI95 {sc['flagged_ci95']}")
    print(f"Ordinary (n={od['n']}): caution {pct(od['caution'], od['n'])}, high_risk {pct(od['high_risk'], od['n'])}; "
          f"flagged {pct(od['flagged'], od['n'])} CI95 {od['flagged_ci95']}")
    for title, key in (('Scams by language', 'scam_by_lang'), ('Scams by category', 'scam_by_category'),
                       ('Scams by identifier', 'scam_by_ident'), ('Ordinary by language', 'ordinary_by_lang'),
                       ('Ordinary by category', 'ordinary_by_category')):
        print(f'\n{title}:')
        for k, v in summary[key].items():
            print(f"  {k:20} n={v['n']:3} high={v['high_risk']:3} caution={v['caution']:3} none={v['no_known_signals']:3}")
    lat = summary['latency_ms']
    print(f"\nLatency (pipeline latency_ms, text): p50 {lat['p50']} ms, p95 {lat['p95']} ms, max {lat['max']} ms, n={lat['n']}")
    print(f"Unchecked (final): {summary['unchecked_final']}  first attempt: {summary['unchecked_first_attempt']}  "
          f"retried rows: {summary['retried_rows']}  rows with a domain: {summary['rows_with_domains']}")
    print(f"Signal fire counts: {summary['signal_fire_counts']}")
    print('\nS1 what-if:  S1 | scam high / caution / missed | ordinary caution / high')
    for w, v in summary['what_if_s1'].items():
        print(f"  {w:>3} | {v['scam_high_risk']:3} / {v['scam_caution']:3} / {v['scam_missed']:3} | "
              f"{v['ord_caution']:3} / {v['ord_high_risk']:3}   +high: {v['scam_high_risk_ids_gained']}  ord high: {v['ord_high_risk_ids']}")
    print('\nMissed scams:')
    for r in summary['missed_scams']:
        print(f"  {r['id']:7} {r['category']:18} {r['ident']:10} score={r['score']:3} "
              f"{[(s['id'], s['points']) for s in r['signals']]} unchecked={r['unchecked']} s1={r['s1_diag']}")
    print('\nFlagged ordinary:')
    for r in summary['flagged_ordinary']:
        print(f"  {r['id']:7} {r['category']:18} {r['band']:10} score={r['score']:3} "
              f"{[(s['id'], s['points'], s['evidence'][:90]) for s in r['signals']]}")
    print(f"\nModel calls: {summary['meta']['model_calls_total']}  errors: {summary['meta']['model_errors']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limit', type=int, help='only the first N messages (smoke run)')
    parser.add_argument('--only', help='comma-separated message ids to (re)run')
    parser.add_argument('--concurrency', type=int, default=3)
    parser.add_argument('--max-attempts', type=int, default=3, help='attempts per message when the claims step fails')
    parser.add_argument('--env-file', type=Path, default=default_env_file())
    parser.add_argument('--out', type=Path, default=HERE / 'results.json')
    parser.add_argument('--merge', action='store_true', help='with --only: replace those rows in --out instead of overwriting it')
    parser.add_argument('--report', action='store_true', help='no model calls: summarize an existing results file')
    parser.add_argument('--compare', type=Path, help='another results file: print band and score agreement per message')
    args = parser.parse_args()
    if args.concurrency < 1 or args.concurrency > 3:
        parser.error('--concurrency must be 1 to 3')

    if args.report:
        data = json.loads(args.out.read_text(encoding='utf-8'))
        rows, meta = data['results'], data['meta']
    else:
        load_key(args.env_file)
        messages = load_messages(args.limit, set(args.only.split(',')) if args.only else None)
        rows, meta = asyncio.run(run_live(messages, args.concurrency, args.max_attempts))
        if args.merge and args.out.is_file():
            old = json.loads(args.out.read_text(encoding='utf-8'))
            fresh = {r['id']: r for r in rows}
            rows = [fresh.pop(r['id'], r) for r in old['results']] + list(fresh.values())
            meta = old['meta'] | {'reruns': old['meta'].get('reruns', []) + [meta]}
            meta['model_calls_total'] = old['meta'].get('model_calls_total', 0) + meta['reruns'][-1]['model_calls_total']
        order = {m['id']: i for i, m in enumerate(load_messages(None, None))}
        rows.sort(key=lambda r: order.get(r['id'], 10**6))
        args.out.write_text(json.dumps({'meta': meta, 'results': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'wrote {args.out}', flush=True)
    summary = summarize(rows, meta)
    args.out.with_suffix('.summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print_report(summary)
    if args.compare:
        compare(rows, json.loads(args.compare.read_text(encoding='utf-8'))['results'])


def compare(rows: list[dict], other: list[dict]) -> None:
    """Run-to-run stability: the score is a fixed formula, but its inputs (claims) come from the model."""
    theirs = {r['id']: r for r in other}
    pairs = [(r, theirs[r['id']]) for r in rows if r['id'] in theirs]
    same_band = sum(a['band'] == b['band'] for a, b in pairs)
    same_score = sum(a['score'] == b['score'] for a, b in pairs)
    print(f'\nStability vs other run: same band {pct(same_band, len(pairs))}, same score {pct(same_score, len(pairs))}')
    for label in ('scam', 'ordinary'):
        group = [(a, b) for a, b in pairs if a['label'] == label]
        print(f'  {label}: same band {pct(sum(a["band"] == b["band"] for a, b in group), len(group))}, '
              f'same score {pct(sum(a["score"] == b["score"] for a, b in group), len(group))}')
    for a, b in pairs:
        if a['band'] != b['band']:
            print(f"  band changed {a['id']:7} {b['band']}({b['score']}) -> {a['band']}({a['score']})  "
                  f"{[(s['id'], s['points']) for s in b['signals']]} -> {[(s['id'], s['points']) for s in a['signals']]}")


if __name__ == '__main__':
    main()
