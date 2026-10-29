"""Regression tests for cache identity and retrying failed report writes."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.app import app
from backend.cache import input_hash
from backend.inputs import ValidInput
from backend.schemas import EventRequest


def key(text: str) -> str:
    return input_hash(ValidInput(text, None, None, None, None))


@pytest.mark.parametrize(('first', 'second'), [
    ('https://example.com/Pay', 'https://example.com/pay'),
    ('t.me/InviteToken', 't.me/invitetoken'),
    ('TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjF', 'TQ5NGy8Ke3b5JkEzVb9Ji8u2JAoPTxRQjf'),
])
def test_case_sensitive_identifiers_have_distinct_cache_keys(first, second):
    assert key(first) != key(second)


@pytest.mark.parametrize(('first', 'second'), [
    ('HELLO\u200b   world', 'hello world'),
    ('Pay SAMPLE@YBL', 'pay sample@ybl'),
    ('https://EXAMPLE.com/Pay', 'https://example.com/Pay'),
    ('0x' + 'Ab' * 20, '0x' + 'ab' * 20),
])
def test_normalization_still_shares_equivalent_inputs(first, second):
    assert key(first) == key(second)


def test_failed_report_save_retains_consented_text_for_retry(tmp_path, monkeypatch):
    path = tmp_path / 'recovery.db'
    monkeypatch.setenv('SQLITE_PATH', str(path))
    client = TestClient(app)
    message = '(test, made up) (sample) Investment: pay sample@ybl'
    checked = client.post('/api/check', json={'lang': 'en', 'anon_id': 'u_owner', 'input': {'text': message}}).json()
    body = {'check_id': checked['check_id'], 'anon_id': 'u_owner', 'consent_store_text': True}
    original = db.add_report

    def failed(*args, **kwargs):
        raise sqlite3.OperationalError('database temporarily unavailable')

    monkeypatch.setattr(db, 'add_report', failed)
    assert client.post('/api/report', json=body).status_code == 503
    monkeypatch.setattr(db, 'add_report', original)
    response = client.post('/api/report', json=body)
    assert response.status_code == 200
    with db.session(path) as con:
        assert con.execute('SELECT text_if_consented FROM reports').fetchone()[0] == message


def test_returning_referral_does_not_count_as_new_user(tmp_path):
    path = tmp_path / 'metrics.db'
    for event in [
        EventRequest(anon_id='u_sharer', event='share_clicked'),
        EventRequest(anon_id='u_existing', event='visit'),
        EventRequest(anon_id='u_existing', event='ref_visit', ref='u_sharer'),
        EventRequest(anon_id='u_new', event='visit', ref='u_sharer'),
        EventRequest(anon_id='u_new', event='ref_visit', ref='u_sharer'),
    ]:
        db.record_event(path, event)
    assert db.stats(path).k_factor == 1.0
