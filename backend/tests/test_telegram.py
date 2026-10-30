"""Telegram HTTP is mocked; the existing extraction/pipeline fixtures stay offline."""
from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import db, pipeline, rate_limit, telegram, telegram_setup
from backend.app import app
from backend.errors import ApiError

SECRET = 'unit-test-webhook-secret-32-characters'
HEADERS = {'X-Telegram-Bot-Api-Secret-Token': SECRET}


def update(number=1, **message):
    return {'update_id': number, 'message': {'message_id': number,
        'chat': {'id': 123, 'type': 'private'}, 'from': {'id': 123, 'language_code': 'hi'},
        **message}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'app.db'))
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123:unit-test-token')
    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://app.example.com')
    telegram._seen.clear()
    telegram._active.clear()
    telegram._languages.clear()
    replies = []
    image = io.BytesIO()
    Image.new('RGB', (20, 20), 'white').save(image, 'JPEG')

    def handle(request):
        if request.url.path.endswith('/sendMessage'):
            replies.append(json.loads(request.content))
            return httpx.Response(200, json={'ok': True, 'result': {'message_id': 1}})
        if request.url.path.endswith('/getFile'):
            return httpx.Response(200, json={'ok': True, 'result': {'file_path': 'photos/test.jpg'}})
        if '/file/' in request.url.path:
            return httpx.Response(200, content=image.getvalue())
        raise AssertionError('Unexpected Telegram operation')
    monkeypatch.setattr(telegram, '_client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    with TestClient(app) as c:
        yield c, replies, tmp_path / 'app.db'


@pytest.mark.parametrize('headers', [{}, {'X-Telegram-Bot-Api-Secret-Token': 'wrong'}])
def test_invalid_secret_never_processes(client, headers):
    c, replies, _ = client
    response = c.post('/api/telegram/webhook', json=update(text='private'), headers=headers)
    assert response.status_code == 401
    assert not replies and not telegram._seen


def test_text_reuses_pipeline_masks_evidence_and_keeps_referral(client):
    c, replies, path = client
    text = 'Investment: pay sample@ybl for an institutional account. 300% guaranteed.'
    assert c.post('/api/telegram/webhook', json=update(text=text), headers=HEADERS).status_code == 200
    assert len(replies) == 1 and replies[0]['chat_id'] == 123
    body = replies[0]['text']
    assert telegram.BAND_LABELS['hi'][0] in body and 'high_risk' not in body and '/100' in body  # sender's language is hi
    assert 'sample@ybl' not in body
    assert '?ref=' + telegram.anon_id(123) in body
    assert 'parse_mode' not in replies[0]
    with db.session(path) as con:
        row = con.execute('SELECT anon_id,lang FROM checks').fetchone()
        assert row['anon_id'] == telegram.anon_id(123) and row['lang'] == 'hi'
        assert text not in '\n'.join(con.iterdump())
    # Duplicate delivery produces no extra check or reply.
    c.post('/api/telegram/webhook', json=update(text=text), headers=HEADERS)
    assert len(replies) == 1


def test_photo_uses_existing_media_validation(client):
    c, replies, path = client
    response = c.post('/api/telegram/webhook', headers=HEADERS,
        json=update(photo=[{'file_id': 'photo', 'width': 20, 'height': 20, 'file_size': 700}]))
    assert response.status_code == 200 and '/100' in replies[0]['text'] and 'high_risk' not in replies[0]['text']
    with db.session(path) as con:
        assert con.execute('SELECT input_type FROM checks').fetchone()[0] == 'image'


def test_unsupported_message_and_oversized_voice(client):
    c, replies, path = client
    c.post('/api/telegram/webhook', headers=HEADERS, json=update(sticker={'file_id': 'sticker'}))
    assert 'screenshot or voice' in replies[-1]['text']
    c.post('/api/telegram/webhook', headers=HEADERS,
           json=update(2, voice={'file_id': 'audio', 'duration': 121, 'mime_type': 'audio/ogg'}))
    assert '2 minutes' in replies[-1]['text']
    assert db.stats(path).checks == 0


def test_rate_limit_is_applied_before_provider_or_media_download(client, monkeypatch):
    def limited(*args):
        raise ApiError(429, 'rate_limited', 'Too many checks. Please try again in an hour.')
    monkeypatch.setattr(rate_limit, 'enforce', limited)
    c, replies, path = client
    c.post('/api/telegram/webhook', headers=HEADERS, json=update(text='Pay sample@ybl'))
    assert 'Too many checks' in replies[0]['text']
    assert db.stats(path).checks == 0


def test_commands_do_not_use_up_checks(client, monkeypatch):
    calls = []
    monkeypatch.setattr(rate_limit, 'enforce', lambda *args: calls.append(args))
    c, replies, _ = client
    for n, text in enumerate(['/start', '/help', '/lang hi'], 1):
        c.post('/api/telegram/webhook', headers=HEADERS, json=update(n, text=text))
    assert len(replies) == 3 and not calls


def test_language_override_and_group_privacy(client):
    c, replies, path = client
    c.post('/api/telegram/webhook', headers=HEADERS, json=update(text='/lang ta'))
    c.post('/api/telegram/webhook', headers=HEADERS, json=update(2, text='Pay for lunch to sample@ybl'))
    with db.session(path) as con:
        assert con.execute('SELECT lang FROM checks').fetchone()[0] == 'ta'
    c.post('/api/telegram/webhook', headers=HEADERS,
           json=update(3, chat={'id': -123, 'type': 'group'}, text='private group text'))
    assert len(replies) == 2


def test_hmac_identity_changes_with_salt(monkeypatch):
    first = telegram.anon_id(123)
    assert first.startswith('u_tg_') and len(first) == 37
    monkeypatch.setenv('IDENTIFIER_SALT', 'a-different-test-only-salt-long-enough')
    assert telegram.anon_id(123) != first


@pytest.mark.asyncio
async def test_response_is_sent_before_background_processing(monkeypatch, tmp_path):
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', SECRET)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123:unit-test-token')
    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://app.example.com')
    telegram._seen.clear()
    telegram._active.clear()
    response_sent = False
    async def process(*args):
        assert response_sent
    monkeypatch.setattr(telegram, 'process', process)
    body = json.dumps(update(text='example')).encode()
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    async def send(message):
        nonlocal response_sent
        if message['type'] == 'http.response.body':
            response_sent = True
    await app({'type': 'http', 'http_version': '1.1', 'method': 'POST', 'scheme': 'https',
        'path': '/api/telegram/webhook', 'raw_path': b'/api/telegram/webhook', 'query_string': b'',
        'headers': [(b'content-type', b'application/json'), (b'x-telegram-bot-api-secret-token', SECRET.encode())],
        'server': ('testserver', 443), 'client': ('127.0.0.1', 1234)}, receive, send)


def test_failures_never_log_bot_token_or_message(client, monkeypatch, caplog):
    c, replies, _ = client
    async def broken(*args):
        raise RuntimeError('123:unit-test-token private-message')
    monkeypatch.setattr(pipeline, 'run_check', broken)
    c.post('/api/telegram/webhook', headers=HEADERS, json=update(text='private-message'))
    assert 'unit-test-token' not in caplog.text and 'private-message' not in caplog.text
    assert 'try again' in replies[0]['text']


def test_auth_before_json_and_duplicate_headers_fail(client):
    c, replies, _ = client
    assert c.post('/api/telegram/webhook', content=b'not json').status_code == 401
    duplicate = [('X-Telegram-Bot-Api-Secret-Token', SECRET)] * 2
    assert c.post('/api/telegram/webhook', json=update(text='private'), headers=duplicate).status_code == 401
    assert c.post('/api/telegram/webhook', content=b'not json', headers=HEADERS).status_code == 400
    assert not replies


def test_voice_note_uses_existing_audio_pipeline(client, monkeypatch):
    c, replies, path = client
    voice = (Path(__file__).parent / 'fixtures/voice.ogg').read_bytes()
    monkeypatch.setattr(telegram, 'download', AsyncMock(return_value=voice))
    response = c.post('/api/telegram/webhook', headers=HEADERS,
        json=update(voice={'file_id': 'voice', 'duration': 2, 'mime_type': 'audio/ogg'}))
    assert response.status_code == 200 and '/100' in replies[0]['text']
    assert 'sample@ybl' not in replies[0]['text']
    with db.session(path) as con:
        row = con.execute('SELECT input_type,band FROM checks').fetchone()
        assert row['input_type'] == 'audio' and row['band'] == 'high_risk'


@pytest.mark.parametrize('path', ['https://elsewhere.example/a.jpg', '../private', '/absolute', 'photo/../secret'])
def test_download_rejects_nontelegram_paths(client, monkeypatch, path):
    monkeypatch.setattr(telegram, 'api', AsyncMock(return_value={'file_path': path}))
    with pytest.raises(telegram.TelegramUnavailable):
        asyncio.run(telegram.download(telegram.File(file_id='photo')))


def test_unannounced_oversized_file_stops_download(client, monkeypatch):
    monkeypatch.setattr(telegram, 'api', AsyncMock(return_value={'file_path': 'photos/test.jpg'}))
    monkeypatch.setattr(telegram, '_client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=b'x' * (telegram.MAX_FILE_BYTES + 1)))))
    with pytest.raises(ApiError) as caught:
        asyncio.run(telegram.download(telegram.File(file_id='photo')))
    assert caught.value.code == 'input_too_large'


def test_bot_api_network_exception_does_not_leak_token(client, monkeypatch, caplog):
    def fail(request):
        raise httpx.ConnectError('private URL ' + str(request.url), request=request)
    monkeypatch.setattr(telegram, '_client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(fail)))
    with pytest.raises(telegram.TelegramUnavailable) as caught:
        asyncio.run(telegram.api('sendMessage', {'chat_id': 123, 'text': 'private'}))
    assert not str(caught.value)
    assert 'unit-test-token' not in caplog.text


def test_setup_rejects_wrong_bot_before_setting_webhook(client, monkeypatch):
    api = AsyncMock(return_value={'is_bot': True, 'username': 'WrongBot'})
    monkeypatch.setattr(telegram, 'api', api)
    with pytest.raises(telegram.TelegramUnavailable):
        asyncio.run(telegram_setup.setup())
    assert [call.args[0] for call in api.call_args_list] == ['getMe']


def test_setup_verifies_identity_and_registers_secret_without_printing_it(client, monkeypatch, capsys):
    api = AsyncMock(side_effect=[{'is_bot': True, 'username': 'CheckBeforeYouPayBot'}, True,
                                {'url': 'https://app.example.com/api/telegram/webhook', 'pending_update_count': 0}])
    monkeypatch.setattr(telegram, 'api', api)
    asyncio.run(telegram_setup.setup())
    assert api.call_args_list[1].args[1]['secret_token'] == SECRET
    output = capsys.readouterr().out
    assert 'registered' in output and SECRET not in output and 'unit-test-token' not in output
