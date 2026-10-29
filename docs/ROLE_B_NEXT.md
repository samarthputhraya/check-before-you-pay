# Role B: next tasks (Thu 29 Oct, afternoon)

**For Risheeth and his coding assistant.** Read `docs/BUILD_BRIEF.md`, `API_CONTRACT.md` and `docs/REVIEW_FIXES.md` first. The same rules apply as before:
- don't change the API contract;
- change scoring weights only when the team agrees;
- add tests where logic changes;
- never commit or print a key;
- make small commits on a branch and open a PR into `main`.

## Where we are
- **The real check is built.** Your PR #2 has 306 tests passing when merged with `main`, and it renders correctly in the browser. Samarth merges it into `main`.
- **The live site is on a Google Cloud VM:** https://34-45-129-243.sslip.io (HTTPS, with SQLite on a persistent disk).
  - It doesn't redeploy on push. Samarth (or Claude) runs `bash deploy/gce/deploy.sh` after a merge.
- **The deadlines:**
  - core freeze and launch are Friday morning;
  - the final submission is due Sat 31 Oct at 9:59 AM.
- **How judging works:** every round asks whether it's live, whether it works, and whether anyone is using it. The Finale judge (Davin Dong) will ask for numbers, so measured numbers count for more than features.

## Tasks, in priority order

### B1. A labelled evaluation set and the numbers we pitch (by 5 PM)
- **Build `eval/messages.jsonl`:**
  - at least 60 scam and at least 60 ordinary payment messages;
  - in English, Hindi and Hinglish, plus at least two other supported languages;
  - each one labelled `scam` or `ordinary`, with its language and source.
- **Where the scam messages come from:** paraphrase public examples, such as SEBI and I4C advisories and news reports of tip-group scams. Mark every one "(sample)". Include no real names or numbers.
- **What the ordinary messages look like:** shop bills ("X Trading Co."), rent and brokerage, school and hospital fees, family transfers, refunds, chit funds, gold schemes. `backend/tests/test_s1_wording.py` has many to start from.
- **Write `eval/run_eval.py`.** In one command, it sends every message through the real pipeline with the real key, using a fresh temporary database. It reports:
  - scams caught as `high_risk`, as `caution`, and missed;
  - ordinary messages that got `caution` or `high_risk`;
  - the same broken down per language;
  - p50 and p95 latency.
- **Run the S1 weight both ways.** Run once at the current 35 points and once at 50, by patching `backend/weights.py` inside the script only, and show the two side by side. The team decides the weight from this table.
- **Done when:** `docs/EVAL.md` holds the table, plus three pitch-ready lines such as "caught N of M scam messages; flagged K of L ordinary payments".

### B2. Real messages from housemates (this evening, 6–9 PM)
- **Collect real scam messages from people at the house,** with their consent. Use the format `seed/messages/` already uses. Strip victims' names, numbers and faces before anything is saved.
- **Add them to the evaluation set as a separate "real" slice,** and rerun B1. Real messages are worth more to judges than made-up ones.

### B3. viaSocket workflow, live (partner track: $50K in credits, and the top 3 get 12 months free)
- **Build it in viaSocket itself.** A report on our site triggers the webhook in `docs/VIASOCKET.md`. viaSocket then:
  - alerts a family contact by WhatsApp or email;
  - adds a row to a Google Sheet.
- **Publish a template too:** "Check before you pay", which calls `POST /api/check` as an HTTP step so any viaSocket agent can check a payment first.
- **Coupon:** `HHGOA26-VIASOCKET`.
- **Done when:**
  - a report on the live site produces the sheet row and the alert;
  - you've recorded a 20-second screen clip of it;
  - the README has a viaSocket section.

### B4. Voice notes: fix them or cut them by 6 PM
- **The problem:** your own benchmark had only 3 of 5 OGG notes finishing within the deadline.
- **What to try:**
  - shrink the audio before sending it (16 kHz mono, at most 60 seconds);
  - use the fastest model that still transcribes correctly;
  - measure 10 real WhatsApp voice notes, in Hindi and English.
- **The decision:**
  - if at least 9 of 10 come back in under 10 seconds, keep voice;
  - if not, tell Rishabh to hide the voice button, and say so in the README. Voice is item 7 on the brief's cut list.

### B5. Dodo Payments backend (only if Rishabh agrees to hand it over; partner track, $15K in credits)
- **Build the backend for the `/pricing` page:**
  - a Family plan at ₹49 a month and an API plan;
  - a checkout endpoint in Dodo test mode;
  - a webhook that verifies Dodo's signature before it records anything in SQLite.
- **Never fake a payment.** Rishabh owns the page itself.
- **Done when:** a test-mode checkout completes from start to finish on the live site.

### B7. The real "Spot the scam" quiz backend (by 6 PM; Rishabh's quiz screen is in PR #6)
- **The problem:** `/api/quiz` and `/api/quiz/answer` still return the 2-item sample. It's the same Hindi messages in every language, and the answers are ignored, so everyone scores 2/2. Your event checks also drop `quiz_done` and `quiz_shared`, because no quiz result is ever stored.
- **What to build:**
  - **Content:** 10 messages per language, in `seed/quiz/{en,hi,mr}.json`. Mix about 6 scams and 4 genuine messages, each with its answer and a one-line "why" in that language, and mark each one "(sample)".
  - **Scoring:** the server scores the answers it receives.
  - **Results and events:** store a `quiz_results` row, record `quiz_done` on the server, and issue the share proof so `quiz_shared` counts. `share.url` stays `/quiz?ref=<anon_id>`.
- **Keep:** the API shapes exactly as in `API_CONTRACT.md`.
- **Done when:** a wrong answer lowers the score, all three languages show their own messages, and `/api/stats` counts quiz shares.

### B6. Small fixes (any time)
- **Show plain words for skipped checks.** The verdict lists them by internal name ("claims, domain_age, script_similarity"). Map each name to plain words in `web/components/i18n.js` (EN and HI), then use the map in `Verdict.js`. Agree the copy with Rishabh first.
- **Write the judges' README backend section,** including a "What's real and what's mocked" table.
- **Before the repo goes public,** scan the git history for anything that looks like a key (`git log -p | grep` for key patterns).

## What Samarth and Claude handle
- The live VM: deploys, backups and the fixed address.
- The TigerGraph Final Round.
- The pitch.

Message Samarth when you hit a blocker. Decide anything inside your own scope yourself.
