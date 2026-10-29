# Handoff: Fri 30 Oct, about 02:00 IST (end of the overnight session)

## What's live
- **Site:** https://34-45-129-243.sslip.io runs branch `feat/pricing` (latest deploy: 3cd8c14).
  - It was deployed from the branch because merging my own PR into `main` was blocked as "merge without review".
  - `main` is behind until PR #11 merges.
- **Health:** `/api/health` returns ok; the LLM and the database are up.
- **Security headers are live:** CSP, X-Frame-Options, Permissions-Policy and HSTS.
- **Tests:** 523 pass.
- **Browser check at 360 px in all 8 languages:**
  - headings, overflow, the ring line and back navigation;
  - focus on a report error;
  - share cards (ta, kn, hi and no-signals) and the stats page (mr, hinglish);
  - the quiz;
  - Listen (hi, ta, and a 503), plus the share-page audio.

## Needs a person this morning, in this order
1. **Merge PR #11** (`feat/pricing` into `main`): https://github.com/samarthputhraya/check-before-you-pay/pull/11
   - It includes Risheeth's #9 (Telegram) and #10 (Listen), plus `codex/round2-correctness`. Those close as merged.
   - After merging, `bash deploy/gce/deploy.sh origin/main` deploys the same code that's live now.
2. **Telegram token:** `TELEGRAM_BOT_TOKEN` in `.env.railway` is 35 characters with no colon. That's only the part after the colon.
   - Paste the full token from BotFather (`<digits>:<secret>`).
   - Then follow docs/TELEGRAM.md: copy `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` and `TRUST_PROXY=caddy` into `/opt/cbyp/app.env` on the VM.
   - Restart the app, then run `docker exec app python -m backend.telegram_setup`.
   - Until then, `POST /api/telegram/webhook` returns 503 (not configured), which is correct.
3. **Dodo:** the key in `.env.railway` returns 401 in both test and live mode.
   - Rishabh needs to create a fresh **test-mode** API key and webhook secret (docs/DODO.md).
   - Until then, `/pricing` shows the plans as unavailable, by design.
4. **Reset `/stats` right before launch** (docs/LAUNCH.md, step 1). Tonight's QA, the eval smoke checks and the demo recording added checks.
5. **Demo video:** see "Demo video" below.

## What changed tonight
- **Web QA sweep:**
  - **Share card:**
    - wraps by measured width in every script and uses the check's language;
    - no duplicate disclaimer;
    - a share counts only once the share sheet or WhatsApp opens.
  - **Navigation and structure:**
    - the phone's back button returns from a verdict to the form;
    - one h1 per page, with h2 sections.
  - **Verdict notes and wording:**
    - a note for personal UPI IDs (when S1 didn't fire);
    - a note when the points add up to more than 100;
    - the ring line has no "and 0 reports" and uses correct singular forms in all 8 languages;
    - the privacy line is honest.
  - **Accessibility:**
    - a failed report send moves focus to the error;
    - tap targets are 44 px;
    - the busy button is readable (4.7:1 contrast).
  - **Quiz:** the Hindi "Genuine" button says असली, and the caption wraps.
  - **Stats:** available in Marathi and Hinglish; "rings" now reads "linked groups of high-risk checks".
- **Listen:**
  - The verdict page has a button that plays the verdict in its language.
    - Backend by Risheeth: `GET /api/check/{id}/audio`, MP3 cached per check.
    - It has loading, stop and retry states and sends a `listen_played` event.
  - The share page has a script-free `<audio preload="none">`, so the person a verdict is forwarded to can listen.
  - A masked UPI ID is spoken as "this UPI ID" (it used to be read as "T A dot Y B L").
  - A Tamil MP3 was transcribed back to check it: it is Tamil and matches the text.
  - **The first tap takes 7–8 s** while the MP3 is made. Replays are instant.
  - **Found only on the VM:** every Listen request returned 503 there.
    - The cause was a 2 s limit on ffmpeg. A cold start on the e2-micro took 5.2 s; warm runs take 0.2–1.2 s.
    - The limit is now 5 s, and ffmpeg uses lame's fastest setting.
    - It worked on the laptop, so check anything that runs a subprocess on the VM itself.
- **Backend fixes:**
  - **A Hindi check came back with an explanation in SMS-style Latin letters.** Explanations in script languages must now be mostly in that script; otherwise the fixed text is shown.
  - **A refund "processing fee" was sometimes classed as an investment withdrawal fee**, which made S1 call it an "investment payment handle". The prompt now separates the two.
  - **"पेमेंट" and "लगाओ" count as asking for money.**
  - **Unregistered domains** (Risheeth's RDAP 404 evidence, 0 points) read as the domain itself, with the registry as the Source link. No "RDAP 404" jargon.
- **Ops:** hourly backups keep only the newest 6 copies once the disk passes 80%. Today the disk is at 25% of 30 GB.

## Numbers (re-measured tonight on the deployed code, fresh model calls)
- **Held-out set (128 messages, 8 languages):**
  - 61/64 scams flagged (95%, CI 87–98%), 22 of them at high risk;
  - 0/64 ordinary messages flagged;
  - check time p50 2.8 s, p95 4.3 s.
- **The run before this one:** 62/64. Between runs, 91% of scams keep the same band.
- README, docs/EVAL.md, docs/pitch.md and docs/AI_GRANTS.md now quote 61/64 instead of the old 60/64.
- **Changes after the eval run:**
  - **Wording:** S4 now reads "linked to earlier high-risk checks", and S4/S5 evidence is in plain words.
  - **Explanation guard:** an explanation that calls earlier checks "complaints" is replaced by the fixed text, unless someone actually pressed Report. The model had written "पुरानी शिकायतों से जुड़ा है" ("linked to old complaints").
  - **No effect on the numbers above:** the eval runs every message on a fresh database, so S4 and S5 never fire there.

## Demo video
- **File:** [`docs/demo.mp4`](docs/demo.mp4): 88 s, phone-sized, narrated in English.
- **What it shows:**
  - Sunita's Hindi check, then the evidence;
  - Listen, with the verdict's real Hindi audio;
  - the second message linking to the first by its UPI ID;
  - the share page, the quiz, and a closing slide with the held-out numbers.
- **How it was recorded:**
  - On a fresh local database, running the same commit that's live (4422bfb), with the real Gemini key.
  - The live database already holds tonight's test checks. Those would link Sunita's *first* message to earlier ones and spoil the story.
- **To re-record on the live site** after the stats reset (LAUNCH.md, step 1): `python tools/demo_video.py https://34-45-129-243.sslip.io out_dir`.

## Known limits
- The model's reading of a message varies a little between runs, even at temperature 0. Same message, different run: the band can move between caution and high risk.
- The quiz exists in 4 languages (en, hi, hinglish, mr). The footer's quiz link in ta/te/kn/bn opens it in English.
- An invite-only VIP group pitch that hasn't asked for money yet scores 15. That's an honest limit, documented in EVAL.md.
