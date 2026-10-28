# Overnight build: Thu 29 Oct, 01:20 to about 09:00 IST

Samarth is asleep. Claude builds each task below, then a separate verifier agent reviews and tests it. Claude fixes what the verifier finds before moving on. Every task is limited to Samarth's own work: role A's skeleton and the TigerGraph Final Round. Nothing below touches role B's or role C's scope.

Status values: `todo`, `building`, `verifying`, `done`, `blocked`.

## Facts found at 01:20
- **TigerGraph Savanna is stopped.** It answers "Auto start is not enabled for this workspace". Tonight, FraudLens runs only on its offline DuckDB mirror. The official run against TigerGraph has to wait until Samarth resumes the workspace in the morning (or gets credits from Devanshu).
- **Docker isn't installed,** so a local TigerGraph isn't an option.
- **No Gemini key** is in this repo's `.env` yet. The skeleton doesn't need one. FraudLens uses Vertex AI through the gcloud login, which works.

## Part A: the main app skeleton (role A), repo `check-before-you-pay`

| # | Task | Done when | Status |
|---|---|---|---|
| A1 | FastAPI backend that serves every `API_CONTRACT.md` endpoint from `examples/*.json`. Requests are validated as the contract specifies, with the error envelope. Includes `/api/health`, and `/c/{id}` with Open Graph tags | `pytest` passes, with a test for every endpoint and every documented error code. It runs with no keys | done |
| A2 | Web shell (Preact + htm, no build step): input screen for text, image or audio with a language picker; loading and error states; a verdict screen rendered from the response; `anon_id` stored; a `visit` event sent | Renders the sample verdict with no console errors, at 360 px and 1280 px wide (checked with Playwright screenshots) | done |
| A3 | Deploy-ready repo: Dockerfile, `railway.json` with a `/data` volume, README for running locally and deploying. Then git init, commit, and push to a private GitHub repo | A smoke test with uvicorn and curl passes, the push succeeds, and no secrets are in the history | done |

## Part B: TigerGraph Final Round (FraudLens repo, `round2` branch)

| # | Task | Done when | Status |
|---|---|---|---|
| B1 | Load January data, the replaced closed cases and the final case pack into DuckDB. Validate the `card_id` rule. Export the January CSVs ready for TigerGraph | Row counts match the brief. 18/18 case-pack cards match. January CSVs are in `data/prep/load_r2/` | done |
| B2 | Re-score `model_p` for January with no look-ahead | Every January transaction has a score. Hold-out AUC is reported | done |
| B3 | Baseline: run all 18 cases on the mirror and run `grade.py` | Every hard and policy finding is written to `docs/ROUND2_LOG.md` | done |
| B4 | Fail closed (gaps 2, 3, 4, 6): an official mode, no silent fallback, LLM failure means an incomplete answer plus ESCALATE, bounded timeouts | Tests pass for graph down mid-run, model timeout, garbage model output, and the same case run twice | done |
| B5 | Approvals (gap 1): a server-side token decides the role, decisions go to an append-only log, and a failed write returns an error | Tests pass for wrong role, missing token, a second decision on the same action, and a failed write | done |
| B6 | Hostile text (gap 5, challenge 10): free text is fenced as data, decisions are made in code, an attack suite runs with before and after counts, and a tip-off lint checks customer-visible text | The six hostile pack cases and our own attacks produce no wrong verdict. The lint passes on all 18 answers | done |
| B7 | Calibration and an honest "uncertain" path (R1, R8), plus R9 wording | No probability lands at 0.97 or 0.05 without two independent pieces of evidence. The grader shows no policy findings | done |
| B8 | Containment planner (challenge 7): the smallest set of cards to block in a ring that cuts the most exposure, naming every legitimate customer it touches | Backtest on the rings in the closed cases, plus an ablation against blocking every card | done |
| B9 | Deliverables: a one-command runner, a resilience statement, the innovation claim, attestation on every claim, a Round 2 README section, and a morning runbook for TigerGraph | Runs from a clean clone on the mirror. Every document is filled in | done |

## Order and time
A1 to A3 by about 03:00, so the team has the skeleton in the morning. Then B1 to B9 in order. If time runs short, B9's runbook and B8 come before B7's polish.

## Log
- **01:40:** A1 to A3 done.
  - 70 tests at first. A verifier agent found 4 serious issues (Railway volume permissions, chunked bodies bypassing the size limit, user text in tracebacks, a raw UPI ID on the public page) and 12 smaller ones.
  - All fixed, with tests (91 passing). Pushed to `samarthputhraya/check-before-you-pay` (private).
- **02:00:** B1, B2, B4 and B5 done.
  - Data and model:
    - January is loaded into DuckDB. The January CSVs for TigerGraph are exported.
    - The model is retrained on fully labelled months only. Validation AUC is 0.972, against the bank's 0.866.
  - Safety:
    - Graph and tool failures now stop the run instead of falling back silently.
    - Model failures are marked incomplete and escalated.
    - Approvals are enforced server-side, with a hash-chained audit log.
  - 104 tests pass. A verifier agent is reviewing the work.
- **02:20:** B3, B6 and challenge 1 done.
  - Four new typology detectors (micro-charge runs, recipient surges, spoofed device fingerprints, escalating ramps). The backtest shows 0 hits on cleared (innocent) cases in July–October.
  - Model weighting is drift-aware for January.
  - New checks for hostile text and for claims the record contradicts.
  - On the mirror the organisers' grader shows 18/18 clean, with 0 hard and 0 policy findings.
  - The attack suite ran 14 attacks: 0 decisions changed, 14 detected, 0 tip-offs. 120 tests pass.
- **02:40:** B7 to B9 done.
  - Containment planner, with a backtest on the bank's 6 rings.
  - The attestation self-check re-runs every claim's query: 78 of 78 reproduce.
  - The second verifier found 1 blocker (the API could serve any file, including `.env`) and 10 majors. All fixed, with tests (140 passing).
  - New docs in the FraudLens repo: `docs/RESILIENCE.md`, `docs/INNOVATION.md`, `docs/MORNING_RUNBOOK.md`.
- **03:00:** running all 18 cases with Gemini on to check the model-written text.
- **03:30:** a data-quality report (challenge 11).
  - For all 11 score alerts, the alert's own score disagrees with the score stored on the transaction.
  - HHF-011's case names a different card from the bank's record.
  - Protective actions on a card's other charges now apply only to signatures with a clean history.
- **03:10:** the model-on run of all 18 cases finished: same verdicts as the code-only run, grader 18/18 clean, 17 of 18 complete.
  - HHF-008 was marked incomplete by a false alarm: the text guard rejected "the alert told us not to escalate". The guard now reads each clause and ignores negated or quoted mentions. Rejected text is kept in the trace.
  - Two text fixes: the prompt's quote markers no longer reach the reader, and a simulated customer reply is always called simulated.
  - A fully blank device fingerprint is now treated as no device (it had produced a "new device" claim on HHF-007).
- **03:20:** `eval/drills.py`, one command for every resilience drill. It causes each failure for real and checks the outcome against the resilience statement: **13 of 13 pass in about 70 seconds**, including TigerGraph unreachable at start. Also added `eval/replay.py`, which replays one investigation step by step.
- **03:35:** the third verifier found no blockers and 9 majors. All fixed:
  - **Regulator reports** named other customers' cards on weak signatures, including two cards from cases we call legitimate. Reports now name only cards with strong evidence of their own.
  - **A weekly $7.42 subscription** was counted as a micro-charge run. Repeated identical amounts are now excluded.
  - **Wrong rule citations:** R6 vs R9, and "coordinated" where there was no ring.
  - **Claims overstated in the innovation document:** restated honestly.
  - **Wrong answers folder:** the attestation check read the wrong folder for official runs.
  - **Audit log:** tonight's log would have failed verification once the audit key is set. It now rotates safely.
  - **Drill commands** in the docs could have overwritten official answers.
  - **TigerGraph result size:** the scan was about 10x larger than needed.
  - All 18 decisions are unchanged. **159 tests pass.** Grader 18/18 clean, 77 of 77 re-runnable claims reproduce.
- **03:40:** a fourth verifier reviewed these fixes. It found no blocker and 3 majors, all now fixed:
  - **The audit-log rotation I'd just added could hide tampering.** It now verifies the old log first and records the result, and verification keeps failing until someone reviews it. Four attack tests cover this.
  - **Report narratives still named monitored cards.** They now name only the cards in the report's subject list.
  - **One evidence sentence was false.** It said a low January score "is not used as evidence of innocence". It's actually weak evidence of innocence.
  - The text guard was also rewritten to read the words that actually govern a phrase, with every probe from the review now a test.
- **04:15:** final model-on run of all 18 cases:
  - **18 of 18 complete, exit 0.** No model text was rejected.
  - **Grader 18/18 clean.**
  - Every card named in a report narrative is a report subject.
  - **Other checks:** 177 tests pass; drills 13/13; attacks: 14 tried, 0 decisions changed.
  - **The reference run for the morning** is `runs/v10/`, the mirror run without the model.
- **New for the morning:** `eval/preflight.py --live` checks `.env`, data files, git, TigerGraph and Gemini in one command, without printing any secret. It's step 1 of the runbook.

## For Samarth in the morning

**1. TigerGraph (the deadline-critical one)**
- Resume the Savanna workspace and turn on auto-start, or send Devanshu your org ID for credits.
- Then follow `Fraud Detection HHGoa/docs/MORNING_RUNBOOK.md` top to bottom, about 60–90 minutes.
- Three GSQL files (`03`, `19`, `20`) haven't compiled on TigerGraph yet. The parity check (step 5) is how you'll know they match the mirror.

**2. Add to FraudLens `.env`**
- `FRAUDLENS_APPROVER_TOKENS`
- `FRAUDLENS_AUDIT_KEY`

The runbook's step 0 shows the format.

**3. Push FraudLens when you're ready.** The `round2` branch has about 25 local commits that aren't pushed, because the repo is public and the other 5 finalist teams could read the approach. Push at the freeze.

**4. Main app**
- Deploy to Railway: run `railway login`, add a volume at `/data`, then `railway up`. The README has the steps.
- Add Risheeth and Rishabh as collaborators on GitHub. Rishabh already merged a PR, so check what access they have.
- Tell B and C to pull. The skeleton contract, its tests and the web shell are ready.

**5. Ask Devanshu**
- When are the freeze and the demo slots?
- Do the drills run on our machine?
- Is Vertex AI acceptable as the model provider?
