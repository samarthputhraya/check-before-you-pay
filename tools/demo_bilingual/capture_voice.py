"""Capture the real iPhone voice note (Risheeth, 30 Oct) checked in the English and the Hindi app, each on its own fresh
local server so the verdict stands alone. Adds 'vattached', 'vloading', 'vverdict' screens to cap/meta.json."""
import json, shutil, subprocess, sys, time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).parent))
from capture import OUT, PY, REPO, env_for, shot  # noqa: E402  (capture.py only captures when run directly)

VOICE = Path(sys.argv[1])
shutil.copy(VOICE, OUT / 'voice_note.mp4')
meta = json.loads((OUT / 'meta.json').read_text(encoding='utf-8'))
ports = {'en': 8103, 'hi': 8104}
servers = {l: subprocess.Popen([str(PY), '-m', 'uvicorn', 'backend.app:app', '--port', str(p), '--log-level', 'warning'],
                               cwd=REPO, env=env_for(l)) for l, p in ports.items()}
try:
    for l, p in ports.items():
        for _ in range(60):
            try:
                if httpx.get(f'http://127.0.0.1:{p}/api/health', timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        httpx.post(f'http://127.0.0.1:{p}/api/check', timeout=60, json={'lang': l, 'anon_id': 'u_test_demo_warm', 'input': {
            'text': 'Hi Priya, rent for November is ₹12,000. Please send it to priya.rent@okicici by the 5th.'}})
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome')
        for lang, port in ports.items():
            base = f'http://127.0.0.1:{port}'
            m = meta[lang]
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True,
                                      has_touch=True)
            ctx.add_init_script(f"localStorage.setItem('cbyp_lang', '{lang}'); "
                                f"localStorage.setItem('cbyp_anon_id', 'u_test_demo_voice_{lang}')")
            pg = ctx.new_page()
            pg.goto(base + '/'); pg.wait_for_selector('textarea'); pg.wait_for_timeout(500)
            pg.locator('.file-buttons input[type=file]').nth(1).set_input_files(str(OUT / 'voice_note.mp4'))
            pg.wait_for_selector('.attachment'); pg.wait_for_timeout(400)
            shot(pg, 'vattached', m, lang, submit='button.block', attachment='.attachment')
            with pg.expect_response(lambda r: r.url.endswith('/api/check') and r.request.method == 'POST',
                                    timeout=90000) as info:
                pg.click('button.block'); pg.wait_for_timeout(250)
                shot(pg, 'vloading', m, lang, submit='button.block')
            data = info.value.json()
            pg.wait_for_selector('#verdict-headline', timeout=90000); pg.wait_for_timeout(600)
            pg.click('details.transcript summary'); pg.wait_for_timeout(500)
            pg.evaluate('window.scrollTo(0, 0)')
            shot(pg, 'vverdict', m, lang, headline='#verdict-headline', signals='.signals', transcript='details.transcript',
                 last_signal='.signals li:last-child')
            m['checks']['voice'] = dict(check_id=data['check_id'], band=data['band'], score=data['score'],
                                        latency_ms=data['latency_ms'], transcript=data.get('transcript'),
                                        signals=[(s['id'], s['points'], s['label']) for s in data['signals']],
                                        explanation=data['explanation'], headline=data['headline'])
            print(lang, data['band'], data['score'], data['latency_ms'], 'ms |', data.get('transcript'), '|',
                  data['explanation'], flush=True)
            ctx.close()
        browser.close()
    (OUT / 'meta.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding='utf-8')
finally:
    for s in servers.values():
        s.terminate()
