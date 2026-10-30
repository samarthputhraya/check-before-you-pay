# Role B task register: assigned, completed and remaining

**Owner:** Risheeth / Role B — backend, AI and data.

**Status date:** 30 October 2026, IST.

**Live site:** https://34-45-129-243.sslip.io

**Main checked:** `95fafa9`, including merged PR #17.

## Overall position

Most implementation work is delivered, and several integrations are live.
**The assignment is not fully complete.** One iPhone voice recording failed
acceptance. Android testing, fluent quiz approval, real-message collection,
the viaSocket clip, test-usage relabelling and five follow-up PR merges remain.

Risheeth's screenshot passed on iPhone/Safari. Hindi and Tamil verdict audio
also played on his **iPhone running iOS 27.2**. These are iPhone results and do
not establish Android acceptance.

The statuses below distinguish code delivered, code merged, live observations,
user reports and work only prepared. No percentage is assigned because the
tasks differ substantially in scope.

## Assignment sources and ownership

- [Build brief](BUILD_BRIEF.md): original Role B responsibilities.
- [Original B1–B7 assignment](https://github.com/samarthputhraya/check-before-you-pay/blob/8b6ca33/docs/ROLE_B_NEXT.md): evaluation, collection, viaSocket, voice, Dodo, small fixes and quiz.
- [Round 2 assignment](ROLE_B_NEXT.md): R1–R5, with branches and PRs into main.
- [API contract](../API_CONTRACT.md): request/response shapes. Round 2 explicitly authorized its new endpoints and documentation.

Samarth owns merges, production settings and deployment. Rishabh owns the web
UI. Round 2 follow-ups do not change scoring weights or signal rules. Earlier
team-approved scoring-v2 changes are already on main and are separate work.
The original request also specified GPT Pro for B1/B3. A separate GPT Pro
session is not evidenced in these records; the deliverables below do not
claim that particular tool-use requirement was verified.

Original targets were B1 by 17:00 on Thursday 29 October, B4/B7 by 18:00, and
collection from 18:00–21:00. Round 2's merge cutoff was Friday 30 October at
09:00. These targets have passed; remaining merges/rollout need Samarth's
post-freeze review. Final submission is due Saturday 31 October at 09:59 IST,
with a team target of 07:59. This register does not confirm submission.

## Initial backend handover

| Assigned responsibility | Delivered | Evidence / state |
|---|---|---|
| Make the check real | Text, screenshot and audio input; model discovery; extraction with verified quotes; deterministic scoring; localized explanations and fallback behavior | PR #2 merged; later changes in #8/#11. The original handover reported 306 passing tests |
| Cache, limits and private ring links | Input caching, rate limits, hashed identifiers, link tables, script similarity and masked public verdicts | Implemented on main; exercised by the backend suite |
| Seed and supporting APIs | Broker data, wallet/entity checks, reporting webhook boundary and usage statistics | Implemented on main; files/setup linked in the README |

Implementation does not establish correctness on every real-world input.
The outstanding phone voice failure remains open.

## Original B1–B7 tasks

| Task given | Completed work | Remaining / owner |
|---|---|---|
| **B1 — labelled set, pitch numbers, S1 at 35 versus 50** | 156 authored messages: 78 scam and 78 ordinary, across eight languages; runner/results; S1 comparison; another 128-message held-out set; pitch write-up | Core deliverable complete. Retain the authored-data caveat. Real-data validation is B2/R5 |
| **B2 — real housemate messages with consent** | Collection, written consent, redaction and evaluation instructions prepared | **Not collected.** No anonymized corpus, consent manifest or receipts supplied. Risheeth collects; two people review/label; then run the real slice |
| **B3 — live viaSocket report → row + alert, template, README, clip** | Samarth's production workflow is live; row/email and duplicate behavior tested per his handoff; README describes it. User chose to keep that flow | Samarth will record the 20-second clip; delivery unconfirmed. No published reusable `/api/check` template URL/evidence supplied. Coupon was not applied; Samarth reported the free plan covers the current flow |
| **B4 — make voice reliable or cut it** | Audio input implemented/live; synthetic English/Hindi OGG probes and clean M4A control succeeded | **Acceptance incomplete; one phone recording failed.** Obtain original, diagnose, retest and complete the ten-note gate. Rishabh/Samarth own any voice-UI cut |
| **B5 — Dodo backend after handover** | Plans, test-mode checkout, order status, verified signed webhook and persistence delivered; live test purchase succeeded per Samarth's handoff | Backend/test checkout delivered. Production payment enablement remains with Samarth |
| **B6 — plain skipped-check copy, backend README, secret scan** | Plain-language unchecked labels and README sections on main through team integration; history scan/report prepared | Scan is a dated snapshot; rerun before publication. License/scanner PR #13 still needs merge |
| **B7 — real quiz backend** | Ten items each in English, Hindi, Hinglish and Marathi; server-side scoring; stored results; quiz events/share proof; API examples | Backend complete. Six wording edits prepared in #14; fluent approval still pending under R5 |

The original B5 request named a ₹49 Family plan. The deployed test setup uses
₹99/month for Family and ₹999/month for API, per [DODO.md](DODO.md); the team
changed Family pricing because of Dodo's minimum charge. Do not describe it as
a ₹49 checkout already tested.

### B1 measurement evidence

The 120-message minimum was exceeded. The initial S1-only comparison re-added
saved signal points without new model calls: at S1=35, 1/78 scams were high
risk; at S1=50, 30/78 were high risk. Both flagged 40/78 at caution-or-high-risk
and flagged 0/78 ordinary messages. This measures band severity on that authored
set, separately from later scoring-v2 changes.

The latest documented held-out run reports **61/64 scams flagged, 0/64 ordinary
payments flagged**, with text p50/p95 of 2.3/2.8 seconds. Those 128 messages were
authored blind, not collected from real users. Three runs flagged 62, 61 and 61
of 64 scams; quote “about 95%” with the limitations. See [EVAL.md](EVAL.md) and
[the evaluation files](../eval/README.md).

The team adopted scoring v2 with S1=50 before Round 2. The comparison above is
historical evidence, not a new request to change the frozen weights.

The separate real-data target is 30+ contributed messages under [COLLECT.md](COLLECT.md).
Actual collected messages and written consent records supplied here: **zero**.
Consent is per message; remove all real names, phone numbers, faces and UPI IDs
(including suspected senders'), plus other private identifiers before saving.
Keep receipts/originals outside Git, require separate publication permission,
and create `eval/real.jsonl` / `eval/real_results.json` only after actual collection,
labelling and the evaluation run.

## Round 2: R1–R5

| Task given | Completed implementation / evidence | Remaining acceptance / release work |
|---|---|---|
| **R1 — Telegram bot** | Private text/photo/voice adapter, authenticated webhook, HMAC user identity, normal pipeline/limits, localized verdict/referral link. Initial code merged via #11. Risheeth text/link passed. Samarth documented real-chat text, screenshot and voice at 1.7–5.0 s server time | #9 identity guard and extra coverage still open. `/lang hi` and unsupported file not live-tested in recorded handoff |
| **R2 — Listen / TTS** | MP3 endpoint, SQLite cache, masking and clean unavailable response; button delivered by web owner. Hindi/Tamil MP3s under 60 s verified; basic iPhone playback user-reported passed | **Android pending.** Full Listen-button/native pronunciation details not recorded. Model-discovery/warmup follow-up #10 open |
| **R3 — refunds, RDAP negatives, sample guard** | Verified refunds mark orders refunded/exclude them from paid counts; cancellation ledger; RDAP 404 adds zero-point “not registered” evidence; sample guard | Code task complete. #12 merged through #11; no scoring change made by these fixes |
| **R4 — public-repo readiness** | MIT license, repeatable scanner and report prepared. Latest recorded scan: 178 reachable commits at local integration `df2c3ef`; no committed `.env`/`.env.railway`; two exact public test vectors only | #13 needs review/merge. Rescan newer commits before publication. Visibility not changed by this work |
| **R5 — people/final acceptance** | Production viaSocket retained; consent instructions; ten fictional voice scripts; readable quiz review; six wording fixes; actual iPhone screenshot result recorded | Voice mismatch, Android, fluent review, real corpus, clip and test-ID relabelling remain open |

### viaSocket decision

Samarth's selected production flow validates a report, finds an existing report
ID, adds a new row, sends the alert for a new row and returns a result. His
handoff documents delivery, duplicate suppression and rejection of non-report
requests. PR #17, including the ten-second delivery timeout, is now merged.

Before that flow was discovered, Risheeth confirmed his own demo sheet,
headers, Editor sharing and own alert address. Sheets/Gmail were connected,
and an alternate draft trigger/plan was prepared. **That draft is incomplete
and inactive by user decision.** No server URL was switched to it. Retaining
Samarth's live flow needs no additional webhook handoff. The production clip
is assigned to Samarth and has not been received here. See [VIASOCKET.md](VIASOCKET.md).

## Actual phone results and open voice issue

Device: Risheeth's iPhone, iOS 27.2; upload browser: Safari. Model not supplied.
Approximate times are user-reported; stored server timings are identified below.

| Case | Check ID | Observation | Status |
|---|---|---|---|
| Screenshot, about 18:48 IST | `chk_01M66FCVS35V00B5` | High risk 100, about 2.4 s; S1=50, S4=20, S5=15, S6=40; domain age unchecked | **PASS on iPhone/Safari**, not Android |
| Original phone voice, about 18:52 IST | `chk_01M66FJQ4DS3N0PG` | No known signals 0, about 2.3 s; expected caution; no signals/unchecked stages | **NOT PASSED** |
| Same intended script as clean M4A via API | `chk_01M66G2981H1TRN0` | Caution 30; correct transcript reported; stored server latency 2.060 s | Control passed; original failure remains |
| Hindi/Tamil spoken verdict links | `chk_01M66A8YW0A5QB37`, `chk_01M66A98E5YK122P` | Both worked on iPhone; API durations 9.46/14.78 s | Basic iPhone playback passed; Android pending |

The screenshot's raw 125 points are capped at 100 as designed. The assistant
fetched the three upload verdicts and confirmed bands/scores/unchecked fields.
Stored server latencies were 2.404, 2.337 and 2.060 s.

**The voice failure's root cause is unknown.** A transcription difference,
missing claim or rejected quote is possible; the clean control does not
identify the cause. No scoring/prompt change has been made to force a pass.

The failed transcript cannot be recovered from the public API. Transcripts are
excluded from stored verdict JSON, and a same-file live replay may return the
cached verdict without one. The original recording is on Risheeth's iPhone;
it has not been supplied to this checkout or Samarth's laptop.

Next: transfer the **original M4A as a file**, preserving bytes, privately to
Samarth. Save outside Git, for example at
`C:\Users\samar\Documents\cbyp-private\voice-tests\` on his machine.
Replay through the local backend with a fresh private database to inspect the
transcript and extracted/verified claims. A new recording or synthetic version
cannot reproduce the original input. The proposed dedicated replay utility
has **not been implemented or tested**; no PR exists for it.

The uploads used a non-test phone ID. Samarth's relabelling of that identity
and associated usage is pending. Setting `cbyp_anon_id` to
`u_test_risheeth_iphone` affects future requests only; that setup is also
unconfirmed. Do not treat usage totals as cleaned of these tests yet.
Samarth's four Telegram checks are also identified as team tests in the
Telegram handoff.

### Synthetic probes: separate from phone acceptance

- English/Hindi synthetic OGG returned caution 30 in 4.42/2.55 s, retaining the
  promised doubling and deposit meaning.
- A labelled screenshot returned high risk in 14.31 s wall time, versus 4.62 s
  stored pipeline time. A warm control took 5.28 s overall / 2.92 s pipeline.
  Retain the slower first observation.
- All were uncached with no unchecked stages. These authored fixtures are not
  real messages or ten consented human voice notes.

Full cases/scripts: [PHONE_ACCEPTANCE.md](PHONE_ACCEPTANCE.md).

## Validation and PR register

| Evidence | Recorded result | Scope / limitation |
|---|---|---|
| Original PR #2 handover | 306 tests passed, user/team reported | Historical snapshot |
| Latest combined run recorded here | **553 passed in 62.21 s** | Main `f5b4267` plus pending Role B branches, #16 and deployed #17; before later quiz edits |
| Quiz/sample checks after wording edits | **39 passed in 5.36 s** | Content, examples, scoring and sample gates; keys/metadata unchanged |
| Focused Telegram / audio suites | 21 / 13 passed | Earlier follow-up checks with offline providers |
| Latest recorded history scan | 178 commits; two public test vectors only | Snapshot `df2c3ef`; rerun after newer commits before publication |

The local `codex/round2-integration` branch is for verification, not deployment.
The 553-test result is not a fresh run after every later commit.

| PR | State checked 30 October | Contents |
|---|---|---|
| [#2](https://github.com/samarthputhraya/check-before-you-pay/pull/2) | Merged | Initial real backend and private links/integrations |
| [#8](https://github.com/samarthputhraya/check-before-you-pay/pull/8) | Merged | Quiz, Dodo, eval/scoring-v2 and team web integration |
| [#11](https://github.com/samarthputhraya/check-before-you-pay/pull/11) | Merged | Initial Telegram/Listen, correctness and team QA/UI |
| [#12](https://github.com/samarthputhraya/check-before-you-pay/pull/12) | Merged through #11 | Refunds, RDAP negatives and sample labels |
| [#15](https://github.com/samarthputhraya/check-before-you-pay/pull/15) | Merged | Launch operations, test-ID exclusion and setup |
| [#17](https://github.com/samarthputhraya/check-before-you-pay/pull/17) | Merged | Live viaSocket timeout/docs and Telegram evidence |
| [#9](https://github.com/samarthputhraya/check-before-you-pay/pull/9) | **Open** | Telegram identity guard and extra tests |
| [#10](https://github.com/samarthputhraya/check-before-you-pay/pull/10) | **Open** | Listen discovery/warmup fixes and acceptance evidence |
| [#13](https://github.com/samarthputhraya/check-before-you-pay/pull/13) | **Open** | MIT license, scanner and report |
| [#14](https://github.com/samarthputhraya/check-before-you-pay/pull/14) | **Open** | Quiz wording, acceptance docs and this register |
| [#16](https://github.com/samarthputhraya/check-before-you-pay/pull/16) | **Open** | Tests isolated from local HTTPS public URL |

An open follow-up does not mean the initial feature is absent from production.
It also does not mean its follow-up code is deployed. Samarth decides merge
order/deployment; #17 does not automatically merge the five open follow-ups.

## Remaining work, owners and completion criteria

| Priority | Owner | Next action | Complete when |
|---|---|---|---|
| 1 | Risheeth → Samarth; Role B diagnoses | Transfer original failed M4A outside Git; recover transcript/claims with fresh local replay | Original failure understood, justified fix reviewed if needed, original case retested correctly |
| 2 | Samarth + Risheeth | Relabel existing phone tests; confirm future test ID | Associated usage excluded from real totals; new request uses `u_test_risheeth_iphone` |
| 3 | Risheeth / Android tester | Hindi/Tamil Listen and screenshot/voice on actual Android | Device/browser, IDs, results/times recorded; failures resolved or owner decision documented |
| 4 | Risheeth + consenting readers; Rishabh/Samarth decide | Five Hindi + five English scripted WhatsApp notes; compare transcripts and time all ten | At least 9/10 correct and under 10 s, or documented cut decision under original B4 rule |
| 5 | Fluent Hindi/Hinglish reviewer | Read all 20 edited messages and explanations in [review sheet](QUIZ_NATIVE_REVIEW.md) | Explicit fluent approval at recorded source revisions, or corrections applied/reviewed. AI-assisted feedback is not approval |
| 6 | Samarth | Deliver 20-second production viaSocket clip | Real report → one row → successful email step shown; webhook URL/inbox excluded |
| 7 | Samarth / viaSocket owner | Confirm/publish reusable `/api/check` template requested in B3 | Working published template/reference supplied, or scope change explicitly accepted |
| 8 | Risheeth + contributors | Written per-message consent, redaction, separate real slice | Anonymized independently labelled corpus and private consent manifest exist; publication permission checked |
| 9 | Role B after collection | Run real-data eval without weight changes | Reproducible denominators, misses/false positives and latency. **No real-data result exists now** |
| 10 | Role B resolves branch issues; Samarth reviews/merges/deploys | Review five open PRs, resolve current-base conflicts, run checks and deploy appropriate changes | PR states and live revision confirm reviewed follow-ups delivered |
| Before visibility change | Samarth / Role B | Rescan final fetched history | Current reviewed scan, license merged and owner visibility decision |

## Handoff records

- [ROUND2_STATUS.md](ROUND2_STATUS.md): detailed implementation/test history.
- [PHONE_ACCEPTANCE.md](PHONE_ACCEPTANCE.md): device results, failure and scripts.
- [LISTEN.md](LISTEN.md): endpoint, caching, failure and audio evidence.
- [QUIZ_NATIVE_REVIEW.md](QUIZ_NATIVE_REVIEW.md): edited text, pending approvals.
- [COLLECT.md](COLLECT.md): consent, redaction, schema and real-data runner.
- [VIASOCKET.md](VIASOCKET.md): selected live flow and inactive alternate.
- [DODO.md](DODO.md): test-mode checkout setup/evidence.
- [SECRET_SCAN.md](https://github.com/samarthputhraya/check-before-you-pay/blob/codex/round2-public-readiness/docs/SECRET_SCAN.md): scan report/limitations in open #13.

Keep keys, webhook URLs, original recordings, consent receipts and database
exports out of this register and Git. As of this snapshot, real collection has
not happened, clip delivery and fluent approval are pending, the original voice
failure is unresolved, and the replay utility is not delivered.
