# Collecting real scam messages tonight (6–9 PM)

**Status, Friday 30 October:** the planned Thursday collection window has
passed. No collected files or written consent receipts have been supplied to
this checkout. Do not claim collection happened or create fictional real-data
results. The instructions below apply when contributions become available.

## Written consent and redaction come first

Before copying or submitting each message, obtain a written yes/no for retaining
its anonymized version for evaluation and processing it with the configured AI
provider. Obtain separate optional permission for demo display and public
repo/video publication. Keep the receipt, contributor identity, collector and
timestamp outside Git under an opaque consent record ID. A Report checkbox
alone does not replace this per-message process. Consent to one message does
not cover another message or another person's private information.

Remove **every real person's name, phone number, face and UPI ID**, including
suspected scam senders' identifiers, before saving or submitting. Also remove
wallets, accounts, emails, transaction IDs, OTPs and private invitation links.
Use explicit placeholders such as `[phone removed]` or
`[UPI removed; suffix @ybl]`; do not restore invented identifiers to increase
detection. Keep public website domains and the relevant claims where possible.
Have a second person review redaction and meaning.

Only approved anonymized versions may go under `seed/messages/consented/`.
Public commits additionally require publication permission. Label displayed
text `(sample)` and identify the source as a real received message with
redaction, not as made-up text. No original screenshot, voice recording,
database export or consent receipt belongs in Git. Removing identifiers changes
S1/link evidence; record redactions and call the results **anonymized real-message
evaluation**, rather than performance on untouched originals.

**Goal:** 30 or more real investment-scam messages from people at the house and their families, with consent, so we can measure the check on real data instead of only on messages we wrote ourselves (`docs/EVAL.md`).

## The easy way: people use the live site themselves
1. They open **https://34-45-129-243.sslip.io** on their phone.
2. They paste a scam message they've actually received (or forward a screenshot), and tap **Check before you pay**.
3. After written consent and redaction above, on the verdict they tap **Report this as a scam** and may tick **Also save the message text**. Without that checkbox we store only the masked verdict, never the text.
4. They must tap Report within 15 minutes of the check, and not across a deploy or restart: the server keeps the text only in memory, so after that only the masked verdict is reported. The page says so when it happens. For a screenshot or voice note that was already checked by someone else, only the verdict is saved too.
5. That's it. Every report links its UPI ID, number or website to future checks, so the ring links get real data at the same time.

Say this when you ask (it's the consent wording, so keep it):

> "Got a stock-tip or 'guaranteed returns' message on WhatsApp? Paste it into our checker and tap Report. If you tick 'save the message text', we keep the text to test our checks. We never keep your name or number, and you can say no."

Hindi:

> "WhatsApp पर कोई स्टॉक टिप या 'पक्का मुनाफ़ा' वाला मैसेज आया है? इसे हमारी साइट पर जाँचें और Report दबाएँ। अगर आप 'मैसेज का टेक्स्ट सेव करें' चुनते हैं, तो हम इसे अपनी जाँच परखने के लिए रखेंगे। हम आपका नाम या नंबर कभी नहीं रखते, और आप मना कर सकते हैं।"

## Rules
- **Only messages people received.** Not their own chats with family, and nothing they sent.
- **Before pasting, cut out:**
  - the person's own name and phone number;
  - other group members' names and numbers;
  - any OTP, bank account number or card number.
  
  Remove suspected scam senders' real UPI IDs and phone numbers too, following
  the explicit collection instructions above. Public website domains may stay.
- **Screenshots:** crop out the person's contact name and profile photo first.
- **Anyone who lost money:** point them to 1930 or cybercrime.gov.in first, before anything else.

## Turning reports into the real evaluation set
After 9 PM, Samarth (or Claude) runs:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://34-45-129-243.sslip.io/api/admin/export -o live.db
```

Then:
1. Read only texts with both recorded written consent and the storage checkbox;
   recheck redaction before copying them from the private export.
2. Two people label each `scam` or `ordinary` independently of the app's score,
   record a rationale and deduplicate forwards. Keep uncertain messages in a
   private review queue rather than forcing a binary label.
3. With separate publication permission, add them to `eval/real.jsonl` with
   `id`, `text`, `label`, `lang`, `category`, `source` (use
   `housemate, consented, anonymized`), opaque `consent_record_id`, `redactions`
   and `rationale`.
4. Rerun `eval/run_eval.py` on that file.

`live.db` holds real reports, so delete it after the export: never commit it or share it.

Use the current evaluation runner without changing scoring weights:

```powershell
python eval/run_eval.py --env-file .env --messages eval/real.jsonl --out eval/real_results.json
```

Results include message text and extraction traces. Review them before any
commit. Report denominators, missed scams, false positives, incomplete checks
and p50/p95, retaining failed attempts. No `eval/real.jsonl` is created until
actual contributions and the required permissions exist. For voice collection,
use the ten fictional scripts in `docs/PHONE_ACCEPTANCE.md`, never victim audio.
