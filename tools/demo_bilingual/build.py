"""docs/demo.mp4, the bilingual demo video: English and Hindi phones side by side, narrated, rendered frame by frame
from the real captures in ./cap.

    python tools/demo_bilingual/capture.py      # two fresh local servers (en, hi), real Gemini calls, about 3 min
    python tools/demo_bilingual/build.py --fps 60 --workers 3 --out docs/demo.mp4   # narration + render, about 5 min

Needs Playwright with Chrome, ffmpeg on PATH and GEMINI_API_KEY in .env.railway (read in process, never printed).
--preview SECONDS --from T renders a short piece for a quick look. cap/ and work/ are scratch folders."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, wave
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
CAP, WORK = HERE / 'cap', HERE / 'work'
WORK.mkdir(exist_ok=True)
REPO = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which('ffmpeg') or 'ffmpeg'
ap = argparse.ArgumentParser()
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--scale', type=float, default=1.0)  # 1 = 1920x1080, 2 = 3840x2160
ap.add_argument('--preview', type=float, default=0)  # render only this many seconds, for a quick look
ap.add_argument('--from', dest='start', type=float, default=0)
ap.add_argument('--telegram', type=Path)
ap.add_argument('--workers', type=int, default=1)
ap.add_argument('--worker', type=int)
ap.add_argument('--out', type=Path, default=HERE / 'demo.mp4')
args = ap.parse_args()
META = json.loads((CAP / 'meta.json').read_text(encoding='utf-8'))

# ---- phone screenshots at 2x of the 390 px CSS width: crisp at any render scale up to 2 --------------------------
SCREEN_W, SCREEN_H = 388, 840          # phone screen in stage px; the capture is 390 x 844 CSS px
K = SCREEN_W / 390
VIEW = (SCREEN_H - 46) / K   # CSS px of page visible under the 46 px status bar
for lang in ('en', 'hi'):
    for name, m in META[lang].items():
        if name == 'checks':
            continue
        dst = WORK / f'{lang}_{name}.png'
        if not dst.exists():
            im = Image.open(CAP / m['file'])
            im.resize((780, round(im.height * 780 / im.width)), Image.LANCZOS).save(dst, optimize=False)


# ---- narration --------------------------------------------------------------------------------------------------
def tts(text):
    path = WORK / f'say_{hashlib.sha1(text.encode()).hexdigest()[:12]}.wav'
    if not path.exists():
        for line in (REPO / '.env.railway').read_text(encoding='utf-8').splitlines():
            if line.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = line.split('=', 1)[1].strip()
        from google import genai
        from google.genai import types
        client = genai.Client()
        for attempt in range(4):
            try:
                # Text only: a style instruction in front of it gets read aloud.
                r = client.models.generate_content(model='gemini-3.8-flash-tts', contents=text,
                    config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')))))
                pcm = r.candidates[0].content.parts[0].inline_data.data
                break
            except Exception as e:  # rate limits on the TTS model: wait and retry
                print('tts retry', type(e).__name__, flush=True); time.sleep(6)
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    with wave.open(str(path)) as w:
        return path, w.getnframes() / w.getframerate()


def mp3_len(path):
    out = subprocess.run([str(Path(FFMPEG).with_name('ffprobe' + Path(FFMPEG).suffix)), '-v', 'error', '-show_entries', 'format=duration', '-of',
                          'csv=p=0', str(path)], capture_output=True, text=True).stdout
    return float(out.strip())


en, hi = META['en'], META['hi']
ck = {l: META[l]['checks'] for l in ('en', 'hi')}
secs = {l: {k: v['latency_ms'] / 1000 for k, v in ck[l].items()} for l in ck}
LISTEN = min(6.5, mp3_len(CAP / 'hi_listen.mp3')), min(6.0, mp3_len(CAP / 'en_listen.mp3'))

S = [  # id, narration, panel (kicker, headline, sub) or a full-screen card
    ('stats', 'In 2025, Indians lost over twenty-two thousand crore rupees to cyber fraud. Seventy-six percent went to fake '
              'investment schemes.', None),
    ('title', 'Check Before You Pay. Forward any investment tip, and see the red flags in seconds, in your language.', None),
    ('personas', 'Arjun and Sunita were both added to a VIP stock-tips group, and asked for fifty thousand rupees. Before '
                 'paying, they paste the message. He reads English. She reads Hindi.',
     ('The same scam, two languages', 'Arjun reads English.<br>Sunita reads Hindi.',
      'Both were added to a WhatsApp “VIP stock tips” group and asked to pay ₹50,000.')),
    ('check', 'One tap. Seconds later: high risk. Don’t pay.',
     ('Check', 'High risk,<br>in seconds', 'Same verdict, each in their own language.')),
    ('evidence', 'Fixed checks decide the score, not the AI. The UPI ID isn’t a SEBI at-valid handle. The link copies '
                 'a real broker. And every claim is quoted word for word.',
     ('How it decides', 'Fixed checks decide.<br>The AI only reads and explains.',
      '<div class="pts"><b>+50</b> The UPI ID isn’t a SEBI @valid handle</div>'
      '<div class="pts"><b>+30</b> The link copies Groww / Zerodha</div>'
      '<div class="pts"><b>+40</b> Claims, quoted word for word</div>')),
    ('listen', 'One tap reads it aloud.',
     ('Listen', 'One tap reads it aloud', 'In Hindi for Sunita. In English for Arjun.')),
    ('ring', 'Next day: a new group, a new message, the same UPI ID. It’s linked to the earlier check. Scammers change '
             'scripts. They can’t hide where the money goes.',
     ('Every check helps the next one', 'Linked to the<br>earlier check',
      'New message, new group, same UPI ID. Identifiers are stored only as salted hashes.')),
    ('share', 'One tap sends it to the family WhatsApp group, in their language.',
     ('Share', 'Sent to the<br>family group', 'A page in their language, with the evidence and the audio.')),
    ('telegram', 'No app needed: forward a text, a screenshot or a voice note to our Telegram bot. In a real chat, '
                 'verdicts came back in two to five seconds, and an ordinary rent request got no warning.', None),
    ('quiz', 'And Spot the Scam: a quiz families share.',
     ('Spot the scam', 'A quiz families share', 'English, Hindi, Hinglish and Marathi.')),
    ('results', 'On a hundred and twenty-eight test messages we never tuned on: sixty-one of sixty-four scams flagged, and '
                'zero false alarms on sixty-four ordinary payments.', None),
    ('close', 'Check Before You Pay. Live today.', None),
]
LEAD, TAIL = 0.35, 0.55
MIN_DUR = dict(title=7.5, check=7.5, share=7.0, quiz=7.0, close=8.0)  # enough time to see the screen
scenes, t = [], 0.0
for sid, say, panel in S:
    wav, n = tts(say)
    extra = (LISTEN[0] + LISTEN[1] + 1.8) if sid == 'listen' else 0
    dur = max(LEAD + n + TAIL + extra, MIN_DUR.get(sid, 0))
    scenes.append(dict(id=sid, t0=t, t1=t + dur, say=str(wav), say_at=t + LEAD, say_len=n, panel=panel))
    t += dur
TOTAL = t
sc = {s['id']: s for s in scenes}
print('scenes:', [(s['id'], round(s['t1'] - s['t0'], 1)) for s in scenes], 'total', round(TOTAL, 1), flush=True)

# ---- phone tracks: segments of (t0, t1, image, y0, y1); taps; highlights -----------------------------------------
tracks = {'en': [], 'hi': []}
taps = []
audio_events = []  # (time, file, max_len)


def seg(lang, t0, t1, img, y0=0, y1=None):
    h = META[lang][img]['height']
    clamp = lambda y: max(0, min(y, h - VIEW))
    tracks[lang].append(dict(t0=t0, t1=t1, img=f'{lang}_{img}', y0=clamp(y0), y1=clamp(y0 if y1 is None else y1)))


def tap(lang, at, img, name, scroll=0):
    b = META[lang][img]['boxes'][name]
    taps.append(dict(t=at, lang=lang, x=(b['x'] + b['w'] / 2) * K, y=(b['y'] + b['h'] / 2 - scroll) * K))
    audio_events.append((at, 'click', 0))


for lang in ('en', 'hi'):
    m = META[lang]
    a = sc['personas']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.42, 'home'); seg(lang, a['t0'] + d * 0.42, a['t1'], 'filled1')
    a = sc['check']; d = a['t1'] - a['t0']
    tp = a['t0'] + 0.5
    seg(lang, a['t0'], tp + 0.15, 'filled1'); tap(lang, tp, 'filled1', 'submit')
    seg(lang, tp + 0.15, tp + 1.9, 'loading1')
    seg(lang, tp + 1.9, a['t1'], 'verdict1', 0, 60)
    a = sc['evidence']; d = a['t1'] - a['t0']
    sig, last = m['verdict1']['boxes']['signals'], m['verdict1']['boxes']['last_signal']
    seg(lang, a['t0'], a['t0'] + d * 0.12, 'verdict1', 60, 60)
    seg(lang, a['t0'] + d * 0.12, a['t0'] + d * 0.45, 'verdict1', 60, sig['y'] - 150)
    seg(lang, a['t0'] + d * 0.45, a['t0'] + d * 0.62, 'verdict1', sig['y'] - 150, sig['y'] - 150)
    seg(lang, a['t0'] + d * 0.62, a['t0'] + d * 0.92, 'verdict1', sig['y'] - 150, last['y'] + last['h'] - 700)
    seg(lang, a['t0'] + d * 0.92, a['t1'], 'verdict1', last['y'] + last['h'] - 700, 0)
    # Listen: Hindi first, then English.
    a = sc['listen']
    start = a['say_at'] + a['say_len'] + 0.3
    first, second = ('hi', 'en')
    me_at = start if lang == first else start + LISTEN[0] + 1.2
    me_len = LISTEN[0] if lang == first else LISTEN[1]
    seg(lang, a['t0'], me_at, 'verdict1', 0, 0); tap(lang, me_at, 'verdict1', 'listen')
    seg(lang, me_at, me_at + me_len, 'listen', 0, 0)
    seg(lang, me_at + me_len, a['t1'], 'verdict1', 0, 0)
    audio_events.append((me_at + 0.25, str(CAP / f'{lang}_listen.mp3'), me_len))
    # Ring: scroll to "check another", tap, paste message 2, tap, verdict 2, scroll to the link.
    a = sc['ring']; d = a['t1'] - a['t0']
    another = m['verdict1']['boxes']['another']; ys = another['y'] - 560
    seg(lang, a['t0'], a['t0'] + 1.0, 'verdict1', 0, ys)
    tap(lang, a['t0'] + 1.15, 'verdict1', 'another', scroll=max(0, min(ys, m['verdict1']['height'] - VIEW)))
    seg(lang, a['t0'] + 1.0, a['t0'] + 1.3, 'verdict1', ys, ys)
    seg(lang, a['t0'] + 1.3, a['t0'] + 2.4, 'filled2')
    tap(lang, a['t0'] + 2.25, 'filled2', 'submit')
    seg(lang, a['t0'] + 2.4, a['t0'] + 3.9, 'loading2')
    ring = m['verdict2']['boxes']['ring']
    seg(lang, a['t0'] + 3.9, a['t0'] + d * 0.45, 'verdict2', 0, 0)
    seg(lang, a['t0'] + d * 0.45, a['t0'] + d * 0.62, 'verdict2', 0, ring['y'] - 420)
    seg(lang, a['t0'] + d * 0.62, a['t1'], 'verdict2', ring['y'] - 420, ring['y'] - 420)
    a = sc['share']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.3, 'share', 0, 0)
    seg(lang, a['t0'] + d * 0.3, a['t1'], 'share', 0, 400)
    a = sc['quiz']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.5, 'quiz1'); tap(lang, a['t0'] + d * 0.45, 'quiz1', 'scam')
    seg(lang, a['t0'] + d * 0.5, a['t1'], 'quiz2')
    if lang == 'hi':
        for s in scenes:
            audio_events.append((s['say_at'], s['say'], 0))

timeline = dict(total=TOTAL, scenes=[{k: v for k, v in s.items() if k not in ('say',)} for s in scenes], tracks=tracks,
                taps=taps, secs=secs, listen=dict(hi=None, en=None))
for lang in ('en', 'hi'):
    a = sc['listen']; start = a['say_at'] + a['say_len'] + 0.3
    timeline['listen'][lang] = [start, start + LISTEN[0]] if lang == 'hi' else [start + LISTEN[0] + 1.2,
                                                                                start + LISTEN[0] + 1.2 + LISTEN[1]]
(WORK / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False), encoding='utf-8')

# ---- render -----------------------------------------------------------------------------------------------------
stage = (HERE / 'stage.html').read_text(encoding='utf-8').replace('/*TIMELINE*/', 'window.TL = ' + json.dumps(
    timeline, ensure_ascii=False) + ';')
(WORK / 'stage.html').write_text(stage, encoding='utf-8')
for f in ('qr.png', 'icon.svg'):
    shutil.copy(CAP / f, WORK / f)
t_end = min(TOTAL, args.start + args.preview) if args.preview else TOTAL
frames = int((t_end - args.start) * args.fps)
video_only = WORK / 'video_only.mp4'
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-tune', 'stillimage']


def render_frames(first, count, path):
    enc = subprocess.Popen([FFMPEG, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(args.fps), '-c:v',
                            'mjpeg', '-i', '-', *ENC, str(path)], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    t_start = time.monotonic()
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='chrome')
        pg = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=args.scale)
        pg.goto((WORK / 'stage.html').as_uri())
        pg.wait_for_function('window.READY === true', timeout=120000)
        for i in range(first, first + count):
            tt = args.start + i / args.fps
            pg.evaluate(f'render({tt:.4f})')
            enc.stdin.write(pg.screenshot(type='jpeg', quality=95, timeout=180000))
            if (i - first) % 600 == 0:
                print(f'[{first}] frame {i - first}/{count} {time.monotonic() - t_start:.0f}s', flush=True)
        b.close()
    enc.stdin.close(); enc.wait()


if args.worker is not None:  # one slice of the frames, then stop
    per = -(-frames // args.workers)
    first = args.worker * per
    render_frames(first, max(0, min(per, frames - first)), WORK / f'seg_{args.worker}.mp4')
    sys.exit(0)
t0 = time.monotonic()
if args.workers > 1:
    cmd = [sys.executable, __file__, '--fps', str(args.fps), '--scale', str(args.scale), '--from', str(args.start),
           '--preview', str(args.preview), '--workers', str(args.workers)]
    procs = [subprocess.Popen(cmd + ['--worker', str(w)]) for w in range(args.workers)]
    if any(p.wait() for p in procs):
        sys.exit('a render worker failed')
    lst = WORK / 'segments.txt'
    lst.write_text(''.join(f"file 'seg_{w}.mp4'" + chr(10) for w in range(args.workers)), encoding='utf-8')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy',
                    str(video_only)], check=True)
else:
    render_frames(0, frames, video_only)
print('rendered', frames, 'frames in', round(time.monotonic() - t0), 's', flush=True)

# ---- audio: narration, the verdicts' own Listen audio, soft taps ------------------------------------------------
click = WORK / 'click.wav'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
                'sine=frequency=2200:duration=0.045,afade=t=out:st=0.005:d=0.04,volume=0.18', str(click)], check=True)
inputs, filters, labels = [], [], []
for n, (at, f, maxlen) in enumerate(e for e in audio_events if args.start <= e[0] < t_end):
    src = str(click) if f == 'click' else f
    inputs += ['-i', src]
    ms = int((at - args.start) * 1000)
    chain = f'[{n + 1}:a]aresample=48000,aformat=channel_layouts=stereo'
    if maxlen:
        chain += f',atrim=0:{maxlen:.2f},afade=t=out:st={max(0, maxlen - 0.8):.2f}:d=0.8,volume=0.9'
    filters.append(f'{chain},adelay={ms}|{ms}[a{n}]'); labels.append(f'[a{n}]')
mix = ''.join(labels) + f'amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[aout]'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(video_only), *inputs, '-filter_complex',
                ';'.join(filters + [mix]), '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-t', f'{t_end - args.start:.2f}', '-movflags', '+faststart', str(args.out)], check=True)
print('wrote', args.out, round(args.out.stat().st_size / 1e6, 1), 'MB', flush=True)
