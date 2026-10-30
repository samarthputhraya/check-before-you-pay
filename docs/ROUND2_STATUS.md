# Round 2 handoff — Friday 30 October

Role B code is in separate PRs; Samarth reviews/merges and deploys. The initial
Telegram, Listen and correctness work is now on main through PR #11, merged as
`afd5f77`. Samarth also deployed that feature set and added the Listen UI. Later
follow-ups remain in PRs; the 9 AM merge cutoff has passed, so their rollout is
for Samarth's post-freeze review.

## Earlier combined verification (before PR #11 merged)

On Friday morning, all five branches merged locally into
`codex/round2-integration` without conflicts against main `db7af7e`.
`python -m pytest -o addopts='' -q --tb=short` passed **508 tests in 58.21 s**.
The combined diff leaves `backend/signals.py`, `backend/weights.py` and `web/`
unchanged. A fresh history scan covered 135 reachable commits, with no committed
environment files and only the two previously reviewed public test vectors.
The integration branch is a local test branch. This 508-test result applies to
the earlier base; subsequent verification must use the newer main described above.

R1 now has 20 focused tests and verifies the confirmed bot identity before
registering its webhook. R2's final real-provider backend probes returned Hindi
MP3 in 4.23 s and Tamil MP3 in 4.60 s; cached retrieval took 15/16 ms without
another model call. Earlier Hindi timeout failures and their diagnostic are
documented in `docs/LISTEN.md`. Android/native-speaker acceptance remains pending.

| Task | PR / state | Acceptance still required |
|---|---|---|
| R1 Telegram | Initial code on main; identity/setup tests in [#9](https://github.com/samarthputhraya/check-before-you-pay/pull/9) | Real forwarded text/photo/voice chat test under 10 s; server configuration if that fails |
| R2 Listen | Backend and button on main/live; later model/warmup fixes in [#10](https://github.com/samarthputhraya/check-before-you-pay/pull/10) | Physical Android playback and native pronunciation |
| R3 correctness | [#12](https://github.com/samarthputhraya/check-before-you-pay/pull/12), merged through #11 | Dodo test-mode delivery when valid server keys exist |
| R4 public readiness | [#13](https://github.com/samarthputhraya/check-before-you-pay/pull/13) | Samarth reviews scan; rerun before visibility change |
| R5 people work | [#14](https://github.com/samarthputhraya/check-before-you-pay/pull/14), instructions prepared | viaSocket sheet/email proof and clip; consented corpus; native quiz signoff; Android tests |

The confirmed public bot username is **CheckBeforeYouPayBot**:
https://t.me/CheckBeforeYouPayBot. The user supplied the token in `.env.example`;
it was moved to ignored `.env` and cleared from the tracked template before any
commit. `getMe` successfully verified the exact username. `getWebhookInfo`
already points to the live endpoint, with zero pending updates and no recent
delivery error. The existing registration was preserved. Real chat acceptance
is still required; registration alone is not proof of a reply. No viaSocket
webhook URL has been supplied. Keep credentials out of PRs and chat.

The local computer-control tool could not establish the browser URL sufficiently
to operate it, and no Telegram/viaSocket connector was available. viaSocket
account setup remains with Risheeth; its sheet question was deferred at his request.

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
