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
