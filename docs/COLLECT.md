# Collecting real scam messages tonight (6–9 PM)

**Goal:** 30 or more real investment-scam messages from people at the house and their families, with consent, so we can measure the check on real data instead of only on messages we wrote ourselves (`docs/EVAL.md`).

## The easy way: people use the live site themselves
1. They open **https://34-45-129-243.sslip.io** on their phone.
2. They paste a scam message they've actually received (or forward a screenshot), and tap **Check before you pay**.
3. On the verdict, they tap **Report this as a scam** and tick **Also save the message text**. Ticking the box is their consent. Without it we store only the masked verdict, never the text.
4. They must tap Report within 15 minutes of the check: after that the server has already forgotten the text, so only the masked verdict is reported.
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
  
  The scammer's UPI ID, link and phone number stay in: they're what we check.
- **Screenshots:** crop out the person's contact name and profile photo first.
- **Anyone who lost money:** point them to 1930 or cybercrime.gov.in first, before anything else.

## Turning reports into the real evaluation set
After 9 PM, Samarth (or Claude) runs:

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://34-45-129-243.sslip.io/api/admin/export -o live.db
```

Then:
1. Read the consented texts from the `reports` table (`text_if_consented` is not null).
2. Label each one `scam` or `ordinary` by hand.
3. Add them to `eval/real.jsonl` with `"source": "housemate, consented"`.
4. Rerun `eval/run_eval.py` on that file.

`live.db` holds real reports, so delete it after the export: never commit it or share it.
