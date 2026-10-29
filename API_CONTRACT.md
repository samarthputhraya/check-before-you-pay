# API contract v1

**The single source of truth for every client.** Only role A (Samarth) changes this file, and only after the team agrees. There is one example JSON per endpoint in `examples/`.

## Conventions

- All request and response bodies are JSON. Files are sent as base64.
- **Errors** return a 4xx or 5xx status with `{"error": {"code": "<snake_case>", "message": "<plain English>"}}`.
  - Codes shared by every endpoint:
    - `invalid_request` (400): a missing or malformed field, or a value outside the allowed list.
    - `not_found` (404)
    - `method_not_allowed` (405)
    - `input_too_large` (413): the body is over the limit. That's 8 MB for `/api/check` and 64 KB for every other endpoint.
    - `internal_error` (500)
  - Each endpoint below lists its own codes.
- **Sample responses:** while an endpoint still returns example data, it sets the header `X-Sample: true`. Clients show a "sample result" note when they see it.
- **Languages** (`lang`): `en`, `hi`, `mr`, `ta`, `te`, `kn`, `bn`, `hinglish`.
- **IDs:** `chk_…` (check), `rep_…` (report), `u_…` (anonymous user).
- **Bands:** `high_risk`, `caution`, `no_known_signals`. Never use "safe".

---

## POST /api/check

**Request**

```json
{
  "lang": "hi",
  "anon_id": "u_7f3a9c",
  "ref": "u_12ab44",
  "input": {
    "text": "VIP Stock Tips: 300% guaranteed. Pay Rs 50,000 to tradepro.vip@ybl to open your institutional account",
    "image_b64": null,
    "image_mime": null,
    "audio_b64": null,
    "audio_mime": null
  }
}
```

**Rules:**
- At least one of `text`, `image_b64` or `audio_b64` is required.
- `image_mime` must be `image/png` or `image/jpeg`.
- `audio_mime` must be `audio/ogg`, `audio/mp4` or `audio/mpeg`.
- `ref` is the `anon_id` from the share link that brought this user, or `null`.

**Response 200**

```json
{
  "check_id": "chk_01JB8Q",
  "band": "high_risk",
  "score": 100,
  "lang": "hi",
  "headline": "पैसे न भेजें: इसमें धोखाधड़ी के कई संकेत हैं",
  "explanation": "…",
  "signals": [
    {
      "id": "S1",
      "label": "…",
      "points": 50,
      "evidence": { "kind": "lookup", "text": "This UPI ID (tr…@ybl) ends in @ybl, not @valid. SEBI-registered brokers collect through @valid handles.", "source_url": "https://www.sebi.gov.in" }
    },
    {
      "id": "S6",
      "label": "…",
      "points": 40,
      "evidence": { "kind": "quote", "text": "300% guaranteed", "source_url": null }
    },
    {
      "id": "S4",
      "label": "…",
      "points": 10,
      "evidence": { "kind": "lookup", "text": "Same UPI ID as 3 earlier reports", "source_url": null }
    }
  ],
  "entities": [ { "type": "upi", "masked": "tr…@ybl" } ],
  "ring": { "linked_checks": 6, "linked_reports": 3, "via": ["same_upi"] },
  "next_steps": [
    { "text": "…", "url": null },
    { "text": "…", "url": "https://www.sebi.gov.in" },
    { "text": "…", "url": "https://cybercrime.gov.in" }
  ],
  "share": { "url": "https://<host>/c/chk_01JB8Q?ref=u_7f3a9c", "card_title": "…" },
  "transcript": null,
  "unchecked": [],
  "cached": false,
  "latency_ms": 3120
}
```

**Field notes:**
- `signals[].evidence.kind` is `quote` (an exact quote from the message) or `lookup` (the result of a check).
- `entities[].type` is one of `upi`, `phone`, `domain`, `url`, `group_link`, `wallet`, `app`. Only masked values are returned.
- `ring.via` takes any of `same_upi`, `same_phone`, `same_domain`, `same_group_link`, `same_wallet`, `same_script`.
- `transcript` is the text we read from a screenshot or voice note; it's `null` for text input.
- **Masking:** evidence text never contains a raw UPI ID, phone number or wallet address; use the masked form (`tr…@ybl`, `98xxxxxx21`). The public view below runs every text field through `backend/privacy.py` as a second guard.
- `evidence.source_url` and `next_steps[].url` must start with `https://`.
- `unchecked` lists the signals that timed out or failed, e.g. `["domain_age", "links"]`. Those signals scored 0.

**Errors**

| Status | `code` | Meaning |
|---|---|---|
| 400 | `empty_input` | No text, image or audio was sent |
| 413 | `input_too_large` | Text over 5,000 characters, or a file over 5 MB |
| 415 | `unsupported_media` | Image or audio type not on the list above |
| 429 | `rate_limited` | More than 30 checks per hour for this user, or the per-IP limit |
| 503 | `check_unavailable` | Only when even the regex fallback fails |

---

## POST /api/report

The user reports a check. If `consent_store_text` is true, we store the message text.

```json
{ "check_id": "chk_01JB8Q", "anon_id": "u_7f3a9c", "consent_store_text": true, "note": null }
```

**Response 200:** `{ "report_id": "rep_01JB9A", "ok": true, "text_saved": true }`

`text_saved` is `false` when the user didn't consent, or when the server no longer had the text (it keeps unsent text in memory for 15 minutes). A repeat report of the same check answers with what the first one stored.

This also fires the viaSocket webhook.

---

## GET /api/check/{check_id}

The public, masked view of a check. It has the same shape as the `/api/check` response but without `transcript`.

---

## GET /c/{check_id}

The HTML share page. It includes Open Graph tags (an English title and the band) and links to the web app.

---

## GET /api/quiz?lang=hi

```json
{ "quiz_id": "q_hi_v1", "items": [ { "id": "q1", "text": "…", "image_url": null } ] }
```

---

## POST /api/quiz/answer

```json
{ "quiz_id": "q_hi_v1", "anon_id": "u_7f3a9c", "answers": { "q1": "scam", "q2": "genuine" } }
```

**Response 200**

```json
{
  "score": 8,
  "total": 10,
  "results": [ { "id": "q1", "correct": true, "answer": "scam", "why": "…" } ],
  "share": { "url": "https://<host>/quiz?ref=u_7f3a9c", "card_title": "…" }
}
```

---

## POST /api/events

```json
{ "anon_id": "u_7f3a9c", "event": "share_clicked", "check_id": "chk_01JB8Q", "ref": null, "props": {} }
```

**Response:** `204`.

`event` is one of `visit`, `check_started`, `check_done`, `share_clicked`, `ref_visit`, `report`, `quiz_done`, `quiz_shared`, `return_visit`, `pricing_view`.

The server records `check_done`, `report` and `quiz_done` itself, plus `checkout_started` and `checkout_paid`. A client that sends any of these five is ignored.

---

## GET /api/plans

The pricing page reads its plans from here, so the prices on the page always match what Dodo will charge.

```json
{
  "test_mode": true,
  "plans": [
    { "id": "family", "name": "Family", "price_inr": 49, "interval": "month", "available": true },
    { "id": "api", "name": "API", "price_inr": 999, "interval": "month", "available": false }
  ]
}
```

- `available` is `false` when that plan's Dodo product isn't configured. The page disables its button and says "Coming soon".
- `test_mode` is `true` unless the server runs with live Dodo keys. While it's `true`, the page shows "Test mode: no real money is charged".

---

## POST /api/checkout

Starts a Dodo Payments checkout. The browser never sees a Dodo key.

```json
{ "plan": "family", "anon_id": "u_7f3a9c" }
```

**Response 200**

```json
{ "order_id": "ord_01JB9A", "checkout_url": "https://test.checkout.dodopayments.com/…" }
```

- **The page sends the browser to `checkout_url`.** After paying, Dodo returns the customer to `/pricing?order=<order_id>`.
- **Errors:**
  - `invalid_request` (400): an unknown plan.
  - `rate_limited` (429)
  - `payments_unavailable` (503): Dodo isn't configured or didn't answer. The page says "Payments are paused, please try again later."

---

## GET /api/orders/{order_id}

The pricing page polls this after Dodo sends the customer back. Only Dodo's signed webhook can mark an order paid; the return URL alone never does.

```json
{ "order_id": "ord_01JB9A", "plan": "family", "status": "paid" }
```

- `status` is `pending`, `paid`, `failed` or `refunded`.
- **Errors:** `not_found` (404).

---

## POST /api/dodo/webhook

Called by Dodo only, never by our pages. The server verifies the Standard Webhooks signature (`webhook-id`, `webhook-timestamp`, `webhook-signature`) with `DODO_WEBHOOK_SECRET` before it records anything.
- **Response:** `200` when processed. A repeat of the same `webhook-id` returns `200` and changes nothing.
- **Errors:** `401` for a bad or stale signature.

`refund.succeeded` links through the payment ID from a verified payment webhook,
marks the associated paid order `refunded`, and removes it from `orders_paid`.
Refund metadata cannot select an order. Refunds arriving before the payment
event are recorded and applied when that verified payment arrives. Refunded
orders cannot be made paid again by a late/replayed success event. As specified
for this MVP, any successful refund (including a partial refund) excludes the
order from the paid-order count. `subscription.cancelled` is recorded once in
the webhook ledger; it does not erase the historical payment or mark a refund.

---

## GET /api/stats

```json
{
  "users": 1234,
  "checks": 4021,
  "reports": 310,
  "languages": { "hi": 1800, "en": 900, "mr": 400 },
  "rings": 42,
  "share_rate": 0.31,
  "k_factor": 0.42,
  "p50_ms": 3100,
  "p95_ms": 7400,
  "quiz_plays": 380,
  "orders_paid": 3,
  "updated_at": "2026-10-30T10:00:00+05:30"
}
```

`quiz_plays` and `orders_paid` were added on 29 Oct. Clients that don't know them ignore them.

---

## GET /api/health

`{ "ok": true, "llm": "up", "db": "up" }`

Answers `GET` and `HEAD`. Returns **503** with `"ok": false` when the database can't be written, so a deploy without a working volume fails its healthcheck.

`db` returns `down` when the database can't be reached. Checks still return a verdict while it's down; S4 and S5 score 0, and `"links"` is added to `unchecked`.
