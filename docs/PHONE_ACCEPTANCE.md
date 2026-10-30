# Phone and voice acceptance

**30 October results:** Risheeth reported that the fresh Hindi and Tamil MP3
links both worked and clarified that his device is an iPhone running iOS 27.2.
Basic iPhone audio playback is user-reported passed. The subsequent upload
checks below were performed in Safari. Device model, complete Listen-button
flow and native pronunciation details were not supplied. Android remains pending.

## iPhone Safari upload results, 30 October

| Check | Time (IST, approximate) | Check ID | Result | Acceptance |
|---|---|---|---|---|
| Screenshot | 18:48 | `chk_01M66FCVS35V00B5` | High risk 100; 2.4 s; S1 50, S4 20, S5 15, S6 40; domain age unchecked | PASS, user-reported |
| Phone voice recording | 18:52 | `chk_01M66FJQ4DS3N0PG` | No known signals 0; 2.3 s; expected caution | NOT PASSED |
| Clean M4A of the same script through the live API | Not supplied | `chk_01M66G2981H1TRN0` | Caution 30; correct transcript reported | API control passed; not a replacement for the failed phone recording |

The assistant retrieved all three public verdicts and confirmed the bands,
scores and unchecked fields. Stored server latencies were 2404, 2337 and
2060 ms respectively; these are distinct from the user's approximate timings.
The failed recording returned no signals and no unchecked stages. That alone
does not distinguish a transcription difference from missing/rejected claims.
The clean M4A success proves one controlled audio input works, not that the
original recording was understood correctly. Root cause remains unproven.

The original phone result's "What we read" transcript has been requested.
Public verdicts omit transcripts by design, and the database excludes source
transcripts from saved verdict JSON; the public API cannot recover this text.
If the result page is no longer open, use the original recording from outside
Git for a reproducible investigation. Do not alter scoring rules or force the
expected band while the evidence is missing.

The user confirmed the original recording is still on Risheeth's iPhone and
is not on Samarth's laptop. Transfer the original M4A privately as a file and
save it outside Git, for example in
`C:\Users\samar\Documents\cbyp-private\voice-tests\` on Samarth's machine.
Use a fresh local database for replay; a same-file live request can return a
cached verdict with no transcript. Run `python tools/replay_check.py <file>`, which uses a fresh throwaway
database and prints the transcript. Preserve the original bytes for diagnosis.

The phone used a non-test anonymous ID for these checks. Samarth must relabel
that known test identity and associated usage as testing before any usage claims.
This relabelling has not been confirmed. Future iPhone checks should use
`u_test_risheeth_iphone`; changing browser storage affects future checks only.

## iPhone test identity

Continue the iPhone check in Safari. On the live origin, save a bookmark named
`utest`, edit its address to the following bookmarklet, then invoke that bookmark
while the live page is open:

```javascript
javascript:localStorage.setItem('cbyp_anon_id','u_test_risheeth_iphone');alert(localStorage.getItem('cbyp_anon_id'));location.reload()
```

The alert must show `u_test_risheeth_iphone`; dismiss it and allow the page to
reload before uploading. Keep subsequent tests in the same Safari context.
Storage is separate between browsers; configuring Safari does not configure
Chrome or an Android phone. The reported upload checks still used a non-test
ID, so the test-ID setup has not been confirmed. iPhone results cannot close
the separate Android gate.

## Emulated Android Chrome, 30 October, 20:15 IST (not a physical phone)

Run by Claude on Samarth's laptop: real Chrome 156 in Playwright's Pixel 7 profile (Android 14 user agent, touch,
390 x 915 screen) against the live site, with the test ID `u_test_android_emulated`. It checks the web flow in
Chrome's Android mode: the upload buttons, the verdict and Listen. It does not test the Android file picker, the
microphone app or the phone's speaker, so the physical Android gate stays open.

| Case | Check ID | Result | Server / wall time |
|---|---|---|---|
| WhatsApp-style screenshot of a labelled fictional stock tip (PNG) | `chk_01M66MAYHT5JJBNQ` | High risk 100; text read correctly; nothing unchecked | 2.84 s / 4.25 s |
| Listen on that verdict | (same) | MP3 returned (200, 108,908 bytes) | 11.95 s on the first tap (cold) |
| Voice note of the fictional script (M4A, synthetic voice) | `chk_01M66MBFZQRMRHQ5` | Caution 30; transcript "Our investment plan guarantees your money will double in 7 days. Deposit today." | 1.82 s / 2.73 s |

## Synthetic live API preflight, 30 October

These checks used `u_test` IDs and authored fixtures. They do not establish
Android upload behavior, real-message performance, consented voice collection
or the ten-note human acceptance gate below.

| Input | Check ID | HTTP | Wall time | Stored/server processing | Result |
|---|---|---:|---:|---:|---|
| Hindi screenshot | `chk_01M66C5G3QW6FJK5` | 200 | 14.31 s | 4.62 s stored | high risk, 100 |
| Same screenshot, warm connection and neutral sample label | `chk_01M66CBJD7RS3TQX` | 200 | 5.28 s | 2.92 s | high risk, 100 |
| English synthetic OGG reading en1 | `chk_01M66C60066WWKXW` | 200 | 4.42 s | Not recorded | caution, 30 |
| Hindi synthetic OGG reading hi1 | `chk_01M66C662KK1GPZN` | 200 | 2.55 s | Not recorded | caution, 30 |

All four checks were uncached and returned no unchecked stages. The screenshot
fixture is the labelled sample in `docs/screenshots/2-home-hi-filled.png`.
The two voice fixtures were generated using the discovered TTS model's stock
voice from the fictional scripts below, then converted to OGG/Opus. They are
not housemate recordings. English and Hindi transcripts retained the promised
doubling in seven days and deposit request. Caution is the expected band for
these claims-only scripts; neither contains a payment identifier.

The first screenshot exceeded the ten-second wall-time target. Its stored
pipeline timing excludes upload, request parsing and input validation. The warm
control used the same image plus a neutral sample label to avoid the cache.
The timing difference does not establish a root cause; keep both observations
and verify on the actual phone/network before claiming screenshot acceptance.
No frontend, scoring or pipeline changes were made for these probes.

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
