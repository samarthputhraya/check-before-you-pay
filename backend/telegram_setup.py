"""Register the deployed webhook using .env; never prints Telegram credentials/URLs."""
from __future__ import annotations

import asyncio
import os

from backend import telegram
from backend.config import get_settings


async def setup() -> None:
    secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')
    telegram.authenticate([secret])
    result = await telegram.api('setWebhook', {
        'url': get_settings().public_base_url + '/api/telegram/webhook',
        'secret_token': secret, 'allowed_updates': ['message'], 'max_connections': 4,
    })
    if result is not True:
        raise telegram.TelegramUnavailable()
    state = await telegram.api('getWebhookInfo', {})
    if not isinstance(state, dict) or state.get('url') != get_settings().public_base_url + '/api/telegram/webhook':
        raise telegram.TelegramUnavailable()
    print('Telegram webhook registered. Pending updates:', state.get('pending_update_count', 0))
    print('Recent delivery error present:', bool(state.get('last_error_date')))


if __name__ == '__main__':
    try:
        asyncio.run(setup())
    except Exception:
        raise SystemExit('Telegram setup failed. Check .env and deployed reachability; credentials were not printed.') from None
