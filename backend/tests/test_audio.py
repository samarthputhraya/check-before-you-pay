import asyncio
import io
import shutil
import wave
from unittest.mock import AsyncMock
from types import SimpleNamespace

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


@pytest.fixture(autouse=True)
def no_recent_failures():
    audio._failed.clear()
    yield
    audio._failed.clear()


@pytest.fixture
def saved(tmp_path, monkeypatch):
    path = tmp_path / 'audio.db'
    monkeypatch.setenv('SQLITE_PATH', str(path))
    view = CheckResponse.model_validate_json((EXAMPLES_DIR / 'check_response.json').read_text(encoding='utf-8'))
    def save(lang='hi'):
        view.lang = lang
        view.headline = {'hi': 'पैसे न भेजें', 'ta': 'பணம் அனுப்ப வேண்டாம்'}[lang]
        view.explanation = {'hi': 'सत्यापित करें sample@ybl', 'ta': 'sample@ybl முகவரியைச் சரிபார்க்கவும்'}[lang]
        view.next_steps = [NextStep(text={'hi': 'पहले जाँचें', 'ta': 'முதலில் சரிபார்க்கவும்'}[lang]), NextStep(text='not spoken')]
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
    assert view.headline in spoken and view.next_steps[0].text in spoken
    assert 'sample@ybl' not in spoken and 'not spoken' not in spoken
    assert '…' not in spoken and audio.SPOKEN_UPI[lang] in spoken  # the masked ID is named, not spelled out
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
    assert tts.await_count == 1  # a retry within a minute doesn't spend the TTS quota again
    monkeypatch.setattr(audio, 'RETRY_AFTER', 0.0)
    assert TestClient(app).get(f'/api/check/{view.check_id}/audio').status_code == 503
    assert tts.await_count == 2  # after the backoff it does try again


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


@pytest.mark.asyncio
async def test_discovery_prefers_capable_flash_lite_speech_model(monkeypatch):
    class Models:
        def __aiter__(self):
            return self.iterate()
        async def iterate(self):
            for name, actions in [('test-flash-lite', ['generateContent']),
                                  ('test-flash-tts', ['generateContent']),
                                  ('test-flash-lite-tts', ['generateContent']),
                                  ('zzz-flash-lite-tts', ['bidiGenerateContent'])]:
                yield SimpleNamespace(name='models/' + name, supported_actions=actions)
    provider = llm.Providers()
    provider.google = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=Models()))))
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    await provider.initialize()
    assert provider.models['tts'] == 'test-flash-lite-tts'
    assert provider.models['extract'] == 'test-flash-lite'


@pytest.mark.asyncio
@pytest.mark.parametrize('mime, payload', [('audio/wav', wav()), ('audio/L16;codec=pcm;rate=24000', b'\0\0' * 24000)],
                         ids=['wav', 'pcm'])
async def test_provider_normalizes_real_response_shapes(monkeypatch, mime, payload):
    generate = AsyncMock(return_value=SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[
        SimpleNamespace(inline_data=SimpleNamespace(data=payload, mime_type=mime))]))]))
    provider = llm.Providers()
    provider.initialize = AsyncMock()
    provider.models['tts'] = 'discovered-test-tts'
    provider.google = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    result = await provider.tts('पैसे भेजने से पहले जाँचें।')
    with wave.open(io.BytesIO(result)) as f:
        assert f.getnframes() == 24000
    assert generate.call_args.kwargs['model'] == 'discovered-test-tts'


@pytest.mark.asyncio
async def test_warmer_reaps_process_on_shutdown(monkeypatch):
    started = asyncio.Event()
    class Child:
        returncode = None
        killed = False
        waits = 0
        async def wait(self):
            self.waits += 1
            started.set()
            if self.returncode is None:
                await asyncio.Event().wait()
            return self.returncode
        def kill(self):
            self.killed = True
            self.returncode = -9
    child = Child()
    monkeypatch.setattr(audio.asyncio, 'create_subprocess_exec', AsyncMock(return_value=child))
    task = asyncio.create_task(audio.keep_warm())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert child.killed and child.waits == 2
