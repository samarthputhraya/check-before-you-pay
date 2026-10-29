# Repository history scan — 30 October 2026

Samarth: no real credential was identified by this scan. The repository has not
been made public. MIT is added as requested; existing vendor license notices
remain in `web/vendor/`.

At approximately 03:26 IST, after `git fetch origin --tags`, the checkout was
not shallow and **126 reachable commits** were scanned across all local and
remote refs (including old working branches and local checkpoint refs). Base
main was `db7af7e6e2dc77e2dcb846317fbcbae00165d500`.

Command: `python deploy/scan_history.py`. It runs
`git log --all --full-history -m --no-ext-diff --no-renames -p`, including deleted
lines and merge-parent diffs. It checks Google, OpenAI, webhook, Slack, GitHub,
Telegram and private-key patterns, plus long high-entropy base64 candidates.
Output contains only locations, lengths and SHA-256 fingerprints, never values.

Findings:

- **No `.env` or `.env.railway` at any path** in the scanned history. Both are
  also ignored by Git now.
- Two distinct credential-shaped candidates, both in
  `backend/tests/test_payments.py` from commit `274f532`: the published Standard
  Webhooks signing test vector and its expected signature. They match upstream
  `test_sign_function`. Their fingerprints are `96ad2ccd81462a76` and
  `b186714e50f982f9`; the scanner allowlists only these exact values at this path.
- No other credential-shaped or high-entropy base64 candidates. No rotation or
  history rewrite was indicated by these findings.

Raw prefix occurrences (including repeated diff context and ordinary words):
`AIza` 1, `sk-` 279, `whsec_` 51, `xox` 1, `ghp_` 1. Prefix occurrences alone
are not keys. The longer pattern and entropy checks above produce the two
reviewed candidates.

This is a heuristic scan of fetched Git text history, not proof that no secret
exists. It does not inspect untracked local settings, remote-only deleted refs,
unreachable objects, LFS content, or binary/PDF/image payloads. Unknown formats
and obfuscated secrets can evade patterns. Run it again after new merges and
immediately before changing visibility. A nonzero exit means a candidate needs
review; never paste a candidate value into a PR or chat.

Sources: [Standard Webhooks public tests](https://github.com/standard-webhooks/standard-webhooks/blob/main/libraries/python/tests/test_webhooks.py),
[MIT license text](https://opensource.org/license/mit).
