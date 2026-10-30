# Handoff: Fri 30 Oct, 08:30 IST (launch morning)

## What's live
- **Site:** https://34-45-129-243.sslip.io runs branch `ops/launch` (85e0188). PR #11 is merged into `main`.
  - PR #15 (`ops/launch` into `main`) is open, with every change from this morning.
  - Merge it, then `bash deploy/gce/deploy.sh origin/main` to redeploy the same code from `main`.
- **Health:** `/api/health` is ok, with the LLM and the database up.
- **Tests:** 538 pass.
- **Live smoke test after the reset:** passed in Marathi with a `u_test` ID.
  - Check 3.1 s; Listen 200 in 6.7 s.
  - Back button, share page audio, `/stats`, `/pricing` and `/quiz` all fine; no console errors.
  - `/stats` stayed at 0.
- **Stats were reset at 08:13.** The old database is at `/opt/cbyp/data/backups/pre-launch-app.db`. It held only our own testing.
- **The demo is primed:** Sunita's message was run at 08:15 with `u_testdemoprime` (high risk, 100).
- **Telegram is live:** [@CheckBeforeYouPayBot](https://t.me/CheckBeforeYouPayBot).
  - Token and secret are on the VM, and the webhook is registered.
  - A wrong or missing secret gets 401.

## Needs a person, in this order
1. **Dodo: create a test-mode API key (about 2 minutes).**
   - Sign in at https://app.dodopayments.com, switch to Test Mode, then Developer → API Keys.
   - Paste the key into `.env.railway` as `DODO_API_KEY`. The current key gets 401 from Dodo's test API.
   - I couldn't make the account myself: the safety check blocked entering the sign-up code sent to Samarth's Gmail.
   - Then run `python tools/dodo_setup.py .env.railway` and `bash deploy/gce/push_env.sh DODO_`.
   - Then pay once with test card 4242 4242 4242 4242 (docs/DODO.md, step 6). Use a `u_test` ID so the order isn't counted.
2. **Telegram: send the bot a real message.** Send a stock-tip text and a 3–5 MB screenshot. Nobody has seen a reply in a private chat yet.
3. **Merge PR #15.** Risheeth's PRs #10 (speech model choice), #13 (MIT license and history audit) and #14 (consent and acceptance handoff) are his to merge. #10 changes Listen's model, so test it after deploying.
4. **Phase 1 submission:** copy the text from [docs/SUBMISSION.md](docs/SUBMISSION.md).
   - Fix the team credits first.
   - Upload docs/demo.mp4 to YouTube (unlisted) if the form wants a video link.
5. **viaSocket:** our webhook is ready, but the workflow needs a viaSocket account (docs/VIASOCKET.md, coupon HHGOA26-VIASOCKET). The README now says it isn't set up.
6. **AI Grants:** the form needs Samarth's WhatsApp (docs/AI_GRANTS.md).

## What changed this morning
- **Stats leave out our testing.**
  - Every `/api/stats` figure ignores anon IDs that start with `u_test`. Visitors can't get one: web IDs are hex, Telegram IDs start `u_tg_`.
  - Test with a `u_test` ID: `localStorage.setItem('cbyp_anon_id', 'u_testyourname')`.
- **Dodo setup is one command once there's a key:** `tools/dodo_setup.py` creates both products and the webhook, then writes the settings.
  - It was tested against a mock of Dodo only.
- **`deploy/gce/push_env.sh PREFIX`** copies settings to the VM without printing them, then restarts the app.
- **README honesty:** the partner rows say the Dodo key, the viaSocket workflow and AI Grants credits aren't set up yet.
- **Pitch step 5** no longer quotes "1 earlier check": with the morning run plus step 1, it reads 2.
- **LLM:** a failed Gemini model discovery now logs its exception type. It failed silently once at 08:13, and recovered after 30 s.

## What changed overnight
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
- **Held-out set (128 messages, 8 languages), latest run (`eval/heldout_v5.json`):**
  - 61/64 scams flagged (95%, CI 87–98%), 21 of them at high risk;
  - 0/64 ordinary messages flagged;
  - check time p50 2.3 s, p95 2.8 s.
- **Three runs on tonight's code:** 62, 61 and 61 of 64. Between runs, 91–92% of scams keep the same band.
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
  - On a fresh local database, at commit 4422bfb, with the real Gemini key. The Hindi screens it shows haven't changed since.
  - The live database already holds tonight's test checks. Those would link Sunita's *first* message to earlier ones and spoil the story.
- **To re-record:** run `python tools/demo_video.py http://127.0.0.1:8000 out_dir` against a fresh local server.
  - It uses a `u_test` ID now, so a recording never counts in `/stats`.
  - Don't record on the live site before the pitch: it runs message 2, and the demo needs message 2 to be new.

## Known limits
- The model's reading of a message varies a little between runs, even at temperature 0. Same message, different run: the band can move between caution and high risk.
- The quiz exists in 4 languages (en, hi, hinglish, mr). The footer's quiz link in ta/te/kn/bn opens it in English.
- An invite-only VIP group pitch that hasn't asked for money yet scores 15. That's an honest limit, documented in EVAL.md.

## For Risheeth (from a code review of PR #11; Telegram is live now, so these matter more)
- **Shared rate limit:** Telegram checks use the literal IP `telegram`, so every bot user shares one 3000/hour bucket.
- **Fixed tonight:** `/start`, `/help` and `/lang` no longer count against the 30-checks-an-hour limit.
- **Partly fixed tonight:** the getFile-plus-download limit is now 3 s, up from 2. Test it with a real 3–5 MB screenshot once the bot is live.
- **Signal ID reuse:** the "website not registered" evidence reuses the id `S3` with 0 points, so a check can carry two S3 entries.
- **Duplicated labels:** the band labels exist three times (`telegram.BAND_LABELS`, `share_page.PAGE_TEXT`, web `i18n.js`). Share one table.
