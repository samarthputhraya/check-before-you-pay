import asyncio
import io
import shutil
import wave
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from mutagen.mp3 import MP3

from backend import audio, db, llm
from backend.app import app
from backend.config import EXAMPLES_DIR
from backend.schemas import CheckResponse, NextStep


def wav(seconds=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(24000)
        f.writeframes(b'\0\0' * (24000 * seconds))
    return output.getvalue()


@pytest.fixture
def saved(tmp_path, monkeypatch):
    path = tmp_path / 'audio.db'
    monkeypatch.setenv('SQLITE_PATH', str(path))
    view = CheckResponse.model_validate_json((EXAMPLES_DIR / 'check_response.json').read_text(encoding='utf-8'))
    def save(lang='hi'):
        view.lang = lang
        view.headline = {'hi': 'पैसे न भेजें', 'ta': 'பணம் அனுப்ப வேண்டாம்'}[lang]
        view.explanation = 'सत्यापित करें sample@ybl'
        view.next_steps = [NextStep(text='पहले जाँचें'), NextStep(text='not spoken')]
        db.save_check(path, view, [], None, None, 'test-audio', 'u_testaudio', 'text', 1.0)
        return view
    return path, save


@pytest.mark.parametrize('lang', ['hi', 'ta'])
def test_audio_masked_and_persistently_cached(saved, monkeypatch, lang):
    path, save = saved
    view = save(lang)
    tts = AsyncMock(return_value=wav())
    encoder = AsyncMock(return_value=b'test-mp3')
    monkeypatch.setattr(llm, 'tts', tts)
    monkeypatch.setattr(audio, 'encode_mp3', encoder)
    url = f'/api/check/{view.check_id}/audio'
    first = TestClient(app).get(url)
    # Fresh client, same persistent database.
    second = TestClient(app).get(url)
    assert first.status_code == second.status_code == 200
    assert first.content == second.content == b'test-mp3'
    assert first.headers['content-type'] == 'audio/mpeg'
    assert tts.await_count == encoder.await_count == 1
    spoken = tts.call_args.args[0]
    assert view.headline in spoken and 'पहले जाँचें' in spoken
    assert 'sample@ybl' not in spoken and 'not spoken' not in spoken
    with db.session(path) as con:
        assert con.execute('SELECT COUNT(*) FROM verdict_audio').fetchone()[0] == 1


@pytest.mark.parametrize('failure', [llm.ProviderUnavailable(), TimeoutError(), ValueError('private detail')])
def test_failure_clean_and_retryable(saved, monkeypatch, failure):
    _, save = saved
    view = save()
    tts = AsyncMock(side_effect=failure)
    monkeypatch.setattr(llm, 'tts', tts)
    for _ in range(2):
        response = TestClient(app).get(f'/api/check/{view.check_id}/audio')
        assert response.status_code == 503
        assert response.json()['error']['code'] == 'audio_unavailable'
        assert 'private detail' not in response.text
    assert tts.await_count == 2


def test_missing_check_does_not_synthesize(saved, monkeypatch):
    tts = AsyncMock()
    monkeypatch.setattr(llm, 'tts', tts)
    assert TestClient(app).get('/api/check/chk_unknown/audio').status_code == 404
    tts.assert_not_called()


def test_duplicate_concurrent_requests_synthesize_once(saved, monkeypatch):
    _, save = saved
    view = save()
    tts = AsyncMock(return_value=wav())
    monkeypatch.setattr(llm, 'tts', tts)
    monkeypatch.setattr(audio, 'encode_mp3', AsyncMock(return_value=b'mp3'))
    async def run():
        assert await asyncio.gather(audio.for_check(view.check_id), audio.for_check(view.check_id)) == [b'mp3', b'mp3']
    asyncio.run(run())
    assert tts.await_count == 1


def test_pcm_format_and_duration_guard():
    normalized = audio.pcm_wave(b'\0\0' * 24000, 'audio/L16;codec=pcm;rate=24000')
    with wave.open(io.BytesIO(normalized)) as f:
        assert f.getnframes() / f.getframerate() == 1
    with pytest.raises(ValueError):
        audio.pcm_wave(b'unknown', 'audio/mpeg')
    with pytest.raises(ValueError):
        asyncio.run(audio.encode_mp3(wav(60)))


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg required; installed in Docker')
def test_real_mp3_codec():
    result = asyncio.run(audio.encode_mp3(wav()))
    decoded = MP3(io.BytesIO(result))
    assert 0 < decoded.info.length < 60
    assert decoded.info.channels == 1
