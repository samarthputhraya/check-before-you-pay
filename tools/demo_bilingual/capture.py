"""Capture phase of the bilingual demo: real checks on two fresh local servers (English and Hindi), full-page phone
screenshots at 3x, element positions, latencies and the verdicts' own Listen audio. Writes into ./cap/."""
import json, os, secrets, subprocess, sys, tempfile, time
from pathlib import Path
import asyncio
import httpx
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / 'cap'
OUT.mkdir(exist_ok=True)
PY = REPO / '.venv' / 'Scripts' / 'python.exe'

PERSONAS = {
    'en': dict(port=8101,
        first='(sample) 🔥 VIP Stock Tips 🔥 Guaranteed 30% returns every month. Open your institutional account today: '
              'send ₹50,000 to wealthpro.desk@ybl and install our app from groww-pro-vip.in. Only 3 seats left!',
        second='(sample) Bank Nifty jackpot call tomorrow, 40% up guaranteed. Join our premium group: pay ₹4,999 to '
               'wealthpro.desk@ybl today.'),
    'hi': dict(port=8102,
        first='(नमूना) 🔥 VIP Stock Tips ग्रुप 🔥 हर महीने 30% पक्का मुनाफ़ा। इंस्टीट्यूशनल अकाउंट खोलने के लिए आज ही ₹50,000 '
              'tradepro.desk@ybl पर भेजें और ऐप यहाँ से डाउनलोड करें: kite-zerodha-pro.in. सिर्फ़ 3 सीटें बची हैं!',
        second='(नमूना) कल Bank Nifty में 40% उछाल पक्का। प्रीमियम ग्रुप जॉइन करने के लिए आज ही ₹4,999 tradepro.desk@ybl पर भेजें।'),
}


def env_for(lang):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('VIASOCKET', 'TELEGRAM', 'DODO', 'PUBLIC_BASE'))}
    for line in (REPO / '.env.railway').read_text(encoding='utf-8').splitlines():
        k, _, v = line.partition('=')
        if k.strip() == 'GEMINI_API_KEY':
            env['GEMINI_API_KEY'] = v.strip()
    env['SQLITE_PATH'] = str(Path(tempfile.mkdtemp(prefix=f'cbyp-demo-{lang}-')) / 'app.db')
    env['IDENTIFIER_SALT'] = secrets.token_hex(32)
    return env


def speak(base, check_id, lang):
    """The Listen button's own speech (same text, model and voice), without the server's 8 s limit, which the hotel
    Wi-Fi keeps hitting from this laptop. The live server answers in about 7 s."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
        os.environ['GEMINI_API_KEY'] = env_for('x')['GEMINI_API_KEY']
    from backend import audio, llm
    view = httpx.get(f'{base}/api/check/{check_id}', timeout=30).json()
    text = chr(10).join([view['headline'], view['explanation']] + [s['text'] for s in view['next_steps'][:1]])
    text = audio._MASKED_UPI.sub(audio.SPOKEN_UPI.get(lang, audio.SPOKEN_UPI['en']), text)
    async def go():
        return await audio.encode_mp3(await llm.tts(text))
    return asyncio.run(go())


def box(page, selector):
    return page.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null;
        const r = e.getBoundingClientRect(); return {x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height}; }""", selector)


def shot(page, name, meta, lang, **boxes):
    path = OUT / f'{lang}_{name}.png'
    page.screenshot(path=str(path), full_page=True)
    meta[name] = dict(file=path.name, height=page.evaluate('document.documentElement.scrollHeight'),
                      boxes={k: box(page, v) for k, v in boxes.items()})


servers = {}
for lang, p in PERSONAS.items():
    servers[lang] = subprocess.Popen([str(PY), '-m', 'uvicorn', 'backend.app:app', '--port', str(p['port']),
                                      '--log-level', 'warning'], cwd=REPO, env=env_for(lang))
try:
    for lang, p in PERSONAS.items():
        for _ in range(60):
            try:
                if httpx.get(f'http://127.0.0.1:{p["port"]}/api/health', timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        # Warm the model connection with an ordinary request that shares nothing with the demo messages, so the
        # recorded times are warm ones (it can't link: only high-risk or reported checks link).
        warm = httpx.post(f'http://127.0.0.1:{p["port"]}/api/check', timeout=60, json={
            'lang': lang, 'anon_id': 'u_test_demo_warm',
            'input': {'text': 'Hi Priya, rent for November is ₹12,000. Please send it to priya.rent@okicici by the 5th.'}})
        print(lang, 'warm-up', warm.json().get('band'), warm.json().get('latency_ms'), flush=True)
    result = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome')
        for lang, p in PERSONAS.items():
            base = f'http://127.0.0.1:{p["port"]}'
            meta = {'checks': {}}
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True,
                                      has_touch=True, locale='hi-IN' if lang == 'hi' else 'en-IN')
            ctx.add_init_script(f"localStorage.setItem('cbyp_lang', '{lang}'); "
                                f"localStorage.setItem('cbyp_anon_id', 'u_test_demo_{lang}')")
            pg = ctx.new_page()
            pg.goto(base + '/'); pg.wait_for_selector('textarea'); pg.wait_for_timeout(600)
            shot(pg, 'home', meta, lang, textarea='textarea', submit='button.block')
            for n, key in ((1, 'first'), (2, 'second')):
                if n == 2:
                    pg.click('.actions .button.secondary'); pg.wait_for_selector('textarea')
                pg.fill('textarea', p[key]); pg.evaluate('document.activeElement.blur()'); pg.wait_for_timeout(300)
                pg.evaluate('window.scrollTo(0, 0)')
                shot(pg, f'filled{n}', meta, lang, textarea='textarea', submit='button.block')
                with pg.expect_response(lambda r: r.url.endswith('/api/check') and r.request.method == 'POST',
                                        timeout=60000) as info:
                    pg.click('button.block')
                    pg.wait_for_timeout(250)
                    shot(pg, f'loading{n}', meta, lang, submit='button.block')
                data = info.value.json()
                pg.wait_for_selector('#verdict-headline', timeout=60000); pg.wait_for_timeout(700)
                pg.evaluate('window.scrollTo(0, 0)')
                meta['checks'][key] = dict(check_id=data['check_id'], band=data['band'], score=data['score'],
                                           latency_ms=data['latency_ms'], ring=data['ring'], signals=[
                                               (s['id'], s['points'], s['label']) for s in data['signals']],
                                           explanation=data['explanation'], share=data['share']['url'], headline=data['headline'])
                shot(pg, f'verdict{n}', meta, lang, card='.verdict', headline='#verdict-headline', listen='.listen button',
                     signals='.signals', last_signal='.signals li:last-child', ring='.ring', share='.actions .button.primary',
                     another='.actions .button.secondary')
                print(lang, key, data['band'], data['score'], data['latency_ms'], 'ms', data['ring'], flush=True)
                if n == 1:
                    for attempt in range(2):
                        audio = httpx.get(f'{base}/api/check/{data["check_id"]}/audio', timeout=60)
                        if audio.status_code == 200:
                            break
                        print(lang, 'audio retry', audio.status_code, audio.text[:120], flush=True)
                        time.sleep(4)
                    mp3 = audio.content if audio.status_code == 200 else speak(base, data['check_id'], lang)
                    (OUT / f'{lang}_listen.mp3').write_bytes(mp3)
                    print(lang, 'audio', audio.status_code, len(mp3), flush=True)
                    pg.click('.listen button'); pg.wait_for_timeout(2500)
                    shot(pg, 'listen', meta, lang, listen='.listen button')
                    pg.click('.listen button'); pg.wait_for_timeout(400)
            share_url = meta['checks']['first']['share'].split('?')[0]
            share_url = base + share_url[share_url.index('/c/'):]
            pg.goto(share_url); pg.wait_for_selector('.verdict'); pg.wait_for_timeout(800)
            shot(pg, 'share', meta, lang)
            pg.goto(base + '/quiz'); pg.wait_for_selector('.quiz-question'); pg.wait_for_timeout(800)
            shot(pg, 'quiz1', meta, lang, scam='.quiz-actions .button.secondary', question='.quiz-question')
            pg.click('.quiz-actions .button.secondary'); pg.wait_for_timeout(900)
            shot(pg, 'quiz2', meta, lang, question='.quiz-question')
            result[lang] = meta
            ctx.close()
        browser.close()
    (OUT / 'meta.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
    (OUT / 'qr.png').write_bytes((REPO / 'docs' / 'qr-live.png').read_bytes())
    (OUT / 'icon.svg').write_bytes((REPO / 'web' / 'icon.svg').read_bytes())
    print('done')
finally:
    for s in servers.values():
        s.terminate()
