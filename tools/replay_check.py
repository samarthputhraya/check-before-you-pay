"""Run one saved screenshot or voice note through the real check on a fresh, throwaway database, and print what the
model read (the transcript), the claims and the verdict.

    python tools/replay_check.py C:/Users/samar/Documents/cbyp-private/voice-tests/recording.m4a [--lang en]

For diagnosing a live result: the live site never stores transcripts, and sending the same file to it again returns
the cached verdict without one. Reads GEMINI_API_KEY (and OPENAI_API_KEY, if set) from .env or .env.railway in process,
never prints them, and loads no other setting, so no webhook, Telegram or payment call can happen. Keep the file
outside Git.
"""
import argparse, base64, json, os, secrets, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIMES = {'.m4a': 'audio/mp4', '.mp4': 'audio/mp4', '.ogg': 'audio/ogg', '.oga': 'audio/ogg', '.opus': 'audio/ogg',
         '.mp3': 'audio/mpeg', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
KEYS = ('GEMINI_API_KEY', 'OPENAI_API_KEY')
OFF = ('VIASOCKET_REPORT_WEBHOOK_URL', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_WEBHOOK_SECRET', 'DODO_API_KEY',
       'DODO_WEBHOOK_SECRET', 'PUBLIC_BASE_URL', 'PHISHTANK_FEED_PATH')


def load_keys():
    for name in ('.env', '.env.railway'):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() in KEYS and not os.environ.get(key.strip()):
                os.environ[key.strip()] = value.strip().strip('"\'')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('file', type=Path)
    parser.add_argument('--lang', default='en')
    args = parser.parse_args()
    mime = MIMES.get(args.file.suffix.lower())
    if not mime:
        sys.exit(f'Unsupported file type {args.file.suffix!r}. Use one of: {", ".join(sorted(MIMES))}')
    load_keys()
    if not os.environ.get('GEMINI_API_KEY'):
        sys.exit('GEMINI_API_KEY is not set, and is not in .env or .env.railway')
    # A fresh database: no earlier check can link to this one, and the cache can't answer instead of the model.
    os.environ['SQLITE_PATH'] = str(Path(tempfile.mkdtemp(prefix='cbyp-replay-')) / 'replay.db')
    os.environ['IDENTIFIER_SALT'] = secrets.token_hex(32)
    for key in OFF:
        os.environ.pop(key, None)
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from backend.app import app

    kind = 'audio' if mime.startswith('audio/') else 'image'
    data = base64.b64encode(args.file.read_bytes()).decode()
    body = {'lang': args.lang, 'anon_id': 'u_test_replay', 'input': {f'{kind}_b64': data, f'{kind}_mime': mime}}
    with TestClient(app) as client:
        response = client.post('/api/check', json=body)
    result = response.json()
    if response.status_code != 200:
        sys.exit(f'HTTP {response.status_code}: {json.dumps(result, ensure_ascii=False)}')
    print(f'{args.file.name} ({mime}, {args.file.stat().st_size:,} bytes)')
    print(f'verdict:     {result["band"]} {result["score"]}/100 in {result["latency_ms"] / 1000:.1f} s')
    print(f'unchecked:   {", ".join(result["unchecked"]) or "none"}')
    print(f'transcript:  {result["transcript"]!r}')
    print(f'explanation: {result["explanation"]}')
    for s in result['signals']:
        print(f'  {s["id"]} +{s["points"]} {s["label"]}: {s["evidence"]["text"]}')
    if not result['signals']:
        print('  no signals')


if __name__ == '__main__':
    main()
