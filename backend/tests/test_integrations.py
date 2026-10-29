"""Provider boundaries, private identifiers, lookup evidence, webhooks and real metrics."""
from __future__ import annotations

import json
import logging
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import db, llm, lookups, webhooks
from backend.app import app
from backend.cache import input_hash
from backend.extraction import Claim, Extraction, regex_extract, verified_extraction
from backend.inputs import ValidInput
from backend.links import identifier_id, identifiers
from backend.privacy import mask_text
from backend.signals import evaluate, score


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'test.db'))
    return TestClient(app)


def submit(client, text='Investment: pay sample@ybl for an institutional account. 300% guaranteed.'):
    response = client.post('/api/check', json={'lang': 'en', 'anon_id': 'u_owner', 'input': {'text': text}})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('text', ['Pay tradepro.vip@ybl.', 'Pay tradepro.vip@ybl now'])
def test_upi_is_not_a_domain(text):
    extraction = regex_extract(text)
    assert extraction.entities.upi_ids == ['tradepro.vip@ybl']
    assert extraction.entities.domains == []


def test_url_paths_are_not_independent_domains():
    extraction = regex_extract('Visit https://example.com/a/other.org')
    assert extraction.entities.domains == ['example.com']
    assert extraction.entities.urls == ['https://example.com/a/other.org']


@pytest.mark.parametrize('value', ['https://t.me/PrivateInviteToken', 't.me/PrivateInviteToken',
                                  'chat.whatsapp.com/PrivateInviteToken', 'https://example.com/path?secret=PrivateInviteToken'])
def test_invite_tokens_and_query_values_are_masked(value):
    assert 'PrivateInviteToken' not in mask_text(value)


def test_unicode_upi_is_redacted_if_extracted():
    text = 'Pay नमूना@ybl now'
    assert 'नमूना@ybl' not in mask_text(text)


def test_shared_messaging_host_is_not_a_ring_link():
    first = identifiers(regex_extract('Join https://t.me/groupA'))
    second = identifiers(regex_extract('Join https://t.me/groupB'))
    assert not set(i.id for i in first) & set(i.id for i in second)
    assert [i.type for i in first] == ['group_link']


def test_identifier_hashes_are_type_and_salt_bound(monkeypatch):
    first = identifier_id('upi', 'sample@ybl')
    assert first != identifier_id('app', 'sample@ybl')
    monkeypatch.setenv('IDENTIFIER_SALT', 'other-test-salt-at-least-32-characters')
    assert first != identifier_id('upi', 'sample@ybl')


def test_cache_normalizes_text_without_changing_wallet_case():
    def key(text):
        return input_hash(ValidInput(text, None, None, None, None))
    assert key('HELLO\u200b   world') == key('hello world')
    # Wallet identifiers themselves retain the case required by their chain.
    values = identifiers(regex_extract('TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjF'))
    assert values[0].type == 'wallet'
    assert values[0].id == identifier_id('wallet', 'TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjF')


def test_verified_claims_drop_hallucinations_and_duplicates():
    result = verified_extraction(Extraction(claims=[
        Claim(type='guaranteed_returns', quote='300% guaranteed'),
        Claim(type='guaranteed_returns', quote='300% guaranteed'),
        Claim(type='withdrawal_fee', quote='pay to withdraw')]), '300% guaranteed')
    assert len(result.claims) == 1


def test_wallet_matches_connect_reports_without_storing_address(client, tmp_path):
    wallet = 'TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjF'
    first = submit(client, wallet)
    client.post('/api/report', json={'check_id': first['check_id'], 'anon_id': 'u_owner', 'consent_store_text': False})
    second = submit(client, wallet + ' new request')
    assert second['score'] == 10
    assert second['ring']['via'] == ['same_wallet']
    assert wallet not in json.dumps(second)
    with db.session(tmp_path / 'test.db') as con:
        assert wallet not in '\n'.join(con.iterdump())


def test_cache_expires_and_report_invalidates_it(client, tmp_path):
    first = submit(client)
    path = tmp_path / 'test.db'
    with db.session(path) as con:
        key = con.execute('SELECT input_hash FROM checks WHERE id=?', (first['check_id'],)).fetchone()[0]
    assert db.cached_check(path, key, 'en') is not None
    assert db.cached_check(path, key, 'hi') is None
    assert db.cached_check(path, key, 'en', time.time() + 86401) is None
    client.post('/api/report', json={'check_id': first['check_id'], 'anon_id': 'u_owner', 'consent_store_text': False})
    assert db.cached_check(path, key, 'en') is None


def test_stats_count_usage_shares_referrals_and_server_events(client):
    check = submit(client)
    base = {'anon_id': 'u_owner', 'check_id': check['check_id']}
    for event in ['share_clicked', 'share_clicked', 'check_done', 'report']:
        assert client.post('/api/events', json=base | {'event': event}).status_code == 204
    client.post('/api/events', json={'anon_id': 'u_referred', 'event': 'ref_visit', 'ref': 'u_owner'})
    stats = client.get('/api/stats').json()
    assert stats['checks'] == 1 and stats['reports'] == 0
    assert stats['users'] == 2 and stats['languages'] == {'en': 1}
    assert stats['share_rate'] == stats['k_factor'] == 1


def test_admin_export_is_authenticated_and_readable(client, tmp_path, monkeypatch):
    submit(client)
    assert client.get('/api/admin/export').status_code == 404
    monkeypatch.setenv('ADMIN_TOKEN', 'test-only-admin-token')
    assert client.get('/api/admin/export', headers={'Authorization': 'Bearer wrong'}).status_code == 404
    result = client.get('/api/admin/export', headers={'Authorization': 'Bearer test-only-admin-token'})
    assert result.status_code == 200 and result.content.startswith(b'SQLite format 3')


@pytest.mark.asyncio
async def test_phishing_feed_matches_verified_online_urls_only(tmp_path, monkeypatch):
    path = tmp_path / 'feed.json'
    path.write_text(json.dumps([
        {'url': 'https://example.com/phish', 'verified': 'yes', 'online': 'yes'},
        {'url': 'https://example.com/offline', 'verified': 'yes', 'online': 'no'}]))
    monkeypatch.setenv('PHISHTANK_FEED_PATH', str(path))
    # Use the actual function: the suite normally stubs lookups at the pipeline boundary.
    hits, failed = REAL_PHISHING(['https://example.com/phish', 'https://example.com/offline'])
    assert hits == ['https://example.com/phish'] and not failed
    assert score(evaluate('', Extraction(), {}, hits))[0] == 40


REAL_PHISHING = lookups.phishing_hits


@pytest.mark.asyncio
async def test_gemini_retry_and_openai_fallback_use_structured_schema():
    provider = llm.Providers()
    provider._attempted = True
    provider.ready = True
    provider.models = {'extract': 'listed-model'}
    google_call = AsyncMock(side_effect=RuntimeError('provider failure'))
    openai_call = AsyncMock(return_value=SimpleNamespace(output_parsed=Extraction()))
    provider.google = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=google_call)))
    provider.openai = SimpleNamespace(responses=SimpleNamespace(parse=openai_call))
    provider._openai_model = lambda setting: 'listed-fallback'
    result = await provider.structured('extract', 'facts only', 'sample', Extraction)
    assert isinstance(result, Extraction)
    assert google_call.await_count == 2 and openai_call.await_count == 1
    assert openai_call.call_args.kwargs['store'] is False


@pytest.mark.asyncio
async def test_explanation_receives_only_masked_evidence():
    provider = llm.Providers()
    signals = evaluate('Investment: pay sample@ybl', regex_extract('Investment: pay sample@ybl'), {})
    provider.structured = AsyncMock(return_value=llm.Explanation(explanation='Verify first.', signals=[]))
    await provider.explain(signals, 'caution', 'hi', [])
    payload = provider.structured.call_args.args[2]
    assert 'sample@ybl' not in payload
    assert json.loads(payload)['band'] == 'caution'
    assert 'message' not in json.loads(payload)


@pytest.mark.asyncio
async def test_webhook_sends_masked_metadata_and_tracks_delivery(client, tmp_path, monkeypatch):
    check = submit(client)
    report = client.post('/api/report', json={'check_id': check['check_id'], 'anon_id': 'u_owner',
        'consent_store_text': True, 'note': 'private note'}).json()
    monkeypatch.setenv('VIASOCKET_REPORT_WEBHOOK_URL', 'https://workflow.example/hook')
    with db.session(tmp_path / 'test.db') as con:
        con.execute("UPDATE reports SET webhook_status='pending'")
    received = []

    def handler(request):
        received.append(json.loads(request.content))
        assert request.headers['Idempotency-Key'] == report['report_id']
        return httpx.Response(200)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(webhooks.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    await webhooks.deliver_pending()
    assert len(received) == 1
    assert 'sample@ybl' not in json.dumps(received)
    assert 'private note' not in json.dumps(received)
    assert 'u_owner' not in json.dumps(received)
    assert db.pending_webhooks(tmp_path / 'test.db') == []


@pytest.mark.asyncio
async def test_webhook_retries_stop_after_three_failures(client, tmp_path, monkeypatch):
    check = submit(client)
    client.post('/api/report', json={'check_id': check['check_id'], 'anon_id': 'u_owner', 'consent_store_text': False})
    monkeypatch.setenv('VIASOCKET_REPORT_WEBHOOK_URL', 'https://workflow.example/hook')
    with db.session(tmp_path / 'test.db') as con:
        con.execute("UPDATE reports SET webhook_status='pending'")
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    monkeypatch.setattr(webhooks.httpx, 'AsyncClient', lambda **kw: real_client(transport=transport, **kw))
    path = tmp_path / 'test.db'
    for _ in range(3):
        with db.session(path) as con:
            con.execute('UPDATE reports SET webhook_after=0')
        await webhooks.deliver_pending()
    with db.session(path) as con:
        row = con.execute('SELECT webhook_attempts,webhook_status FROM reports').fetchone()
    assert tuple(row) == (3, 'failed')


def test_report_without_webhook_logs_skip_and_still_saves(client, tmp_path, caplog):
    check = submit(client)
    with caplog.at_level(logging.INFO, logger='cbyp'):
        response = client.post('/api/report', json={'check_id': check['check_id'], 'anon_id': 'u_owner',
            'consent_store_text': False})
    assert response.status_code == 200
    assert 'viasocket not configured' in caplog.text
    with db.session(tmp_path / 'test.db') as con:
        assert con.execute('SELECT webhook_status FROM reports').fetchone()[0] == 'skipped'


@pytest.mark.asyncio
async def test_report_response_is_sent_before_failed_webhook(client, monkeypatch):
    check = submit(client)
    order = []

    async def observed_app(scope, receive, send):
        async def observed_send(message):
            if message['type'] == 'http.response.body' and not message.get('more_body'):
                order.append('response_sent')
            await send(message)
        await app(scope, receive, observed_send)

    real_client = httpx.AsyncClient
    api_client = real_client(transport=httpx.ASGITransport(app=observed_app), base_url='http://testserver')

    def failed(request):
        order.append('webhook_failed')
        raise httpx.ReadTimeout('private provider failure')

    monkeypatch.setenv('VIASOCKET_REPORT_WEBHOOK_URL', 'https://workflow.example/hook')
    monkeypatch.setattr(webhooks.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(failed), **kw))
    async with api_client:
        response = await api_client.post('/api/report', json={'check_id': check['check_id'], 'anon_id': 'u_owner',
            'consent_store_text': False})
    assert response.status_code == 200 and response.json()['ok'] is True
    assert order == ['response_sent', 'webhook_failed']


@pytest.mark.parametrize('mutation', ['unlabelled', 'no_consent', 'not_anonymized', 'duplicate_id', 'invented_quote'])
def test_seed_format_rejects_missing_labels_consent_and_unverified_quotes(tmp_path, mutation):
    from seed.load import read_messages

    row = {'id': 'chk_test', 'label': '(test, made up) (sample)',
        'text': '(test, made up) (sample) 300% guaranteed', 'source': 'made_up', 'claims': []}
    rows = [row]
    if mutation == 'unlabelled':
        row['text'] = '300% guaranteed'
    elif mutation == 'no_consent':
        row['source'] = 'consented'
        row['consent_to_use'] = False
    elif mutation == 'not_anonymized':
        row['source'] = 'consented'
        row['consent_to_use'] = True
        row['anonymized'] = False
    elif mutation == 'duplicate_id':
        rows.append(dict(row))
    else:
        row['claims'] = [{'type': 'withdrawal_fee', 'quote': 'unseen quote'}]
    (tmp_path / 'sample.json').write_text(json.dumps(rows), encoding='utf-8')
    with pytest.raises(ValueError):
        read_messages(tmp_path)
