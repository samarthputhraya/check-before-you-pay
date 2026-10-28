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
| A1 | FastAPI backend that serves every `API_CONTRACT.md` endpoint from `examples/*.json`. Requests are validated as the contract specifies, with the error envelope. Includes `/api/health`, and `/c/{id}` with Open Graph tags | `pytest` passes, with a test for every endpoint and every documented error code. It runs with no keys | todo |
| A2 | Web shell (Preact + htm, no build step): input screen for text, image or audio with a language picker; loading and error states; a verdict screen rendered from the response; `anon_id` stored; a `visit` event sent | Renders the sample verdict with no console errors, at 360 px and 1280 px wide (checked with Playwright screenshots) | todo |
| A3 | Deploy-ready repo: Dockerfile, `railway.json` with a `/data` volume, README for running locally and deploying. Then git init, commit, and push to a private GitHub repo | A smoke test with uvicorn and curl passes, the push succeeds, and no secrets are in the history | todo |

## Part B: TigerGraph Final Round (FraudLens repo, `round2` branch)

| # | Task | Done when | Status |
|---|---|---|---|
| B1 | Load January data, the replaced closed cases and the final case pack into DuckDB. Validate the `card_id` rule. Export the January CSVs ready for TigerGraph | Row counts match the brief. 18/18 case-pack cards match. January CSVs are in `data/prep/load_r2/` | todo |
| B2 | Re-score `model_p` for January with no look-ahead | Every January transaction has a score. Hold-out AUC is reported | todo |
| B3 | Baseline: run all 18 cases on the mirror and run `grade.py` | Every hard and policy finding is written to `docs/ROUND2_LOG.md` | todo |
| B4 | Fail closed (gaps 2, 3, 4, 6): an official mode, no silent fallback, LLM failure means an incomplete answer plus ESCALATE, bounded timeouts | Tests pass for graph down mid-run, model timeout, garbage model output, and the same case run twice | todo |
| B5 | Approvals (gap 1): a server-side token decides the role, decisions go to an append-only log, and a failed write returns an error | Tests pass for wrong role, missing token, a second decision on the same action, and a failed write | todo |
| B6 | Hostile text (gap 5, challenge 10): free text is fenced as data, decisions are made in code, an attack suite runs with before and after counts, and a tip-off lint checks customer-visible text | The six hostile pack cases and our own attacks produce no wrong verdict. The lint passes on all 18 answers | todo |
| B7 | Calibration and an honest "uncertain" path (R1, R8), plus R9 wording | No probability lands at 0.97 or 0.05 without two independent pieces of evidence. The grader shows no policy findings | todo |
| B8 | Containment planner (challenge 7): the smallest set of cards to block in a ring that cuts the most exposure, naming every legitimate customer it touches | Backtest on the rings in the closed cases, plus an ablation against blocking every card | todo |
| B9 | Deliverables: a one-command runner, a resilience statement, the innovation claim, attestation on every claim, a Round 2 README section, and a morning runbook for TigerGraph | Runs from a clean clone on the mirror. Every document is filled in | todo |

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
