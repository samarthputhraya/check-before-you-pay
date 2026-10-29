# Telegram bot

Code is ready for offline review. **Bot creation, a deployed webhook and a real
test-chat reply are still pending.** No token has been obtained in this session.

## Setup

1. Risheeth opens the official `@BotFather` in Telegram and creates a bot with
   `/newbot`. Choose an available public username and retain its token privately.
2. Set `TELEGRAM_BOT_TOKEN` and a separate random `TELEGRAM_WEBHOOK_SECRET` in
   `.env`. The webhook secret must be 32–256 characters using letters, digits,
   `_` or `-`. Set the existing random `IDENTIFIER_SALT` (32+ characters) and
   `PUBLIC_BASE_URL=https://34-45-129-243.sslip.io`.
3. Transfer these credentials to Samarth using the team's private channel so he
   can configure the service and deploy this PR. Never paste them into a PR,
   issue, shell command line, screen recording, or public chat. No raw tokens or
   Bot API URLs should appear in logs.
4. After deployment, run `python -m backend.telegram_setup`. It calls Telegram's
   `setWebhook` with `secret_token`, only `message` updates and four connections.
   It checks `getWebhookInfo` without printing the token or webhook URL. It does
   not discard pending updates. Missing configuration fails closed.
5. Keep the bot in private chats for this demo. Group messages and other update
   types are acknowledged and ignored, so the bot does not process bystanders'
   messages. No unofficial WhatsApp automation is used.

## User flow

Forward text, a photo, an image document or an OGG/M4A/MP3 voice note to the bot.
The same input validation, 30-check/hour user limit, coarse adapter limit and
`pipeline.run_check` apply. Files are capped at 5 MB, images at 25 megapixels,
voice at two minutes, and text at 5,000 characters. Media is fetched only from
Telegram's fixed API host, with redirects disabled, size checks during download
and a two-second download budget; submitted links are never fetched.

The returned verdict is masked, with its band/score, top three signals, next
steps and the public `/c/{id}?ref={anon_id}` link. Plain text avoids interpreting
message evidence as HTML/Markdown. `/start` and `/help` explain the input and
privacy behavior. `/lang hi` (or en/mr/ta/te/kn/bn/hinglish) changes the next checks.
Language preferences are HMAC-keyed, memory-only and expire after 24 hours or a
restart. Telegram locale defaults to Hindi/Marathi/Tamil/Telugu/Kannada/Bengali
when recognized and English otherwise. Verdict content comes from the normal
localized pipeline; command/error copy is currently English.

## Privacy and delivery limits

- The user ID is HMAC-SHA256 under `IDENTIFIER_SALT`, truncated to 128 bits and
  prefixed `u_tg_`. Neither raw user/chat IDs nor Telegram updates go into SQLite.
- Source text and downloaded media exist only during processing, with the same
  bounded consent buffer used by normal checks. The bot does not offer a Report
  command or persist source text. Telegram itself retains chat history under its
  own service policies; the application's promise is about its own storage.
- The server sends HTTP 200 before processing in a FastAPI background task.
  Work gets 8.5 seconds and sending the reply 1.3 seconds. Provider/network
  delays produce a retry message; under-ten-second success still needs live
  measurement, especially for voice.
- Up to 64 active updates and 4,096 recent update hashes are held in memory.
  Replayed updates are deduplicated while present. A restart or eviction loses
  this memory; an already acknowledged in-flight update may lose its reply.
  There is no durable raw-message queue and no exactly-once delivery claim.
- API exceptions are reduced to generic status messages. The token appears in
  Telegram URLs by protocol, so HTTP transport logs are suppressed and no error
  response/body/URL is logged by the adapter.

## Validation and acceptance

`python -m pytest backend/tests/test_telegram.py` covers authentication, text,
photos, unsupported input, size/rate limits, HMAC IDs, language selection,
private-chat behavior, replay suppression, log redaction and fast acknowledgment.
HTTP calls and model providers are mocked in tests.

After Samarth deploys and provider health is up, record the public bot username
and test-chat evidence here: forward a labelled scam sample; verify localized
band, score, three-or-fewer evidence entries and a working referral URL. Repeat
with a screenshot and voice note; time arrival-to-reply on the phone. Check
`/lang hi` and a rejected unsupported file. No live acceptance is claimed yet.

Official references: [Bot creation](https://core.telegram.org/bots/tutorial#obtain-your-bot-token),
[webhook authentication](https://core.telegram.org/bots/api#setwebhook),
[file download](https://core.telegram.org/bots/api#getfile),
[sendMessage](https://core.telegram.org/bots/api#sendmessage),
[FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/).
