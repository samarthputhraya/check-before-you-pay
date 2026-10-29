# Dodo Payments setup (test mode)

The backend code is done and tested offline against a mocked Dodo. It has not made a real Dodo call yet, because we
have no key. These steps take about 15 minutes in the Dodo dashboard, and step 6 is the first real end-to-end test.

## Read first: ₹49 may be below Dodo's subscription minimum

Dodo's [minimum amounts](https://docs.dodopayments.com/features/adaptive-currency.md#minimum-amounts) table says a
subscription in any currency other than USD, EUR or GBP must be worth at least **US$1.00**. INR's own minimum is
₹5, but the US$1.00 check applies on top of it. ₹49 is about US$0.55, so Dodo will probably refuse a ₹49-a-month
subscription with `TOTAL_PAYMENT_AMOUNT_BELOW_MINIMUM_AMOUNT`.

- Step 6 shows whether it does. When checkout fails, the server log prints Dodo's error code, for example
  `dodo checkout failed: HTTP 422 TOTAL_PAYMENT_AMOUNT_BELOW_MINIMUM_AMOUNT`.
- If it does, raise the Family price in Dodo to ₹99 a month (about US$1.10). The pricing page reads its prices from
  Dodo, so no code change is needed. The brief and the contract say ₹49, so tell role A before you change it.

## 1. Test mode and an API key

1. Open the Dodo dashboard and switch to **Test Mode**. A test-mode key only works against test mode.
2. Go to **Developer → API Keys**, create a key and copy it. It is shown once.

## 2. Create the two products

Go to **Products → Add product** and create both of these:

| Product | Type | Price | Currency | Billing |
|---|---|---|---|---|
| Family | Subscription | ₹49 (see above) | INR | every 1 month |
| API | Subscription | ₹999 | INR | every 1 month |

- Copy each product ID (`pdt_…`).
- Leave the discount empty. The page shows the product's price, and a discount would make Dodo charge less than that.
- Both products must be INR, recurring, and billed every month. Otherwise `/api/plans` marks the plan unavailable,
  and the log says `dodo product for family is off sale: not billed in INR every month`. That way the page never
  shows a price Dodo won't charge.
- Dodo always treats INR-to-INR payments as tax-inclusive, so the price on the page is the amount charged.

## 3. Add the webhook endpoint

1. Go to **Developer → Webhooks → Add endpoint**.
2. URL: `https://34-45-129-243.sslip.io/api/dodo/webhook`
3. Select these four events: `payment.succeeded`, `payment.failed`, `subscription.active` and `subscription.failed`.
   Don't leave the selection empty, because an empty selection sends every event type.
4. Click **Create endpoint**, then copy the signing secret (`whsec_…`) from the endpoint's **Overview** tab.

## 4. Set the environment variables

For local runs, put these in `.env`. For the VM, put them in `/opt/cbyp/app.env`, which reaches the VM with
`gcloud compute scp` (see the Deploy section of the README). Then restart or redeploy.

```bash
DODO_API_KEY=<the test-mode key>
DODO_WEBHOOK_SECRET=whsec_<from the endpoint's Overview tab>
DODO_MODE=test_mode
DODO_PRODUCT_FAMILY=pdt_<Family>
DODO_PRODUCT_API=pdt_<API>
DODO_PRICE_FAMILY_INR=49     # shown only while Dodo can't be reached
DODO_PRICE_API_INR=999
PUBLIC_BASE_URL=https://34-45-129-243.sslip.io
```

- `PUBLIC_BASE_URL` sets the URL that Dodo sends the customer back to: `<PUBLIC_BASE_URL>/pricing?order=<order_id>`.
- `DODO_MODE` is test mode unless it is exactly `live_mode`.
- Checkout stays off until the key, the webhook secret and that plan's product ID are all set. Without the secret,
  no payment could ever be confirmed.

## 5. Check the configuration

```bash
curl https://34-45-129-243.sslip.io/api/plans
```

Both plans should show `"available": true`, prices that match the Dodo dashboard, and `"test_mode": true`. If a plan
shows `false`, the server log names the cause:

| Log line | Fix |
|---|---|
| `dodo product for api is off sale: HTTP 404` | Wrong product ID, or the product is in the other mode |
| `dodo product for api is off sale: HTTP 401` | Wrong API key, or a live key used in test mode |
| `dodo product for api is off sale: not billed in INR every month` | Fix the product's currency or billing period |
| `dodo price lookup for api failed: ConnectTimeout` | Dodo didn't answer. The plan stays on sale at the fallback price, and the lookup is retried after a minute |

## 6. Test end to end

1. Open `https://34-45-129-243.sslip.io/pricing`, choose Family and pay on Dodo's page with a
   [test card](https://docs.dodopayments.com/miscellaneous/testing-process.md):
   - Visa `4242 4242 4242 4242`, expiry `06/32`, CVV `123`.
   - Or the Indian Visa `4576 2389 1277 1450` with the same expiry and CVV.
   - Or the UPI ID `success@upi`, with the billing country set to India.
2. Dodo sends you back to `/pricing?order=ord_…`. Within a few seconds `GET /api/orders/ord_…` should return
   `"status": "paid"`, and `orders_paid` in `/api/stats` should go up by 1.
3. Under **Developer → Webhooks**, the endpoint's delivery log should show `200` for each event.
4. Try a declined card, `4000 0000 0000 0002`. The order should become `failed`. A retry that then succeeds on the
   same checkout page still marks it `paid`.
5. **Send example** on the webhook page should also get `200`. The example's metadata doesn't name any of our orders,
   so it changes nothing, but a `200` proves the signing secret is right. A `401` means the secret is wrong.

## 7. What the pricing page must do (role C)

1. **Read the plans.** Read `GET /api/plans` and show each `price_inr` per month.
   - If `available` is `false`, disable that plan's button and show "Coming soon".
   - If `test_mode` is `true`, show "Test mode: no real money is charged".
   - Send the `pricing_view` event once when the page opens.
2. **Start checkout.** On click, `POST /api/checkout` with `{ "plan", "anon_id" }`.
   - `200`: send the browser to `checkout_url` with `location.assign`.
   - `503 payments_unavailable`: show "Payments are paused, please try again later."
   - `429`: show the error's `message`.
   - Each click creates a new order, because a Dodo checkout URL works only once.
3. **After the return.** Read `order` from the URL, then run `history.replaceState(null, '', '/pricing?order=' + id)`.
   Dodo adds `status`, `payment_id` or `subscription_id`, and the buyer's `email` to the return URL. Never show,
   store or send those values, and never trust `status`: only the signed webhook can mark an order paid.
   (The server already removes this query string from its access logs.)
4. **Poll for the result.** Poll `GET /api/orders/{order_id}` every 2 seconds for up to 60 seconds.
   - `paid`: say thank you.
   - `failed`: say "Your payment didn't go through" and offer to try again, which starts a new checkout.
   - Still `pending` after 60 seconds: say "We're still waiting for Dodo to confirm. Refresh in a minute."
   - `404` (an unknown order): show the normal pricing page.

## How it works

- **Prices.** `GET /products/{id}` reads each product's `price`, which Dodo gives in paise. The result is cached for
  10 minutes. If Dodo doesn't answer within 2 seconds, the page shows `DODO_PRICE_*_INR` and tries Dodo again after
  a minute.
- **Checkout.** We create an `ord_…` order (`pending`) first. Then we make one `POST /checkouts` with
  `product_cart: [{product_id, quantity: 1}]`, the return URL, and `metadata: {order_id, plan, anon_id}`, with an
  8-second limit. It is never retried, because a request that timed out may still have created a session. If it
  fails, the order is marked `failed` and the page gets `503`.
- **Webhook.** The Standard Webhooks signature is checked over the raw body: HMAC-SHA256 of
  `{webhook-id}.{webhook-timestamp}.{body}`, with the base64 key inside `whsec_…`, at most 5 minutes of clock skew
  either way, and any one of several `v1,…` signatures accepted. A bad or stale signature gets `401` and nothing is
  recorded. Each `webhook-id` is processed only once.
  - The order is found through `data.metadata.order_id`.
  - The event must match the order's mode and plan, and also its checkout session (`data.checkout_session_id`) or
    its plan's product (`data.product_id` or `data.product_cart`). That way, paying for something else with copied
    metadata can't unlock an order.
  - `payment.succeeded` and `subscription.active` mark the order paid, once, and record `checkout_paid`.
  - `payment.failed` and `subscription.failed` mark a pending order failed. Paid is final.
  - Every other event type gets `200` and is ignored.
- **What we store.** The `orders` table holds the ID, plan, anonymous ID, Dodo session ID, status, mode, the two
  timestamps, and the Dodo payment or subscription ID. It holds no email, card or other payment details.
- **What `orders_paid` counts.** It counts paid orders in the current `DODO_MODE`, so test payments stop counting
  once the server runs live. While `/api/plans` says `test_mode`, label it as test orders on the stats page.

## Going live (only once live mode is approved)

Live mode has its own API key, products, webhook endpoint and signing secret. Create all four in the dashboard's
live mode and swap in the live values. Then set `DODO_MODE=live_mode` and restart. `/api/plans` then reports
`"test_mode": false`.
