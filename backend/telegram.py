"""Telegram adapter: transient updates, masked replies, and the existing check pipeline."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import re
import time
from collections import OrderedDict
from threading import Lock
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, StrictInt

from backend import pipeline, rate_limit
from backend.config import AUDIO_MIMES, LANGS, MAX_FILE_BYTES, get_settings
from backend.errors import ApiError
from backend.inputs import validate_check_input
from backend.privacy import public_view
from backend.schemas import CheckInput, CheckRequest, CheckResponse

log = logging.getLogger('cbyp.telegram')
# Bot tokens occur in Telegram URLs. Never emit transport request logs.
for logger_name in ('httpx', 'httpcore'):
    logging.getLogger(logger_name).setLevel(logging.WARNING)


class Sender(BaseModel):
    id: StrictInt = Field(gt=0)
    language_code: str = ''
    is_bot: bool = False


class Chat(BaseModel):
    id: StrictInt
    type: str


class File(BaseModel):
    file_id: str = Field(min_length=1, max_length=512)
    file_size: int | None = Field(default=None, ge=0)
    mime_type: str | None = None
    duration: int = Field(default=0, ge=0)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)


class Message(BaseModel):
    message_id: StrictInt
    chat: Chat
    sender: Sender | None = Field(default=None, alias='from')
    text: str | None = None
    caption: str | None = None
    photo: list[File] = Field(default_factory=list, max_length=20)
    voice: File | None = None
    document: File | None = None


class Update(BaseModel):
    update_id: StrictInt = Field(ge=0)
    message: Message | None = None


class TelegramUnavailable(Exception):
    """Never carries a Bot API URL or Telegram response body."""


_lock = Lock()
_seen: OrderedDict[str, float] = OrderedDict()
_active: set[str] = set()
_languages: OrderedDict[str, tuple[str, float]] = OrderedDict()


def authenticate(headers: list[str]) -> None:
    secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', secret):
        raise ApiError(503, 'telegram_unavailable', 'Telegram is not configured.')
    if len(headers) != 1 or not hmac.compare_digest(headers[0].encode(), secret.encode()):
        raise ApiError(401, 'invalid_signature', 'Webhook authentication failed.')
    if (not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', os.getenv('TELEGRAM_BOT_TOKEN', '').strip())
            or len(os.getenv('IDENTIFIER_SALT', '')) < 32):
        raise ApiError(503, 'telegram_unavailable', 'Telegram is not configured.')
    base = get_settings().public_base_url or ''
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ApiError(503, 'telegram_unavailable', 'Telegram needs a public HTTPS address.')


def _digest(kind: str, value: int) -> str:
    salt = os.getenv('IDENTIFIER_SALT', '')
    if len(salt) < 32:
        raise TelegramUnavailable()
    return hmac.new(salt.encode(), f'telegram:{kind}:{value}'.encode(), hashlib.sha256).hexdigest()[:32]


def anon_id(user_id: int) -> str:
    return 'u_tg_' + _digest('user', user_id)


def reserve(update_id: int) -> str | None:
    """Bound transient work/deduplication without storing Telegram IDs or text."""
    key, now = _digest('update', update_id), time.monotonic()
    with _lock:
        while _seen and next(iter(_seen.values())) < now - 86400:
            _seen.popitem(last=False)
        if key in _seen or key in _active:
            return None
        if len(_active) >= 64:
            raise ApiError(503, 'telegram_unavailable', 'The bot is busy. Please try again.')
        _active.add(key)
        _seen[key] = now
        while len(_seen) > 4096:
            _seen.popitem(last=False)
    return key


def language(owner: str, code: str) -> str:
    with _lock:
        saved = _languages.get(owner)
        if saved and saved[1] > time.monotonic():
            return saved[0]
        _languages.pop(owner, None)
    short = code.lower().split('-')[0]
    return short if short in ('hi', 'mr', 'ta', 'te', 'kn', 'bn') else 'en'


def set_language(owner: str, lang: str) -> None:
    with _lock:
        _languages[owner] = (lang, time.monotonic() + 86400)
        _languages.move_to_end(owner)
        while len(_languages) > 4096:
            _languages.popitem(last=False)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=2, follow_redirects=False)


async def api(method: str, payload: dict) -> dict | bool:
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
        raise TelegramUnavailable()
    try:
        async with _client() as client:
            response = await client.post(f'https://api.telegram.org/bot{token}/{method}', json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('ok') is not True:
                raise TelegramUnavailable()
            return data.get('result', {})
    except Exception:
        raise TelegramUnavailable() from None


async def download(file: File) -> bytes:
    if (file.file_size or 0) > MAX_FILE_BYTES:
        raise ApiError(413, 'input_too_large', 'Files can be at most 5 MB.')
    async with asyncio.timeout(2):
        info = await api('getFile', {'file_id': file.file_id})
        if not isinstance(info, dict):
            raise TelegramUnavailable()
        path = info.get('file_path', '')
        if (not isinstance(path, str) or not re.fullmatch(r'[A-Za-z0-9_/.-]+', path)
                or path.startswith('/') or '..' in path.split('/')):
            raise TelegramUnavailable()
        if info.get('file_size', 0) > MAX_FILE_BYTES:
            raise ApiError(413, 'input_too_large', 'Files can be at most 5 MB.')
        token = os.environ['TELEGRAM_BOT_TOKEN'].strip()
        async with _client() as client:
            async with client.stream('GET', f'https://api.telegram.org/file/bot{token}/{path}') as response:
                if response.status_code != 200:
                    raise TelegramUnavailable()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_FILE_BYTES:
                        raise ApiError(413, 'input_too_large', 'Files can be at most 5 MB.')
        return bytes(content)


async def check_input(message: Message) -> CheckInput:
    caption = message.caption
    if message.photo:
        allowed = [p for p in message.photo if (p.file_size or 0) <= MAX_FILE_BYTES]
        if not allowed:
            raise ApiError(413, 'input_too_large', 'Files can be at most 5 MB.')
        selected = max(allowed, key=lambda p: p.width * p.height)
        data = await download(selected)
        return CheckInput(text=caption, image_b64=base64.b64encode(data).decode(), image_mime='image/jpeg')
    if message.voice:
        file = message.voice
        mime = file.mime_type or 'audio/ogg'
        if mime not in AUDIO_MIMES:
            raise ApiError(415, 'unsupported_media', 'Send an OGG, M4A or MP3 voice note.')
        if file.duration > 120:
            raise ApiError(413, 'input_too_large', 'Voice notes can be at most 2 minutes.')
        return CheckInput(text=caption, audio_b64=base64.b64encode(await download(file)).decode(), audio_mime=mime)
    if message.document:
        file = message.document
        if file.mime_type not in ('image/png', 'image/jpeg'):
            raise ApiError(415, 'unsupported_media', 'Send a message, PNG/JPEG screenshot or voice note.')
        return CheckInput(text=caption, image_b64=base64.b64encode(await download(file)).decode(), image_mime=file.mime_type)
    if message.text:
        return CheckInput(text=message.text)
    raise ApiError(415, 'unsupported_media', 'Send a message, PNG/JPEG screenshot or voice note.')


def verdict_text(result: CheckResponse) -> str:
    view = public_view(result)
    lines = [view.headline[:240], f'{view.band} · {view.score}/100']
    for item in sorted(view.signals, key=lambda s: (-s.points, s.id))[:3]:
        lines += ['', f'{item.label[:100]} (+{item.points})', item.evidence.text[:450]]
        if item.evidence.source_url:
            lines.append(str(item.evidence.source_url)[:200])
    lines += ['', view.explanation[:500]]
    for step in view.next_steps[:3]:
        lines.append('• ' + step.text[:160])
        if step.url:
            lines.append(str(step.url)[:150])
    # Preserve the public referral link even when evidence needs truncating.
    body = '\n'.join(lines)
    body = body.encode('utf-16-le')[:6400].decode('utf-16-le', errors='ignore')
    return body + '\n\n' + str(view.share.url)


async def process(update: Update, reservation: str) -> None:
    message = update.message
    try:
        if not message or not message.sender or message.sender.is_bot or message.chat.type != 'private':
            return
        owner = anon_id(message.sender.id)
        lang = language(owner, message.sender.language_code)
        reply = ''
        try:
            # Leave time for sendMessage. Cancellation propagates into the pipeline.
            async with asyncio.timeout(8.5):
                await asyncio.to_thread(rate_limit.enforce, owner, 'telegram')
                command = (message.text or '').split()
                verb = command[0].split('@')[0] if command else ''
                if verb == '/lang':
                    if len(command) != 2 or command[1] not in LANGS:
                        reply = 'Use /lang en, hi, mr, ta, te, kn, bn or hinglish.'
                    else:
                        set_language(owner, command[1])
                        reply = f'Language: {command[1]}. Forward a message, screenshot or voice note.'
                elif verb in ('/start', '/help'):
                    reply = ('Forward a message, PNG/JPEG screenshot or voice note here. '
                             'Use /lang hi to change language. Identifiers in public verdicts are masked. '
                             'Your message is processed by our model provider; we do not store its text in the database.')
                else:
                    inp = await check_input(message)
                    valid = await asyncio.to_thread(validate_check_input, inp)
                    result = await pipeline.run_check(CheckRequest(lang=lang, anon_id=owner, input=inp), valid,
                                                      get_settings().public_base_url)
                    reply = verdict_text(result)
        except ApiError as error:
            reply = error.message
        except (TimeoutError, TelegramUnavailable):
            reply = 'We could not finish this check. Please try again or paste the message on our website.'
        except Exception:
            # Neither provider exceptions nor Bot API errors may expose source text/token URLs.
            log.warning('telegram check unavailable')
            reply = 'We could not finish this check. Please try again.'
        async with asyncio.timeout(1.3):
            await api('sendMessage', {'chat_id': message.chat.id, 'text': reply,
                                     'link_preview_options': {'is_disabled': True}})
    except Exception:
        log.warning('telegram reply unavailable')
    finally:
        with _lock:
            _active.discard(reservation)
