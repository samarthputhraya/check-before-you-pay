# Seed data

Run `python -m seed.load` after configuring `IDENTIFIER_SALT` in `.env` (at least
32 random characters). The command loads four checks labelled `(test, made up)`
and `(sample)`, including a shared UPI link. It is repeatable, uses no provider calls, and excludes
sample checks from usage totals and public ring totals. Open `/c/chk_sample02`
to inspect the sample ring. No real housemate messages have been collected yet.

## Message files for tonight's testing

The loader reads every `seed/messages/*.json` file. Each file is an array with
this shape (this example is made up):

```json
[
  {
    "id": "chk_test_example",
    "label": "Investment request (test, made up) (sample)",
    "source": "made_up",
    "consent_to_use": false,
    "text": "(test, made up) (sample) Investment: 300% guaranteed. Pay sample@ybl.",
    "claims": [{"type": "guaranteed_returns", "quote": "300% guaranteed"}]
  }
]
```

For a real example, first obtain permission to use it and remove the victim's
name, number and other identifying details. Set `source` to `consented`,
`consent_to_use` to the boolean `true`, and `anonymized` to the boolean `true`.
Keep `(sample)` in both label and text. Remove `(test, made up)` only when the
message actually comes from a consented source. Do not include the sender's
name, consent conversation, private screenshot or phone contact in the JSON.

Give every message a fresh `chk_...` ID; loaded IDs are skipped on repeat runs.
Use new IDs when replacing the made-up examples. `claims` can be empty; curated
claims must use supported types from the brief and quotes present in the text.
The loader checks labels, consent, anonymization confirmation, unique IDs and
quote support before it writes. It never calls a model or invents claims.

All imported examples stay excluded from real usage totals. The loader does not
infer consent or automatically identify victims' names; review anonymization
before committing a real example.

The broker list is consumed directly by the signal engine; RDAP uses the bundled
IANA bootstrap snapshot. The quiz API reads `seed/quiz/*.json` directly and
validates every file when it loads, so the quiz needs no seeding step.

## Optional phishing feed

S7 accepts a local, decompressed PhishTank verified-online JSON snapshot via
`PHISHTANK_FEED_PATH`. Missing or older-than-24-hour snapshots yield zero points
and `unchecked: ["phishing_feed"]` for URL inputs. No submitted URL is visited.

Follow [PhishTank's developer instructions](https://phishtank.org/developer_info.php):
identify downloads with a descriptive User-Agent and register an application key
for automated downloads. The application does not download feeds automatically;
an operator must supply and refresh the snapshot under the provider's terms.

## Verified references

- The [SEBI circular, section 2.1](https://www.sebi.gov.in/sebi_data/attachdocs/jun-2025/1749641449497.pdf)
  specifies `@valid` plus the bank name, such as `@validhdfc`. S1 tests the prefix
  as specified by the build brief; a matching prefix is never an endorsement.
- [Gemini audio documentation](https://ai.google.dev/gemini-api/docs/audio)
  lists OGG, Opus, MPEG and M4A support. The wrapper maps the contract's
  `audio/mp4` to provider MIME `audio/m4a`.

Role B owns this folder (see `docs/BUILD_BRIEF.md`, section 10):

- `brokers.json`: at least 25 official broker, exchange, mutual fund and crypto exchange domains.
- `quiz/*.json`: the "Spot the scam" items, at least Hindi, English and one more language.
- `messages/*.json`: real scam messages from housemates, collected with consent, with victims' names and numbers removed. Every item is labelled "(sample)".
- `load.py`: one command that loads all of the above into the database.
