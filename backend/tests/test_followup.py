"""Follow-up audit: private identifier boundaries, cache failures and ring totals."""
from __future__ import annotations

import sqlite3
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend import db, llm, weights
from backend.app import app
from backend.extraction import canonical_url, regex_extract
from backend.cache import input_hash
from backend.inputs import ValidInput


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'followup.db'))
    return TestClient(app)


def submit(client, text):
    response = client.post('/api/check', json={'lang': 'en', 'anon_id': 'u_followup', 'input': {'text': text}})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('identifier', ['tradepro.vip@gmail.com', 'foo.tradepro.vip@ybl.com',
                                      'tradepro.vip@x', 'tradepro.vip@ybl.', 'TRADEPRO.VIP@EXAMPLE.DE'])
def test_email_or_upi_name_never_becomes_a_domain(identifier):
    result = regex_extract('Contact ' + identifier)
    assert result.entities.domains == []
    assert result.entities.urls == []


def test_real_bare_domains_still_accept_punctuation_and_paths():
    result = regex_extract('Visit example.org. Or example.net/path or sub.example.com/pay.')
    assert result.entities.domains == ['example.net', 'example.org', 'sub.example.com']


@pytest.mark.parametrize('email', ['RK@EXAMPLE.DE', 'RK@EXAMPLE.UK', 'RK@EXAMPLE.INFO', 'RK@EXAMPLE.BIZ'])
def test_uppercase_email_suffixes_are_not_upi_handles(email):
    assert regex_extract(email).entities.upi_ids == []


@pytest.mark.parametrize('explanation', ['This is 100% a scam.', '100 % certain.', 'This is safe.'])
def test_explanation_certainty_falls_back(client, monkeypatch, explanation):
    monkeypatch.setattr(llm, 'explain', AsyncMock(return_value=llm.Explanation(explanation=explanation, signals=[])))
    result = submit(client, 'Investment: pay sample@ybl for an institutional account. 300% guaranteed.')
    assert result['explanation'] != explanation
    assert 'explanation' not in result['unchecked']


@pytest.mark.parametrize(('url', 'expected'), [
    ('https://example.com:80/pay', 'https://example.com:80/pay'),
    ('http://example.com:443/pay', 'http://example.com:443/pay'),
    ('https://example.com:443/pay', 'https://example.com/pay'),
    ('http://example.com:80/pay', 'http://example.com/pay'),
])
def test_url_identity_preserves_nondefault_ports(url, expected):
    assert canonical_url(url) == expected


def test_different_ports_do_not_share_cached_verdicts():
    def key(text):
        return input_hash(ValidInput(text, None, None, None, None))

    assert key('https://example.com:80/Pay') != key('https://example.com/Pay')


def test_cached_database_failure_updates_share_title(client, monkeypatch):
    # S1 alone is caution; the report adds an S4 link that lifts the next check to high risk.
    text = 'Investment: pay sample@ybl today.'
    first = submit(client, text)
    assert first['band'] == 'caution'
    client.post('/api/report', json={'check_id': first['check_id'], 'anon_id': 'u_followup',
                                    'consent_store_text': False})
    second = submit(client, text + ' Join today.')
    assert second['band'] == 'high_risk'

    def failed_save(*args, **kwargs):
        raise sqlite3.OperationalError('temporary database failure')

    monkeypatch.setattr(db, 'save_check', failed_save)
    cached = submit(client, text + ' Join today.')
    assert cached['cached'] and cached['band'] == 'caution'
    assert cached['share']['card_title'] == cached['headline']
    assert 'links' in cached['unchecked']


def test_rechecks_alone_do_not_inflate_public_ring_total(client):
    text = 'Trading: 300% guaranteed. Pay sample@ybl for an institutional account at kite-zerodha-app.in'
    first = submit(client, text)
    assert first['band'] == 'high_risk'
    repeat = submit(client, text)
    assert repeat['cached']
    assert client.get('/api/stats').json()['rings'] == 0
    distinct = submit(client, text + ' Join today.')
    assert distinct['ring']['linked_checks'] > 0
    assert client.get('/api/stats').json()['rings'] == 1


@pytest.mark.parametrize(('raw', 'expected'), [
    ('{"transcript":"complete phrase", "claims":[', 'complete phrase'),
    ('{"transcript":"cut off phrase', None),
    ('{"transcript":"a \\"quoted\\" phrase",', 'a "quoted" phrase'),
    ('{"transcript":123,', None),
    ('{"transcript":"",', None),
    ('{"claims":[{"quote":"transcript"}],', None),
    ('{"transcript":"\\ud800",', None),
])
def test_partial_media_accepts_only_complete_transcript_strings(raw, expected):
    assert llm.completed_transcript(raw) == expected


def streaming_provider(chunks, failure=None):
    provider = llm.Providers()
    provider.ready = True
    provider.models = {'extract': 'test-flash-lite'}
    closed = []

    async def stream():
        try:
            for chunk in chunks:
                yield SimpleNamespace(text=chunk)
            if failure:
                raise failure
        finally:
            closed.append(True)

    generate = AsyncMock(side_effect=lambda **kwargs: stream())
    provider.google = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate)))
    return provider, generate, closed


@pytest.mark.asyncio
async def test_streamed_media_verifies_quotes_and_closes_response():
    raw = json.dumps({'transcript': 'Pay sample@ybl. 300% guaranteed.', 'claims': [
        {'type': 'guaranteed_returns', 'quote': '300% guaranteed'},
        {'type': 'withdrawal_fee', 'quote': 'not in the source'}], 'app_names': []})
    provider, generate, closed = streaming_provider([raw[:35], raw[35:]])
    transcript, extracted = await provider.read_media(b'test audio', 'audio/ogg')
    assert transcript == 'Pay sample@ybl. 300% guaranteed.'
    assert extracted.entities.upi_ids == ['sample@ybl']
    assert len(extracted.claims) == 1
    assert generate.await_count == 1 and closed == [True]


@pytest.mark.asyncio
async def test_stream_failure_retains_complete_transcript_without_claims():
    provider, generate, closed = streaming_provider(
        ['{"transcript":"Investment: pay sample@ybl.", "claims":['], TimeoutError())
    transcript, extracted = await provider.read_media(b'test audio', 'audio/ogg')
    assert transcript == 'Investment: pay sample@ybl.' and extracted is None
    assert generate.await_count == 1 and closed == [True]


@pytest.mark.asyncio
async def test_truncated_transcript_is_retried_then_rejected():
    provider, generate, closed = streaming_provider(['{"transcript":"never complete'], TimeoutError())
    with pytest.raises(llm.ProviderUnavailable):
        await provider.read_media(b'test audio', 'audio/ogg')
    assert generate.await_count == 2 and closed == [True, True]


@pytest.mark.asyncio
async def test_stream_does_not_swallow_request_cancellation():
    provider, generate, closed = streaming_provider(['{"transcript":"complete",'], asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await provider.read_media(b'test audio', 'audio/ogg')
    assert generate.await_count == 1 and closed == [True]


def test_recovered_media_can_return_regex_verdict_with_unchecked_claims(client, monkeypatch):
    # Exercise orchestration directly using validated media, without needing a codec fixture.
    from backend.pipeline import run_check
    from backend.schemas import CheckRequest

    monkeypatch.setattr(llm, 'read_media', AsyncMock(return_value=('Investment: pay sample@ybl.', None)))
    monkeypatch.setattr(llm, 'extract', AsyncMock(side_effect=llm.ProviderUnavailable()))
    body = CheckRequest(lang='en', anon_id='u_followup', input={'text': 'Accompanying message'})
    result = asyncio.run(run_check(body, ValidInput(None, None, None, b'test audio', 'audio/ogg'), 'https://example.org'))
    assert result.score == weights.S1
    assert 'claims' in result.unchecked and 'transcription' not in result.unchecked
    assert result.transcript == 'Investment: pay sample@ybl.'


@pytest.mark.asyncio
@pytest.mark.parametrize('configured', ['test-flash-lite', 'models/test-flash-lite'])
async def test_model_names_copied_from_inventory_are_accepted(monkeypatch, configured):
    class Models:
        def __aiter__(self):
            return self.iterate()

        async def iterate(self):
            yield SimpleNamespace(name='models/test-flash-lite', supported_actions=['generateContent'])

    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-key')
    monkeypatch.setenv('GEMINI_EXTRACT_MODEL', configured)
    provider = llm.Providers()
    provider.google = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=Models()))))
    await provider.initialize()
    assert provider.ready and provider.models['extract'] == 'test-flash-lite'
