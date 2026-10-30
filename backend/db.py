"""All SQLite access: WAL, parameterized SQL, bounded transactions, online backups."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np

from backend.ids import new_id
from backend.links import Embedding, Identifier, connected_groups, cosine
from backend.schemas import CheckResponse, CheckView, EventRequest, Ring, StatsResponse
from backend.weights import SCRIPT_SIMILARITY

SCHEMA = '''
CREATE TABLE IF NOT EXISTS checks (
 id TEXT PRIMARY KEY, created_at REAL NOT NULL, band TEXT NOT NULL, score INTEGER NOT NULL,
 lang TEXT NOT NULL, input_type TEXT NOT NULL, anon_id TEXT NOT NULL, script_id TEXT,
 response_json TEXT NOT NULL, input_hash TEXT NOT NULL, is_sample INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, masked TEXT NOT NULL, meta_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS check_entities (
 check_id TEXT NOT NULL REFERENCES checks(id), entity_id TEXT NOT NULL REFERENCES entities(id),
 PRIMARY KEY(check_id, entity_id));
CREATE INDEX IF NOT EXISTS by_entity ON check_entities(entity_id, check_id);
CREATE TABLE IF NOT EXISTS scripts (
 id TEXT PRIMARY KEY, embedding_blob BLOB NOT NULL, sample_count INTEGER NOT NULL, model TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS by_script ON checks(script_id);
CREATE TABLE IF NOT EXISTS reports (
 id TEXT PRIMARY KEY, check_id TEXT NOT NULL REFERENCES checks(id), created_at REAL NOT NULL,
 text_if_consented TEXT, anon_id TEXT NOT NULL, note TEXT,
 webhook_status TEXT NOT NULL DEFAULT 'pending', webhook_attempts INTEGER NOT NULL DEFAULT 0,
 webhook_after REAL NOT NULL DEFAULT 0, UNIQUE(check_id, anon_id));
CREATE TABLE IF NOT EXISTS cache (
 input_hash TEXT NOT NULL, lang TEXT NOT NULL, check_id TEXT NOT NULL REFERENCES checks(id),
 created_at REAL NOT NULL, PRIMARY KEY(input_hash, lang));
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, anon_id TEXT NOT NULL, event TEXT NOT NULL, check_id TEXT, ref TEXT,
 props_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS by_event ON events(event, created_at);
CREATE TABLE IF NOT EXISTS quiz_results (
 id TEXT PRIMARY KEY, anon_id TEXT NOT NULL, quiz_id TEXT NOT NULL, score INTEGER NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rate_limits (bucket TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS rate_bucket ON rate_limits(bucket, created_at);
CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dodo_payment_orders (
 payment_id TEXT NOT NULL, mode TEXT NOT NULL, order_id TEXT NOT NULL REFERENCES orders(id),
 PRIMARY KEY(payment_id, mode));
CREATE TABLE IF NOT EXISTS dodo_refunds (
 payment_id TEXT NOT NULL, mode TEXT NOT NULL, PRIMARY KEY(payment_id, mode));
CREATE TABLE IF NOT EXISTS orders (
 id TEXT PRIMARY KEY, plan TEXT NOT NULL, anon_id TEXT NOT NULL, session_id TEXT, status TEXT NOT NULL,
 mode TEXT NOT NULL, created_at REAL NOT NULL, paid_at REAL, dodo_ref TEXT);
CREATE TABLE IF NOT EXISTS dodo_webhooks (id TEXT PRIMARY KEY, type TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS orders_paid_by_anon ON orders(anon_id, status);
CREATE TABLE IF NOT EXISTS verdict_audio (
 check_id TEXT PRIMARY KEY REFERENCES checks(id), digest TEXT NOT NULL, mp3 BLOB NOT NULL);
'''

CACHE_REVISION = '2026-10-30-overnight'  # new S4 label, explanation script guard, claim definitions


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=0.25)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=250')
    con.execute('PRAGMA foreign_keys=ON')
    deadline = time.monotonic() + 1.8
    con.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    return con


@contextmanager
def session(path: Path) -> Iterator[sqlite3.Connection]:
    con = connect(path)
    try:
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


def ping(path: Path) -> bool:
    try:
        with session(path) as con:
            con.execute('BEGIN IMMEDIATE')
        return True
    except (sqlite3.Error, OSError):
        return False


def prepare_cache(path: Path) -> None:
    """Invalidate old verdicts once when scoring/extraction semantics change."""
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute("SELECT value FROM app_metadata WHERE key='cache_revision'").fetchone()
        if not row or row[0] != CACHE_REVISION:
            con.execute('DELETE FROM cache')
            con.execute("INSERT OR REPLACE INTO app_metadata VALUES ('cache_revision',?)", (CACHE_REVISION,))


def get_check(path: Path, check_id: str) -> CheckView | None:
    with session(path) as con:
        row = con.execute('SELECT response_json FROM checks WHERE id=?', (check_id,)).fetchone()
        return CheckView.model_validate_json(row[0]) if row else None


def cached_check(path: Path, key: str, lang: str, now: float | None = None) -> CheckView | None:
    with session(path) as con:
        row = con.execute('''SELECT c.response_json FROM cache k JOIN checks c ON c.id=k.check_id
                             WHERE k.input_hash=? AND k.lang=? AND k.created_at>?''',
                          (key, lang, (now or time.time()) - 86400)).fetchone()
        return CheckView.model_validate_json(row[0]) if row else None


def get_audio(path: Path, check_id: str, digest: str) -> bytes | None:
    with session(path) as con:
        row = con.execute('SELECT mp3 FROM verdict_audio WHERE check_id=? AND digest=?',
                          (check_id, digest)).fetchone()
        return bytes(row[0]) if row else None


def save_audio(path: Path, check_id: str, digest: str, mp3: bytes) -> None:
    with session(path) as con:
        con.execute('INSERT OR REPLACE INTO verdict_audio VALUES (?,?,?)', (check_id, digest, mp3))


def _ring(con: sqlite3.Connection, ids: list[str], before: float, exclude: str = '', script_id: str | None = None,
          input_hash: str | None = None) -> Ring:
    linked: dict[str, set[str]] = {}
    if ids:
        placeholders = ','.join('?' for _ in ids)
        rows = con.execute(f'''SELECT c.id,e.type FROM checks c JOIN check_entities ce ON ce.check_id=c.id
             JOIN entities e ON e.id=ce.entity_id WHERE e.id IN ({placeholders}) AND c.created_at<? AND c.id!=?
             AND (? IS NULL OR c.input_hash!=?)
             AND (c.band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                           (*ids, before, exclude, input_hash, input_hash)).fetchall()
        for row in rows:
            if row['type'] in ('upi', 'phone', 'domain', 'group_link', 'wallet'):
                linked.setdefault(row['id'], set()).add('same_' + row['type'])
    if script_id:
        rows = con.execute('''SELECT id FROM checks c WHERE script_id=? AND created_at<? AND id!=?
            AND (? IS NULL OR input_hash!=?)
            AND (band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                           (script_id, before, exclude, input_hash, input_hash)).fetchall()
        for row in rows:
            linked.setdefault(row['id'], set()).add('same_script')
    reports = 0
    if linked:
        reports = con.execute(f"SELECT COUNT(*) FROM reports WHERE check_id IN ({','.join('?' for _ in linked)})",
                              tuple(linked)).fetchone()[0]
    return Ring(linked_checks=len(linked), linked_reports=reports,
                via=sorted(set().union(*linked.values())) if linked else [])


def ring_for_check(path: Path, check_id: str) -> Ring:
    with session(path) as con:
        row = con.execute('SELECT created_at,script_id,input_hash FROM checks WHERE id=?', (check_id,)).fetchone()
        if not row:
            return Ring(linked_checks=0, linked_reports=0, via=[])
        ids = [r[0] for r in con.execute('SELECT entity_id FROM check_entities WHERE check_id=?', (check_id,))]
        return _ring(con, ids, row['created_at'], check_id, row['script_id'], row['input_hash'])


def link_context(path: Path, identifiers: list[Identifier], embedding: Embedding | None,
                 before: float, input_hash: str | None = None) -> tuple[Ring, str | None, int]:
    with session(path) as con:
        script_id = None
        count = 0
        if embedding:
            best = SCRIPT_SIMILARITY
            for row in con.execute('SELECT id,embedding_blob FROM scripts WHERE model=? ORDER BY id', (embedding.model,)):
                similarity = cosine(embedding.values, np.frombuffer(row['embedding_blob'], dtype='<f4').tolist())
                if similarity >= best:
                    best, script_id = similarity, row['id']
            if script_id:
                count = con.execute('''SELECT COUNT(*) FROM checks c WHERE script_id=? AND created_at<?
                    AND (? IS NULL OR input_hash!=?)
                    AND (band='high_risk' OR EXISTS(SELECT 1 FROM reports r WHERE r.check_id=c.id))''',
                                    (script_id, before, input_hash, input_hash)).fetchone()[0]
        return _ring(con, [i.id for i in identifiers], before, script_id=script_id, input_hash=input_hash), script_id, count


def save_check(path: Path, result: CheckResponse, identifiers: list[Identifier], embedding: Embedding | None,
               script_id: str | None, key: str, anon_id: str, input_type: str, created: float,
               ref: str | None = None, sample: bool = False) -> None:
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if embedding:
            script_id = script_id or new_id('scr')
            vector = np.asarray(embedding.values, dtype='<f4')
            if vector.ndim != 1 or not vector.size or not np.isfinite(vector).all():
                raise ValueError('Invalid embedding')
            con.execute('''INSERT INTO scripts(id,embedding_blob,sample_count,model) VALUES (?,?,1,?)
                ON CONFLICT(id) DO UPDATE SET sample_count=sample_count+1''',
                        (script_id, vector.tobytes(), embedding.model))
        elif result.cached:
            source = con.execute('SELECT c.script_id FROM cache k JOIN checks c ON c.id=k.check_id WHERE k.input_hash=? AND k.lang=?',
                                 (key, result.lang)).fetchone()
            script_id = source[0] if source else None
        con.execute('''INSERT INTO checks
                    (id,created_at,band,score,lang,input_type,anon_id,script_id,response_json,input_hash,is_sample)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (result.check_id, created, result.band, result.score, result.lang, input_type, anon_id,
                     script_id, result.model_dump_json(exclude={'transcript'}), key, int(sample)))
        for entity in identifiers:
            con.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?,?)',
                        (entity.id, entity.type, entity.masked, json.dumps(entity.meta)))
            con.execute('INSERT OR IGNORE INTO check_entities VALUES (?,?)', (result.check_id, entity.id))
        if result.cached:
            con.execute('''INSERT OR IGNORE INTO check_entities SELECT ?,ce.entity_id FROM cache k
                JOIN check_entities ce ON ce.check_id=k.check_id WHERE k.input_hash=? AND k.lang=?''',
                        (result.check_id, key, result.lang))
        # Hits do not refresh TTL. Partial failures must not become a 24-hour answer.
        if not result.cached and not result.unchecked and not sample:
            con.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?,?)', (key, result.lang, result.check_id, created))
        if not sample:
            _event(con, EventRequest(anon_id=anon_id, event='check_done', check_id=result.check_id, ref=ref,
                                    props={'latency_ms': result.latency_ms, 'band': result.band,
                                           'lang': result.lang, 'input_type': input_type}), created)


def entity_history(path: Path, entity_id: str) -> list[dict]:
    with session(path) as con:
        return [dict(r) for r in con.execute('''SELECT c.id,c.created_at,c.band,c.score,
            (SELECT COUNT(*) FROM reports r WHERE r.check_id=c.id) AS reports
            FROM checks c JOIN check_entities ce ON ce.check_id=c.id WHERE ce.entity_id=? ORDER BY c.created_at''', (entity_id,))]


def add_report(path: Path, check_id: str, anon_id: str, text: str | None, note: str | None,
               webhook_enabled: bool = True) -> tuple[str, bool, bool]:
    """Returns (report_id, created, text_saved); a repeat report answers with what the first one stored."""
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('SELECT 1 FROM checks WHERE id=?', (check_id,)).fetchone():
            raise KeyError(check_id)
        existing = con.execute('SELECT id, text_if_consented IS NOT NULL FROM reports WHERE check_id=? AND anon_id=?',
                               (check_id, anon_id)).fetchone()
        if existing:
            return existing[0], False, bool(existing[1])
        report_id = new_id('rep')
        con.execute('''INSERT INTO reports(id,check_id,created_at,text_if_consented,anon_id,note,webhook_status)
                       VALUES (?,?,?,?,?,?,?)''',
                    (report_id, check_id, time.time(), text, anon_id, note, 'pending' if webhook_enabled else 'skipped'))
        con.execute('DELETE FROM cache')  # New reports change the available evidence.
        _event(con, EventRequest(anon_id=anon_id, event='report', check_id=check_id), time.time())
        return report_id, True, text is not None


def save_quiz_result(path: Path, anon_id: str, quiz_id: str, lang: str, score: int) -> str:
    """One row per finished quiz plus the authoritative quiz_done; a later quiz_shared counts only after this."""
    now = time.time()
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        result_id = new_id('qzr')
        con.execute('INSERT INTO quiz_results VALUES (?,?,?,?,?)', (result_id, anon_id, quiz_id, score, now))
        _event(con, EventRequest(anon_id=anon_id, event='quiz_done', props={'score': score, 'lang': lang}), now)
        return result_id


def _event(con: sqlite3.Connection, body: EventRequest, now: float) -> None:
    props = {k: v for k, v in body.props.items() if k in ('latency_ms', 'band', 'lang', 'input_type', 'score', 'plan')}
    con.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                (new_id('evt'), body.anon_id, body.event, body.check_id, body.ref, json.dumps(props), now))


def record_event(path: Path, body: EventRequest) -> None:
    if body.event in ('check_done', 'report', 'quiz_done', 'checkout_started', 'checkout_paid'):
        return  # These are authoritative server events; ignore client copies.
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if body.event == 'share_clicked':
            if not con.execute('SELECT 1 FROM checks WHERE id=? AND anon_id=? AND is_sample=0',
                               (body.check_id, body.anon_id)).fetchone():
                return
            if con.execute("SELECT 1 FROM events WHERE event='share_clicked' AND anon_id=? AND check_id=?",
                           (body.anon_id, body.check_id)).fetchone():
                return
        if body.event == 'quiz_shared' and not con.execute(
                'SELECT 1 FROM quiz_results WHERE anon_id=?', (body.anon_id,)).fetchone():
            return
        if body.event in ('visit', 'ref_visit', 'return_visit', 'pricing_view') and con.execute(
                'SELECT 1 FROM events WHERE anon_id=? AND event=? AND created_at>? LIMIT 1',
                (body.anon_id, body.event, time.time() - 3600)).fetchone():
            return
        _event(con, body, time.time())


def allow_request(path: Path, buckets: list[tuple[str, int]], now: float | None = None) -> bool:
    now = now or time.time()
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM rate_limits WHERE created_at<=?', (now - 3600,))
        for bucket, limit in buckets:
            if con.execute('SELECT COUNT(*) FROM rate_limits WHERE bucket=?', (bucket,)).fetchone()[0] >= limit:
                return False
        con.executemany('INSERT INTO rate_limits VALUES (?,?)', [(b, now) for b, _ in buckets])
        return True


def top_rings(path: Path, k: int | None = 10, include_samples: bool = False) -> list[list[str]]:
    with session(path) as con:
        con.execute('BEGIN')  # One WAL snapshot across the node and edge reads.
        # Rechecking one forward cannot create a ring in the public totals.
        # Fold its copies into one node, retaining all discovered entity edges.
        representatives: dict[str, str] = {}
        nodes: dict[str, str] = {}
        for row in con.execute('''SELECT id,input_hash FROM checks WHERE band='high_risk'
                AND (? OR is_sample=0) ORDER BY created_at,id''', (include_samples,)):
            nodes[row['id']] = representatives.setdefault(row['input_hash'], row['id'])
        rows = con.execute('''SELECT c.id,ce.entity_id FROM checks c JOIN check_entities ce ON ce.check_id=c.id
            JOIN entities e ON e.id=ce.entity_id WHERE c.band='high_risk' AND (? OR c.is_sample=0)
            AND e.type IN ('upi','phone','domain','group_link','wallet')''', (include_samples,)).fetchall()
        scripts = con.execute("SELECT id,'script:'||script_id FROM checks WHERE band='high_risk' AND script_id IS NOT NULL AND (? OR is_sample=0)",
                              (include_samples,)).fetchall()
        return connected_groups([(nodes[r[0]], r[1]) for r in [*rows, *scripts]], k)


def stats(path: Path, dodo_mode: str = 'test_mode') -> StatsResponse:
    with session(path) as con:
        # Only the current Dodo mode: once live, test-mode payments never count as paid orders.
        orders_paid = con.execute("SELECT COUNT(*) FROM orders WHERE status='paid' AND mode=?", (dodo_mode,)).fetchone()[0]
        checks = con.execute('SELECT id,anon_id,lang,response_json FROM checks WHERE is_sample=0').fetchall()
        users = {r['anon_id'] for r in checks}
        users.update(r[0] for r in con.execute('SELECT DISTINCT anon_id FROM events'))
        languages: dict[str, int] = {}
        latencies = []
        for row in checks:
            languages[row['lang']] = languages.get(row['lang'], 0) + 1
            latencies.append(json.loads(row['response_json'])['latency_ms'])
        reports = con.execute('SELECT COUNT(*) FROM reports r JOIN checks c ON c.id=r.check_id WHERE c.is_sample=0').fetchone()[0]
        shared = con.execute("SELECT COUNT(DISTINCT e.check_id) FROM events e JOIN checks c ON c.id=e.check_id WHERE e.event='share_clicked' AND c.is_sample=0").fetchone()[0]
        sharers = {r[0] for r in con.execute("SELECT DISTINCT anon_id FROM events WHERE event IN ('share_clicked','quiz_shared')")}
        # Credit the source that first brought a user. A returning user clicking
        # another share is not a newly acquired user, and can't inflate k-factor.
        first_touches = con.execute('''SELECT anon_id,ref FROM (
            SELECT anon_id,ref,ROW_NUMBER() OVER (PARTITION BY anon_id ORDER BY created_at,rowid) AS position
            FROM events) WHERE position=1''')
        referred = {r[0] for r in first_touches if r[1] in sharers and r[0] != r[1]}
        quiz_plays = con.execute('SELECT COUNT(*) FROM quiz_results').fetchone()[0]
    return StatsResponse(users=len(users), checks=len(checks), reports=reports, languages=languages,
                         rings=len(top_rings(path, None)), share_rate=shared / len(checks) if checks else 0,
                         k_factor=len(referred) / len(sharers) if sharers else 0,
                         p50_ms=int(np.percentile(latencies, 50)) if latencies else 0,
                         p95_ms=int(np.percentile(latencies, 95)) if latencies else 0,
                         quiz_plays=quiz_plays, orders_paid=orders_paid,
                         updated_at=datetime.now(timezone.utc).isoformat())


def pending_webhooks(path: Path) -> list[dict]:
    with session(path) as con:
        return [dict(r) for r in con.execute('''SELECT id,check_id FROM reports WHERE webhook_status='pending'
            AND webhook_attempts<3 AND webhook_after<=? ORDER BY created_at LIMIT 10''', (time.time(),))]


def webhook_result(path: Path, report_id: str, delivered: bool) -> None:
    with session(path) as con:
        con.execute('''UPDATE reports SET webhook_attempts=webhook_attempts+1,
            webhook_status=CASE WHEN ? THEN 'delivered' WHEN webhook_attempts>=2 THEN 'failed' ELSE 'pending' END,
            webhook_after=? WHERE id=?''', (delivered, time.time() + 60, report_id))


def create_order(path: Path, plan: str, anon_id: str, mode: str) -> str:
    order_id = new_id('ord')
    with session(path) as con:
        con.execute("INSERT INTO orders(id,plan,anon_id,status,mode,created_at) VALUES (?,?,?,'pending',?,?)",
                    (order_id, plan, anon_id, mode, time.time()))
    return order_id


def start_order(path: Path, order_id: str, session_id: str, anon_id: str, plan: str) -> None:
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('UPDATE orders SET session_id=? WHERE id=?', (session_id, order_id))
        _event(con, EventRequest(anon_id=anon_id, event='checkout_started', props={'plan': plan}), time.time())


def fail_order(path: Path, order_id: str) -> None:
    with session(path) as con:
        con.execute("UPDATE orders SET status='failed' WHERE id=? AND status='pending'", (order_id,))


def has_paid_order(path: Path, anon_id: str) -> bool:
    with session(path) as con:
        return con.execute("SELECT 1 FROM orders WHERE anon_id=? AND status='paid' LIMIT 1", (anon_id,)).fetchone() is not None


def get_order(path: Path, order_id: str) -> dict | None:
    with session(path) as con:
        row = con.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        return dict(row) if row else None


def apply_dodo_event(path: Path, webhook_id: str, kind: str, order_id: str | None, status: str | None,
                     dodo_ref: str | None, payment_id: str | None = None) -> str:
    """Record a verified Dodo webhook exactly once. Refunded is final; failed only replaces pending,
    so a late payment.failed from a declined first card can't undo the retry that succeeded."""
    now = time.time()
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        fresh = con.execute('INSERT OR IGNORE INTO dodo_webhooks VALUES (?,?,?)', (webhook_id, kind, now)).rowcount
        if status == 'paid' and payment_id:
            con.execute('''INSERT OR IGNORE INTO dodo_payment_orders
                SELECT ?,mode,id FROM orders WHERE id=?''', (payment_id, order_id))
            if con.execute('''SELECT 1 FROM dodo_refunds r JOIN orders o ON o.mode=r.mode
                              WHERE o.id=? AND r.payment_id=?''', (order_id, payment_id)).fetchone():
                con.execute("UPDATE orders SET status='refunded',dodo_ref=? WHERE id=?", (payment_id, order_id))
                return 'refunded'
        if not fresh:
            return 'duplicate'
        if status == 'paid' and con.execute('''UPDATE orders SET status='paid',paid_at=?,dodo_ref=COALESCE(?,dodo_ref)
                WHERE id=? AND status IN ('pending','failed') ''', (now, dodo_ref, order_id)).rowcount:
            row = con.execute('SELECT anon_id,plan FROM orders WHERE id=?', (order_id,)).fetchone()
            _event(con, EventRequest(anon_id=row['anon_id'], event='checkout_paid', props={'plan': row['plan']}), now)
            return 'paid'
        if status == 'failed' and con.execute('''UPDATE orders SET status='failed',dodo_ref=COALESCE(?,dodo_ref)
                WHERE id=? AND status='pending' ''', (dodo_ref, order_id)).rowcount:
            return 'failed'
        return 'unchanged'


def apply_dodo_refund(path: Path, webhook_id: str, payment_id: str, mode: str) -> str:
    """Called only after signature verification; refund metadata cannot select an order."""
    with session(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('INSERT OR IGNORE INTO dodo_webhooks VALUES (?,?,?)',
                           (webhook_id, 'refund.succeeded', time.time())).rowcount:
            return 'duplicate'
        con.execute('INSERT OR IGNORE INTO dodo_refunds VALUES (?,?)', (payment_id, mode))
        changed = con.execute('''UPDATE orders SET status='refunded' WHERE status='paid' AND mode=? AND
            (id IN (SELECT order_id FROM dodo_payment_orders WHERE payment_id=? AND mode=?)
             OR dodo_ref=?)''', (mode, payment_id, mode, payment_id)).rowcount
        return 'refunded' if changed else 'refund recorded'


def export_database(path: Path) -> bytes:
    with session(path) as source:
        with sqlite3.connect(':memory:') as target:
            source.backup(target)
            return target.serialize()
