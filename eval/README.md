# Eval set and runner

What's in this folder, and how to measure the check again after a change. The write-up of the numbers is in
[`docs/EVAL.md`](../docs/EVAL.md).

| File | What it is |
|---|---|
| `messages.jsonl` | 156 messages (78 scam, 78 ordinary) in 8 languages. We wrote them ourselves, before reading the scoring code, and committed them before the first run. All identifiers are made up |
| `run_eval.py` | The runner. It sends every message through the real check pipeline with the real Gemini key |
| `results.json` | Run 1: each message's band, score, signals, `unchecked`, latency, what the model extracted, and why S1 did or didn't fire |
| `results_run2.json` | Run 2, the same 156 messages again, used to measure how stable the verdicts are from run to run |
| `*.summary.json` | The totals that `docs/EVAL.md` quotes, recomputed from the matching results file |

## Each line of `messages.jsonl`

`{"id", "label": "scam"|"ordinary", "lang", "category", "ident", "text", "source"}`

- `ident` says what identifier the message carries: `upi`, `link`, `phone`, `none`, `fake_valid` (a scam that imitates
  a SEBI `@valid` handle) or `valid_upi` (a real broker's `@valid` handle). It lets us split the results by identifier.
- `source` says which public pattern a scam paraphrases (the SEBI warning of 22 Oct 2026, I4C advisories, the RBI
  Alert List, news reports), or "written by us". We wrote these from what those warnings describe. None is a copy of a
  real message.

If you add messages, write them before you look at what the code would do with them, and commit them on their own
first. Otherwise the set ends up measuring the regex instead of the problem.

## Rerun it

Use the Python environment that has the backend's requirements installed. On Windows, set `PYTHONIOENCODING=utf-8`
first so Indian scripts print.

```bash
python eval/run_eval.py --limit 5                    # smoke run: 5 messages, about 15 model calls
python eval/run_eval.py                              # full run: 156 messages, about 480 model calls, about 4 minutes
python eval/run_eval.py --report                     # no model calls: reprint the totals and the S1 what-if table
python eval/run_eval.py --out eval/results_run2.json --compare eval/results.json   # second run plus stability
python eval/run_eval.py --only en_s05,hi_s08 --merge # rerun a few messages and replace their rows
```

**The key.** The runner reads only `GEMINI_API_KEY`, from `.env.railway` in the repo root, or from the main checkout
when it runs inside a git worktree. Use `--env-file` to point it somewhere else. It never prints the key, only
`key: set`. It loads nothing else from that file, so no admin, payment or webhook keys.

**What a run does**

- **A fresh database for every message.** Each message gets its own temporary SQLite file, so every message is scored
  as if we had never seen it: no cache hits, and no ring links (S4) or script matches (S5) to other eval messages. This
  means S4 and S5 can't score at all here. The ring-link feature needs its own test.
- **A random `IDENTIFIER_SALT`** for each run, and a high `IP_CHECKS_PER_HOUR`.
- **The same path as production, minus the rate limiter.** It calls `validate_check_input` and then
  `backend.pipeline.run_check`, which is what `POST /api/check` does after rate limiting. The phishing feed (S7) is off,
  as it is in production today, and so are the OpenAI fallback and the viaSocket webhook.
- **At most 3 checks at a time.** A 429 from Gemini pauses every worker. A message whose claims step failed is retried
  up to 3 times, each time with a fresh database, and the results keep the first attempt's `unchecked` as well.
- **Every model call is counted.** The `meta` block records the calls by model, plus timeouts and HTTP errors.

**The S1 what-if.** `--report` re-adds the saved signal points with S1 at 35, 40, 45 and 50, then applies the band
cut-offs. It reads the current S1 weight and cut-offs from `backend/weights.py` and `backend/signals.py`, so it stays
right if those change. No model calls are made.

## Limits

- We wrote the set ourselves, and real forwarded messages will look different. Treat these numbers as a floor for how
  well the checks understand language, not as production accuracy.
- Most of the made-up domains aren't registered, so their RDAP lookup finds no record. They show up as
  `unchecked: domain_age`, and S3 (a new domain) never scores. RDAP calls go over the network.
- Latency is measured on a laptop, with 3 checks running at once. It isn't production latency.
