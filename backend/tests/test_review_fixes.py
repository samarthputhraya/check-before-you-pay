"""Regressions from the 29 Oct review: real tip-group messages must score, re-checks must not drift,
and shared hosts or UPI names must never become links or stored domains."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import llm, lookups
from backend.app import app
from backend.extraction import Claim, Extraction, regex_extract, verified_extraction
from backend.links import identifiers
from backend.lookups import phishing_hits as real_phishing_hits  # bound before conftest replaces it
from backend.rate_limit import client_ip
from backend.signals import evaluate

HIGH = ('Investment: pay sample@ybl for an institutional account. 300% guaranteed. '
        'Download the app from http://kite-zerodha-app.in')


def body(text, owner='u_review', lang='en'):
    return {'lang': lang, 'anon_id': owner, 'input': {'text': text}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'checks.db'))
    return TestClient(app)


@pytest.mark.parametrize(('text', 'upi'), [
    ('Invest in our stock tips group. Pay ₹10,000 to stockpro@ybl.', 'stockpro@ybl'),
    ('UPI: rk.sharma@okaxis.', 'rk.sharma@okaxis'),
    ('Send it to 9876543210@ybl.', '9876543210@ybl'),
])
def test_upi_id_at_the_end_of_a_sentence_is_found(text, upi):
    assert regex_extract(text).entities.upi_ids == [upi]


def test_email_address_is_not_a_upi_id():
    assert regex_extract('Write to rk@gmail.com for details').entities.upi_ids == []


@pytest.mark.parametrize('text', ['Pay to tradepro.vip@ybl now', 'Pay rahul.sharma@okaxis today'])
def test_upi_name_is_never_read_as_a_website(text):
    assert regex_extract(text).entities.domains == []


def test_real_website_at_the_end_of_a_sentence_is_still_found():
    assert regex_extract('Download from kite-zerodha-app.in.').entities.domains == ['kite-zerodha-app.in']


@pytest.mark.parametrize('text', [
    'Invest in our stock tips group. Pay ₹10,000 to stockpro@ybl.',
    'स्टॉक मार्केट टिप्स: रोज़ 5% मुनाफ़ा। rk.sharma@ybl पर भेजें',
    'हर महीने 30% गारंटीड रिटर्न। rk.sharma@ybl पर 5000 भेजें',
    'Daily 5% profit guaranteed in crypto. Deposit 10000 to rk.sharma@ybl',
    'Bank Nifty option tips. Pay 4999 to rk.sharma@ybl',
    'Forex signals group. Pay 2999 to rk.sharma@ybl to join',
])
def test_tip_group_payment_requests_get_s1(text):
    assert 'S1' in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize('text', [
    'Please pay 500 to shop@ybl for the groceries and return the bag',
    'Send 1000 to help@ybl for our non-profit food drive',
])
def test_ordinary_payments_get_no_s1(text):
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]


def test_verified_investment_claim_gives_s1_context():
    text = 'Join our VIP club. Pay 5000 to club@ybl'
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]
    claimed = verified_extraction(Extraction(claims=[Claim(type='vip_or_institutional_account', quote='VIP club')]), text)
    assert 'S1' in [s.id for s in evaluate(text, claimed, {})]


def test_rechecking_the_same_message_keeps_the_same_score(client, monkeypatch):
    async def failed_ages(domains):
        return {}, True  # a partial check is never cached, so every re-check is scored again

    monkeypatch.setattr(lookups, 'domain_ages', failed_ages)
    verdicts = [client.post('/api/check', json=body(HIGH, owner=f'u_{i}')).json() for i in range(3)]
    assert [v['score'] for v in verdicts] == [verdicts[0]['score']] * 3
    assert verdicts[0]['band'] == 'high_risk'
    assert all(v['ring']['linked_checks'] == 0 for v in verdicts)
    # A different message with the same UPI ID is a real link.
    other = client.post('/api/check', json=body('Stock tips: pay 5000 to sample@ybl today')).json()
    assert 'same_upi' in other['ring']['via']


def test_reported_copy_of_the_same_message_still_counts(client, monkeypatch):
    async def failed_ages(domains):
        return {}, True

    monkeypatch.setattr(lookups, 'domain_ages', failed_ages)
    first = client.post('/api/check', json=body(HIGH)).json()
    assert client.post('/api/report', json={'check_id': first['check_id'], 'anon_id': 'u_review',
                                            'consent_store_text': False}).status_code == 200
    again = client.post('/api/check', json=body(HIGH, owner='u_other')).json()
    assert again['ring']['linked_reports'] == 1


def test_shared_hosts_do_not_link_unrelated_checks(client):
    client.post('/api/check', json=body(HIGH + ' Join https://t.me/+VipGroup1'))
    benign = client.post('/api/check', json=body('Our book club meets weekly, join https://t.me/+BookClub999')).json()
    assert 'same_domain' not in benign['ring']['via']
    assert 'S4' not in [s['id'] for s in benign['signals']]


def test_domain_links_ignore_www_and_skip_shared_platforms():
    found = identifiers(regex_extract('See https://www.Kite-Zerodha-App.in and https://drive.google.com/file/d/x'))
    assert [(i.type, i.masked) for i in found] == [('domain', 'kite-zerodha-app.in')]


def test_unconfigured_phishing_feed_is_off_not_failed(monkeypatch, tmp_path):
    assert real_phishing_hits(['https://kite-zerodha-app.in/']) == ([], False)
    monkeypatch.setenv('PHISHTANK_FEED_PATH', str(tmp_path / 'missing.json'))
    assert real_phishing_hits(['https://kite-zerodha-app.in/']) == ([], True)


def test_client_ip_is_the_entry_the_proxy_appended():
    request = SimpleNamespace(headers={'x-forwarded-for': '203.0.113.9, 198.51.100.77'}, client=SimpleNamespace(host='10.0.0.1'))
    assert client_ip(request) == '198.51.100.77'
    assert client_ip(SimpleNamespace(headers={}, client=SimpleNamespace(host='10.0.0.1'))) == '10.0.0.1'


def test_spoofed_forwarded_for_does_not_reset_the_ip_limit(client, monkeypatch):
    monkeypatch.setenv('IP_CHECKS_PER_HOUR', '3')
    for i in range(3):
        assert client.post('/api/check', json=body('hello', owner=f'u_ip{i}'),
                           headers={'x-forwarded-for': f'203.0.113.{i}, 198.51.100.77'}).status_code == 200
    spoofed = client.post('/api/check', json=body('hello', owner='u_ip9'),
                          headers={'x-forwarded-for': '192.0.2.1, 198.51.100.77'})
    assert spoofed.status_code == 429


class _Models:
    def __init__(self):
        self.calls = 0

    async def list(self):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError('429 at boot')

        async def listing():
            yield SimpleNamespace(name='models/gemini-x-flash-lite', supported_actions=['generateContent'])
        return listing()


def test_model_discovery_retries_after_a_failed_boot(monkeypatch):
    monkeypatch.setenv('GEMINI_EXTRACT_MODEL', 'models/gemini-x-flash-lite')

    async def scenario():
        providers = llm.Providers()
        providers.google = SimpleNamespace(aio=SimpleNamespace(models=_Models()))
        providers._attempted = True
        await providers._discover_models()
        assert not providers.ready
        await providers.initialize()  # within 30 s of the failure: no retry yet
        assert providers._retry_task is None
        providers._retry_at = 0
        await providers.initialize()
        await providers._retry_task
        return providers

    providers = asyncio.run(scenario())
    assert providers.ready and providers.models['extract'] == 'gemini-x-flash-lite'
