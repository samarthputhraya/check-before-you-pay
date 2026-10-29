"""Integration review, 29 Oct: client IP behind Caddy, undecodable webhook secrets, non-investment claims, the payment
verb inside a UPI ID, and the @valid allowlist."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend import weights
from backend.extraction import Claim, Extraction, regex_extract, sebi_valid_handle, verified_extraction
from backend.payments import Dodo
from backend.rate_limit import client_ip
from backend.signals import evaluate


def request(peer, xff=None):
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers={'x-forwarded-for': xff} if xff else {})


def test_behind_caddy_the_client_is_the_rightmost_forwarded_address(monkeypatch):
    monkeypatch.setenv('TRUST_PROXY', 'caddy')
    assert client_ip(request('172.18.0.3', '203.0.113.7')) == '203.0.113.7'
    assert client_ip(request('172.18.0.3', '1.2.3.4, 203.0.113.7')) == '203.0.113.7'
    # a public peer is the client itself: its header is never trusted
    assert client_ip(request('8.8.8.8', '203.0.113.7')) == '8.8.8.8'  # (TEST-NET ranges count as private in Python)


def test_forwarded_header_is_ignored_unless_configured(monkeypatch):
    monkeypatch.delenv('TRUST_PROXY', raising=False)
    assert client_ip(request('172.18.0.3', '203.0.113.7')) == '172.18.0.3'


@pytest.mark.parametrize('secret', ['"whsec_dGVzdA=="', 'not-base64!!', ''])
def test_undecodable_webhook_secret_means_not_on_sale(secret):
    cfg = Dodo(mode='test_mode', products={'family': 'pdt_1'}, api_key='k', webhook_secret=secret)
    assert not cfg.configured('family')


def test_recovery_fee_alone_is_not_an_investment_payment():
    text = 'Recover your stuck money, pay 2000 fee to adv.sharma@oksbi'
    claimed = verified_extraction(Extraction(claims=[Claim(type='recovery_fee', quote='Recover your stuck money')]), text)
    signals = {s.id: s.points for s in evaluate(text, claimed, {})}
    assert 'S1' not in signals and signals['S6'] == weights.CLAIMS['recovery_fee']


def test_a_upi_id_is_not_a_payment_verb():
    text = 'My UPI for the mutual fund SIP discussion is ram@paytm'
    assert 'S1' not in [s.id for s in evaluate(text, regex_extract(text), {})]


@pytest.mark.parametrize(('upi', 'sebi'), [('x.brk@validhdfc', True), ('x.brk@VALIDICICI', True), ('x@validyesbank', True),
                                           ('x@valid', False), ('x@validupi', False), ('x@validstock', False),
                                           ('x@validprofit', False), ('x@ybl', False)])
def test_valid_handle_needs_a_known_bank(upi, sebi):
    assert sebi_valid_handle(upi) is sebi
