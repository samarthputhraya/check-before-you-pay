"""Explicit, paid-provider benchmark using made-up inputs and temporary databases.

python -m backend.benchmark --audio data/validation/voice.ogg --output docs/benchmark-review.json
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import llm
from backend.app import app

TEXTS = [
    '(test, made up) (sample) Stock tips: 300% guaranteed. Pay sample@ybl for an institutional account.',
    '(test, made up) (sample) Crypto profits: send money to sample@ybl. Returns guaranteed.',
    '(test, made up) (sample) स्टॉक रिटर्न के लिए sample@ybl पर भुगतान करें। गारंटीड मुनाफ़ा।',
    '(test, made up) (sample) Pay for lunch to sample@ybl.',
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text-runs', type=int, default=20)
    parser.add_argument('--media-runs', type=int, default=5)
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--output', type=Path, default=Path('data/validation/benchmark.json'))
    args = parser.parse_args()
    if args.text_runs < 2 or args.media_runs < 2:
        parser.error('Use at least two samples per group for percentiles.')
    image = Image.new('RGB', (1150, 170), 'white')
    ImageDraw.Draw(image).text((15, 20), TEXTS[0], fill='black', font_size=18)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    media = {'image_b64': base64.b64encode(image_bytes.getvalue()).decode(), 'image_mime': 'image/png'}
    cases = [('text', 'hi' if i % 2 else 'en', {'text': TEXTS[i % len(TEXTS)]}) for i in range(args.text_runs)]
    cases += [('image', 'en', media) for _ in range(args.media_runs)]
    if args.audio:
        audio = {'audio_b64': base64.b64encode(args.audio.read_bytes()).decode(), 'audio_mime': 'audio/ogg'}
        cases += [('audio', 'en', audio) for _ in range(args.media_runs)]
    rows = []
    # Never write benchmark checks/events to the deployment database or send alerts.
    original_db = os.environ.get('SQLITE_PATH')
    original_webhook = os.environ.pop('VIASOCKET_REPORT_WEBHOOK_URL', None)
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os.environ['SQLITE_PATH'] = str(root / 'startup.db')
            startup = time.perf_counter()
            with TestClient(app) as client:
                startup_ms = round((time.perf_counter() - startup) * 1000)
                if not llm.providers.ready:
                    raise SystemExit('Model discovery failed; no live benchmark was run.')
                models = dict(llm.providers.models)
                for index, (kind, lang, inp) in enumerate(cases):
                    os.environ['SQLITE_PATH'] = str(root / f'case-{index}.db')
                    started = time.perf_counter()
                    response = client.post('/api/check', json={'lang': lang, 'anon_id': 'u_benchmark', 'input': inp})
                    value = response.json()
                    row = {'case': index + 1, 'input_type': kind, 'lang': lang, 'status': response.status_code,
                           'wall_ms': round((time.perf_counter() - started) * 1000), 'score': value.get('score'),
                           'unchecked': value.get('unchecked'), 'cached': value.get('cached', False)}
                    rows.append(row)
                    print(json.dumps(row), flush=True)
    finally:
        if original_db is None:
            os.environ.pop('SQLITE_PATH', None)
        else:
            os.environ['SQLITE_PATH'] = original_db
        if original_webhook is not None:
            os.environ['VIASOCKET_REPORT_WEBHOOK_URL'] = original_webhook
    summary = {}
    for kind in sorted({row['input_type'] for row in rows}):
        group = [row for row in rows if row['input_type'] == kind]
        times = [row['wall_ms'] for row in group]
        complete = [row['wall_ms'] for row in group if row['status'] == 200 and not row['unchecked']]
        summary[kind] = {'n': len(group), 'successes': sum(row['status'] == 200 for row in group),
                         'complete_risk_checks': len(complete),
                         'p50_ms': round(float(np.percentile(times, 50))),
                         'p95_ms': round(float(np.percentile(times, 95))), 'max_ms': max(times),
                         'complete_p50_ms': round(float(np.percentile(complete, 50))) if complete else None,
                         'complete_p95_ms': round(float(np.percentile(complete, 95))) if complete else None}
    artifact = {'measured_at': datetime.now(timezone.utc).isoformat(), 'models': models,
                'startup_ms': startup_ms, 'method': 'Sequential real Gemini calls through FastAPI TestClient; fresh temporary DB per case; no cache hits; made-up inputs. Local measurements, not phone/Railway acceptance.',
                'summary': summary, 'results': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SUMMARY ' + json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
