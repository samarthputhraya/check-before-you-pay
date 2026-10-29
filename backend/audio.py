"""Bounded verdict speech and persistent MP3 cache. No source messages are read."""
from __future__ import annotations

import asyncio
import hashlib
import io
import re
import wave
from contextlib import suppress

from backend import db, llm
from backend.config import get_settings
from backend.errors import ApiError
from backend.privacy import public_view

# A masked UPI ID read aloud is noise ("T A dot Y B L"); the speech says what it is instead.
_MASKED_UPI = re.compile(r'[\w.-]*…@[\w.-]+')
SPOKEN_UPI = {'en': 'this UPI ID', 'hi': 'यह UPI आईडी', 'mr': 'हा UPI आयडी', 'hinglish': 'ye UPI ID',
              'ta': 'இந்த UPI ஐடி', 'te': 'ఈ UPI ఐడీ', 'kn': 'ಈ UPI ಐಡಿ', 'bn': 'এই UPI আইডি'}

# One deployment worker. Fixed stripes bound memory and serialize duplicate requests.
_locks = [asyncio.Lock() for _ in range(32)]


def pcm_wave(data: bytes, mime: str) -> bytes:
    """Normalize Gemini WAV or explicitly described mono, little-endian L16."""
    import re
    if len(data) > 6_000_000:
        raise ValueError('audio too large')
    if data.startswith(b'RIFF') and mime.lower().split(';')[0] in ('audio/wav', 'audio/x-wav'):
        return data
    match = re.fullmatch(r'audio/(?:l16|pcm);\s*(?:codec=pcm;\s*)?rate=(\d+)', mime.lower())
    if not match or int(match[1]) not in (16000, 22050, 24000, 44100, 48000) or len(data) % 2:
        raise ValueError('unsupported speech format')
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(match[1]))
        wav.writeframes(data)
    return output.getvalue()


async def encode_mp3(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), 'rb') as wav:
        duration = wav.getnframes() / wav.getframerate()
        # Leave headroom for MP3 encoder padding; never truncate spoken advice.
        if not 0 < duration < 59 or len(data) > 6_000_000:
            raise ValueError('speech must be shorter than a minute')
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'wav', '-i', 'pipe:0',
        '-vn', '-ac', '1', '-ar', '24000', '-c:a', 'libmp3lame', '-b:a', '64k',
        '-f', 'mp3', 'pipe:1', stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        async with asyncio.timeout(2):
            result, _ = await proc.communicate(data)
    finally:
        if proc.returncode is None:
            with suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
    if proc.returncode or not result or len(result) > 1_000_000:
        raise ValueError('speech conversion failed')
    return result


async def for_check(check_id: str) -> bytes:
    try:
        async with asyncio.timeout(12):
            path = get_settings().sqlite_path
            view = await asyncio.to_thread(db.get_check, path, check_id)
            if view is None:
                raise ApiError(404, 'not_found', 'No check with that ID.')
            view = public_view(view)
            text = '\n'.join([view.headline, view.explanation] + [s.text for s in view.next_steps[:1]])
            text = _MASKED_UPI.sub(SPOKEN_UPI.get(view.lang, SPOKEN_UPI['en']), text)
            if len(text) > 2000:
                raise ValueError('speech too long')
            digest = hashlib.sha256((view.lang + '\n' + text).encode()).hexdigest()
            lock = _locks[int(hashlib.sha256((str(path) + check_id).encode()).hexdigest()[:8], 16) % len(_locks)]
            async with lock:
                cached = await asyncio.to_thread(db.get_audio, path, check_id, digest)
                if cached is not None:
                    return cached
                async with asyncio.timeout(8):
                    wav = await llm.tts(text)
                result = await encode_mp3(wav)
                await asyncio.to_thread(db.save_audio, path, check_id, digest, result)
                return result
    except ApiError:
        raise
    except (Exception,):
        # Never expose provider details, source text or subprocess diagnostics.
        raise ApiError(503, 'audio_unavailable', 'Audio is unavailable. Please try again later.') from None
