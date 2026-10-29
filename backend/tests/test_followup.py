"""Follow-up audit: private identifier boundaries, cache failures and ring totals."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import db
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
                                      'tradepro.vip@x', 'tradepro.vip@ybl.'])
def test_email_or_upi_name_never_becomes_a_domain(identifier):
    result = regex_extract('Contact ' + identifier)
    assert result.entities.domains == []
    assert result.entities.urls == []


def test_real_bare_domains_still_accept_punctuation_and_paths():
    result = regex_extract('Visit example.org. Or example.net/path or sub.example.com/pay.')
    assert result.entities.domains == ['example.net', 'example.org', 'sub.example.com']


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
    text = 'Investment: pay sample@ybl for an institutional account. 300% guaranteed.'
    first = submit(client, text)
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
