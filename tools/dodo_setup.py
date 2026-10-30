"""Set up Dodo test mode from one API key: create the Family and API products and the webhook endpoint unless they
already exist, then write the DODO_* settings into an env file. Safe to run again: it reuses what it finds.

    python tools/dodo_setup.py .env.railway

Needs DODO_API_KEY (a test-mode key) and PUBLIC_BASE_URL in that file. Prints product and webhook IDs, never the key or
the signing secret. Copy the DODO_* lines to /opt/cbyp/app.env on the VM afterwards, then restart the app.
API reference: https://docs.dodopayments.com/api-reference (products, webhooks).
"""
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

BASE = 'https://test.dodopayments.com'
EVENTS = ['payment.succeeded', 'payment.failed', 'subscription.active', 'subscription.failed']
# plan -> (env var, product name, description, price in rupees). Dodo refuses any payment under US$1.00 (seen live on
# 30 Oct: "Minimum amount of 1.00 USD is required"), so ₹49 couldn't be paid; ₹99 is about US$1.10.
PRODUCTS = {
    'family': ('DODO_PRODUCT_FAMILY', 'Check Before You Pay: Family', 'Checks for the whole family, every month.', 99),
    'api': ('DODO_PRODUCT_API', 'Check Before You Pay: API', 'The check API for apps and banks, every month.', 999),
}


def fail(response: httpx.Response, what: str) -> None:
    # Dodo's error bodies name a code and a message, never the key.
    raise SystemExit(f'{what} failed: HTTP {response.status_code} {response.text[:300]}')


def monthly_inr(rupees: int) -> dict:
    return {'type': 'recurring_price', 'currency': 'INR', 'price': rupees * 100, 'discount': 0, 'discount_bps': 0,
            'purchasing_power_parity': False, 'tax_inclusive': True,
            'payment_frequency_count': 1, 'payment_frequency_interval': 'Month',
            'subscription_period_count': 10, 'subscription_period_interval': 'Year'}


def product(client: httpx.Client, name: str, description: str, rupees: int) -> str:
    """The product with this name, created if missing and repriced if Dodo has a different price."""
    listed = client.get('/products', params={'page_size': 100, 'archived': 'false'})
    if listed.status_code != 200:
        fail(listed, 'listing products')
    found = next((item['product_id'] for item in listed.json().get('items', []) if item.get('name') == name), None)
    if found is None:
        created = client.post('/products', json={'name': name, 'description': description, 'tax_category': 'saas',
                                                 'price': monthly_inr(rupees)})
        if created.status_code not in (200, 201):
            fail(created, f'creating {name!r}')
        return created.json()['product_id']
    current = client.get(f'/products/{found}')
    if current.status_code != 200:
        fail(current, f'reading {name!r}')
    if (current.json().get('price') or {}).get('price') != rupees * 100:
        updated = client.patch(f'/products/{found}', json={'price': monthly_inr(rupees)})
        if updated.status_code not in (200, 204):
            fail(updated, f'repricing {name!r}')
        print(f'{name}: repriced to Rs {rupees}')
    return found


def webhook(client: httpx.Client, url: str) -> tuple[str, str]:
    listed = client.get('/webhooks', params={'limit': 100})
    if listed.status_code != 200:
        fail(listed, 'listing webhooks')
    found = next((w for w in listed.json().get('data', []) if w.get('url') == url and not w.get('disabled')), None)
    if found is None:
        created = client.post('/webhooks', json={'url': url, 'description': 'Check Before You Pay orders',
                                                 'filter_types': EVENTS})
        if created.status_code not in (200, 201):
            fail(created, 'creating the webhook')
        found = created.json()
    secret = client.get(f"/webhooks/{found['id']}/secret")
    if secret.status_code != 200:
        fail(secret, 'reading the signing secret')
    return found['id'], secret.json()['secret']


def write_env(path: Path, values: dict[str, str]) -> None:
    """Replace or add each KEY=value line, keeping every other line and the file's line endings as they are."""
    raw = path.read_bytes().decode('utf-8')
    newline = '\r\n' if '\r\n' in raw else '\n'
    lines = raw.splitlines()
    left = dict(values)
    for i, line in enumerate(lines):
        key = line.split('=', 1)[0].strip()
        if key in left:
            lines[i] = f'{key}={left.pop(key)}'
    lines += [f'{key}={value}' for key, value in left.items()]
    path.write_bytes((newline.join(lines) + newline).encode('utf-8'))


def main(env_file: str) -> None:
    path = Path(env_file)
    env = dotenv_values(path)
    key, base_url = (env.get('DODO_API_KEY') or '').strip(), (env.get('PUBLIC_BASE_URL') or '').strip().rstrip('/')
    if not key or not base_url.startswith('https://'):
        raise SystemExit(f'{path} needs DODO_API_KEY and an https PUBLIC_BASE_URL')
    with httpx.Client(base_url=BASE, headers={'Authorization': 'Bearer ' + key}, timeout=20) as client:
        check = client.get('/products', params={'page_size': 1})
        if check.status_code == 401:
            raise SystemExit('Dodo refused the key (401). Create a new key in the dashboard while it is in Test Mode.')
        values = {'DODO_MODE': 'test_mode'}
        for plan, (var, name, description, rupees) in PRODUCTS.items():
            values[var] = product(client, name, description, rupees)
            values[f'DODO_PRICE_{plan.upper()}_INR'] = str(rupees)
            print(f'{plan}: {values[var]} at Rs {rupees} a month')
        hook_id, values['DODO_WEBHOOK_SECRET'] = webhook(client, base_url + '/api/dodo/webhook')
        print(f'webhook: {hook_id} -> {base_url}/api/dodo/webhook ({", ".join(EVENTS)})')
    write_env(path, values)
    print(f'Wrote {", ".join(sorted(values))} to {path}. The signing secret was not printed.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
