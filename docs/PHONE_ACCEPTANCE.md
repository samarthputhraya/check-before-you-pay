# Phone and voice acceptance — pending

Use a real Android phone and the live site. Record device/browser, IST time,
network, check ID, wall time, language, expected result, actual result and issue.
Use anonymous IDs starting `u_test`. No phone test is claimed by API tests.

## Screenshots and Listen

With per-message consent, submit a real WhatsApp screenshot after redacting the
names, faces, phone numbers and real payment identifiers. Confirm the extracted
text, evidence, language, verdict and share link. Record errors and slowness.

After R2 is merged/deployed, create Hindi and Tamil verdicts and tap Listen.
Confirm the headline, explanation and first next step are audible, in the right
language, with no clipped final sentence. Time first playback and repeat playback
after reload; confirm MP3 under 60 seconds. Ask native speakers about pronunciation.
Endpoint and frontend handoff are in PR #10 (`docs/LISTEN.md`).

## Ten scripted WhatsApp voice notes

Ask readers for five Hindi and five English OGG/Opus notes, one reading of each
script below. Each is a fictional sample. Do not use victims' recordings. Obtain
written consent per recording for storage and AI processing; keep recordings,
consent receipts and a file-to-script manifest outside the repo. Public voice
release needs separate consent. Say “sample” at the start of each recording.

| ID | Script |
|---|---|
| en1 | Sample. Our investment plan guarantees that your money will double in seven days. Deposit today. |
| en2 | Sample. Your profit is ready. Pay a withdrawal fee before you can receive your money. |
| en3 | Sample. Like three videos to earn money. Deposit one thousand rupees to unlock the next tasks. |
| en4 | Sample. Your monthly SIP will be collected through your existing bank mandate. Check the official app if you have questions. |
| en5 | Sample. Do not pay a stranger who promises guaranteed returns. Do not share your OTP. |
| hi1 | नमूना। हमारी निवेश योजना में सात दिन में पैसा दोगुना होने की गारंटी है। आज ही पैसे जमा करें। |
| hi2 | नमूना। आपका मुनाफ़ा तैयार है। पैसे निकालने से पहले निकासी शुल्क जमा करें। |
| hi3 | नमूना। तीन वीडियो लाइक करके पैसे कमाएँ। अगले टास्क खोलने के लिए एक हज़ार रुपये जमा करें। |
| hi4 | नमूना। आपकी मासिक एसआईपी की रकम आपके पहले से तय बैंक मैंडेट से कटेगी। सवाल हो तो आधिकारिक ऐप में जाँचें। |
| hi5 | नमूना। पक्के मुनाफ़े का वादा करने वाले अनजान व्यक्ति को पैसे न भेजें। अपना ओटीपी किसी को न बताएँ। |

Use an ordinary speaking pace, a mix of quiet and normal house noise, and a
maximum of 60 seconds per recording. Submit audio only, without the script in
the text field. Use a fresh recording rather than ten cached submissions of one
file. A listener compares each returned transcript to the recording, especially
negation, amounts, returns, payment requests and withdrawal conditions.

Record all ten outcomes. Proposed acceptance: at least 9/10 with correct meaning,
HTTP 200, no incomplete enabled check, no cache hit, and end-to-end response
strictly under 10 seconds. Also report p50/p95. Missing notes or human review do
not count as a pass. Report a failure to Rishabh/Samarth for the launch decision;
Role B does not change the frontend voice control.

## Native quiz review

A Hindi/Hinglish speaker reads every message and explanation in
`seed/quiz/hi.json` and `seed/quiz/hinglish.json`; a Marathi speaker reviews
`seed/quiz/mr.json` if available. Record language, item ID, naturalness, whether
the label is clear, suggested wording and reviewer approval. Avoid publishing
reviewer identities without consent. AI text inspection is not native-speaker
signoff. Any edits go in a PR and preserve quiz answer keys unless the team
explicitly agrees otherwise.
