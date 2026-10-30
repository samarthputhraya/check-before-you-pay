# Round 2 handoff — Friday 30 October, before 9 AM IST freeze

Role B code is in separate PRs; Samarth reviews/merges and deploys.

## Final combined verification

On Friday morning, all five branches merged locally into
`codex/round2-integration` without conflicts against main `db7af7e`.
`python -m pytest -o addopts='' -q --tb=short` passed **508 tests in 58.21 s**.
The combined diff leaves `backend/signals.py`, `backend/weights.py` and `web/`
unchanged. A fresh history scan covered 135 reachable commits, with no committed
environment files and only the two previously reviewed public test vectors.
The integration branch is a local test branch; none of these PRs has been merged
into remote main or deployed by this work.

R1 now has 20 focused tests and verifies the confirmed bot identity before
registering its webhook. R2's final real-provider backend probes returned Hindi
MP3 in 4.23 s and Tamil MP3 in 4.60 s; cached retrieval took 15/16 ms without
another model call. Earlier Hindi timeout failures and their diagnostic are
documented in `docs/LISTEN.md`. Android/native-speaker acceptance remains pending.

| Task | PR / state | Acceptance still required |
|---|---|---|
| R1 Telegram | [#9](https://github.com/samarthputhraya/check-before-you-pay/pull/9) | Bot token in private environment; Samarth deploy/register webhook; forwarded text/photo/voice test chat under 10 s |
| R2 Listen | [#10](https://github.com/samarthputhraya/check-before-you-pay/pull/10) | Rishabh button integration; deployed Hindi/Tamil Android playback and native pronunciation |
| R3 correctness | [#12](https://github.com/samarthputhraya/check-before-you-pay/pull/12) | Review/merge/deploy; Dodo test-mode delivery when server keys exist |
| R4 public readiness | [#13](https://github.com/samarthputhraya/check-before-you-pay/pull/13) | Samarth reviews scan; rerun before visibility change |
| R5 people work | [#14](https://github.com/samarthputhraya/check-before-you-pay/pull/14), instructions prepared | viaSocket sheet/email proof and clip; consented corpus; native quiz signoff; Android tests |

The confirmed public bot username is **CheckBeforeYouPayBot**:
https://t.me/CheckBeforeYouPayBot. At the last local check, `TELEGRAM_BOT_TOKEN`
was absent from `.env`. No token or viaSocket webhook URL has been obtained or
sent. Keep both out of PRs/chat; transfer privately to Samarth when available.

The local computer-control tool could not establish the browser URL sufficiently
to operate it, and no Telegram/viaSocket connector was available. BotFather and
viaSocket account setup remain with Risheeth; no external completion is claimed.

## Live API smoke evidence

On 30 October early morning IST, `/api/health` returned 200 with LLM/database up,
and Hindi `/api/quiz` returned 10 items. A labelled synthetic text submitted with
`u_test_round2_smoke` returned 200 in **4.62 seconds**, `high_risk`, score 100,
no unchecked stages and no cache hit: `chk_01M64TRQJF6CY3PA`.
This is one API observation against existing live main, not a latency benchmark,
phone test or acceptance of the unmerged Round 2 features.

## Instructions ready for the human handoff

- `docs/VIASOCKET.md`: exact masked fields, private demo Sheet, own-email recipient,
  Google connection within viaSocket, deduplication and a 20-second proof clip.
- `docs/COLLECT.md`: written consent per message, redaction before saving, separate
  public-release consent, real-data schema and the current evaluation command.
- `docs/PHONE_ACCEPTANCE.md`: ten fictional voice scripts, Android screenshot and
  Listen checks, and native Hindi/Hinglish/Marathi quiz review.

The planned Thursday 6–9 PM collection window has passed; no resulting files were
provided. `eval/real.jsonl` and real-data results are intentionally absent. Do not
present authored examples, automated checks or pending forms as human evidence.
