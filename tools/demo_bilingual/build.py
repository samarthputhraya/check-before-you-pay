"""docs/demo.mp4, the bilingual demo video: English and Hindi phones side by side, narrated over a soft music bed,
rendered frame by frame from real captures (capture.py, capture_voice.py) on a light theme.

    python tools/demo_bilingual/capture.py                      # en + hi checks on fresh local servers
    python tools/demo_bilingual/capture_voice.py <voice.m4a>    # the iPhone voice note, kept outside Git
    copy the 40 s build timelapse to tools/demo_bilingual/cap/timelapse.mp4 (also kept outside Git)
    python tools/demo_bilingual/build.py --fps 60 --scale 1.3333 --workers 4 --out docs/demo.mp4
    python tools/demo_bilingual/build.py --preview 4 --from 30 --out preview.mp4   # a short piece for a quick look

Needs Playwright with Chrome, ffmpeg on PATH, GEMINI_API_KEY in .env.railway (read in process, never printed) and
bgm/bgm.mp3 (an instrumental bed; made with Lyria 3.5 by bgm.py)."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, wave
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
CAP, WORK = HERE / 'cap', HERE / 'work'
WORK.mkdir(exist_ok=True)
REPO = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which('ffmpeg') or 'ffmpeg'
FFPROBE = str(Path(FFMPEG).with_name('ffprobe' + Path(FFMPEG).suffix))
BGM = HERE / 'bgm' / 'bgm.mp3'
ap = argparse.ArgumentParser()
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--scale', type=float, default=1.0)
ap.add_argument('--preview', type=float, default=0)
ap.add_argument('--from', dest='start', type=float, default=0)
ap.add_argument('--workers', type=int, default=1)
ap.add_argument('--worker', type=int)
ap.add_argument('--out', type=Path, default=HERE / 'demo.mp4')
ap.add_argument('--audio-only', action='store_true')  # remix the sound onto the last render
args = ap.parse_args()
META = json.loads((CAP / 'meta.json').read_text(encoding='utf-8'))

SCREEN_W, SCREEN_H = 388, 840
K = SCREEN_W / 390
VIEW = (SCREEN_H - 46) / K
for lang in ('en', 'hi'):
    for name, m in META[lang].items():
        if name == 'checks':
            continue
        dst = WORK / f'{lang}_{name}.png'
        if not dst.exists():
            im = Image.open(CAP / m['file'])
            im.resize((780, round(im.height * 780 / im.width)), Image.LANCZOS).save(dst)


def tts(text):
    path = WORK / f'say_{hashlib.sha1(text.encode()).hexdigest()[:12]}.wav'
    if not path.exists():
        for line in (REPO / '.env.railway').read_text(encoding='utf-8').splitlines():
            if line.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = line.split('=', 1)[1].strip()
        from google import genai
        from google.genai import types
        client = genai.Client()
        for attempt in range(5):
            try:  # text only: a style instruction in front of it gets read aloud
                r = client.models.generate_content(model='gemini-3.8-flash-tts', contents=text,
                    config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')))))
                pcm = r.candidates[0].content.parts[0].inline_data.data
                if pcm[:4] == b'RIFF':  # a whole WAV (with a provenance chunk at the end): keep only its audio
                    import io
                    with wave.open(io.BytesIO(pcm)) as inner:
                        pcm = inner.readframes(inner.getnframes())
                break
            except Exception as e:
                print('tts retry', type(e).__name__, flush=True); time.sleep(6)
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    fast = path.with_name(path.stem + '_f108.wav')  # a touch brisker, same pitch
    if not fast.exists():
        subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(path), '-filter:a', 'atempo=1.08', str(fast)], check=True)
    with wave.open(str(fast)) as w:
        return fast, w.getnframes() / w.getframerate()


def duration(path):
    return float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                                capture_output=True, text=True).stdout.strip())


def sentence_end(path, lo, hi):
    """The last pause between lo and hi seconds: the Listen clip stops at the end of a sentence, not mid-word."""
    log = subprocess.run([FFMPEG, '-hide_banner', '-i', str(path), '-af', 'silencedetect=n=-35dB:d=0.25', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    starts = [float(l.split('silence_start:')[1].split()[0]) for l in log.splitlines() if 'silence_start:' in l]
    fits = [s for s in starts if lo <= s <= hi]
    return (max(fits) + 0.12) if fits else hi


VOICE = CAP / 'voice_note.mp4'
LISTEN = sentence_end(CAP / 'hi_listen.mp3', 2, 4.5), sentence_end(CAP / 'en_listen.mp3', 2, 4.5)  # the headline sentence
REC = duration(VOICE)
TIMELAPSE = CAP / 'timelapse.mp4'
TL_LEN = duration(TIMELAPSE)
vc = {l: META[l]['checks']['voice'] for l in ('en', 'hi')}
first = {l: META[l]['checks']['first'] for l in ('en', 'hi')}

P = lambda kicker, head, sub: [f'<div class="kicker">{kicker}</div>', f'<div class="head">{head}</div>', f'<div class="sub">{sub}</div>']
S = [
    ('hook', 'In 2025, Indians lost over twenty-two thousand crore rupees to cyber fraud. Three-quarters of it went to fake '
             'investment schemes.', None),
    ('problem', 'It usually starts the same way. You’re added to a WhatsApp “VIP tips” group. You’re sent an app that '
                'copies a real broker. And you’re asked to pay a personal UPI ID.', None),
    ('title', 'Check Before You Pay. Forward the message, and see the red flags in seconds, in your own language.', None),
    ('personas', 'Meet Arjun in Bengaluru, and Sunita in Pune. Both got the same pitch: thirty percent a month, pay fifty '
                 'thousand today. He reads English. She reads Hindi.',
     P('The same scam, two languages', 'Arjun reads English.<br>Sunita reads Hindi.',
       'Both were added to a WhatsApp “VIP stock tips” group and asked to pay ₹50,000 to a personal UPI ID.')),
    ('check', 'One tap. In under four seconds, both see the same verdict: high risk. Don’t pay.',
     P('Check', '<span class="r">High risk</span>,<br>in under 4 seconds', 'The same verdict, each in their own language.')),
    ('evidence', 'Every point comes with proof. The UPI ID isn’t a SEBI at-valid handle. The link copies a real broker. Every '
                 'claim is quoted word for word. Fixed checks set the score; the AI only explains.',
     ['<div class="kicker">How it decides</div>', '<div class="head">Every point<br>shows its proof</div>',
      '<div class="pts"><b>+50</b>The UPI ID isn’t a SEBI @valid handle</div>',
      '<div class="pts"><b>+30</b>The link copies Groww and Zerodha</div>',
      '<div class="pts"><b>+40</b>Claims, quoted word for word</div>',
      '<div class="sub" style="margin-top:18px">Fixed checks set the score. The AI only reads and explains.</div>']),
    ('listen', 'For parents who’d rather listen, one tap reads it aloud.',
     P('Listen', 'One tap<br>reads it aloud', 'Real audio from the app: Hindi for Sunita, then English for Arjun.')),
    ('voice', 'Many tips arrive as voice notes. Here’s one our teammate recorded on an iPhone, reading a sample scam.',
     ['<div class="kicker">A real voice note · iPhone</div>',
      '<div class="quote">“Join our VIP stock tip group. Guaranteed 30% returns every month. Send ₹50,000 to '
      '<em>sample dot desk at Y B L</em> today.”</div>', '<div class="meta">Recorded on an iPhone by our teammate Risheeth, reading a sample scam script · 30 Oct</div>']),
    ('voice2', 'It even catches a UPI ID that’s spoken aloud. High risk.',
     ['<div class="kicker">Heard, not just read</div>',
      f'<div class="head"><span class="r">High risk · {vc["en"]["score"]}</span></div>',
      '<div class="pts"><b>+50</b>The spoken UPI ID, sample.desk@ybl, isn’t a SEBI @valid handle</div>',
      '<div class="pts"><b>+40</b>“Guaranteed 30% returns every month”</div>']),
    ('ring', 'The next day, a new group sends a new message, with the same UPI ID. It’s linked to the earlier check. '
             'Scammers change their words. They can’t hide where the money goes.',
     P('Every check helps the next one', 'Linked to the<br>earlier check',
       'A new message from a new group, with the same UPI ID. The link shows up on the very next check.')),
    ('share', 'One tap sends the verdict to the family WhatsApp group, as a page in their language, with audio.',
     P('Share', 'Sent to the<br>family group', 'A page in their language, with the evidence and the audio.')),
    ('telegram', 'No app to install: forward it to our Telegram bot. In a real chat, text, screenshot and voice-note checks came '
                 'back in two to five seconds, and an ordinary rent request got no warning.', None),
    ('quiz', 'And Spot the Scam turns it into a quiz that families share.',
     P('Spot the scam', 'A quiz families share', 'In English, Hindi, Hinglish and Marathi.')),
    ('trust', 'It never calls anyone a fraud. It shows the evidence, links to SEBI Check and the 1930 helpline, and stores '
              'identifiers only as salted hashes.', None),
    ('results', 'On a hundred and twenty-eight test messages we never tuned on, it flagged sixty-one of sixty-four scams, '
                'with zero false alarms.', None),
    ('timelapse', 'We built it in three days, at Hacker House Goa.', None),
    ('close', 'Check Before You Pay is live today. Before you pay anyone, check.', None),
]
PHONE_SCENES = ['personas', 'check', 'evidence', 'listen', 'voice', 'voice2', 'ring', 'share', 'quiz']
LEAD, TAIL = 0.45, 0.6
MIN_DUR = dict(title=7.5, check=7.5, share=7.5, quiz=7.0, close=8.5, voice2=7.5)
scenes, t = [], 0.0
for sid, say, panel in S:
    wav, n = tts(say)
    extra = (LISTEN[0] + LISTEN[1] + 1.9) if sid == 'listen' else (REC + 1.9) if sid == 'voice' else 0
    dur = max(LEAD + n + TAIL + extra, MIN_DUR.get(sid, 0))
    if sid == 'timelapse':
        dur = TL_LEN + 1.6  # the whole timelapse, from 0.6 s in
    scenes.append(dict(id=sid, t0=t, t1=t + dur, say=str(wav), say_at=t + LEAD, say_len=n, panel=panel))
    t += dur
TOTAL = t
sc = {s['id']: s for s in scenes}
print('scenes:', [(s['id'], round(s['t1'] - s['t0'], 1)) for s in scenes], 'total', round(TOTAL, 1), flush=True)

tracks, taps, chips, audio = {'en': [], 'hi': []}, [], [], []


def seg(lang, t0, t1, img, y0=0, y1=None):
    h = META[lang][img]['height']
    clamp = lambda y: max(0, min(y, h - VIEW))
    tracks[lang].append(dict(t0=t0, t1=t1, img=f'{lang}_{img}', y0=clamp(y0), y1=clamp(y0 if y1 is None else y1)))


def tap(lang, at, img, name, scroll=0):
    b = META[lang][img]['boxes'][name]
    taps.append(dict(t=at, lang=lang, x=(b['x'] + b['w'] / 2) * K, y=(b['y'] + b['h'] / 2 - scroll) * K))


listen_at = {}
for lang in ('en', 'hi'):
    m = META[lang]
    a = sc['personas']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.38, 'home'); seg(lang, a['t0'] + d * 0.38, a['t1'], 'filled1')
    a = sc['check']; tp = a['t0'] + 0.7
    seg(lang, a['t0'], tp + 0.15, 'filled1'); tap(lang, tp, 'filled1', 'submit')
    seg(lang, tp + 0.15, tp + 2.0, 'loading1'); seg(lang, tp + 2.0, a['t1'], 'verdict1', 0, 60)
    chips.append(dict(lang=lang, t0=tp + 2.1, t1=a['t1'], text=('High risk · ' if lang == 'en' else 'ज़्यादा ख़तरा · ')
                      + f'{first[lang]["latency_ms"] / 1000:.1f} s'))
    a = sc['evidence']; d = a['t1'] - a['t0']
    sig, last = m['verdict1']['boxes']['signals'], m['verdict1']['boxes']['last_signal']
    seg(lang, a['t0'], a['t0'] + d * 0.1, 'verdict1', 60, 60)
    seg(lang, a['t0'] + d * 0.1, a['t0'] + d * 0.35, 'verdict1', 60, sig['y'] - 150)
    seg(lang, a['t0'] + d * 0.35, a['t0'] + d * 0.55, 'verdict1', sig['y'] - 150, sig['y'] - 150)
    seg(lang, a['t0'] + d * 0.55, a['t0'] + d * 0.85, 'verdict1', sig['y'] - 150, last['y'] + last['h'] - 700)
    seg(lang, a['t0'] + d * 0.85, a['t1'], 'verdict1', last['y'] + last['h'] - 700, 0)
    a = sc['listen']; start = a['say_at'] + a['say_len'] + 0.35
    at = start if lang == 'hi' else start + LISTEN[0] + 1.1
    ln = LISTEN[0] if lang == 'hi' else LISTEN[1]
    listen_at[lang] = [at, at + ln]
    seg(lang, a['t0'], at, 'verdict1', 0, 0); tap(lang, at - 0.15, 'verdict1', 'listen')
    seg(lang, at, at + ln, 'listen', 0, 0); seg(lang, at + ln, a['t1'], 'verdict1', 0, 0)
    audio.append(dict(at=at + 0.2, file=str(CAP / f'{lang}_listen.mp3'), len=ln, gain=1.0))
    # The real iPhone voice note: attached, played, then checked.
    a = sc['voice']; rec_at = a['say_at'] + a['say_len'] + 0.35; rec_end = rec_at + REC
    seg(lang, a['t0'], rec_end + 0.6, 'vattached', 0, 0)
    tap(lang, rec_end + 0.45, 'vattached', 'submit')
    seg(lang, rec_end + 0.6, a['t1'], 'vloading', 0, 0)
    a = sc['voice2']; d = a['t1'] - a['t0']
    tb = m['vverdict']['boxes']['transcript']
    seg(lang, a['t0'], a['t0'] + 0.6, 'vloading', 0, 0)
    seg(lang, a['t0'] + 0.6, a['t0'] + d * 0.45, 'vverdict', 0, 0)
    seg(lang, a['t0'] + d * 0.45, a['t0'] + d * 0.75, 'vverdict', 0, tb['y'] + tb['h'] - 640)
    seg(lang, a['t0'] + d * 0.75, a['t1'], 'vverdict', tb['y'] + tb['h'] - 640, tb['y'] + tb['h'] - 640)
    chips.append(dict(lang=lang, t0=a['t0'] + 0.7, t1=a['t1'],
                      text=('High risk · ' if lang == 'en' else 'ज़्यादा ख़तरा · ') + str(vc[lang]['score'])))
    a = sc['ring']; d = a['t1'] - a['t0']
    another = m['verdict1']['boxes']['another']; ys = max(0, min(another['y'] - 560, m['verdict1']['height'] - VIEW))
    seg(lang, a['t0'], a['t0'] + 1.0, 'verdict1', 0, ys); tap(lang, a['t0'] + 1.15, 'verdict1', 'another', scroll=ys)
    seg(lang, a['t0'] + 1.0, a['t0'] + 1.3, 'verdict1', ys, ys)
    seg(lang, a['t0'] + 1.3, a['t0'] + 2.5, 'filled2'); tap(lang, a['t0'] + 2.3, 'filled2', 'submit')
    seg(lang, a['t0'] + 2.5, a['t0'] + 4.0, 'loading2')
    ring = m['verdict2']['boxes']['ring']
    seg(lang, a['t0'] + 4.0, a['t0'] + d * 0.45, 'verdict2', 0, 0)
    seg(lang, a['t0'] + d * 0.45, a['t0'] + d * 0.65, 'verdict2', 0, ring['y'] - 420)
    seg(lang, a['t0'] + d * 0.65, a['t1'], 'verdict2', ring['y'] - 420, ring['y'] - 420)
    a = sc['share']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.3, 'share', 0, 0); seg(lang, a['t0'] + d * 0.3, a['t1'], 'share', 0, 400)
    a = sc['quiz']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.5, 'quiz1'); tap(lang, a['t0'] + d * 0.45, 'quiz1', 'scam')
    seg(lang, a['t0'] + d * 0.5, a['t1'], 'quiz2')
a = sc['voice']
audio.append(dict(at=a['say_at'] + a['say_len'] + 0.35, file=str(VOICE), len=REC, gain=1.25))
narration = [dict(at=s['say_at'], file=s['say']) for s in scenes]
# Over the timelapse: the three days, so it isn't 40 seconds of music alone.
TIMELAPSE_LINES = [(9.0, 'Day one, we locked the idea: a check anyone can run before they pay.'),
                   (18.5, 'Day two, the first check ran end to end, and we tested it on a hundred and twenty-eight messages '
                          'it had never seen.'),
                   (29.5, 'Day three, it went live: on the web, on Telegram, with alerts to family.')]
for offset, line in TIMELAPSE_LINES:
    wav, n = tts(line)
    narration.append(dict(at=sc['timelapse']['t0'] + offset, file=str(wav)))
    print(f'timelapse line at +{offset}s: {n:.1f}s', flush=True)

timeline = dict(total=TOTAL, scenes=[{k: v for k, v in s.items() if k != 'say'} for s in scenes], tracks=tracks, taps=taps,
                chips=chips, listen=listen_at, phoneScenes=PHONE_SCENES)
ICON = lambda d: f'<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0b6839" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{d}</svg>'
icons = {'ICON1': ICON('<path d="M12 3v18M5 7h14M7 7l-3 7a4 4 0 0 0 6 0zM17 7l-3 7a4 4 0 0 0 6 0z"/>'),
         'ICON2': ICON('<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/>'),
         'ICON3': ICON('<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>'),
         'ICON4': ICON('<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>')}
status = ('<span style="display:flex;gap:6px;align-items:center">'
 '<svg width="18" height="12" viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" fill="#111"/><rect x="5" y="5.5" width="3" height="6.5" rx="1" fill="#111"/><rect x="10" y="3" width="3" height="9" rx="1" fill="#111"/><rect x="15" y="0" width="3" height="12" rx="1" fill="#111"/></svg>'
 '<svg width="16" height="12" viewBox="0 0 16 12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.5 6.5 0 0 1 9.2 0l-1.5 1.5a4.4 4.4 0 0 0-6.2 0zM1 4.4a9.9 9.9 0 0 1 14 0l-1.5 1.5a7.8 7.8 0 0 0-11 0z" fill="#111"/></svg>'
 '<svg width="27" height="13" viewBox="0 0 27 13"><rect x=".5" y=".5" width="23" height="12" rx="3.5" fill="none" stroke="#111" opacity=".45"/><rect x="2.5" y="2.5" width="16" height="8" rx="2" fill="#111"/><rect x="25" y="4.5" width="1.6" height="4" rx=".8" fill="#111" opacity=".45"/></svg></span>')
stage = (HERE / 'stage.html').read_text(encoding='utf-8').replace('/*TIMELINE*/', 'window.TL = ' + json.dumps(
    timeline, ensure_ascii=False) + ';').replace('STATUSICONS', status)
for k, v in icons.items():
    stage = stage.replace(k, v)
(WORK / 'stage.html').write_text(stage, encoding='utf-8')
(WORK / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False), encoding='utf-8')
for f in ('qr.png', 'icon.svg'):
    shutil.copy(CAP / f, WORK / f)

t_end = min(TOTAL, args.start + args.preview) if args.preview else TOTAL
frames = int((t_end - args.start) * args.fps)
video_only = WORK / 'video_only.mp4'
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-tune', 'stillimage']


def render_frames(first_frame, count, path):
    enc = subprocess.Popen([FFMPEG, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(args.fps), '-c:v',
                            'mjpeg', '-i', '-', *ENC, str(path)], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    t0 = time.monotonic()
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='chrome')
        pg = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=args.scale)
        pg.goto((WORK / 'stage.html').as_uri())
        pg.wait_for_function('window.READY === true', timeout=180000)
        for i in range(first_frame, first_frame + count):
            pg.evaluate(f'render({args.start + i / args.fps:.4f})')
            enc.stdin.write(pg.screenshot(type='jpeg', quality=95, timeout=180000))
            if (i - first_frame) % 600 == 0:
                print(f'[{first_frame}] {i - first_frame}/{count} {time.monotonic() - t0:.0f}s', flush=True)
        b.close()
    enc.stdin.close(); enc.wait()


if args.worker is not None:
    per = -(-frames // args.workers)
    f0 = args.worker * per
    render_frames(f0, max(0, min(per, frames - f0)), WORK / f'seg_{args.worker}.mp4')
    sys.exit(0)
started = time.monotonic()
if args.audio_only:
    pass
elif args.workers > 1:
    cmd = [sys.executable, __file__, '--fps', str(args.fps), '--scale', str(args.scale), '--from', str(args.start),
           '--preview', str(args.preview), '--workers', str(args.workers)]
    procs = [subprocess.Popen(cmd + ['--worker', str(w)]) for w in range(args.workers)]
    if any(p.wait() for p in procs):
        sys.exit('a render worker failed')
    (WORK / 'segments.txt').write_text(''.join(f"file 'seg_{w}.mp4'" + chr(10) for w in range(args.workers)), encoding='utf-8')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'segments.txt'),
                    '-c', 'copy', str(video_only)], check=True)
else:
    render_frames(0, frames, video_only)
print('rendered', frames, 'frames in', round(time.monotonic() - started), 's', flush=True)

# ---- the 40-second build timelapse, composited into its window (rounded corners, fading with the scene) -------------
tl_at = sc['timelapse']['t0'] + 0.6 - args.start
if args.audio_only and (WORK / 'video_tl.mp4').exists():
    video_only = WORK / 'video_tl.mp4'
elif -TL_LEN < tl_at < t_end - args.start:
    from PIL import ImageDraw
    sx = args.scale
    W_, H_, X_, Y_ = round(1280 * sx), round(720 * sx), round(320 * sx), round(236 * sx)
    W_, H_ = W_ - W_ % 2, H_ - H_ % 2
    mask = Image.new('L', (W_, H_), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W_ - 1, H_ - 1], radius=round(28 * sx), fill=255)
    mask.save(WORK / 'tlmask.png')
    composed = WORK / 'video_tl.mp4'
    ff = (f'[1:v]scale={W_}:{H_}:flags=lanczos,unsharp=5:5:0.6:5:5:0,fps={args.fps},format=rgba[tl];'
          f'[2:v]format=gray[m];[tl][m]alphamerge,fade=t=in:st=0:d=0.5:alpha=1,'
          f'fade=t=out:st={TL_LEN - 0.5:.2f}:d=0.5:alpha=1,setpts=PTS-STARTPTS+{max(0, tl_at):.3f}/TB[tla];'
          f'[0:v][tla]overlay={X_}:{Y_}:eof_action=pass:format=auto[v]')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(video_only), '-i', str(TIMELAPSE), '-loop', '1', '-i',
                    str(WORK / 'tlmask.png'), '-filter_complex', ff, '-map', '[v]', '-c:v', 'libx264', '-preset', 'medium',
                    '-crf', '15', '-pix_fmt', 'yuv420p', '-r', str(args.fps),
                    str(composed)], check=True)
    video_only = composed
    print('timelapse composited', flush=True)

# ---- audio: a foreground bus (narration, the app's Listen audio, the iPhone voice note) over the music, which ducks
# under it; then loudness-normalised for YouTube (-14 LUFS).
span = t_end - args.start
inputs, chains, fg = [], [], []
items = [dict(x, kind='say') for x in narration] + [dict(x, kind='clip') for x in audio]
items = [x for x in items if args.start <= x['at'] < t_end]
for n, x in enumerate(items):
    inputs += ['-i', x['file']]
    ms = int((x['at'] - args.start) * 1000)
    ch = f'[{n + 1}:a]aresample=48000,aformat=channel_layouts=stereo'
    if x['kind'] == 'clip':
        ch += f',atrim=0:{x["len"]:.2f},afade=t=in:d=0.05,afade=t=out:st={max(0, x["len"] - 0.35):.2f}:d=0.35,volume={x["gain"]}'
    chains.append(f'{ch},adelay={ms}|{ms}[f{n}]'); fg.append(f'[f{n}]')
b = len(items) + 1
inputs += ['-ss', f'{args.start:.2f}', '-i', str(BGM)]
chains.append(''.join(fg) + f'amix=inputs={len(fg)}:normalize=0,apad=whole_dur={span:.2f}[fgmix]')
chains.append('[fgmix]asplit=2[fg1][key]')
chains.append(f'[{b}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{span:.2f},volume=0.24,'
              f'afade=t=in:d=2,afade=t=out:st={max(0, span - 3.5):.2f}:d=3.5[bgm]')
chains.append('[bgm][key]sidechaincompress=threshold=0.05:ratio=3:attack=120:release=1800:makeup=1[duck]')
chains.append('[fg1][duck]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(video_only), *inputs, '-filter_complex', ';'.join(chains),
                '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-t', f'{span:.2f}',
                '-movflags', '+faststart', str(args.out)], check=True)
print('wrote', args.out, round(args.out.stat().st_size / 1e6, 1), 'MB', flush=True)
