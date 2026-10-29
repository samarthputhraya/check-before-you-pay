"""Load labelled synthetic checks without provider calls or invented usage numbers.

Run from the repo root: python -m seed.load
"""
from __future__ import annotations

import json
import time

from backend import db, language
from backend.config import ROOT, get_settings
from backend.extraction import Extraction, verified_extraction
from backend.links import identifiers, display_entities
from backend.schemas import CheckResponse, Share
from backend.signals import brokers, evaluate, score, signal
from backend import weights


def load() -> int:
    settings = get_settings()
    if len(brokers()) < 25:
        raise ValueError('At least 25 official domain records are required')
    rows = json.loads((ROOT / 'seed/messages/demo.json').read_text(encoding='utf-8'))
    loaded = 0
    for index, row in enumerate(rows):
        if '(sample)' not in row['label'] or '(sample)' not in row['text']:
            raise ValueError('Every seed item must be explicitly labelled (sample)')
        if db.get_check(settings.sqlite_path, row['id']) is not None:
            continue
        extracted = verified_extraction(Extraction.model_validate({'claims': row['claims']}), row['text'])
        records = identifiers(extracted)
        created = time.time() - len(rows) + index
        ring, _, _ = db.link_context(settings.sqlite_path, records, None, created)
        signals = evaluate(row['text'], extracted, {})
        if ring.via:
            signals.append(signal('S4', min(weights.S4_CAP, len(ring.via) * weights.S4_PER_TYPE),
                'Earlier sample checks', f'{ring.linked_checks} earlier sample checks linked (sample)'))
        total, band = score(signals)
        headline, explanation, steps = language.fallback(band, 'en', ['script_similarity'])
        headline += ' (sample)'
        base = settings.public_base_url or 'http://localhost:8000'
        result = CheckResponse(check_id=row['id'], band=band, score=total, lang='en',
            headline=headline, explanation=explanation + ' Synthetic demonstration (sample).',
            signals=signals, entities=display_entities(extracted), ring=ring, next_steps=steps,
            share=Share(url=f'{base}/c/{row["id"]}?ref=u_sample', card_title=headline),
            transcript=None, unchecked=['script_similarity'], cached=False, latency_ms=0)
        db.save_check(settings.sqlite_path, result, records, None, None, 'seed:' + row['id'],
                      'u_sample', 'text', created, sample=True)
        loaded += 1
    return loaded


if __name__ == '__main__':
    try:
        print(f'Loaded {load()} sample checks. Samples are excluded from usage totals.')
    except (ValueError, OSError) as exc:
        raise SystemExit('Seed load failed: ' + type(exc).__name__ + '. Check configuration and seed files.') from None
