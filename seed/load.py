"""Load labelled synthetic checks without provider calls or invented usage numbers.

Run from the repo root: python -m seed.load
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import TypeAdapter

from backend import db, language
from backend.config import ROOT, get_settings
from backend.extraction import Extraction, verified_extraction
from backend.links import identifiers, display_entities
from backend.schemas import CheckId, CheckResponse, Share
from backend.signals import brokers, evaluate, score, signal
from backend import weights


def read_messages(directory: Path) -> list[dict]:
    rows = []
    ids = set()
    for file in sorted(directory.glob('*.json')):
        payload = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(payload, list):
            raise ValueError('Seed files must contain an array of messages')
        for row in payload:
            if not isinstance(row, dict) or row.get('source') not in ('made_up', 'consented'):
                raise ValueError('Every seed needs an explicit source')
            if row['source'] == 'consented' and row.get('consent_to_use') is not True:
                raise ValueError('Real examples require explicit consent to use')
            if row['source'] == 'consented' and row.get('anonymized') is not True:
                raise ValueError('Real examples must be confirmed anonymized')
            if row['source'] == 'made_up' and any('(test, made up)' not in row.get(k, '') for k in ('label', 'text')):
                raise ValueError('Made-up messages must be labelled (test, made up)')
            if any('(sample)' not in row.get(k, '') for k in ('label', 'text')):
                raise ValueError('Every seed item must be explicitly labelled (sample)')
            TypeAdapter(CheckId).validate_python(row.get('id'))
            if row.get('id') in ids:
                raise ValueError('Seed IDs must be unique across all message files')
            if not isinstance(row.get('text'), str) or len(row['text']) > 5000:
                raise ValueError('Seed text must fit the input limit')
            # Verify every curated quote before writing anything to the database.
            claims = Extraction.model_validate({'claims': row.get('claims', [])})
            if len(verified_extraction(claims, row['text']).claims) != len(claims.claims):
                raise ValueError('Every seed claim needs a unique quote present in the message')
            ids.add(row['id'])
            rows.append(row)
    return rows


def load() -> int:
    settings = get_settings()
    if len(brokers()) < 25:
        raise ValueError('At least 25 official domain records are required')
    rows = read_messages(ROOT / 'seed/messages')
    loaded = 0
    for index, row in enumerate(rows):
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
        suffix = ' (test, made up) (sample)' if row['source'] == 'made_up' else ' (sample)'
        headline += suffix
        base = settings.public_base_url or 'http://localhost:8000'
        result = CheckResponse(check_id=row['id'], band=band, score=total, lang='en',
            headline=headline, explanation=explanation + suffix,
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
