# Pre-merge review fixes - 29 October 2026

The review referred to the earlier 116-test checkpoint. The current branch has
202 passing tests. API JSON shapes and risk weights have not changed.

## Findings and changes

| Finding | Resolution |
|---|---|
| UPI followed by a full stop | The final punctuation is accepted without permitting an email-domain continuation. The exact `stockpro@ybl.` reproduction extracts the UPI and scores S1 at 35. |
| Investment vocabulary too narrow | Added crypto, profit, returns, guaranteed, tips, nifty, options, forex and corresponding Hindi/other-language terms. Payment intent and a non-valid UPI remain required. |
| Dotted UPI becomes a public domain | Bare-domain candidates overlapping an extracted UPI are excluded. An end-to-end regression confirms `tradepro.vip@ybl.` sends no domain to RDAP and persists no domain entity. |
| Rechecks inflate S4/S5 | Entity and script evidence queries exclude earlier checks with the current input hash. Five forced partial checks retain the same score and have no self-created ring evidence. The required injection-line variant uses the same source hash. Different messages can still link through real identifiers/scripts. |
| Short pipeline deadlines prevent retries | Removed the 2.8/1.5/3.5-second cutoffs. Each provider attempt has an eight-second local cap; the shared request budget is 9.5 seconds. A regression exercises a first attempt that fails after three seconds and a successful retry. |
| Shared service domains create rings | Skip shared hosts and their subdomains, including Telegram, WhatsApp, Google Drive/Docs, YouTube and common link shorteners. Actual group invite links remain HMAC-linked by the full URL. |
| Discovery never recovers / misleading health | Failed discovery is retried after a 30-second backoff, including a background worker. No request-driven retry storm. Health reports `llm: down`, `ok: false`, HTTP 503 while unavailable; it returns to 200 when discovery succeeds. Runtime generation failures also update readiness. |
| Forwarded IP spoofing / shared Wi-Fi | Removed wildcard proxy trust. Docker runs Uvicorn with `--no-proxy-headers`; X-Forwarded-For is never used. The default IP budget is 3000/hour, with 30/hour per anonymous user unchanged. Railway's overwritten X-Real-IP is an explicit edge-only opt-in. |
| Almost-everywhere unchecked notices | A disabled phishing feed is omitted entirely. Explanation fallback uses local language copy and does not add `explanation` to unchecked. Genuine configured-feed/claim/link failures are still disclosed. |
| S2 matches dhanbank/growwithme | Match complete brand tokens, typos or recognized app/payment/login affixes. Tests cover both reported false positives and retained impersonation matches. |
| Client events inflate metrics | Rate-limit events per user and IP; require server-issued HttpOnly HMAC proof plus check ownership for share events; deduplicate shares; ignore forged completion/report/quiz-result events. Quiz shares require a stored quiz result. |
| internal_error uses HTTP 503 | Report database failures now return HTTP 500 with the existing error envelope. Consent text remains available for a retry. |

Cache entries from earlier scoring semantics are invalidated once at application
startup using a stored cache revision. Normal restarts with the same revision
preserve the cache.

## Deadline constraint and media path

Two full eight-second attempts plus explanation cannot fit inside the brief's
ten-second overall request budget. Attempts may run up to eight seconds; a retry
uses the remaining request budget. Exhaustion returns regex evidence/unchecked
signals, or a plain `check_unavailable` error if a file could not be read at all.

Gemini rejects an advertised HTTP transport deadline below ten seconds. The SDK
transport is therefore set to ten seconds, with an independent local eight-second
cancellation around each attempt. The failed transport-deadline benchmark is
retained separately and is explicitly marked invalid for acceptance measurements.

For media, one structured response first transcribes the file and then extracts
claims/entities. Quotes are still verified against the transcript before scoring.
This removes a serial model round trip while preserving the existing public
transcript field and privacy rules. The standalone transcribe/extract wrappers
and the OpenAI audio fallback remain available.

## Real-key latency measurements

The latest run made 20 text, 5 screenshot and 5 OGG voice requests against the
configured Gemini key. Every request used a fresh temporary database; there were
no cache hits or production usage writes. Models were discovered at startup.
This is local API latency, not Railway or Android acceptance.

| Input | N | HTTP 200 | All risk checks completed | p50, all requests | p95, all requests |
|---|---:|---:|---:|---:|---:|
| Text, English/Hindi mix | 20 | 20 | 20 | 2.71 s | 9.31 s |
| Screenshot | 5 | 5 | 5 | 4.48 s | 7.04 s |
| OGG voice | 5 | 3 | 3 | 9.16 s | 9.35 s |

Voice is **not yet reliable enough to claim deployed phone acceptance** with this
key/model and network: two of five files hit the request deadline before a
transcript was available. Successful voice requests had p50 6.13 s and p95 8.86 s.
An isolated OGG-versus-WAV comparison did not support a codec conversion fix:
OGG completed in 4.17/6.39 s; WAV took 7.54/7.65 s. No unsupported conversion was
added. A live OpenAI fallback key was not configured for these measurements.

The text median meets the brief's five-second target; the tail remains slower.
No claim of universal five-second responses or successful voice acceptance is made.

Raw records and exact method: `docs/benchmark-review.json`.
The serial-media baseline is `docs/benchmark-review-serial-media.json`; the
rejected-deadline run is `docs/benchmark-review-rejected-deadline.json`.

Reproduce with a real key (this spends provider credits):

```powershell
python -m backend.benchmark --text-runs 20 --media-runs 5 --audio data/validation/voice.ogg --output data/validation/benchmark.json
```

The optional audio path must point to an explicitly made-up OGG sample prepared
locally. Test fixtures contain silence and are unsuitable for a transcription
acceptance benchmark.

## Deployment settings for role A

```dotenv
PUBLIC_BASE_URL=https://<your-public-host>
IP_CHECKS_PER_HOUR=3000
TRUST_RAILWAY_EDGE=true
```

Use the last setting **only** for Railway HTTP edge ingress with the platform's
`RAILWAY_ENVIRONMENT_ID` present, no TCP proxy, and no untrusted direct/private
ingress. Outside that boundary, leave it false and use the actual socket peer.
Do not restore `--forwarded-allow-ips='*'`. Update an existing IP limit of 100 in
the deployment environment; changing the example file does not override it.

Anonymous visit counts are still estimates, not authenticated people. Rate
limits and event validation constrain abuse; they cannot prove that a visitor
is a unique human. Checks and reports are authoritative server records.

References: [Railway request headers](https://docs.railway.com/networking/public-networking/specs-and-limits),
[Uvicorn proxy trust settings](https://uvicorn.dev/settings/),
[FastAPI response cookies](https://fastapi.tiangolo.com/advanced/response-cookies/).
