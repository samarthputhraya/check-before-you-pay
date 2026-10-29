# Role B handoff - 29 October 2026

Branch: `codex/radnor-backend`.
Review: https://github.com/samarthputhraya/check-before-you-pay/pull/2

The implementation covers role B's code assignment from the v2 build brief.
The API contract and scoring weights are unchanged. Samarth's latest `main`
changes have been merged into this branch.

## Delivered

| Assignment | Implementation and verification |
|---|---|
| Real text checks | Discovered Gemini models, structured extraction, source-verified quotes, fixed S1/S2/S3/S6 scoring, localized explanations |
| Cache and rate limits | Normalized SHA-256 keys, language-specific 24-hour cache, per-user and hashed per-IP limits; persistence and expiry tested |
| Entity links and S4 | HMAC identifiers, masked storage, earlier high-risk/reported check joins, distinct link types, union-find ring counts |
| Script similarity and S5 | Model-specific embeddings, cosine threshold 0.90, separate script score; embedding outage preserves identifier links |
| Screenshots and voice | PNG/JPEG validation and OCR, OGG/M4A/MP3 validation, two-minute/five-MB limits, original-language transcription |
| Seed data | More than 25 curated domain records, one-command loader, four made-up examples with explicit labels and a format for tonight's consented examples |
| viaSocket code | Post-response delivery, exact payload example, two-second network timeout, durable bounded retries, empty-URL skip log |
| Wallet checks | Ethereum/Bitcoin/Tron extraction, masked display, keyed hashes, earlier-report matching under S4; no unsupported blockchain reputation claims |
| Stats and backup | Stored checks/reports/events, users, languages, share rate, referral factor, p50/p95, sample exclusions, token-protected SQLite online backup |
| Privacy and outages | No provider keys in browser; no unconsented raw text on disk; owner-bound volatile consent buffer; masked public pages; partial verdicts for failed checks |

`python -m pytest` runs 144 offline tests. Tests stub the provider boundary and
never send real webhooks. `python -m ruff check backend seed --select F` checks
unused names and imports. The test suite includes the fixed-score determinism
and prompt-injection cases required by the brief.

## Live validation

These are local Gemini smoke measurements using explicitly made-up messages and
a temporary database, not deployed performance or real usage figures.

| Case | Result |
|---|---|
| All eight language options | Score 55 for the same investment request; 2.39-2.76 seconds per request |
| Explanations | Seven returned complete model explanations; Kannada used the local language fallback and marked `explanation` unchecked |
| Screenshot | OCR text returned; score 55; no unchecked items; 4.30 seconds |
| OGG/Opus voice sample | Transcription returned; score 30; no unchecked items; 7.83 seconds |
| Cached text | Cache hit; 40 ms |
| Hindi ring check | Linked to one earlier report through UPI and script; 2.96 seconds in the earlier smoke run |

The audio transcription budget is five seconds inside the media request's
9.5-second budget. Screenshot reading retains a shorter budget. Provider/network
variance can still trigger fallbacks; an unreadable file returns a plain error.

## Team integration

```powershell
git fetch origin
git switch --track origin/codex/radnor-backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m seed.load
.venv\Scripts\python.exe -m uvicorn backend.app:app --reload
```

If you already have the branch locally, switch to it and pull instead of using
`--track`. Copy `.env.example` to `.env` only when `.env` does not already exist;
preserve each teammate's keys. Set `GEMINI_API_KEY` and a random `IDENTIFIER_SALT`
of at least 32 characters. Use `python -m backend.model_inventory` before choosing
model names. Do not share `.env` through Git or chat.

Role C can use `/api/docs`, the unchanged contract, and `/c/chk_sample02` after
seeding. The actual check routes do not carry `X-Sample`; the quiz still does.
Share images, quiz, pricing, Wispr and the growth UI remain role C's scope.

## Explicitly deferred external work

- **viaSocket:** the human confirmed no workflow exists yet. The code side is
  ready. Follow `docs/VIASOCKET.md` to connect the agreed family contact and sheet,
  add the webhook URL to `.env`, restart, and test one labelled report. No live
  alert or sheet integration is claimed.
- **Real messages:** the human confirmed none have been collected. Tonight,
  obtain consent, anonymize them and use the format in `seed/README.md`.
  The current examples are all made up.
- **Railway/phone acceptance:** role A still needs the public service, persistent
  volume and HTTPS origin; then the team must run a real phone check. No live URL
  or Android performance result is claimed from local tests.
- **OpenAI fallback:** the wrapper and retry/fallback tests are implemented.
  A live fallback requires an accessible configured OpenAI key and explicit model
  settings; AI Grants/account setup belongs to role A. Live fallback calls were
  not part of these Gemini measurements.
- **TTS:** the provider wrapper exists as a stretch feature. No new endpoint or
  UI was added beyond the API contract.

Reports without a webhook URL are saved with delivery status `skipped`, logged
as `viasocket not configured`, and never replayed when a URL is added later.
Report text is available for consent only for 15 minutes in memory; restarting
the process clears that buffer. The public verdict never includes a transcript.
