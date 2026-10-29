# Seed data

Run `python -m seed.load` after configuring `IDENTIFIER_SALT` in `.env` (at least
32 random characters). The command loads two explicitly labelled synthetic checks
and their shared UPI link. It is repeatable, uses no provider calls, and excludes
sample checks from usage totals and public ring totals. Open `/c/chk_sample02`
to inspect the sample ring. No real housemate messages have been collected yet.

The broker list is consumed directly by the signal engine; RDAP uses the bundled
IANA bootstrap snapshot. The quiz remains a sample endpoint owned by role C.

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
