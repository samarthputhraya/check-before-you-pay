"""Dodo Payments: plans, checkout, order status and the signed webhook. Dodo is a mock transport; no network."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import db, payments
from backend.app import app

API_KEY = 'test-only-dodo-api-key-4f1c'
KEY = b'test-only-webhook-signing-key-32'
SECRET = 'whsec_' + base64.b64encode(KEY).decode()
SESSION = 'cks_test_0001'
CHECKOUT_URL = 'https://test.checkout.dodopayments.com/session/cks_test_0001'
PAISE = {'pdt_family': 4900, 'pdt_api': 99900}


def product(product_id, paise, **price):
    return {'product_id': product_id, 'price': {
        'type': 'recurring_price', 'currency': 'INR', 'price': paise, 'payment_frequency_count': 1,
        'payment_frequency_interval': 'Month', 'subscription_period_count': 1, 'subscription_period_interval': 'Year',
        'tax_inclusive': True, **price}}


def dodo_ok(request):
    if request.method == 'GET':
        product_id = request.url.path.rsplit('/', 1)[-1]
        return httpx.Response(200, json=product(product_id, PAISE[product_id]))
    return httpx.Response(200, json={'session_id': SESSION, 'checkout_url': CHECKOUT_URL})


class FakeDodo:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.respond = dodo_ok

    def __call__(self, request):
        self.requests.append(request)
        return self.respond(request)

    def posts(self):
        return [r for r in self.requests if r.method == 'POST']


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLITE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.delenv('PUBLIC_BASE_URL', raising=False)
    return TestClient(app)


@pytest.fixture
def dodo(monkeypatch):
    """Test-mode Dodo with both products configured. Every Dodo call goes to this fake."""
    for name, value in {'DODO_API_KEY': API_KEY, 'DODO_WEBHOOK_SECRET': SECRET,
                        'DODO_PRODUCT_FAMILY': 'pdt_family', 'DODO_PRODUCT_API': 'pdt_api'}.items():
        monkeypatch.setenv(name, value)
    fake = FakeDodo()
    real = httpx.AsyncClient
    monkeypatch.setattr(payments.httpx, 'AsyncClient', lambda **kw: real(transport=httpx.MockTransport(fake), **kw))
    return fake


@pytest.fixture
def offline(monkeypatch):
    def refuse(**kw):
        raise AssertionError('Dodo must not be called')
    monkeypatch.setattr(payments.httpx, 'AsyncClient', refuse)


def sign(body: bytes, msg_id='msg_0001', stamp=None, key=KEY) -> dict:
    stamp = str(int(time.time())) if stamp is None else str(stamp)
    digest = hmac.new(key, f'{msg_id}.{stamp}.'.encode() + body, hashlib.sha256).digest()
    return {'webhook-id': msg_id, 'webhook-timestamp': stamp,
            'webhook-signature': 'v1,' + base64.b64encode(digest).decode(), 'content-type': 'application/json'}


def event(order_id, kind='payment.succeeded', plan='family', **data) -> bytes:
    payload = {'payload_type': 'Payment', 'payment_id': 'pay_test_0001', 'checkout_session_id': SESSION,
               'product_cart': None, 'metadata': {'order_id': order_id, 'plan': plan, 'anon_id': 'u_buyer'}} | data
    return json.dumps({'business_id': 'bus_test', 'type': kind, 'timestamp': '2026-10-29T12:00:00Z',
                       'data': payload}).encode()


def deliver(client, body, **sign_kw):
    return client.post('/api/dodo/webhook', content=body, headers=sign(body, **sign_kw))


def start(client, plan='family', anon_id='u_buyer') -> str:
    response = client.post('/api/checkout', json={'plan': plan, 'anon_id': anon_id})
    assert response.status_code == 200, response.text
    assert response.json()['checkout_url'] == CHECKOUT_URL
    return response.json()['order_id']


def status(client, order_id) -> str:
    return client.get(f'/api/orders/{order_id}').json()['status']


def events(tmp_path, name) -> list[tuple]:
    with db.session(tmp_path / 'test.db') as con:
        return [tuple(r) for r in con.execute('SELECT anon_id,props_json FROM events WHERE event=?', (name,))]


def assert_error(response, code, http_status):
    assert response.status_code == http_status, response.text
    assert response.json()['error']['code'] == code


# ---- not configured ---------------------------------------------------------

def test_unconfigured_plans_are_unavailable_at_default_prices(client, offline):
    assert client.get('/api/plans').json() == {'test_mode': True, 'plans': [
        {'id': 'family', 'name': 'Family', 'price_inr': 49, 'interval': 'month', 'available': False},
        {'id': 'api', 'name': 'API', 'price_inr': 999, 'interval': 'month', 'available': False}]}


@pytest.mark.parametrize('missing', ['DODO_API_KEY', 'DODO_WEBHOOK_SECRET', 'DODO_PRODUCT_FAMILY'])
def test_checkout_without_config_is_503_and_creates_no_order(client, dodo, monkeypatch, tmp_path, missing):
    monkeypatch.delenv(missing)
    assert_error(client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'}), 'payments_unavailable', 503)
    assert not dodo.posts()
    with db.session(tmp_path / 'test.db') as con:
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0


def test_webhook_without_secret_is_503(client):
    body = event('ord_x')
    assert_error(client.post('/api/dodo/webhook', content=body, headers=sign(body)), 'payments_unavailable', 503)


# ---- plans ------------------------------------------------------------------

def test_plans_use_dodo_prices_in_test_mode_by_default(client, dodo, monkeypatch):
    monkeypatch.setitem(PAISE, 'pdt_api', 149900)
    body = client.get('/api/plans').json()
    assert body['test_mode'] is True
    assert [(p['id'], p['price_inr'], p['available']) for p in body['plans']] == [('family', 49, True), ('api', 1499, True)]
    assert sorted(str(r.url) for r in dodo.requests) == ['https://test.dodopayments.com/products/pdt_api',
                                                        'https://test.dodopayments.com/products/pdt_family']
    assert all(r.headers['authorization'] == f'Bearer {API_KEY}' for r in dodo.requests)


@pytest.mark.parametrize(('mode', 'host', 'test_mode'), [
    ('live_mode', 'live.dodopayments.com', False), ('LIVE_MODE', 'test.dodopayments.com', True),
    ('live', 'test.dodopayments.com', True), ('', 'test.dodopayments.com', True)])
def test_live_mode_only_when_exactly_live_mode(client, dodo, monkeypatch, mode, host, test_mode):
    monkeypatch.setenv('DODO_MODE', mode)
    assert client.get('/api/plans').json()['test_mode'] is test_mode
    start(client)
    assert {r.url.host for r in dodo.requests} == {host}


def test_plan_prices_are_cached(client, dodo):
    for _ in range(3):
        client.get('/api/plans')
    assert len(dodo.requests) == 2


def test_paise_that_are_not_whole_rupees_are_kept(client, dodo):
    dodo.respond = lambda request: httpx.Response(200, json=product('pdt_family', 4950))
    assert client.get('/api/plans').json()['plans'][0]['price_inr'] == 49.5


def raise_timeout(request):
    raise httpx.ConnectTimeout('private failure detail', request=request)


@pytest.mark.parametrize('respond', [raise_timeout, lambda request: httpx.Response(503, text='down'),
                                     lambda request: httpx.Response(429)])
def test_price_falls_back_when_dodo_is_unreachable(client, dodo, monkeypatch, respond):
    monkeypatch.setenv('DODO_PRICE_FAMILY_INR', '59')
    dodo.respond = respond
    plans = client.get('/api/plans').json()['plans']
    assert [(p['price_inr'], p['available']) for p in plans] == [(59, True), (999, True)]


def test_invalid_fallback_price_uses_the_built_in_default(client, offline, monkeypatch):
    monkeypatch.setenv('DODO_PRICE_FAMILY_INR', 'forty-nine')
    assert client.get('/api/plans').json()['plans'][0]['price_inr'] == 49


@pytest.mark.parametrize('respond', [
    lambda request: httpx.Response(404, json={'code': 'NOT_FOUND'}),
    lambda request: httpx.Response(200, json=product('pdt_family', 4900, currency='USD')),
    lambda request: httpx.Response(200, json=product('pdt_family', 4900, payment_frequency_interval='Year')),
    lambda request: httpx.Response(200, json={'product_id': 'pdt_family', 'price': {'type': 'one_time_price',
                                                                                     'currency': 'INR', 'price': 4900}}),
    lambda request: httpx.Response(200, text='not json')])
def test_product_dodo_rejects_or_that_is_not_monthly_inr_is_off_sale(client, dodo, respond):
    dodo.respond = lambda request: respond(request) if request.method == 'GET' else dodo_ok(request)
    assert [p['available'] for p in client.get('/api/plans').json()['plans']] == [False, False]
    assert_error(client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'}), 'payments_unavailable', 503)
    assert not dodo.posts()


# ---- checkout ---------------------------------------------------------------

def test_checkout_creates_a_pending_order_and_one_dodo_session(client, dodo, tmp_path):
    order_id = start(client)
    [request] = dodo.posts()
    assert str(request.url) == 'https://test.dodopayments.com/checkouts'
    assert request.headers['authorization'] == f'Bearer {API_KEY}'
    assert json.loads(request.content) == {
        'product_cart': [{'product_id': 'pdt_family', 'quantity': 1}],
        'return_url': f'http://testserver/pricing?order={order_id}',
        'metadata': {'order_id': order_id, 'plan': 'family', 'anon_id': 'u_buyer'}}
    assert client.get(f'/api/orders/{order_id}').json() == {'order_id': order_id, 'plan': 'family', 'status': 'pending'}
    order = db.get_order(tmp_path / 'test.db', order_id)
    assert set(order) == {'id', 'plan', 'anon_id', 'session_id', 'status', 'mode', 'created_at', 'paid_at', 'dodo_ref'}
    assert (order['session_id'], order['mode'], order['paid_at']) == (SESSION, 'test_mode', None)
    assert events(tmp_path, 'checkout_started') == [('u_buyer', '{"plan": "family"}')]


def test_checkout_return_url_uses_public_base_url(client, dodo, monkeypatch):
    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://34-45-129-243.sslip.io/')
    order_id = start(client)
    assert json.loads(dodo.posts()[0].content)['return_url'] == f'https://34-45-129-243.sslip.io/pricing?order={order_id}'


@pytest.mark.parametrize('body', [{'plan': 'gold', 'anon_id': 'u_buyer'}, {'plan': 'family', 'anon_id': 'buyer'},
                                  {'plan': 'family'}])
def test_checkout_rejects_unknown_plan_and_bad_anon_id(client, dodo, body):
    assert_error(client.post('/api/checkout', json=body), 'invalid_request', 400)
    assert not dodo.requests


async def slow(request):
    await asyncio.sleep(1)
    return dodo_ok(request)


@pytest.mark.parametrize('respond', [
    lambda request: httpx.Response(500, text=f'internal detail {API_KEY}'),
    lambda request: httpx.Response(401, json={'message': f'bad key {API_KEY}'}),
    raise_timeout,
    slow,
    lambda request: httpx.Response(200, json={'session_id': SESSION, 'checkout_url': None}),
    lambda request: httpx.Response(200, json={'session_id': SESSION, 'checkout_url': 'http://evil.example/'}),
    lambda request: httpx.Response(200, json=['not', 'an', 'object'])])
def test_dodo_checkout_failure_is_503_never_retried_and_never_paid(client, dodo, monkeypatch, tmp_path, respond):
    monkeypatch.setattr(payments, 'CHECKOUT_TIMEOUT', 0.05)
    client.get('/api/plans')  # warm the price cache so only the checkout call fails
    dodo.respond = respond
    response = client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'})
    assert_error(response, 'payments_unavailable', 503)
    assert response.json()['error']['message'] == 'Payments are paused. Please try again later.'
    assert API_KEY not in response.text and 'detail' not in response.text
    assert len(dodo.posts()) == 1
    with db.session(tmp_path / 'test.db') as con:
        assert [tuple(r) for r in con.execute('SELECT status,paid_at FROM orders')] == [('failed', None)]
    assert events(tmp_path, 'checkout_started') == []


def test_dodo_error_code_is_logged_but_not_its_message(client, dodo, caplog):
    client.get('/api/plans')
    dodo.respond = lambda request: httpx.Response(422, json={
        'code': 'TOTAL_PAYMENT_AMOUNT_BELOW_MINIMUM_AMOUNT', 'message': 'Minimum amount of 1.00 USD is required'})
    with caplog.at_level(logging.WARNING, logger='cbyp'):
        assert_error(client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'}),
                     'payments_unavailable', 503)
    assert 'dodo checkout failed: HTTP 422 TOTAL_PAYMENT_AMOUNT_BELOW_MINIMUM_AMOUNT' in caplog.text
    assert 'Minimum amount' not in caplog.text


def test_checkout_is_rate_limited_per_user(client, dodo):
    for _ in range(10):
        start(client)
    assert_error(client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'}), 'rate_limited', 429)
    start(client, anon_id='u_other')


# ---- orders -----------------------------------------------------------------

@pytest.mark.parametrize('order_id', ['ord_unknown', 'ord_', 'chk_01JB8Q', 'ord_a$b', 'ord_' + 'a' * 41])
def test_unknown_or_malformed_order_is_404(client, order_id):
    assert_error(client.get(f'/api/orders/{order_id}'), 'not_found', 404)


# ---- webhook: signatures ----------------------------------------------------

def test_signature_matches_the_standard_webhooks_reference_vector():
    # test_sign_function in standard-webhooks/libraries/python/tests/test_webhooks.py
    key = payments.signing_key('whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw')
    headers = {'webhook-id': 'msg_p5jXN8AQM9LWM0D4loKWxJek', 'webhook-timestamp': '1614265330',
               'webhook-signature': 'v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE='}
    body = b'{"test": 2432232314}'
    assert payments.verify(key, headers, body, now=1614265330) == 'msg_p5jXN8AQM9LWM0D4loKWxJek'
    with pytest.raises(payments.InvalidSignature):
        payments.verify(key, headers, b'{"test": 2432232315}', now=1614265330)


@pytest.mark.parametrize('secret', ['', 'whsec_', 'whsec_not base64!', 'whsec_a'])
def test_unusable_secret_gives_no_key(secret):
    assert payments.signing_key(secret) is None


@pytest.mark.parametrize('tamper', [
    lambda h, b: (h | {'webhook-signature': sign(b, key=b'some-other-signing-key-32-bytes!')['webhook-signature']}, b),
    lambda h, b: (h, b.replace(b'family', b'api')),
    lambda h, b: (h | {'webhook-id': 'msg_other'}, b),
    lambda h, b: ({k: v for k, v in h.items() if k != 'webhook-id'}, b),
    lambda h, b: ({k: v for k, v in h.items() if k != 'webhook-timestamp'}, b),
    lambda h, b: ({k: v for k, v in h.items() if k != 'webhook-signature'}, b),
    lambda h, b: (h | {'webhook-timestamp': h['webhook-timestamp'] + '.0'}, b),
    lambda h, b: (h | {'webhook-signature': h['webhook-signature'].replace('v1,', 'v2,')}, b),
    lambda h, b: (h | {'webhook-signature': h['webhook-signature'][3:]}, b)])
def test_bad_signature_is_401_and_records_nothing(client, dodo, tmp_path, tamper):
    order_id = start(client)
    body = event(order_id)
    headers, sent = tamper(sign(body), body)
    assert_error(client.post('/api/dodo/webhook', content=sent, headers=headers), 'invalid_signature', 401)
    assert status(client, order_id) == 'pending'
    with db.session(tmp_path / 'test.db') as con:
        assert con.execute('SELECT COUNT(*) FROM dodo_webhooks').fetchone()[0] == 0


@pytest.mark.parametrize(('skew', 'accepted'), [(-301, False), (301, False), (-299, True), (299, True)])
def test_timestamp_tolerance_is_five_minutes_either_way(client, dodo, skew, accepted):
    order_id = start(client)
    response = deliver(client, event(order_id), stamp=int(time.time()) + skew)
    assert response.status_code == (200 if accepted else 401)
    assert status(client, order_id) == ('paid' if accepted else 'pending')


def test_any_matching_signature_in_a_multi_signature_header_is_accepted(client, dodo):
    order_id = start(client)
    body = event(order_id)
    headers = sign(body)
    headers['webhook-signature'] = f'v1,bm90LXRoZS1zaWduYXR1cmU= {headers["webhook-signature"]} v2,ignored'
    assert client.post('/api/dodo/webhook', content=body, headers=headers).status_code == 200
    assert status(client, order_id) == 'paid'


def test_signed_body_that_is_not_json_is_400(client, dodo):
    assert_error(deliver(client, b'not json'), 'invalid_request', 400)


def test_webhook_body_limit_allows_large_dodo_payloads(client, dodo):
    order_id = start(client)
    body = event(order_id, custom_field_responses=[{'key': 'note', 'value': 'x' * 100_000}])
    assert deliver(client, body).status_code == 200
    assert status(client, order_id) == 'paid'
    huge = event(order_id, custom_field_responses=[{'key': 'note', 'value': 'x' * 300_000}])
    assert_error(deliver(client, huge, msg_id='msg_huge'), 'input_too_large', 413)


# ---- webhook: effects -------------------------------------------------------

def test_full_flow_checkout_signed_webhook_paid_and_counted(client, dodo, tmp_path):
    order_id = start(client)
    assert client.get('/api/stats').json()['orders_paid'] == 0
    assert deliver(client, event(order_id)).status_code == 200
    assert client.get(f'/api/orders/{order_id}').json() == {'order_id': order_id, 'plan': 'family', 'status': 'paid'}
    assert client.get('/api/stats').json()['orders_paid'] == 1
    assert events(tmp_path, 'checkout_paid') == [('u_buyer', '{"plan": "family"}')]
    # The subscription's own event for the same purchase changes nothing more.
    active = event(order_id, 'subscription.active', payload_type='Subscription', subscription_id='sub_1',
                   product_id='pdt_family', checkout_session_id=None)
    assert deliver(client, active, msg_id='msg_0002').status_code == 200
    assert client.get('/api/stats').json()['orders_paid'] == 1
    assert len(events(tmp_path, 'checkout_paid')) == 1
    order = db.get_order(tmp_path / 'test.db', order_id)
    assert order['paid_at'] and order['dodo_ref'] == 'pay_test_0001'


def test_subscription_active_marks_paid_by_its_product(client, dodo, tmp_path):
    order_id = start(client, plan='api')
    active = event(order_id, 'subscription.active', plan='api', payload_type='Subscription', subscription_id='sub_9',
                   product_id='pdt_api', checkout_session_id=None, payment_id=None)
    assert deliver(client, active).status_code == 200
    assert status(client, order_id) == 'paid'
    assert db.get_order(tmp_path / 'test.db', order_id)['dodo_ref'] == 'sub_9'


def test_replayed_webhook_id_returns_200_and_changes_nothing(client, dodo, tmp_path):
    order_id = start(client)
    assert deliver(client, event(order_id, 'payment.failed')).status_code == 200
    assert status(client, order_id) == 'failed'
    # Same webhook-id, validly signed: a replay, even with a different body.
    assert deliver(client, event(order_id)).status_code == 200
    assert status(client, order_id) == 'failed'
    assert events(tmp_path, 'checkout_paid') == []


def test_paid_is_final_and_a_failed_card_can_be_retried(client, dodo, tmp_path):
    order_id = start(client)
    assert deliver(client, event(order_id, 'payment.failed', payment_id='pay_declined'), msg_id='m1').status_code == 200
    assert status(client, order_id) == 'failed'
    assert deliver(client, event(order_id), msg_id='m2').status_code == 200
    assert status(client, order_id) == 'paid'
    assert deliver(client, event(order_id, 'payment.failed', payment_id='pay_late'), msg_id='m3').status_code == 200
    assert status(client, order_id) == 'paid'
    assert len(events(tmp_path, 'checkout_paid')) == 1
    assert db.get_order(tmp_path / 'test.db', order_id)['dodo_ref'] == 'pay_test_0001'


@pytest.mark.parametrize(('kind', 'data', 'meta'), [
    ('payment.succeeded', {}, {'plan': 'api'}),
    ('payment.succeeded', {}, {'order_id': 'ord_doesnotexist'}),
    ('payment.succeeded', {}, {'order_id': None}),
    ('payment.succeeded', {'checkout_session_id': 'cks_someone_else',
                           'product_cart': [{'product_id': 'pdt_api', 'quantity': 1}]}, {}),
    ('subscription.active', {'checkout_session_id': None, 'product_id': 'pdt_api'}, {}),
    ('refund.succeeded', {}, {}),
    ('payment.processing', {}, {})])
def test_events_that_do_not_match_the_order_are_ignored(client, dodo, kind, data, meta):
    order_id = start(client)
    body = json.loads(event(order_id, kind, **data))
    body['data']['metadata'] |= meta
    assert deliver(client, json.dumps(body).encode()).status_code == 200
    assert status(client, order_id) == 'pending'


def test_one_time_product_is_matched_through_its_cart(client, dodo):
    order_id = start(client)
    body = event(order_id, checkout_session_id=None, product_cart=[{'product_id': 'pdt_family', 'quantity': 1}])
    assert deliver(client, body).status_code == 200
    assert status(client, order_id) == 'paid'


def test_mode_mismatch_never_marks_an_order_paid(client, dodo, monkeypatch):
    order_id = start(client)  # created in test mode
    monkeypatch.setenv('DODO_MODE', 'live_mode')
    assert deliver(client, event(order_id)).status_code == 200
    assert status(client, order_id) == 'pending'


def test_orders_paid_counts_only_the_current_mode(client, dodo, monkeypatch):
    deliver(client, event(start(client)))
    assert client.get('/api/stats').json()['orders_paid'] == 1
    monkeypatch.setenv('DODO_MODE', 'live_mode')
    assert client.get('/api/stats').json()['orders_paid'] == 0


# ---- events -----------------------------------------------------------------

def test_clients_cannot_forge_checkout_events_but_can_send_pricing_view(client, tmp_path):
    for name in ('checkout_started', 'checkout_paid', 'pricing_view', 'pricing_view'):
        assert client.post('/api/events', json={'anon_id': 'u_buyer', 'event': name}).status_code == 204
    assert events(tmp_path, 'checkout_started') == events(tmp_path, 'checkout_paid') == []
    assert len(events(tmp_path, 'pricing_view')) == 1  # repeat views within the hour count once
    assert client.get('/api/stats').json()['orders_paid'] == 0


# ---- secrets ----------------------------------------------------------------

def test_keys_never_appear_in_responses_or_logs(client, dodo, caplog):
    caplog.set_level(logging.DEBUG)
    for name in ('httpx', 'httpcore', 'cbyp'):
        caplog.set_level(logging.DEBUG, logger=name)
    echo = f'bad key {API_KEY} {SECRET}'
    texts = [repr(payments.config())]
    dodo.respond = lambda request: httpx.Response(401, text=echo)  # product lookups rejected
    texts.append(client.get('/api/plans').text)
    payments._prices.clear()
    dodo.respond = lambda request: dodo_ok(request) if request.method == 'GET' else httpx.Response(500, text=echo)
    texts.append(client.post('/api/checkout', json={'plan': 'family', 'anon_id': 'u_buyer'}).text)
    dodo.respond = dodo_ok
    order_id = start(client)
    texts.append(deliver(client, event(order_id), key=b'wrong-key-wrong-key-wrong-key-00').text)
    texts.append(deliver(client, event(order_id)).text)
    assert status(client, order_id) == 'paid'
    texts.append(caplog.text)
    for line in ('off sale: HTTP 401', 'dodo checkout failed: HTTP 500', 'dodo webhook rejected',
                 'dodo webhook payment.succeeded: paid'):
        assert line in caplog.text
    for text in texts:
        assert API_KEY not in text and SECRET.removeprefix('whsec_') not in text and KEY.decode() not in text


def test_access_log_drops_the_return_url_query():
    record = logging.LogRecord('uvicorn.access', logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ('1.2.3.4:5', 'GET', '/pricing?order=ord_1&status=active&email=a%40b.in', '1.1', 200), None)
    assert payments.RedactReturnQuery().filter(record)
    assert record.getMessage() == '1.2.3.4:5 - "GET /pricing?[redacted] HTTP/1.1" 200'
    other = logging.LogRecord('uvicorn.access', logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                              ('1.2.3.4:5', 'GET', '/c/chk_1?ref=u_1', '1.1', 200), None)
    payments.RedactReturnQuery().filter(other)
    assert '/c/chk_1?ref=u_1' in other.getMessage()
