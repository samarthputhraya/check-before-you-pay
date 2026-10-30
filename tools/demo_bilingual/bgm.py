"""Make the instrumental music bed with Lyria 3.5: python tools/demo_bilingual/bgm.py [count]. Writes bgm/bgm_N.mp3."""
import os, sys
from pathlib import Path
for line in (Path(__file__).resolve().parents[2] / '.env.railway').read_text(encoding='utf-8').splitlines():
    if line.startswith('GEMINI_API_KEY='): os.environ['GEMINI_API_KEY'] = line.split('=', 1)[1].strip()
from google import genai
c = genai.Client()
PROMPT = ('Instrumental only, absolutely no vocals or singing. About three minutes long. A calm, warm, modern ambient '
          'track to sit under a product demo voice-over: soft felt piano, gentle warm synth pads, airy textures and a '
          'very soft, steady pulse. Hopeful and reassuring, around 80 BPM, in a major key. Even, low-key energy the whole '
          'way through: no drops, no loud builds, no sudden changes. Ends with a soft fade.')
for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2):
    r = c.models.generate_content(model='lyria-3.5', contents=PROMPT)
    for part in r.parts:
        if part.inline_data is not None:
            out = Path(__file__).parent / 'bgm' / f'bgm_{i}.mp3'; out.write_bytes(part.inline_data.data); print('saved', out, len(part.inline_data.data), flush=True)
        elif part.text:
            print('text:', part.text[:300].replace(chr(10), ' '), flush=True)
