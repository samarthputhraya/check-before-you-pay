# AGENTS.md

Before you do any work in this repo, read `docs/BUILD_BRIEF.md` and `API_CONTRACT.md`. They define what we're building ("Check Before You Pay"), why, how, and who owns each part. Ask your human which role they are: A, B or C.

## Rules

- Build only your role's scope from the brief. If you think something else is needed, ask your human first.
- Never change a shape in `API_CONTRACT.md` on your own. Role A owns that file.
- Look up library APIs in the official docs before you use them. Don't guess signatures or model names.
- Keep secrets only in `.env`. Never log or commit a key, and never send one to the browser.
- The risk score comes from the fixed formula in `backend/signals.py`. The LLM only extracts and explains.
- Commit small and often, with plain messages. `main` must always run.
- If something fails twice, stop and debug properly: reproduce, isolate, form a hypothesis, test.
- Quality bar: a judge forwards a real scam message on their phone and gets a correct verdict, with evidence, in their own language, in under 5 seconds. Build to that standard.
