# API contract v1

**The single source of truth for every client.** Only role A (Samarth) changes this file, and only after the team agrees. There is one example JSON per endpoint in `examples/`.

## Conventions

- All request and response bodies are JSON. Files are sent as base64.
- **Errors** return a 4xx or 5xx status with `{"error": {"code": "<snake_case>", "message": "<plain English>"}}`.
  - Codes shared by every endpoint:
    - `invalid_request` (400): a missing or malformed field, or a value outside the allowed list.
    - `not_found` (404)
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
  "score": 80,
  "lang": "hi",
  "headline": "पैसे न भेजें: इसमें धोखाधड़ी के कई संकेत हैं",
  "explanation": "…",
  "signals": [
    {
      "id": "S1",
      "label": "…",
      "points": 35,
      "evidence": { "kind": "lookup", "text": "tradepro.vip@ybl is not a SEBI @valid UPI handle", "source_url": "https://www.sebi.gov.in" }
    },
    {
      "id": "S6",
      "label": "…",
      "points": 20,
      "evidence": { "kind": "quote", "text": "300% guaranteed", "source_url": null }
    },
    {
      "id": "S4",
      "label": "…",
      "points": 10,
      "evidence": { "kind": "lookup", "text": "Same UPI ID as 3 earlier reports", "source_url": null }
    },
    {
      "id": "S5",
      "label": "…",
      "points": 15,
      "evidence": { "kind": "lookup", "text": "Matches a script seen in 6 earlier checks", "source_url": null }
    }
  ],
  "entities": [ { "type": "upi", "masked": "tr…@ybl" } ],
  "ring": { "linked_checks": 6, "linked_reports": 3, "via": ["same_upi", "same_script"] },
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

**Response 200:** `{ "report_id": "rep_01JB9A", "ok": true }`

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

`event` is one of `visit`, `check_started`, `check_done`, `share_clicked`, `ref_visit`, `report`, `quiz_done`, `quiz_shared`, `return_visit`.

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
  "updated_at": "2026-10-30T10:00:00+05:30"
}
```

---

## GET /api/health

`{ "ok": true, "llm": "up", "db": "up" }`

`db` returns `down` when the database can't be reached. Checks still return a verdict while it's down; S4 and S5 score 0, and `"links"` is added to `unchecked`.
