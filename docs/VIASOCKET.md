# Report webhook setup

The backend is ready. A five-step plan has been generated in Risheeth's
viaSocket account, but Google Sheets and Gmail authorization is still pending.
No configured live workflow, spreadsheet row or email has been verified yet.

## What the backend does

`POST /api/report` saves the report and returns its normal response. If
`VIASOCKET_REPORT_WEBHOOK_URL` is empty, it logs exactly `viasocket not configured`
and skips delivery for that report. Adding a URL later does not send old skipped
reports.

If configured, a background task POSTs JSON after sending the report response.
The network request has a two-second total timeout. Failure never changes report
success. Pending deliveries survive restarts and retry after at least 60 seconds,
up to three attempts total. The worker checks pending deliveries every 30 seconds.
An HTTP redirect is treated as failure. The URL must use HTTPS.

The `Idempotency-Key` HTTP header is the report ID. Configure the workflow to
ignore already handled report IDs; this prevents duplicate notifications if a
delivery succeeded but its acknowledgement was lost.

## Exact JSON fields

The made-up example below has the same fields the backend sends. IDs, scores,
language, masked entities and the public URL vary with the actual report.

```json
{
  "event": "report",
  "report_id": "rep_example",
  "check_id": "chk_example",
  "band": "high_risk",
  "score": 65,
  "lang": "hi",
  "entities": [{"type": "upi", "masked": "sa…@ybl"}],
  "url": "https://34-45-129-243.sslip.io/c/chk_example"
}
```

There is no message text, transcript, report note, raw identifier, anonymous user
ID or recipient address in the payload. The public URL has no referral parameter.
The machine-readable example is `examples/viasocket_report.json`.

## Map these fields in viaSocket

1. Create a workflow with a Webhook trigger. Copy its HTTPS URL into `.env` as
   `VIASOCKET_REPORT_WEBHOOK_URL`; restart the backend after changing `.env`.
2. Set `PUBLIC_BASE_URL` in `.env` to the deployed HTTPS origin so the payload's
   `url` opens the public verdict.
3. Connect the intended Google Sheet. Add columns `report_id`, `check_id`, `band`,
   `score`, `lang`, `entities`, `url`. Serialize `entities` as JSON for a single
   cell. Use `report_id` to deduplicate deliveries.
4. Add an email action to Risheeth's own confirmed Google email for this demo.
   Configure the recipient inside the workflow. Example subject:
   `Check Before You Pay: {{band}}`; body: `A check was reported. Risk score:
   {{score}}. Review the evidence: {{url}}`.
5. Activate the workflow and report a new, explicitly labelled test check. Confirm
   one sheet row and one alert. Retry the same report and confirm no duplicates.
   Do not test with a real victim's data.

## Use the check API in another workflow

Configure an HTTP POST action to `https://34-45-129-243.sslip.io/api/check`, with JSON:

```json
{
  "lang": "en",
  "anon_id": "u_test_viasocket",
  "ref": null,
  "input": {"text": "(test, made up) (sample) Investment: pay sample@ybl"}
}
```

Map the incoming text into `input.text`. Set a caller timeout above ten seconds;
route HTTP errors using their `error.code` and `error.message`. The normal
30-checks/hour per anonymous ID limit still applies. No model key belongs in
the workflow request.

## Agreed demo setup and handoff

Risheeth creates the Google Sheet himself at sheets.new while signed into his
own account. Name it **Check Before You Pay – reports (demo)** and share Editor
access with **samarthputhraya@gmail.com**. Header row:
`report_id`, `check_id`, `band`, `score`, `lang`, `entities`, `url`.
Paste the sheet URL into the team handoff; the sheet stays private.

Connect Google from the Google Sheets step inside viaSocket. No Drive connector
is required. Use only the masked fields above. Use Risheeth's own email as the
alert recipient. Risheeth explicitly confirmed
`risheeth200623@gmail.com` for the demo alert.
Do not use a real family member for the demo.

Send the webhook URL privately to Samarth so he can set
`VIASOCKET_REPORT_WEBHOOK_URL` on the live server. Never commit, screenshot or
paste it in the PR. Keep any local copy only in `.env`.

Record a 20-second clip showing one labelled `u_test` report becoming one sheet
row and one email. Keep the webhook URL, Google account screens and inbox
contents outside the clip. Test replay separately: same report ID, no second
row/email. Record completion and proof only after actually observing them.

Current status: the user supplied the sheet URL and confirmed its ownership,
Editor access for Samarth and all seven headers. Risheeth confirmed the alert
recipient. The generated plan receives a webhook, validates `event` and
`report_id`, looks up the ID in Sheet1, stops duplicates, then appends the row
and sends the email for a new ID. The Google Sheets connection popup is open;
Google Sheets and Gmail authorization must be completed before the plan can be
built and its mappings verified. No webhook URL has been obtained or sent,
no live activation or duplicate test has occurred, and no clip has been recorded.
See `docs/ROUND2_STATUS.md` for the remaining acceptance work.

References: [viaSocket webhook triggers](https://viasocket.com/help/workflow/trigger/instant-triggers),
[workflow actions](https://viasocket.com/help/workflow/actions).
