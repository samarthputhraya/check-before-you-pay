"""Dodo Payments over plain httpx: plan prices, hosted checkout, and signed webhooks (Standard Webhooks v1).

This is the only module that reads DODO_API_KEY or DODO_WEBHOOK_SECRET. Failures log an exception type or HTTP status,
never a Dodo response body, URL or header. Only a verified webhook marks an order paid; the return URL never does.
API reference: https://docs.dodopayments.com/api-reference (POST /checkouts, GET /products/{id}, webhooks).
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import quote

import httpx

from backend import db
from backend.errors import ApiError
from backend.schemas import Plan

log = logging.getLogger('cbyp')

BASE_URLS = {'test_mode': 'https://test.dodopayments.com', 'live_mode': 'https://live.dodopayments.com'}
# plan id -> (name, product ID variable, fallback price variable, fallback price in rupees). Family is ₹99, not ₹49:
# Dodo refuses any payment under US$1.00 (seen live on 30 Oct).
PLANS = {'family': ('Family', 'DODO_PRODUCT_FAMILY', 'DODO_PRICE_FAMILY_INR', 99),
         'api': ('API', 'DODO_PRODUCT_API', 'DODO_PRICE_API_INR', 999)}
CHECKOUT_TIMEOUT = 8.0
PRICE_TIMEOUT = 2.0
PRICE_TTL = 600.0
RETRY_TTL = 60.0  # a failed lookup is remembered briefly, so an outage doesn't add 2 s to every pricing view
WEBHOOK_TOLERANCE = 300  # seconds of clock skew either way, as in the Standard Webhooks libraries
EVENT_STATUS = {'payment.succeeded': 'paid', 'subscription.active': 'paid',
                'payment.failed': 'failed', 'subscription.failed': 'failed'}
_TIMESTAMP = re.compile(r'[0-9]{1,12}')
_ORDER_ID = re.compile(r'ord_[A-Za-z0-9_-]{1,40}')
_PRICE = re.compile(r'[1-9][0-9]{0,6}')
_ERROR_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,63}')


@dataclass(frozen=True)
class Dodo:
    mode: str
    products: dict[str, str]
    api_key: str = field(repr=False)
    webhook_secret: str = field(repr=False)

    @property
    def base_url(self) -> str:
        return BASE_URLS[self.mode]

    def configured(self, plan: str) -> bool:
        # Without the webhook secret no payment could ever be confirmed, so none is taken.
        return bool(self.api_key and signing_key(self.webhook_secret) and self.products.get(plan))


def config() -> Dodo:
    return Dodo(mode='live_mode' if os.getenv('DODO_MODE') == 'live_mode' else 'test_mode',
                products={plan: os.getenv(env, '').strip() for plan, (_, env, _, _) in PLANS.items()},
                api_key=os.getenv('DODO_API_KEY', '').strip(),
                webhook_secret=os.getenv('DODO_WEBHOOK_SECRET', '').strip())


def unavailable() -> ApiError:
    return ApiError(503, 'payments_unavailable', 'Payments are paused. Please try again later.')


def _client(cfg: Dodo, timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=cfg.base_url, headers={'Authorization': f'Bearer {cfg.api_key}'},
                             timeout=timeout, follow_redirects=False)


def _describe(response: httpx.Response) -> str:
    """HTTP status plus Dodo's error code, an enum such as TOTAL_PAYMENT_AMOUNT_BELOW_MINIMUM_AMOUNT. Never the body."""
    try:
        code = response.json().get('code')
    except (ValueError, AttributeError):
        code = None
    return f'HTTP {response.status_code}' + (f' {code}' if isinstance(code, str) and _ERROR_CODE.fullmatch(code) else '')


def _failure(exc: Exception) -> str:
    return _describe(exc.response) if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__


# ---- Plans ------------------------------------------------------------------

# (mode, product ID) -> (expires at, available, rupees; None means show the fallback price)
_prices: dict[tuple[str, str], tuple[float, bool, int | float | None]] = {}


def _fallback(plan: str) -> int:
    _, _, env, default = PLANS[plan]
    raw = os.getenv(env, '').strip()
    return int(raw) if _PRICE.fullmatch(raw) else default


def _rupees(product: object) -> int | float | None:
    """Dodo's price in rupees, or None unless the product bills INR once a month. Dodo prices are in paise."""
    price = product.get('price') if isinstance(product, dict) else None
    if not (isinstance(price, dict) and price.get('type') == 'recurring_price' and price.get('currency') == 'INR'
            and str(price.get('payment_frequency_interval')).lower() == 'month'
            and price.get('payment_frequency_count') == 1):
        return None
    paise = price.get('price')
    if type(paise) is not int or paise <= 0:
        return None
    return paise // 100 if paise % 100 == 0 else paise / 100


async def _lookup(client: httpx.AsyncClient, plan: str, product_id: str) -> tuple[bool, int | float | None]:
    """(available, rupees). If Dodo is unreachable the plan stays on sale at the fallback price. A product Dodo rejects,
    or one that doesn't bill INR monthly, comes off sale, so the page never shows a price Dodo won't charge."""
    try:
        async with asyncio.timeout(PRICE_TIMEOUT):
            response = await client.get('/products/' + quote(product_id, safe=''))
        if response.status_code >= 500 or response.status_code == 429:
            response.raise_for_status()
    except (httpx.HTTPError, TimeoutError) as exc:
        log.warning('dodo price lookup for %s failed: %s', plan, _failure(exc))
        return True, None
    try:
        rupees = _rupees(response.json()) if response.status_code == 200 else None
    except ValueError:
        rupees = None
    if rupees is None:
        log.warning('dodo product for %s is off sale: %s', plan,
                    _describe(response) if response.status_code != 200 else 'not billed in INR every month')
    return rupees is not None, rupees


async def plans(cfg: Dodo) -> list[Plan]:
    now = time.monotonic()
    keys = {plan: (cfg.mode, cfg.products[plan]) for plan in PLANS if cfg.configured(plan)}
    stale = [plan for plan, key in keys.items() if key not in _prices or _prices[key][0] <= now]
    if stale:
        async with _client(cfg, PRICE_TIMEOUT) as client:
            found = await asyncio.gather(*(_lookup(client, plan, cfg.products[plan]) for plan in stale))
        for plan, (available, rupees) in zip(stale, found):
            _prices[keys[plan]] = (now + (PRICE_TTL if rupees is not None else RETRY_TTL), available, rupees)
    result = []
    for plan, (name, *_) in PLANS.items():
        _, available, rupees = _prices[keys[plan]] if plan in keys else (0.0, False, None)
        result.append(Plan(id=plan, name=name, price_inr=rupees or _fallback(plan), interval='month',
                           available=available))
    return result


# ---- Checkout ---------------------------------------------------------------

async def start_checkout(path: Path, cfg: Dodo, plan: str, anon_id: str, base: str) -> tuple[str, str]:
    """Create our order, then Dodo's hosted checkout for it. Returns (order_id, checkout_url)."""
    if not next(p for p in await plans(cfg) if p.id == plan).available:
        raise unavailable()
    try:
        order_id = await asyncio.to_thread(db.create_order, path, plan, anon_id, cfg.mode)
    except (sqlite3.Error, OSError):
        raise ApiError(500, 'internal_error', 'We could not start checkout. Please try again.') from None
    try:
        session_id, url = await _create_session(cfg, plan, order_id, anon_id, base)
    except ApiError:
        with suppress(sqlite3.Error, OSError):
            await asyncio.to_thread(db.fail_order, path, order_id)
        raise
    try:
        await asyncio.to_thread(db.start_order, path, order_id, session_id, anon_id, plan)
    except (sqlite3.Error, OSError):
        raise ApiError(500, 'internal_error', 'We could not start checkout. Please try again.') from None
    return order_id, url


async def _create_session(cfg: Dodo, plan: str, order_id: str, anon_id: str, base: str) -> tuple[str, str]:
    """POST /checkouts exactly once. Never retried: a request that timed out may still have created a session."""
    body = {'product_cart': [{'product_id': cfg.products[plan], 'quantity': 1}],
            'return_url': f'{base}/pricing?order={order_id}',
            'metadata': {'order_id': order_id, 'plan': plan, 'anon_id': anon_id}}
    try:
        async with asyncio.timeout(CHECKOUT_TIMEOUT), _client(cfg, CHECKOUT_TIMEOUT) as client:
            response = await client.post('/checkouts', json=body)
            response.raise_for_status()
            data = response.json()
        session_id, url = data['session_id'], data['checkout_url']
        if not (isinstance(session_id, str) and session_id and isinstance(url, str) and url.startswith('https://')
                and len(url) <= 2000):
            raise ValueError('unexpected checkout response')
    except (httpx.HTTPError, TimeoutError, ValueError, LookupError, TypeError) as exc:
        log.warning('dodo checkout failed: %s', _failure(exc))
        raise unavailable() from None
    return session_id, url


# ---- Webhooks ---------------------------------------------------------------

class InvalidSignature(Exception):
    pass


def signing_key(secret: str) -> bytes | None:
    """The HMAC key inside a `whsec_…` secret: base64, padding optional as in the reference libraries."""
    raw = secret.removeprefix('whsec_')
    try:
        return base64.b64decode(raw + '=' * (-len(raw) % 4), validate=True) or None
    except binascii.Error:
        return None


def verify(key: bytes, headers: Mapping[str, str], body: bytes, now: float | None = None) -> str:
    """Standard Webhooks v1 over the raw body. Returns the verified webhook-id, or raises InvalidSignature."""
    msg_id, stamp, signatures = (headers.get(h, '') for h in ('webhook-id', 'webhook-timestamp', 'webhook-signature'))
    if not (msg_id and signatures and _TIMESTAMP.fullmatch(stamp)):
        raise InvalidSignature('missing or malformed headers')
    if abs((time.time() if now is None else now) - int(stamp)) > WEBHOOK_TOLERANCE:
        raise InvalidSignature('timestamp outside the 5 minute tolerance')
    expected = b'v1,' + base64.b64encode(hmac.new(key, f'{msg_id}.{stamp}.'.encode() + body, hashlib.sha256).digest())
    if not any(hmac.compare_digest(expected, candidate.encode()) for candidate in signatures.split(' ')):
        raise InvalidSignature('no matching signature')
    return msg_id


async def webhook(path: Path, headers: Mapping[str, str], body: bytes) -> None:
    cfg = config()
    key = signing_key(cfg.webhook_secret)
    if key is None:
        log.warning('dodo webhook refused: DODO_WEBHOOK_SECRET is missing or not a whsec_ secret')
        raise unavailable()  # 503, so Dodo retries once the secret is set
    try:
        webhook_id = verify(key, headers, body)
    except InvalidSignature as exc:
        log.warning('dodo webhook rejected: %s', exc)
        raise ApiError(401, 'invalid_signature', 'The webhook signature is not valid.') from None
    try:
        event = json.loads(body)
    except ValueError:
        raise ApiError(400, 'invalid_request', 'The webhook body is not JSON.') from None
    try:
        kind, outcome = await asyncio.to_thread(apply_event, path, cfg, webhook_id, event)
    except (sqlite3.Error, OSError):
        raise ApiError(500, 'internal_error', 'We could not record this event.') from None  # Dodo retries
    log.info('dodo webhook %s: %s', kind or 'unknown', outcome)


def apply_event(path: Path, cfg: Dodo, webhook_id: str, event: object) -> tuple[str, str]:
    """Apply one verified event. Returns (type, outcome) for the log."""
    event = event if isinstance(event, dict) else {}
    kind = event['type'][:64] if isinstance(event.get('type'), str) else ''
    data = event.get('data') if isinstance(event.get('data'), dict) else {}
    if kind == 'refund.succeeded':
        payment_id = data.get('payment_id')
        if not isinstance(payment_id, str) or not re.fullmatch(r'pay_[A-Za-z0-9_-]{1,128}', payment_id):
            raise ApiError(400, 'invalid_request', 'The refund must identify its payment.')
        return kind, db.apply_dodo_refund(path, webhook_id, payment_id, cfg.mode)
    meta = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
    status = EVENT_STATUS.get(kind)
    order_id = meta.get('order_id')
    valid_id = isinstance(order_id, str) and _ORDER_ID.fullmatch(order_id)
    reason = _mismatch(cfg, db.get_order(path, order_id) if valid_id else None, meta, data) if status else 'ignored'
    ref = next((v for v in (data.get('subscription_id'), data.get('payment_id')) if isinstance(v, str) and v), None)
    if status and reason:
        # Not recorded: if our config was wrong (a product ID typo), Dodo's resend can still apply once it's fixed.
        return kind, reason
    payment_id = data.get('payment_id')
    payment_id = payment_id if isinstance(payment_id, str) and re.fullmatch(r'pay_[A-Za-z0-9_-]{1,128}', payment_id) else None
    outcome = db.apply_dodo_event(path, webhook_id, kind, order_id if status else None, status, ref, payment_id)
    return kind, outcome


def _mismatch(cfg: Dodo, order: dict | None, meta: dict, data: dict) -> str | None:
    """Why this event must not move the order, or None. Metadata alone is not trusted: the event must also name the
    order's checkout session or its plan's product, so paying for something else can't unlock this order."""
    if order is None:
        return 'unknown order'
    if order['mode'] != cfg.mode:
        return 'mode mismatch'  # a test payment never unlocks a live order, or the reverse
    if meta.get('plan') != order['plan']:
        return 'plan mismatch'
    cart = data.get('product_cart') if isinstance(data.get('product_cart'), list) else []
    named = [data.get('product_id'), *(item.get('product_id') for item in cart if isinstance(item, dict))]
    product = cfg.products.get(order['plan'])
    if not ((order['session_id'] and data.get('checkout_session_id') == order['session_id'])
            or (product and product in named)):
        return 'not this checkout'
    return None


class RedactReturnQuery(logging.Filter):
    """Dodo appends the buyer's email to the return URL (/pricing?order=…&email=…). Keep it out of access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str) and args[2].startswith('/pricing?'):
            record.args = (*args[:2], '/pricing?[redacted]', *args[3:])
        return True
