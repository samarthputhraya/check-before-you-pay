# Report webhook setup

**Live since Fri 30 Oct, 14:20 IST.** Every report on the live site goes to the viaSocket flow
"Check Before You Pay: reports" (in Samarth's viaSocket workspace). The flow runs these steps:

1. **find_existing:** ignore anything that isn't a report from our site (event, ID formats and evidence URL are
   checked), then look the `report_id` up in the reports sheet.
2. **add_row:** if it isn't there yet, add one row to the Google Sheet "Check Before You Pay: reports" (in
   Samarth's Drive): received_at, report_id, check_id, band, score, lang, masked entities, evidence URL.
3. **alert:** for a new row only, email samarthputhraya@gmail.com: "Check Before You Pay: High risk reported",
   with the score, the masked identifiers, the evidence link and the 1930 helpline.
4. **result:** answers the webhook with `{ok, report_id, added, reason, alerted}`.

**Checked live on 30 Oct with two labelled test checks (`u_test_viasocket`):**
- Each report added exactly one row, and the second one emailed the alert. The first test ran before the email step
  existed.
- The server marked both delivered on the first attempt.
- Re-sending the same report answered `"reason": "duplicate"` and added no row and sent no email.
- A request that isn't a report answered `"not a report"` and changed nothing.

The webhook URL is only in the server's environment (`VIASOCKET_REPORT_WEBHOOK_URL`), never in the repo. The
viaSocket agent token used to build the flow stays in the local `.env.railway`; the server doesn't have it. To pause
the flow: https://flow.viasocket.com → Automations. To revoke the token: https://flow.viasocket.com/agent-access →
Regenerate.

## What the backend does

`POST /api/report` saves the report and returns its normal response. If
`VIASOCKET_REPORT_WEBHOOK_URL` is empty, it logs exactly `viasocket not configured`
and skips delivery for that report. Adding a URL later does not send old skipped
reports.

If configured, a background task POSTs JSON after sending the report response.
The network request has a ten-second total timeout, because viaSocket runs the whole workflow (a sheet row and an
email) before it answers. Delivery runs in the background after the report is saved. Failure never changes report
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
4. Add an email action to a family contact who has agreed to receive these alerts.
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

References: [viaSocket webhook triggers](https://viasocket.com/help/workflow/trigger/instant-triggers),
[workflow actions](https://viasocket.com/help/workflow/actions).

## Inactive Risheeth demo draft

The user explicitly chose to keep Samarth's production workflow described above.
Leave the alternate Risheeth draft inactive; do not replace the live server URL.
No new private webhook handoff is needed for that decision.

Before discovering the production flow, Risheeth supplied a private demo Sheet
named "Check Before You Pay ? reports (demo)" and confirmed its ownership,
Samarth's Editor access and seven headers: report_id, check_id, band, score,
lang, entities, url. He explicitly confirmed risheeth200623@gmail.com for his
own demo alerts. Google Sheets and Gmail connections show ready in his workspace.

The alternate builder has a webhook trigger and a five-step plan: validate event
and report ID, look up the ID in Sheet1, stop duplicates, append the seven masked
fields, then send the alert. Expected payload and remaining action mappings are
incomplete. This alternate draft has not been activated or tested, and no URL
from it was obtained, sent or committed.

The remaining viaSocket deliverable here is a 20-second recording of the
production report becoming one row and one email. It requires access to
Samarth's live workflow and sheet. Keep webhook URLs, account screens and inbox
contents out of the clip. Confirm email delivery using a workflow result or
step status without showing the inbox. Do not stage a row or fake delivery.
