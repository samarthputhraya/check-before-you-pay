# Repository history scan — 30 October 2026

Samarth: no real credential was identified by this scan. The repository is public
(it was made public after the first scan; the rescan at the end of this file covers
it). MIT is added as requested; existing vendor license notices remain in `web/vendor/`.

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

## Follow-up scan, 30 October

After fetching main `f5b4267` and Samarth's deployed `ops/launch` branch,
the local integration at `df2c3ef` passed the same scan over **178 reachable
commits**. No `.env` or `.env.railway` path was committed. The only candidates
remain the two exact public test vectors described above. This snapshot includes
the pending Role B branches and PR #17; rerun after later commits before making
the repository public. No repository visibility change was made.

## Rescan on the public repository, Fri 30 Oct, 20:05 IST

The repository is public. After `git fetch origin`, the integration of main `95fafa9` with PRs #9, #10, #13, #14 and
#16 passed the same scan over **184 reachable commits** across all fetched refs (exit 0). No `.env` or `.env.railway`
path was ever committed. The only candidates are still the two exact public test vectors above. Rerun after any later
merge.
