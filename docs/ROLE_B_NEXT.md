# Role B: next tasks (Thu 29 Oct, night, round 2)

**For Risheeth and his coding assistant.** Round 1 (B1–B7) is done and live: the eval, quiz backend, Dodo backend, voice notes, and scoring v2. See `docs/EVAL.md` and PR #8.

**Rules:**
- Read `docs/BUILD_BRIEF.md`, `API_CONTRACT.md` and `docs/EVAL.md` first.
- Work on a branch, open a PR into `main`, and keep `python -m pytest` green.
- Never commit or print a key.
- **Don't change scoring weights or signal rules:** the held-out numbers depend on them. If you think one should change, write the case and the eval run, and ask Samarth.
- New endpoints are fine. Add them to `API_CONTRACT.md` in the same PR and say so in the PR description.
- **Deadline:** core freeze is Friday morning. Anything not merged by **9:00 AM Fri** waits until after launch.

**Live site:** https://34-45-129-243.sslip.io. Samarth (or Claude) deploys after each merge. Use anon IDs starting `u_test` when you test against it.

## Tasks, in priority order

### R1. Telegram bot: check a message where people already are (about 3 h)
WhatsApp automation is off limits (brief section 13), but Telegram's Bot API is official, and the scam tip groups live there too.
- **Users:** forward a message, screenshot or voice note to the bot, and it replies with the verdict in under 10 s:
  - the band, the score, the top 3 signals with evidence;
  - the "What to do" lines;
  - a link to the public verdict page `/c/{check_id}?ref=<anon_id>`, so the share loop works.
- **Webhook:** `POST /api/telegram/webhook`. Verify the `X-Telegram-Bot-Api-Secret-Token` header against `TELEGRAM_WEBHOOK_SECRET` in constant time, and reply 200 fast (process in a background task).
- **Settings:** `TELEGRAM_BOT_TOKEN` comes from BotFather; never log it, and remember it's part of every Bot API URL.
- **Reuse the existing pipeline:** the same `run_check`, rate limits and input limits. `anon_id` is `u_tg_` plus an HMAC of the Telegram user ID under `IDENTIFIER_SALT`, never the raw ID.
- **Language:** take it from the user's `language_code` (hi, mr, ta, te, kn, bn, else en). Add `/lang hi` to switch.
- **Privacy:** store nothing beyond what `/api/check` already stores. No message text.
- **Tests:** offline, with the Telegram HTTP calls mocked. Cover signature failure, rate limit, a text check, a photo check, and an unsupported message type.
- **Done when:**
  - a forwarded scam message in a test chat gets the verdict and the link;
  - `docs/TELEGRAM.md` says how to create the bot and set the webhook (`setWebhook` with `secret_token`);
  - Samarth has the token, sent privately, to put on the server.

### R2. "Listen": the verdict read aloud (about 1.5 h; for the persona who prefers voice)
- **Endpoint:** `GET /api/check/{check_id}/audio` returns the verdict's headline, explanation and first next step as speech in the check's language. Use the existing `llm.tts()` and a discovered TTS model.
- **Caching:** cache it per check in SQLite or on disk, so a forwarded verdict is synthesized once. Make the timeout and failure clean: a 503 `audio_unavailable` that the button can show.
- **Format:** OGG/Opus or MP3, under 60 s.
- **Frontend:** tell Rishabh the endpoint so he can add a Listen button. Don't edit `web/`.
- **Done when:** Hindi and Tamil verdicts play on an Android phone, and it has tests.

### R3. Small correctness fixes (about 1 h)
- **Refunds and cancellations:**
  - `refund.succeeded` marks a paid order `refunded`, which isn't counted in `orders_paid`;
  - `subscription.cancelled` is recorded;
  - add `refunded` to the order statuses in the contract.
  - Keep "only a verified webhook changes an order".
- **A domain that doesn't exist (RDAP 404)** shows as "website age couldn't be checked" today. Report it in the evidence as "this website isn't registered", and don't list it under `unchecked`.
  - Don't give it points; that's a scoring change, and it needs the eval first.
- **Repo safety:** add a test that fails if any `examples/` or `seed/` file contains something shaped like a real 10-digit phone number or a real UPI handle outside `(sample)` text.

### R4. Make the repo safe to go public (about 30 min)
Partner judges may need the code.
- Run a secret scan over the whole git history: `git log -p` against key patterns, at least `AIza`, `sk-`, `whsec_`, `xox`, `ghp_`, and long base64.
- Confirm `.env` and `.env.railway` were never committed.
- Add a `LICENSE` (MIT, unless the team says otherwise).
- Report what you found to Samarth. Don't make the repo public yourself.

### R5. People tasks (no code, tonight and tomorrow morning)
- **viaSocket workflow, live** (partner prize): follow `docs/VIASOCKET.md` in your viaSocket account, then send Samarth the webhook URL privately. Record a 20-second clip: a report on the live site turns into a sheet row and an email.
- **Real messages:** follow `docs/COLLECT.md`. Then add a labelled `eval/real.jsonl`, and run `python eval/run_eval.py --messages eval/real.jsonl --out eval/real_results.json`. A real-data number beats every number we have.
- **Native check of the quiz content:** review `seed/quiz/hi.json` and `seed/quiz/hinglish.json`, and Marathi if you can. Fix anything that doesn't sound natural, in a PR.
- **Your Android phone:** a real WhatsApp screenshot and voice note through the live site. Note anything slow or wrong.

## What Samarth and Claude handle
- Deploys, the server and its settings.
- Dodo product setup once a valid test key arrives.
- The TigerGraph Final Round, the pitch and the launch checklist (`docs/LAUNCH.md`).
