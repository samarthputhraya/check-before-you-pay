# How well does the check work? (eval, 29 Oct 2026)

## The numbers to quote: a held-out set nobody tuned on

After the first eval (below), we changed the scoring (scoring v2). Then we measured on a **second set of 128 messages**, written by someone who never saw the code or the first set. It was committed before any run (`eval/heldout.jsonl`, commit 7e97847). Both versions ran on it with the real Gemini key, and each message was scored as if seen for the first time.

| | Scoring before (the build live until 29 Oct night) | Scoring v2 |
|---|---|---|
| Scam messages flagged (caution or high risk) | 25 / 64 = 39% (95% CI 28–51%) | **60 / 64 = 94% (95% CI 85–98%)** |
| Scam messages at high risk | 3 / 64 | **18 / 64** |
| Ordinary payments flagged | 0 / 64 | **0 / 64 (95% CI 0–6%)** |
| Scams with a personal UPI ID | 20 / 23 | 23 / 23 |
| Scams with only a link | 5 / 13 | 12 / 13 |
| Scams with only a phone number | 0 / 10 | 10 / 10 |
| Scams with no identifier at all | 0 / 14 | 11 / 14 |
| Scams with a fake `@valid` handle | 0 / 4 | 4 / 4 |
| Check time, p50 / p95 (text, laptop, 3 at a time) | 3.2 s / 5.4 s | 3.3 s / 4.9 s |

- **The set:** 64 scam and 64 ordinary messages, in English, Hindi, Hinglish, Marathi, Tamil, Telugu, Kannada and Bengali.
- **The ordinary messages are mostly hard cases:**
  - 33 ask for payment to a personal UPI ID: shop bills, rent, school fees, chit funds, gold schemes and family requests;
  - 4 are real brokers asking for funds to a genuine `@validhdfc` or `@validicici` handle.
- **After the final code review** two rules tightened: pay-to-unlock tasks and recovery fees no longer count as *investment* for S1 (they're scams, but SEBI's @valid rule is about securities), and the payment word is looked for outside the UPI ID. Re-scoring the same model outputs offline (no new model calls) keeps 60 / 64 flagged and 0 / 64 ordinary; high risk goes from 22 to 18, the four task and recovery scams now read caution. The table shows the final numbers.

**The 4 v2 still misses** are invite-only VIP group pitches with no money request yet, scoring 5–15. That's an honest limit: the check flags a request to pay, and a first message that only invites you in gives it little to go on.

**What changed in v2** (each change was measured on the first set, and the first set is never quoted as the result):
- **New claim types:** sure-shot insider tips, pay-to-unlock tasks and recovery fees.
- **A prompt that defines every claim.** A specific promised return ("10% weekly") counts as a guarantee.
- **A stricter SEBI handle:** `@valid` must be followed by a bank's name, so `@validupi` or a bare `@valid` doesn't pass.
- **More payment verbs:** recharge, top up, "daal do" and the Tamil form.
- **Weights v2:**
  - S1 goes from 35 to 50.
  - Five scam-only claims go from 10 to 30 each: guaranteed returns, a fee to withdraw, pay-to-unlock tasks, sure-shot tips and recovery fees.
  - The claims cap goes from 30 to 40, so claims alone can only reach caution. A high-risk verdict always needs a checked fact as well.

**Three lines for the pitch:**
- "On 128 messages we'd never tuned on, in eight languages, it flagged 60 of 64 scams and none of 64 ordinary payments."
- "It flags a scam even with no UPI ID in it: 10 of 10 phone-only scams, 11 of 14 with no identifier at all."
- "Before this week's changes it caught 39%; now it catches 94%, with zero false alarms on bills, rent and family transfers."

**Caveats:**
- We wrote both sets ourselves, though blind, and the held-out author never saw the code.
- Real messages from users come next (see `docs/COLLECT.md`).
- Ring links (S4 and S5) are switched off in this measurement. On the live site they only add points.

---

# The first eval (the development set: what we tuned on)

**Short answer.** We ran 156 messages in 8 languages through the real pipeline, with the live Gemini key, twice.

- **It flagged 40 of the 78 scam messages.** That's 51% (95% CI 40–62%).
- **It flagged none of the 78 ordinary payments.** That's 0% (95% CI 0–4.7%).
- **When a scam asks for money to a personal UPI ID, it flagged 34 of 37** (92%).
- **When a scam has no UPI ID and no look-alike link, it flagged 0 of 24.** That gap, not the S1 weight, is the main thing to fix.

The data, the runner and how to rerun it are in [`eval/`](../eval/README.md). Run 1 (`eval/results.json`) is the main
measurement. Run 2 (`eval/results_run2.json`) is the same 156 messages again, run to check stability.

### Method

- **We wrote the messages blind, and committed them first.** 78 scam and 78 ordinary messages were committed (a9f90ba)
  before anyone opened `signals.py`, `extraction.py`, `weights.py` or the S1 tests.
  - **Languages:** en, hi and Hinglish (28 each), and mr, ta, te and kn (14 each), and bn (16). Each language is about
    half scam and half ordinary.
  - **Scams:** 9 categories. 37 carry a personal UPI ID, 12 only a link, 11 only a phone number, 13 no identifier at
    all, and 5 a fake `@valid…` handle.
  - **Ordinary messages:** mostly hard negatives. 43 ask for payment to a personal UPI ID: shop and trader bills
    ("Shree Ganesh Trading Co."), rent and brokerage, school and hospital fees ("investigation charges"), chit funds,
    jewellers' gold schemes, insurance, SIP reminders, salary, refunds, return tickets, family transfers, "please share
    this" and donations. 4 more are real brokers asking for payment to their `@valid` handle.
- **Each message runs as if it were the first ever.** It goes through `validate_check_input` and then
  `pipeline.run_check`, the same code `/api/check` calls, with its own fresh SQLite file and a random salt.
  - **So S4 and S5 can't fire here.** There are no earlier checks to link to, and there is no ring to inflate scores.
  - **S7 is off,** as it is in production.
- **Models:** `gemini-flash-lite-latest` for extraction and explanation, `gemini-embedding-2` for embeddings. They were
  picked by the app's own model discovery.
- **Band cut-offs:** taken from the code. S1 is 35, `high_risk` is a score of 60 or more, and `caution` is 30 or more
  (`backend/weights.py:2`, `backend/signals.py:118-120`).
- **What "flagged" means:** a band of `caution` or `high_risk`. Recall is the share of scams flagged. The false-positive
  rate is the share of ordinary messages flagged.

### Results (run 1; run 2 gave the same band for all 156)

### Scam messages (n = 78)

| | high_risk | caution | missed (no_known_signals) | flagged |
|---|---|---|---|---|
| All scams | 1 (1%) | 39 (50%) | 38 (49%) | **40/78 (51%)** |

**By language**

| lang | n | high | caution | missed | flagged |
|---|---|---|---|---|---|
| en | 14 | 0 | 7 | 7 | 7/14 (50%) |
| hi | 14 | 1 | 6 | 7 | 7/14 (50%) |
| hinglish | 14 | 0 | 7 | 7 | 7/14 (50%) |
| mr | 7 | 0 | 4 | 3 | 4/7 (57%) |
| ta | 7 | 0 | 2 | 5 | 2/7 (29%) |
| te | 7 | 0 | 4 | 3 | 4/7 (57%) |
| kn | 7 | 0 | 5 | 2 | 5/7 (71%) |
| bn | 8 | 0 | 4 | 4 | 4/8 (50%) |

Language matters much less than what the message contains. Each language has 7 to 14 scam messages, so a gap of one or
two messages between languages is noise. The exception is Tamil, which loses S1 to a verb form; see error 3 below.

**By category**

| category | n | high | caution | missed | flagged |
|---|---|---|---|---|---|
| fake app / look-alike link | 7 | 0 | 7 | 0 | 7/7 (100%) |
| IPO allotment / institutional account | 8 | 1 | 6 | 1 | 7/8 (88%) |
| withdrawal fee or tax | 8 | 0 | 6 | 2 | 6/8 (75%) |
| VIP / invite-only tip group | 11 | 0 | 7 | 4 | 7/11 (64%) |
| crypto / USDT doubling | 10 | 0 | 5 | 5 | 5/10 (50%) |
| task / part-time job | 11 | 0 | 3 | 8 | 3/11 (27%) |
| fake "SEBI registered" | 8 | 0 | 2 | 6 | 2/8 (25%) |
| pump and dump ("up 40% tomorrow") | 8 | 0 | 2 | 6 | 2/8 (25%) |
| forex / binary options | 7 | 0 | 1 | 6 | 1/7 (14%) |

**By what the message contains**

| identifier | n | flagged | why |
|---|---|---|---|
| personal UPI ID | 37 | **34 (92%)** | S1 fired on 32 of them |
| look-alike or other link | 12 | 5 (42%) | the 5 were broker look-alikes (S2) |
| fake `@valid…` handle | 5 | 1 (20%) | S1 treats the fake handle as a real SEBI one |
| phone number only | 11 | **0** | only S6 can score, and it's capped at 30 |
| no identifier | 13 | **0** | the same |

### Ordinary messages (n = 78)

- **Flagged `caution`:** 0 of 78. **Flagged `high_risk`:** 0 of 78. This held in every language and category.
- **S1 fired on none of the 43** ordinary messages that ask for payment to a personal UPI ID (95% CI 0–8.2%), including
  the trading-company bill, the property brokerage and the "investigation charges".
- **The highest score any ordinary message got was 5.** That was run 1's rent message, where the model read "by Saturday
  so I can hand over the keys" as urgency. In run 2 it scored 0.

### Combined

| | run 1 | run 2 |
|---|---|---|
| Recall (scams flagged) | 40/78 = 51% (CI 40–62%) | 40/78 = 51% |
| False-positive rate (ordinary flagged) | 0/78 = 0% (CI 0–4.7%) | 0/78 = 0% |
| Same band as run 1 | | 156/156 |
| Same score as run 1 | | 148/156 |

### Stability

The score is a fixed formula, but some of its inputs are claims that the model extracts. 8 of 156 scores changed
between runs, every one because a claim was found in one run and not the other. All 156 bands stayed the same at
S1 = 35, but a message sitting on a band edge can flip.

- **en_s02 scored 60, 55 and 45** across the smoke run, run 1 and run 2. "60-80% profit expected" was tagged as
  `guaranteed_returns` in some runs and not in others.
- **In production the 24-hour cache returns the same verdict** for the same text. So "same input, same score" is true
  within a day, and only roughly true across days.

### Latency (text input, measured inside `run_check`, 3 checks running at once, on a laptop)

| | p50 | p95 | checks over 8 s |
|---|---|---|---|
| run 1 | 2.96 s | 5.88 s | 5 |
| run 2 | 3.03 s | 9.08 s | 10 |

**The slow tail is timeouts.** When a Gemini call (embedding or explanation) hits its 8 s limit, the check stops at the
9.5 s deadline and still returns a verdict. Run 1's 5 slow checks all came in its first minute, which looks like a cold
start. p95 is the number least likely to hold in production, in either direction.

### Unchecked (how often each check was skipped)

| check | run 1 (final) | run 1 (first try) | run 2 (final) |
|---|---|---|---|
| `domain_age` | 15 | 15 | 15 |
| `script_similarity` (embedding timed out) | 4 | 7 | 6 |
| `claims` (Gemini extraction failed) | 0 | 3 | 0 |
| `links` (out of time) | 0 | 3 | 0 |

- **Gemini failed rarely,** and never with a 429 or an HTTP error.
  - **Run 1:** 3 extraction failures, all in the first minute and all timeouts. All 3 succeeded on a retry with a
    fresh database.
  - **Run 2:** 1 extraction failure.
  - **Timeouts in total:** 24 in run 1 (16 generate, 8 embed) and 17 in run 2.
- **`domain_age` failed on 15 of the 17 messages with a domain.**
  - 13 of the domains are ones we made up and that aren't registered, so their RDAP lookup finds no record.
  - The `t.me` lookup failed too.
  - So did one real domain, `camsonline.com`, in both runs. We didn't find out why.
  - Because of this, **S3 never fired.** Real scam domains are registered, and often new. For an upper bound: if every
    scam message whose lookup failed had scored +25 for a new domain, `high_risk` would go from 1 scam to 8, and
    5 more scams would be flagged (45 of 78).

### Which signals carried the score (run 1)

| signal | scam messages | ordinary messages |
|---|---|---|
| S1 non-@valid UPI for investing | 32 | 0 |
| S2 look-alike domain | 7 | 0 |
| S3 new domain | 0 (see above) | 0 |
| S4 / S5 ring links | 0 (isolated by design) | 0 |
| S6 claims with verified quotes | 60 | 1 (5 points) |
| S7 phishing feed | off | off |

39 of the 40 flagged scams have S1 or S2. **S6 flagged only one scam on its own:** te_s06, which scored exactly 30 from
three claim types. S6 is capped at 30, so reaching `caution` without S1 or S2 takes three different claim types at full
value, and the model rarely finds that many.

### The S1 weight: 35, 40, 45 or 50

For each weight, we re-added the saved signal points with that S1 value; there were no new model calls. Run 2's
`high_risk` count is in brackets.

| S1 | scam high_risk | scam caution | scam missed | recall | ordinary caution | ordinary high_risk |
|---|---|---|---|---|---|---|
| **35 (now)** | 1 (1) | 39 | 38 | 51% | 0 | 0 |
| 40 | 5 (4) | 35 | 38 | 51% | 0 | 0 |
| 45 | 19 (18) | 21 | 38 | 51% | 0 | 0 |
| 50 | 30 (31) | 10 | 38 | 51% | 0 | 0 |

**Recommendation: S1 = 50.**

- **What it changes.** The weight doesn't change recall or false positives here, since S1 alone is already at least 30.
  It only decides whether a flagged scam says `caution` or `high_risk`.
  - **At 35,** the textbook case gets only `caution`: an investment pitch, a personal UPI ID and one concrete claim
    ("guaranteed", "VIP/institutional account"). 1 of 78 scams reaches `high_risk`.
  - **At 50,** S1 plus any one 10-point claim reaches `high_risk`: 30 of 78 scams (31 in run 2).
  - **At 45,** a second claim type is still needed. Whether the model finds it varies from run to run, so 45 leaves more
    verdicts sitting on the 60 line.
- **S1 alone still stays `caution` at 50.** A personal UPI ID with nothing else never says "Don't pay".
- **The cost we can't measure here.** S1 fired on 0 of 43 ordinary UPI payment requests, so this set can't show what 50
  costs. What it would cost is this: any real bill that wrongly trips S1 (the 95% upper bound is 8%) and also gets one
  10-point claim would read `high_risk` instead of `caution`. Chit funds and gold schemes that promise a bonus are the
  likeliest cases.
- **Before changing it:** update the tests (brief section 6), and check again once real forwarded messages come in.

### The 10 worst errors

None of the errors were false positives, so all 10 are missed scams. They're listed by how clear the scam is.

| # | id | what it is | score | signals | why it was missed |
|---|---|---|---|---|---|
| 1 | hg_s11 | task scam: "₹10,000 recharge karo taskhub.pay@okicici pe … bonus ke saath wapas" | 0 | none | It has a personal UPI ID and asks for a deposit, but no investment word, so S1's investment check fails (`signals.py:132-134`). The model found no claim, and there's no claim type for task deposits |
| 2 | ta_s04 | the same task pattern in Tamil, with a UPI ID | 0 | none | The same S1 gap. The model typed both claims as `other`, which scores 0 (`signals.py:151-152`) |
| 3 | ta_s01 | VIP tip group, ₹5,999 to `chennaitrades.vip@ybl` | 10 | S6+10 | S1 was lost to the payment-verb regex (`signals.py:53`): it lists அனுப்பு, but the message says அனுப்பவும். The same pitch scored 45–55 in the other 7 languages |
| 4 | hi_s10 | "SEBI rule: pay only to @valid": `angelvip.brk@validaxis` | 25 | S6+25 | Any handle starting with `valid` counts as a SEBI handle (`signals.py:127`). It had 3 claims and 25 points, 5 short of `caution` |
| 5 | en_s10 | elite group, `elitewealth.brk@validyesbank` | 15 | S6+15 | The same `@valid` imitation |
| 6 | hg_s14 | "SEBI registration no. INH000099999", plus `sebi-approved-tips.in` | 0 | none | When a registration number is present, the SEBI claim is dropped (`signals.py:154-155`), even though a fake number is easy to write. SEBI isn't in `seed/brokers.json`, so the domain isn't a look-alike. The domain lookup found no record |
| 7 | en_s14 | forex manager: "8-12% weekly returns … capital is 100% safe", phone only | 0 / 10 | none / S6+10 | In run 1 the model typed the return promise as `other`, worth 0. With only a phone number, 30 is the most it could ever score |
| 8 | hi_s08 | "शेयर कल 40% ऊपर जाएगा, ऑपरेटर से पक्की खबर … ग्रुप से बाहर न भेजें" | 0 | none | The model found no claim. There's no claim type for an insider tip or for secrecy, and nothing to pay, so S1 can't apply. 6 of 8 pump-and-dump messages were missed |
| 9 | en_s05 | part-time job, like videos for ₹50 each, WhatsApp number | 0 | none | The model found no claim, and with only a phone number nothing else can score |
| 10 | en_s09 | forex robot, "92% win rate", `fx-primeoption.com` | 10 / 0 | S6+10 / none | The domain isn't a broker look-alike, and it isn't registered, so S2 and S3 had nothing. The claim was found in one run only |

**Near misses that were still flagged.** en_s11 and te_s02 (fake broker apps) lost S1 because "recharge your trading
wallet via UPI to …" and రీఛార్జ్ చేయండి have no payment verb the regex knows. S2 kept them in `caution`.

### The patterns behind the misses, and where each could be fixed

These are described, not changed. Scoring changes need the team to agree.

1. **Scams without a UPI ID can't reach `caution`.**
   - **The size of it:** 31 of the 38 misses have no personal UPI ID. All 24 phone-only and no-identifier scams were
     missed.
   - **Why:** without S1 or S2, the only signal that can score is S6. It's capped at 30 (`weights.py:9`), the
     `caution` cut-off is 30 (`signals.py:120`), and each claim type counts only once (`signals.py:150-162`).
   - **What would fix it:** a signal for "investment pitch plus a contact or link", or a higher S6 cap for pitches that
     combine several claims.
2. **The model extracts too few claims, and the scored list leaves out common pitches.**
   - **The size of it:** 15 scams had no verified claim at all. 12 raw claims were typed `other` or
     `impersonates_brand`, which score 0.
   - **Where:** the extraction prompt tells the model not to infer guaranteed returns (`llm.py:29`), and the claim types
     are listed in `extraction.py:12-14` and `weights.py:12-16`.
   - **Claim types that are missing:** task deposits or commissions, insider or operator tips ("up 40% tomorrow"),
     doubling your money, and secrecy ("don't share outside the group").
3. **Fake `@valid` handles pass as SEBI handles.**
   - **The size of it:** 4 of the 5 imitations lost S1 and were missed.
   - **Why:** any handle that starts with `valid` passes (`signals.py:127`). Also, `extraction.py:40` reads
     `@valid-upi` as `@valid`.
   - **What would fix it:** an allow-list of the real `@valid<bank>` suffixes from SEBI's circular.
4. **The payment-verb list has gaps** (`signals.py:53`).
   - **Missing:** "recharge", "top up", "via UPI to", the Tamil imperative அனுப்பவும், and the Hinglish "deni hai".
   - **The cost:** S1 on 3 scams, one of which (ta_s01) was missed entirely.
5. **Task scams fail S1's investment check** (`signals.py:132-134`, with the word list at `signals.py:21-50`).
   - **The size of it:** 3 of 11 task scams were flagged. The two with a UPI ID scored 0.
   - **Why:** the S1 rule is written for investment scams, and these ask for a deposit to unlock tasks.
   - **What would fix it:** a separate rule, or a claim type for "pay to unlock earnings", rather than widening S1,
     which is precise today.

**Smaller:** a SEBI claim that comes with any registration number scores nothing (`signals.py:154-155`), and SEBI
isn't in the look-alike list (`seed/brokers.json`).

### Three lines for the pitch

These are exact, and true for both runs.

1. "Before reading our own scoring code, we wrote 156 messages in 8 languages. It flagged 40 of the 78 scams and none of
   the 78 ordinary messages, 43 of which ask for payment to a personal UPI ID: shop bills, rent, school and hospital
   fees, chit funds."
2. "When a scam asks you to pay a personal UPI ID, it flags 34 of 37. When there's no UPI ID or look-alike link, it
   catches almost nothing yet, 0 of 24, and that's what we're fixing next."
3. "We ran all 156 twice through the live Gemini pipeline, and every verdict came out in the same band. The median check
   took 3 seconds."

### Caveats

- **We wrote the data ourselves.** We wrote it before reading the scoring code and committed it before the first run,
  but the same team built both the product and the test. The scam messages paraphrase public patterns (the SEBI warning
  of 22 Oct 2026, I4C and RBI advisories, news reports). They aren't real forwards, and the `source` tags name the
  pattern, not a document we copied.
- **Real messages come next.** Every number here should be rerun on consented user reports, and we need them before
  quoting precision on real traffic. The 0% false-positive rate covers 78 messages; its 95% upper bound is 4.7%.
- **Domain-age lookups hit the network,** and most of our made-up domains aren't registered, so S3 (a new domain)
  scored nothing. Real look-alike domains would likely score higher.
- **The ring links (S4 and S5) were switched off on purpose.** Each message was scored as if first seen. This eval says
  nothing about the ring-link feature.
- **The latency is local, not production.** It was measured on a laptop with 3 checks running at once and no rate
  limiter. Railway's numbers will differ.
- **Small groups.** Each language other than en, hi and Hinglish has 7 or 8 scam messages, so the per-language rates
  move by 13–14 points per message.
- **Model calls.** 971 in total: 15 in the smoke run, 484 in run 1 and 472 in run 2. 41 timeouts, no 429s and no
  HTTP errors.
