"""docs/demo.mp4, the film version: a dark, motion-graphics demo with a virtual camera over the real app captures.

    python tools/demo_bilingual/capture.py                      # en + hi checks on fresh local servers
    python tools/demo_bilingual/capture_voice.py <voice.m4a>    # the iPhone voice note, kept outside Git
    copy the 40 s build timelapse to tools/demo_bilingual/cap/timelapse.mp4 (also kept outside Git)
    python tools/demo_bilingual/build_film.py --fps 60 --scale 1.3333 --workers 4 --out docs/demo.mp4
    python tools/demo_bilingual/build_film.py --preview 4 --from 30 --out preview.mp4   # a short piece

Inputs: cap/ (from the capture scripts, plus timelapse.mp4), bgm/bed.mp3 (two Lyria 3.5 tracks joined), and
GEMINI_API_KEY in .env.railway (read in process, never printed)."""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, time, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
CAP, WORK = HERE / 'cap', HERE / 'work_film'
WORK.mkdir(exist_ok=True)
REPO = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which('ffmpeg') or 'ffmpeg'
FFPROBE = str(Path(FFMPEG).with_name('ffprobe' + Path(FFMPEG).suffix))
BGM = HERE / 'bgm' / 'bed.mp3'
VOICE_NAME = 'Charon'
STATUS_HTML = '<span style="display:flex;gap:6px;align-items:center"><svg width="18" height="12" viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" fill="#111"/><rect x="5" y="5.5" width="3" height="6.5" rx="1" fill="#111"/><rect x="10" y="3" width="3" height="9" rx="1" fill="#111"/><rect x="15" y="0" width="3" height="12" rx="1" fill="#111"/></svg><svg width="16" height="12" viewBox="0 0 16 12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.5 6.5 0 0 1 9.2 0l-1.5 1.5a4.4 4.4 0 0 0-6.2 0zM1 4.4a9.9 9.9 0 0 1 14 0l-1.5 1.5a7.8 7.8 0 0 0-11 0z" fill="#111"/></svg><svg width="27" height="13" viewBox="0 0 27 13"><rect x=".5" y=".5" width="23" height="12" rx="3.5" fill="none" stroke="#111" opacity=".45"/><rect x="2.5" y="2.5" width="16" height="8" rx="2" fill="#111"/><rect x="25" y="4.5" width="1.6" height="4" rx=".8" fill="#111" opacity=".45"/></svg></span>'
ap = argparse.ArgumentParser()
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--scale', type=float, default=1.0)
ap.add_argument('--preview', type=float, default=0)
ap.add_argument('--from', dest='start', type=float, default=0)
ap.add_argument('--workers', type=int, default=1)
ap.add_argument('--worker', type=int)
ap.add_argument('--audio-only', action='store_true')
ap.add_argument('--out', type=Path, default=HERE / 'demo.mp4')
args = ap.parse_args()
META = json.loads((CAP / 'meta.json').read_text(encoding='utf-8'))

# ---- phone screens at 1000 px wide: crisp under the virtual camera's zoom ------------------------------------------
SCREEN_W, SCREEN_H, STATUS = 388, 840, 46
K = SCREEN_W / 390
VIEW = (SCREEN_H - STATUS) / K
PHX, PHY = {'en': 508, 'hi': 1000}, 108
for lang in ('en', 'hi'):
    for name, m in META[lang].items():
        if name == 'checks':
            continue
        dst = WORK / f'{lang}_{name}.png'
        if not dst.exists():
            im = Image.open(CAP / m['file'])
            im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS).save(dst)


def tts(text):
    path = WORK / f'say_{VOICE_NAME}_{hashlib.sha1(text.encode()).hexdigest()[:12]}.wav'
    if not path.exists():
        for line in (REPO / '.env.railway').read_text(encoding='utf-8').splitlines():
            if line.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = line.split('=', 1)[1].strip()
        from google import genai
        from google.genai import types
        client = genai.Client()
        for attempt in range(6):
            try:  # text only: a style instruction in front of it gets read aloud
                r = client.models.generate_content(model='gemini-3.8-flash-tts', contents=text,
                    config=types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)))))
                pcm = r.candidates[0].content.parts[0].inline_data.data
                if pcm[:4] == b'RIFF':  # a whole WAV with a provenance chunk at the end: keep only its audio
                    with wave.open(io.BytesIO(pcm)) as inner:
                        pcm = inner.readframes(inner.getnframes())
                break
            except Exception as e:
                print('tts retry', type(e).__name__, flush=True); time.sleep(6)
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    fast = path.with_name(path.stem + '_f106.wav')
    if not fast.exists():
        subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(path), '-filter:a', 'atempo=1.06', str(fast)], check=True)
    with wave.open(str(fast)) as w:
        return fast, w.getnframes() / w.getframerate()


def duration(path):
    return float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                                capture_output=True, text=True).stdout.strip())


def envelope(path, fps=30):
    """Loudness per frame (0-1), so the waveforms on screen move with the real audio."""
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(path), '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 8000 // fps
    rms = np.sqrt(np.array([np.mean(a[i:i + hop] ** 2) for i in range(0, max(1, len(a) - hop), hop)]) + 1e-9)
    return [round(float(x), 3) for x in np.clip(rms / (np.percentile(rms, 98) + 1e-6), 0, 1)]


def sentence_end(path, lo, hi):
    log = subprocess.run([FFMPEG, '-hide_banner', '-i', str(path), '-af', 'silencedetect=n=-35dB:d=0.25', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    starts = [float(l.split('silence_start:')[1].split()[0]) for l in log.splitlines() if 'silence_start:' in l]
    fits = [s for s in starts if lo <= s <= hi]
    return (max(fits) + 0.12) if fits else hi


VOICE = CAP / 'voice_note.mp4'
TIMELAPSE = CAP / 'timelapse.mp4'
LISTEN = sentence_end(CAP / 'hi_listen.mp3', 2, 4.5), sentence_end(CAP / 'en_listen.mp3', 2, 4.5)
REC, TL_LEN = duration(VOICE), duration(TIMELAPSE)
vc = {l: META[l]['checks']['voice'] for l in ('en', 'hi')}
first = {l: META[l]['checks']['first'] for l in ('en', 'hi')}

# id, chapter, narration
S = [
    ('cold', '', 'Every day, millions of Indians get messages like these. Most are harmless. Some are built to empty your '
                 'savings.'),
    ('stat', '', 'In 2025, Indians lost over twenty-two thousand crore rupees to cyber fraud. Three-quarters of it went to '
                 'fake investment schemes.'),
    ('problem', '01 · The scam', 'The script rarely changes. An invite-only VIP tips group. An app that copies a real broker. '
                                 'And a personal UPI ID to pay.'),
    ('title', '', 'Check Before You Pay. Forward the message, and see the red flags in seconds, in your own language.'),
    ('personas', '02 · The check', 'Arjun reads English. Sunita reads Hindi. Both got the same pitch: thirty percent a '
                                   'month, pay fifty thousand today.'),
    ('check', '02 · The check', 'One tap. Under four seconds. High risk. Don’t pay.'),
    ('decide', '03 · How it decides', 'Here’s how it decides. Gemini reads the message and quotes each claim word for '
                                      'word. Then fixed checks set the score, not the AI. The UPI ID isn’t a SEBI '
                                      'at-valid handle: plus fifty. The link copies a real broker: plus thirty. '
                                      'Guaranteed returns: plus forty.'),
    ('evidence', '03 · How it decides', 'Every point shows its proof, in your own language.'),
    ('listen', '04 · Listen', 'For parents who’d rather listen, one tap reads it aloud.'),
    ('voice', '05 · Voice notes', 'Many tips arrive as voice notes. Our teammate recorded this one on an iPhone, reading a '
                                  'sample scam.'),
    ('voice2', '05 · Voice notes', 'It hears the UPI ID even when it’s spoken, writes it out, and checks it. High risk, '
                                   'ninety.'),
    ('ring', '06 · Every check helps the next', 'The next day, a new group sends a new message, with the same UPI ID.'),
    ('graph', '06 · Every check helps the next', 'It’s linked to the earlier check, instantly. Scammers can change their '
                                                 'words. They can’t hide where the money goes.'),
    ('share', '07 · Share', 'One tap sends the verdict to the family WhatsApp group, in their language.'),
    ('telegram', '08 · Telegram', 'No app to install: forward it to our Telegram bot. In a real chat, verdicts came back in '
                                  'two to five seconds, and an ordinary rent request got no warning.'),
    ('quiz', '09 · Spot the scam', 'And Spot the Scam turns it into a quiz that families share.'),
    ('trust', '10 · Built to be trusted', 'It never calls anyone a fraud. It shows the evidence, links to SEBI Check and the '
                                          '1930 helpline, and stores identifiers only as salted hashes.'),
    ('results', '11 · Measured', 'On a hundred and twenty-eight messages it had never seen, it flagged sixty-one of '
                                 'sixty-four scams, with zero false alarms.'),
    ('timelapse', '12 · Behind the scenes', 'We built it in three days, at Hacker House Goa.'),
    ('close', '', 'Check Before You Pay. Live today. Before you pay anyone, check.'),
]
TIMELAPSE_LINES = [(9.0, 'Day one, we locked the idea: a check anyone can run before they pay.'),
                   (18.5, 'Day two, the first check ran end to end, and we tested it on a hundred and twenty-eight messages '
                          'it had never seen.'),
                   (29.5, 'Day three, it went live: on the web, on Telegram, with alerts to family.')]
PHONE_SCENES = ['personas', 'check', 'evidence', 'listen', 'voice2', 'ring', 'share', 'quiz']
LEAD, TAIL = 0.4, 0.55
MIN_DUR = dict(cold=6.5, title=7.0, check=7.5, evidence=6.5, share=7.0, quiz=6.5, close=8.5, voice2=7.5, graph=8.5,
               personas=10.0, ring=6.5, decide=17.0)
scenes, t = [], 0.0
for sid, chapter, say in S:
    wav, n = tts(say)
    extra = (LISTEN[0] + LISTEN[1] + 1.8) if sid == 'listen' else (REC + 1.4) if sid == 'voice' else 0
    dur = max(LEAD + n + TAIL + extra, MIN_DUR.get(sid, 0))
    if sid == 'timelapse':
        dur = TL_LEN + 1.6
    scenes.append(dict(id=sid, chapter=chapter, t0=t, t1=t + dur, say=str(wav), say_at=t + LEAD, say_len=n, text=say))
    t += dur
TOTAL = t
sc = {s['id']: s for s in scenes}
print('scenes:', [(s['id'], round(s['t1'] - s['t0'], 1)) for s in scenes], 'total', round(TOTAL, 1), flush=True)

narration = [dict(at=s['say_at'], file=s['say'], len=s['say_len'], text=s['text']) for s in scenes]
for offset, line in TIMELAPSE_LINES:
    wav, n = tts(line)
    narration.append(dict(at=sc['timelapse']['t0'] + offset, file=str(wav), len=n, text=line))


def chunks(text):
    parts = re.split(r'(?<=[.!?:])\s+', text)
    out = []
    for p in parts:
        while len(p) > 64 and ', ' in p[20:]:
            k = p.index(', ', 20) + 1
            out.append(p[:k]); p = p[k:].strip()
        if p:
            out.append(p)
    return out


captions = []
for x in narration:
    cs = chunks(x['text']); total = sum(len(c) for c in cs); at = x['at']
    for c in cs:
        d = x['len'] * len(c) / total
        captions.append(dict(t0=at, t1=at + d, text=c)); at += d

# ---- phones: segments, taps, chips, camera ----------------------------------------------------------------------
tracks, taps, chips, cam = {'en': [], 'hi': []}, [], [], []
audio = []


def seg(lang, t0, t1, img, y0=0, y1=None):
    h = META[lang][img]['height']
    clamp = lambda y: max(0, min(y, h - VIEW))
    tracks[lang].append(dict(t0=t0, t1=t1, img=f'{lang}_{img}', y0=clamp(y0), y1=clamp(y0 if y1 is None else y1)))
    return clamp(y0 if y1 is None else y1)


def tap(lang, at, img, name, scroll=0):
    b = META[lang][img]['boxes'][name]
    taps.append(dict(t=at, lang=lang, x=(b['x'] + b['w'] / 2) * K, y=(b['y'] + b['h'] / 2 - scroll) * K))


def at_stage(lang, img, name, scroll):
    b = META[lang][img]['boxes'][name]
    return PHX[lang] + 12 + (b['x'] + b['w'] / 2) * K, PHY + 12 + STATUS + (b['y'] + b['h'] / 2 - scroll) * K


def key(t_, cx=960, cy=540, s=1.0):
    cam.append(dict(t=t_, cx=cx, cy=cy, s=s))


listen_at = {}
for lang in ('en', 'hi'):
    m = META[lang]
    a = sc['personas']; d = a['t1'] - a['t0']
    seg(lang, a['t0'] - 0.01, a['t0'] + d * 0.4, 'home'); seg(lang, a['t0'] + d * 0.4, a['t1'], 'filled1')
    a = sc['check']; tp = a['t0'] + 0.7
    seg(lang, a['t0'], tp + 0.15, 'filled1'); tap(lang, tp, 'filled1', 'submit')
    seg(lang, tp + 0.15, tp + 2.0, 'loading1'); seg(lang, tp + 2.0, a['t1'], 'verdict1', 0, 0)
    chips.append(dict(lang=lang, t0=tp + 2.1, t1=a['t1'] - 0.2,
                      text=('High risk · ' if lang == 'en' else 'ज़्यादा ख़तरा · ') + f'{first[lang]["latency_ms"] / 1000:.1f} s'))
    a = sc['evidence']; d = a['t1'] - a['t0']
    sig = m['verdict1']['boxes']['signals']; ys = sig['y'] - 30
    seg(lang, a['t0'], a['t1'], 'verdict1', ys, ys)
    a = sc['listen']; start = a['say_at'] + a['say_len'] + 0.35
    at = start if lang == 'hi' else start + LISTEN[0] + 1.1
    ln = LISTEN[0] if lang == 'hi' else LISTEN[1]
    listen_at[lang] = [at, at + ln]
    seg(lang, a['t0'], at, 'verdict1', 0, 0); tap(lang, at - 0.15, 'verdict1', 'listen')
    seg(lang, at, at + ln, 'listen', 0, 0); seg(lang, at + ln, a['t1'], 'verdict1', 0, 0)
    audio.append(dict(at=at + 0.2, file=str(CAP / f'{lang}_listen.mp3'), len=ln, gain=1.0))
    a = sc['voice2']; d = a['t1'] - a['t0']
    tb = m['vverdict']['boxes']['transcript']; yt = tb['y'] + tb['h'] - 600
    seg(lang, a['t0'], a['t0'] + 0.5, 'vloading', 0, 0)
    seg(lang, a['t0'] + 0.5, a['t0'] + d * 0.35, 'vverdict', 0, 0)
    seg(lang, a['t0'] + d * 0.35, a['t0'] + d * 0.55, 'vverdict', 0, yt)
    seg(lang, a['t0'] + d * 0.55, a['t1'], 'vverdict', yt, yt)
    chips.append(dict(lang=lang, t0=a['t0'] + 0.7, t1=a['t1'] - 0.2,
                      text=('High risk · ' if lang == 'en' else 'ज़्यादा ख़तरा · ') + str(vc[lang]['score'])))
    a = sc['ring']; d = a['t1'] - a['t0']
    another = m['verdict1']['boxes']['another']; ya = max(0, min(another['y'] - 560, m['verdict1']['height'] - VIEW))
    seg(lang, a['t0'], a['t0'] + 0.8, 'verdict1', 0, ya); tap(lang, a['t0'] + 0.95, 'verdict1', 'another', scroll=ya)
    seg(lang, a['t0'] + 0.8, a['t0'] + 1.1, 'verdict1', ya, ya)
    seg(lang, a['t0'] + 1.1, a['t0'] + 2.2, 'filled2'); tap(lang, a['t0'] + 2.0, 'filled2', 'submit')
    seg(lang, a['t0'] + 2.2, a['t0'] + 3.5, 'loading2')
    ring = m['verdict2']['boxes']['ring']; yr = ring['y'] - 420
    seg(lang, a['t0'] + 3.5, a['t0'] + 4.4, 'verdict2', 0, 0)
    seg(lang, a['t0'] + 4.4, a['t1'] + 0.01, 'verdict2', 0, yr)
    a = sc['share']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.3, 'share', 0, 0); seg(lang, a['t0'] + d * 0.3, a['t1'], 'share', 0, 380)
    a = sc['quiz']; d = a['t1'] - a['t0']
    seg(lang, a['t0'], a['t0'] + d * 0.5, 'quiz1'); tap(lang, a['t0'] + d * 0.45, 'quiz1', 'scam')
    seg(lang, a['t0'] + d * 0.5, a['t1'], 'quiz2')

# Camera: wide by default; pushes in where the eye should go.
a = sc['personas']; key(a['t0'], s=0.96); key(a['t1'], s=1.0)
a = sc['check']; key(a['t0'] + 2.6, s=1.0); key(a['t0'] + 3.8, cy=470, s=1.16); key(a['t1'], cy=470, s=1.18)
a = sc['evidence']; d = a['t1'] - a['t0']
ex, ey = at_stage('en', 'verdict1', 'signals', META['en']['verdict1']['boxes']['signals']['y'] - 30)
hx, hy = at_stage('hi', 'verdict1', 'signals', META['hi']['verdict1']['boxes']['signals']['y'] - 30)
key(a['t0'], s=1.0); key(a['t0'] + 0.9, ex, ey - 120, 1.75); key(a['t0'] + d * 0.5, ex, ey - 60, 1.8)
key(a['t0'] + d * 0.5 + 0.9, hx, hy - 120, 1.75); key(a['t1'] - 0.6, hx, hy - 60, 1.8); key(a['t1'] + 0.2, s=1.0)
a = sc['listen']
for lang in ('hi', 'en'):
    lx, ly = at_stage(lang, 'verdict1', 'listen', 0)
    s0, s1 = listen_at[lang]
    key(s0 - 0.6, lx + 110, ly + 120, 1.6); key(s1, lx + 110, ly + 120, 1.62)
key(a['t0'], s=1.0); key(a['t1'] + 0.1, s=1.0)
a = sc['voice2']; d = a['t1'] - a['t0']
for lang, frac in (('en', 0.55), ('hi', 0.78)):
    b = META[lang]['vverdict']['boxes']['transcript']; yt = b['y'] + b['h'] - 600
    tx, ty = at_stage(lang, 'vverdict', 'transcript', max(0, min(yt, META[lang]['vverdict']['height'] - VIEW)))
    key(a['t0'] + d * frac, tx, ty - 40, 1.7); key(a['t0'] + d * frac + d * 0.18, tx, ty - 40, 1.72)
key(a['t0'], s=1.0); key(a['t0'] + d * 0.4, s=1.0); key(a['t1'] + 0.1, s=1.0)
a = sc['ring']; d = a['t1'] - a['t0']
ry = PHY + 12 + STATUS + 420 * K
key(a['t0'] + 4.4, s=1.0); key(a['t1'], 960, ry, 1.3)
a = sc['share']; key(a['t0'], s=1.0); key(a['t1'], s=1.05)
a = sc['quiz']; key(a['t0'], s=1.0); key(a['t1'], s=1.04)
cam.sort(key=lambda k: k['t'])

a = sc['voice']; rec_at = a['say_at'] + a['say_len'] + 0.3
audio.append(dict(at=rec_at, file=str(VOICE), len=REC, gain=1.25))
env = {'hi': envelope(CAP / 'hi_listen.mp3'), 'en': envelope(CAP / 'en_listen.mp3'), 'voice': envelope(VOICE)}
ve = np.array(env['voice']); talk = np.where(ve > 0.12)[0]
sp0, sp1 = (talk[0] / 30, talk[-1] / 30) if len(talk) else (0.3, REC - 0.3)
words = 'Sample. Join our VIP stock tip group. Guaranteed 30% returns every month. Send ₹50,000 to sample dot desk at Y B L today.'.split()
wl = [len(w) + 1 for w in words]; acc, word_t = 0, []
for w, l in zip(words, wl):
    word_t.append(dict(w=w, t=rec_at + sp0 + (sp1 - sp0) * acc / sum(wl))); acc += l

timeline = dict(total=TOTAL, scenes=[{k: v for k, v in s.items() if k not in ('say',)} for s in scenes], tracks=tracks,
                taps=taps, chips=chips, cam=cam, captions=captions, listen=listen_at, env=env, rec=[rec_at, rec_at + REC],
                words=word_t, phoneScenes=PHONE_SCENES, phx=PHX, phy=PHY,
                first={l: dict(ms=first[l]['latency_ms'], score=first[l]['score']) for l in first},
                voiceScore=vc['en']['score'], tl=[sc['timelapse']['t0'] + 0.6, sc['timelapse']['t0'] + 0.6 + TL_LEN])
stage = (HERE / 'stage_film.html').read_text(encoding='utf-8').replace('/*TIMELINE*/', 'window.TL = ' + json.dumps(
    timeline, ensure_ascii=False) + ';').replace('STATUSICONS', STATUS_HTML)
(WORK / 'stage.html').write_text(stage, encoding='utf-8')
(WORK / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False), encoding='utf-8')
for f in ('qr.png', 'icon.svg'):
    shutil.copy(CAP / f, WORK / f)

t_end = min(TOTAL, args.start + args.preview) if args.preview else TOTAL
frames = int((t_end - args.start) * args.fps)
video_only = WORK / 'video_only.mp4'
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p']


def render_frames(f0, count, path):
    enc = subprocess.Popen([FFMPEG, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(args.fps), '-c:v',
                            'mjpeg', '-i', '-', *ENC, str(path)], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    t0 = time.monotonic()
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='chrome')
        pg = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=args.scale)
        pg.goto((WORK / 'stage.html').as_uri())
        pg.wait_for_function('window.READY === true', timeout=180000)
        for i in range(f0, f0 + count):
            pg.evaluate(f'render({args.start + i / args.fps:.4f})')
            enc.stdin.write(pg.screenshot(type='jpeg', quality=95, timeout=180000))
            if (i - f0) % 600 == 0:
                print(f'[{f0}] {i - f0}/{count} {time.monotonic() - t0:.0f}s', flush=True)
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
    failed = [w for w, p in enumerate(procs) if p.wait()]  # wait for all; a busy machine can time out one screenshot
    for w in failed:
        print('re-rendering slice', w, flush=True)
        if subprocess.call(cmd + ['--worker', str(w)]):
            sys.exit(f'render worker {w} failed twice')
    (WORK / 'segments.txt').write_text(''.join(f"file 'seg_{w}.mp4'" + chr(10) for w in range(args.workers)), encoding='utf-8')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(WORK / 'segments.txt'),
                    '-c', 'copy', str(video_only)], check=True)
else:
    render_frames(0, frames, video_only)
print('rendered', frames, 'frames in', round(time.monotonic() - started), 's', flush=True)

# ---- the timelapse, composited into its window ----------------------------------------------------------------------
tl_at = timeline['tl'][0] - args.start
if args.audio_only and (WORK / 'video_tl.mp4').exists():
    video_only = WORK / 'video_tl.mp4'
elif -TL_LEN < tl_at < t_end - args.start:
    sx = args.scale
    W_, H_, X_, Y_ = round(1280 * sx), round(720 * sx), round(320 * sx), round(214 * sx)
    W_, H_ = W_ - W_ % 2, H_ - H_ % 2
    mask = Image.new('L', (W_, H_), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W_ - 1, H_ - 1], radius=round(26 * sx), fill=255)
    mask.save(WORK / 'tlmask.png')
    ff = (f'[1:v]scale={W_}:{H_}:flags=lanczos,unsharp=5:5:0.6:5:5:0,fps={args.fps},format=rgba[tl];'
          f'[2:v]format=gray[m];[tl][m]alphamerge,fade=t=in:st=0:d=0.5:alpha=1,'
          f'fade=t=out:st={TL_LEN - 0.5:.2f}:d=0.5:alpha=1,setpts=PTS-STARTPTS+{max(0, tl_at):.3f}/TB[tla];'
          f'[0:v][tla]overlay={X_}:{Y_}:eof_action=pass:format=auto[v]')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(video_only), '-i', str(TIMELAPSE), '-loop', '1', '-i',
                    str(WORK / 'tlmask.png'), '-filter_complex', ff, '-map', '[v]', '-c:v', 'libx264', '-preset', 'medium',
                    '-crf', '15', '-pix_fmt', 'yuv420p', '-r', str(args.fps), str(WORK / 'video_tl.mp4')], check=True)
    video_only = WORK / 'video_tl.mp4'
    print('timelapse composited', flush=True)

# ---- audio: narration, the app's audio and the iPhone voice note over a music bed that dips under the voice ---------
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
    else:
        ch += f',afade=t=in:d=0.02,afade=t=out:st={max(0, x["len"] - 0.05):.2f}:d=0.05'
    chains.append(f'{ch},adelay={ms}|{ms}[f{n}]'); fg.append(f'[f{n}]')
b = len(items) + 1
inputs += ['-ss', f'{args.start:.2f}', '-i', str(BGM)]
chains.append(''.join(fg) + f'amix=inputs={len(fg)}:normalize=0,apad=whole_dur={span:.2f}[fgmix]')
chains.append('[fgmix]asplit=2[fg1][key]')
chains.append(f'[{b}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{span:.2f},volume=0.26,'
              f'afade=t=in:d=1.5,afade=t=out:st={max(0, span - 3.5):.2f}:d=3.5[bgm]')
chains.append('[bgm][key]sidechaincompress=threshold=0.05:ratio=3:attack=120:release=1800:makeup=1[duck]')
chains.append('[fg1][duck]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', str(video_only), *inputs, '-filter_complex', ';'.join(chains),
                '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-t', f'{span:.2f}',
                '-movflags', '+faststart', str(args.out)], check=True)
print('wrote', args.out, round(args.out.stat().st_size / 1e6, 1), 'MB', flush=True)
