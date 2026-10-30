"""Record a narrated demo video of the app: phone-sized screen capture with Playwright, an English voice-over made
with Gemini TTS, captions, the verdict's own Hindi audio, and all of it muxed into an MP4 with ffmpeg.

    python tools/demo_video.py https://34-45-129-243.sslip.io out_dir

Needs Playwright with Chrome, ffmpeg (on PATH, or FFMPEG=...), httpx and mutagen, and GEMINI_API_KEY in .env.railway
(read in process, never printed). Record right after a stats reset, or against a fresh local database: an earlier run of
the same messages links the first check to it, and the story needs the first check to stand alone.
"""
import json, os, shutil, subprocess, sys, threading, time, wave
import httpx
from mutagen.mp3 import MP3
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1], Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
FFMPEG = os.environ.get('FFMPEG') or shutil.which('ffmpeg') or 'ffmpeg'
ENV_FILE = Path(__file__).resolve().parents[1] / '.env.railway'
SUNITA = ('(नमूना) 🔥 VIP Stock Tips ग्रुप 🔥 हर महीने 30% पक्का मुनाफ़ा। इंस्टीट्यूशनल अकाउंट खोलने के लिए आज ही ₹50,000 '
          'tradepro.desk@ybl पर भेजें और ऐप यहाँ से डाउनलोड करें: kite-zerodha-pro.in. सिर्फ़ 3 सीटें बची हैं!')
SECOND = '(sample) Bank Nifty jackpot call kal 40% upar jayega. Premium group join karne ke liye ₹4,999 tradepro.desk@ybl pe bhejo.'

# (caption on screen, narration). Each scene's narration length sets how long the scene is held.
SCENES = [
    ('Sunita, 52, Pune, gets this in a WhatsApp "VIP" group',
     'Sunita, fifty two, from Pune, was added to a VIP stock tips group on WhatsApp. They want fifty thousand rupees for an institutional account.'),
    ('She checks it in Hindi before paying',
     'Before she pays, she pastes the message into Check Before You Pay, in Hindi.'),
    ('High risk, with the evidence',
     'High risk. The UPI ID is not a SEBI at-valid handle. The app link copies Zerodha. And here is the exact line where they promise thirty percent a month.'),
    ('Fixed checks decide the score; the AI only reads and explains',
     'The AI did not decide this score. Fixed checks did, and every point shows its proof.'),
    ('One tap reads it aloud, in Hindi',
     'And one tap reads it aloud, in Hindi, for anyone who would rather listen.'),
    ('A new message, a new group, the same UPI ID',
     'The next day, a different group sends a different message. Same UPI ID.'),
    ('Linked to the earlier check: scammers change scripts, not where the money goes',
     'It is linked to the earlier check. Scammers change their scripts every day. They cannot hide where the money goes.'),
    ('One tap sends this page to the family group',
     'One tap sends the verdict to the family group, in their language.'),
    ('Spot the scam: a quiz families share',
     'And a quiz that families share, in four languages.'),
    ('Measured on 128 messages we never tuned on',
     'On a hundred and twenty eight test messages we never tuned on, it flagged sixty one of sixty four scams, and none of the ordinary payments.'),
]


def tts(text: str, path: Path) -> float:
    if not path.exists():
        for l in open(ENV_FILE, encoding='utf-8'):
            if l.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = l.split('=', 1)[1].strip()
        from google import genai
        from google.genai import types
        global CLIENT
        if 'CLIENT' not in globals():
            CLIENT = genai.Client()
        r = CLIENT.models.generate_content(model='gemini-3.8-flash-tts', contents=text, config=types.GenerateContentConfig(
            response_modalities=['AUDIO'], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')))))
        pcm = r.candidates[0].content.parts[0].inline_data.data
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


durations = [tts(n, OUT / f'scene{i}.wav') + 0.6 for i, (_, n) in enumerate(SCENES)]
print('narration seconds:', [round(d, 1) for d in durations], 'total', round(sum(durations), 1))

CAPTION_JS = """(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) { el = document.createElement('div'); el.id = 'demo-caption'; document.body.appendChild(el);
    Object.assign(el.style, {position: 'fixed', left: '10px', right: '10px', bottom: '14px', zIndex: 9999, padding: '10px 12px',
      background: 'rgba(22,32,27,0.92)', color: '#fff', font: '600 15px/1.35 system-ui, sans-serif', borderRadius: '10px'}); }
  el.textContent = text; }"""

marks = []
SHARE_URL = []
CLIP = {}  # the verdict's own Hindi audio, fetched while the evidence scenes play so the tap is instant
CLIP_MAX = 9.0
END_SLATE_JS = """() => {
  const d = document.createElement('div');
  Object.assign(d.style, {position: 'fixed', inset: '0', zIndex: 9998, background: '#0b6839', color: '#fff', display: 'flex',
    flexDirection: 'column', justifyContent: 'center', padding: '32px', font: '600 20px/1.4 system-ui, sans-serif', gap: '18px'});
  d.innerHTML = '<div style="font-size:30px;font-weight:800">Check Before You Pay</div>' +
    '<div><span style="font-size:44px;font-weight:800">61 / 64</span><br>scam messages flagged</div>' +
    '<div><span style="font-size:44px;font-weight:800">0 / 64</span><br>ordinary payments flagged</div>' +
    '<div>8 languages · about 3 seconds a check</div>' +
    '<div style="font-size:16px;opacity:.85">Held-out test set, 30 Oct 2026. docs/EVAL.md</div>' +
    '<div style="font-size:18px">34-45-129-243.sslip.io</div>';
  document.body.appendChild(d); }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, record_video_dir=str(OUT / 'raw'),
                        record_video_size={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script("localStorage.setItem('cbyp_lang', 'hi')")
    pg = ctx.new_page()
    t0 = time.monotonic()

    def scene(i):
        pg.evaluate(CAPTION_JS, SCENES[i][0]); marks.append(time.monotonic() - t0)

    def hold(i, started):
        left = durations[i] - (time.monotonic() - started)
        if left > 0: pg.wait_for_timeout(int(left * 1000))

    pg.goto(BASE + '/'); pg.wait_for_selector('textarea')
    s = time.monotonic(); scene(0); pg.fill('textarea', SUNITA); hold(0, s)
    s = time.monotonic(); scene(1)
    with pg.expect_response(lambda r: r.url.endswith('/api/check') and r.request.method == 'POST', timeout=30000) as first:
        pg.click('button.block')
    check_id = first.value.json()['check_id']
    threading.Thread(target=lambda: CLIP.update(mp3=httpx.get(f'{BASE}/api/check/{check_id}/audio', timeout=40).content)).start()
    pg.wait_for_selector('#verdict-headline', timeout=30000); hold(1, s)
    s = time.monotonic(); scene(2); pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(3500)
    pg.evaluate("document.querySelector('.signals').scrollIntoView({block: 'start', behavior: 'smooth'})"); hold(2, s)
    s = time.monotonic(); scene(3); pg.evaluate("document.querySelector('.signals li:last-child').scrollIntoView({block: 'center', behavior: 'smooth'})"); hold(3, s)
    s = time.monotonic(); pg.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})"); scene(4); hold(4, s)
    for _ in range(60):
        if 'mp3' in CLIP: break
        pg.wait_for_timeout(500)
    (OUT / 'verdict.mp3').write_bytes(CLIP['mp3'])
    clip_len = min(CLIP_MAX, MP3(str(OUT / 'verdict.mp3')).info.length)
    pg.click('.listen button'); CLIP['at'] = time.monotonic() - t0
    pg.wait_for_timeout(int(clip_len * 1000) + 400)
    pg.click('.listen button')  # stop, so the page matches the audio
    s = time.monotonic(); scene(5); pg.click('.actions .button.secondary'); pg.wait_for_selector('textarea'); pg.fill('textarea', SECOND)
    with pg.expect_response(lambda r: r.url.endswith('/api/check') and r.request.method == 'POST', timeout=30000) as info:
        pg.click('button.block')
    SHARE_URL.append(info.value.json()['share']['url'].replace('https://34-45-129-243.sslip.io', BASE))
    pg.wait_for_selector('#verdict-headline', timeout=30000); hold(5, s)
    s = time.monotonic(); scene(6)
    pg.evaluate("(document.querySelector('.ring') || document.body).scrollIntoView({block: 'center', behavior: 'smooth'})"); hold(6, s)
    s = time.monotonic()
    pg.goto(SHARE_URL[0] if SHARE_URL else BASE + '/c/chk_sample02'); pg.wait_for_selector('.verdict'); scene(7); hold(7, s)
    s = time.monotonic(); pg.goto(BASE + '/quiz'); pg.wait_for_selector('.quiz-question'); scene(8); hold(8, s)
    s = time.monotonic(); scene(9); pg.evaluate(END_SLATE_JS); hold(9, s)
    pg.wait_for_timeout(1200)
    video = pg.video.path()
    ctx.close(); b.close()

print('scene marks (s):', [round(m, 1) for m in marks])
# Narration track: each scene's clip placed at its mark.
inputs, filters = [], []
for i, m in enumerate(marks):
    inputs += ['-i', str(OUT / f'scene{i}.wav')]
    filters.append(f'[{i + 1}:a]adelay={int(m * 1000)}|{int(m * 1000)}[a{i}]')
# The verdict's real Hindi audio, from the tap, faded out at CLIP_MAX seconds.
inputs += ['-i', str(OUT / 'verdict.mp3')]
at = int(CLIP['at'] * 1000) + 200
filters.append(f'[{len(marks) + 1}:a]atrim=0:{CLIP_MAX},afade=t=out:st={CLIP_MAX - 1}:d=1,adelay={at}|{at}[clip]')
mix = ''.join(f'[a{i}]' for i in range(len(marks))) + f'[clip]amix=inputs={len(marks) + 1}:normalize=0[aout]'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', video, *inputs, '-filter_complex', ';'.join(filters + [mix]),
                '-map', '0:v', '-map', '[aout]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', str(OUT / 'demo.mp4')], check=True)
print('wrote', OUT / 'demo.mp4', (OUT / 'demo.mp4').stat().st_size, 'bytes')
