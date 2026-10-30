# Round 2 handoff — Friday 30 October

Role B code is in separate PRs; Samarth reviews/merges and deploys. The initial
Telegram, Listen and correctness work is now on main through PR #11, merged as
`afd5f77`. Samarth also deployed that feature set and added the Listen UI. Later
follow-ups remain in PRs; the 9 AM merge cutoff has passed, so their rollout is
for Samarth's post-freeze review.

## Current combined verification

Against main `f5b4267` (including PR #15), all pending Role B branches, the
test-isolation fix in [#16](https://github.com/samarthputhraya/check-before-you-pay/pull/16)
and Samarth's deployed PR #17 were merged locally. A Telegram documentation
conflict was resolved on its own PR branch to preserve the live configuration
and identity guard. The combined suite passed **553 tests in 62.21 s**:
`python -m pytest -o addopts='' -q --tb=short`.
The test-isolation fix clears the developer's `PUBLIC_BASE_URL` in the offline
fixture: otherwise a live HTTPS URL makes the HTTP test client's event cookie
Secure and causes shares to be omitted. Production cookie security is unchanged.
The combined diff against this main leaves scoring files and `web/` unchanged.
The integration branch remains local and is not a deployment branch.
A history scan at integration commit `df2c3ef` covered **178 reachable commits**:
no committed `.env` or `.env.railway`, and only the two documented public
Standard Webhooks test vectors. This is a heuristic scan; rerun it before
making the repository public.

After the subsequent Hindi/Hinglish wording edits, the quiz and sample-data
checks passed **39 tests in 5.36 s**. The matching API examples were updated.
Answer keys and quiz metadata were verified unchanged. The 553-test combined
run above predates these copy edits; the focused run validates their affected
content, public examples and scoring behavior.

## Earlier combined verification (before PR #11 merged)

On Friday morning, all five branches merged locally into
`codex/round2-integration` without conflicts against main `db7af7e`.
`python -m pytest -o addopts='' -q --tb=short` passed **508 tests in 58.21 s**.
The combined diff leaves `backend/signals.py`, `backend/weights.py` and `web/`
unchanged. A fresh history scan covered 135 reachable commits, with no committed
environment files and only the two previously reviewed public test vectors.
The integration branch is a local test branch. This 508-test result applies to
the earlier base; subsequent verification must use the newer main described above.

R1 now has 21 focused tests and verifies the confirmed bot identity before
registering its webhook. R2's final real-provider backend probes returned Hindi
MP3 in 4.23 s and Tamil MP3 in 4.60 s; cached retrieval took 15/16 ms without
another model call. Earlier Hindi timeout failures and their diagnostic are
documented in `docs/LISTEN.md`. Risheeth subsequently reported successful
playback of both fresh Hindi and Tamil links in response to the Android prompt.
Detailed device/timing and native pronunciation results were not supplied.

| Task | PR / state | Acceptance still required |
|---|---|---|
| R1 Telegram | Live; user reports text verdict and working link passed; setup follow-up in [#9](https://github.com/samarthputhraya/check-before-you-pay/pull/9) | Screenshot/voice chat acceptance remains; the text result is user-reported |
| R2 Listen | Live; fresh Hindi/Tamil Android playback user-reported passed; follow-up in [#10](https://github.com/samarthputhraya/check-before-you-pay/pull/10) | Listen-button phone flow, device/timing details and native pronunciation not recorded |
| R3 correctness | [#12](https://github.com/samarthputhraya/check-before-you-pay/pull/12), merged through #11; tests passed | Code task complete |
| R4 public readiness | [#13](https://github.com/samarthputhraya/check-before-you-pay/pull/13) | Samarth reviews scan; rerun before visibility change |
| R5 people work | [#14](https://github.com/samarthputhraya/check-before-you-pay/pull/14); retain Samarth's live viaSocket workflow per user decision | Clip assigned to Samarth; corpus not collected; Hindi/Hinglish reviewer available but approval pending; screenshot/voice phone tests |

The confirmed public bot username is **CheckBeforeYouPayBot**:
https://telegram.me/CheckBeforeYouPayBot. The user supplied the token in `.env.example`;
it was moved to ignored `.env` and cleared from the tracked template before any
commit. `getMe` successfully verified the exact username. `getWebhookInfo`
already points to the live endpoint, with zero pending updates and no recent
delivery error. The existing registration was preserved. Risheeth subsequently
reported that the requested private-chat text check passed with a verdict and
working link, responding to the under-10-second test prompt. No timing trace was
captured here. Screenshot/voice chat acceptance remains. Keep credentials out
of PRs and chat; the production viaSocket URL is already configured by Samarth.

The user's browser timed out reaching `t.me`, before opening the chat. They were
directed to search for `@CheckBeforeYouPayBot` inside the Telegram app. This is
not evidence of a bot response or a bot failure. The locally generated webhook
secret did not match the existing server configuration; do not run setup with
that local value until Samarth aligns the server and registration privately.

The earlier computer-control failures were resolved enough to reach the
viaSocket automation dashboard and generate a five-step workflow plan.
The user supplied the private demo Sheet URL and confirmed the correct headers,
ownership and Samarth's Editor access. Risheeth explicitly confirmed his own
email for alerts. Google Sheets and Gmail connections now show ready.
The proposed plan validates event/report ID, looks up
the report ID, stops duplicates, then appends a row and sends one email for a new
ID. A draft webhook trigger exists, awaiting expected payload and the remaining
action mappings. This draft has not been activated or tested.

Samarth's newer PR #17 reports a separate production viaSocket flow live since
14:20 IST in his own workspace, with his sheet/email, two test reports and a
successful duplicate test. This is attributed handoff evidence, not a new test
by this work. The user explicitly chose to retain Samarth's production workflow
and leave the Risheeth draft inactive. No server setting has been changed and
no second workflow has been activated. The user confirmed Samarth will record
the 20-second clip. Delivery of the clip remains pending; webhook URLs and inbox
contents must be excluded from capture.

## Live API smoke evidence

On 30 October early morning IST, `/api/health` returned 200 with LLM/database up,
and Hindi `/api/quiz` returned 10 items. A labelled synthetic text submitted with
`u_test_round2_smoke` returned 200 in **4.62 seconds**, `high_risk`, score 100,
no unchecked stages and no cache hit: `chk_01M64TRQJF6CY3PA`.
This is one API observation against existing live main, not a latency benchmark,
phone test or acceptance of the unmerged Round 2 features.

After #11 merged, new live Hindi and Tamil checks and their audio endpoints
returned 200. Hindi: `chk_01M65AGM2WB9WVJQ`, check 3.54 s, audio 10.72 s,
MP3 duration 12.62 s. Tamil: `chk_01M65AH1S6ENXT22`, check 4.77 s, audio 6.61 s,
MP3 duration 12.74 s. Repeat audio downloads took 0.94/0.92 s and returned
identical bytes. These synthetic API checks do not establish physical phone or
native-speaker acceptance. Samarth's viewport/browser checks are in `HANDOFF.md`.

Later that afternoon, the older check IDs returned 404. Fresh `u_test` checks
and MP3s returned 200: Hindi `chk_01M66A8YW0A5QB37` (check 3.75 s, audio 6.30 s,
MP3 9.46 s) and Tamil `chk_01M66A98E5YK122P` (check 2.87 s, audio 9.12 s,
MP3 14.78 s). Fresh links were sent to Risheeth for Android playback acceptance;
Risheeth replied that the replacements worked, confirming playback in response
to the Android prompt. This is user-reported evidence; no phone model, measured
timing or detailed native pronunciation assessment was supplied.

## Instructions ready for the human handoff

- `docs/VIASOCKET.md`: exact masked fields, private demo Sheet, own-email recipient,
  Google connection within viaSocket, deduplication and a 20-second proof clip.
- `docs/COLLECT.md`: written consent per message, redaction before saving, separate
  public-release consent, real-data schema and the current evaluation command.
- `docs/PHONE_ACCEPTANCE.md`: ten fictional voice scripts, Android screenshot and
  Listen checks, and native Hindi/Hinglish/Marathi quiz review.
- `docs/QUIZ_NATIVE_REVIEW.md`: readable messages, explanations, approval fields
  and exact source revision hashes for a fluent reviewer. Approval remains pending.

The user explicitly confirmed that no real messages, anonymized corpus, consent
manifest or receipts have been collected on Samarth's machine or committed to
any branch. Real-data evaluation remains pending. `eval/real.jsonl` and real-data
results are intentionally absent; no real-message result may be claimed.
The user selected Hindi and Hinglish for fluent review. The 20 items and their
explanations are prepared in `docs/QUIZ_NATIVE_REVIEW.md`; actual approval or
corrections are still required. Subsequent feedback was explicitly AI-assisted:
the user reported all answer keys correct and supplied wording edits for hi/q2,
hi/q5, hi/q9, hi/q10, hinglish/q3 and hinglish/q9. Those edits were applied and
the review sheet regenerated with new source hashes. Answer keys and quiz
metadata are unchanged. Fluent-speaker approval of the edited 20 items is still
pending; the AI-assisted feedback is not human signoff.
