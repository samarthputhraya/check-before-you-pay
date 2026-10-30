# Handoff: Fri 30 Oct, 13:30 IST

## What's live
- **Site:** https://34-45-129-243.sslip.io runs branch `ops/launch` at `ccdfb52`. Health is ok.
  - PR #15 (`ops/launch` into `main`) is open and mergeable. Claude can't merge its own PR; a person has to.
- **Dodo:** live in test mode. Family is ₹99 a month (Dodo refuses payments under US$1.00, so ₹49 couldn't be charged); API is ₹999.
  - A test purchase paid end to end: Indian test card 4576 2389 1277 1450, then "Simulate Success" on Cashfree's page. The signed webhook marked the order paid in 1.9 s.
  - The failure path works too (card 4242 fails at once for INR subscriptions). See docs/DODO.md.
- **Telegram:** @CheckBeforeYouPayBot. The webhook is registered and has no errors, but no real chat has reached it yet.
- **/stats:** reset at 08:13. It is still at **0 users**. Our own testing (`u_test` IDs) never counts.
- **Link previews:** the plain site link shows a picture card (`web/og/home.png`), like the shared verdict links already did.
- **Tests:** 539 pass.

## Needs a person, in this order
1. **Get real users.** Every judging round asks "is anyone using it?", and we're at 0.
   - **Posts:** copy is in docs/SUBMISSION.md, ready to paste, each with its own `?ref=` tag (X, LinkedIn, WhatsApp in Hindi and English, Instagram).
   - **Creators:** ask the House of NGMI creators to check a real message they received.
   - **Posters:** print docs/poster.pdf (A4, with a QR code) for the house and the demo stage.
2. **Submit on Devfolio.** No Devfolio confirmation email has arrived, so Phase 1 may not be submitted.
   - Final close: **Sat 31 Oct, 9:59 AM; aim for 7:59 AM.**
   - Fields: docs/SUBMISSION.md. Gallery: docs/screenshots/. Diagrams: docs/diagrams/.
   - Video: docs/demo.mp4. Upload it to YouTube as unlisted if the form wants a link.
3. **Merge PR #17** (PR #15 is merged). The live site already runs its code, so no deploy is needed.
4. **Telegram:** done. Checked in a real chat on 30 Oct (text, screenshot, voice note); see docs/TELEGRAM.md. Those 4 checks are Samarth's own tests, not users.
   - `t.me` and `telegram.org` time out on the hotel Wi-Fi (its DNS sends `t.me` to a different address than Google DNS does). `telegram.me`, `web.telegram.org` and the bot API all work, so the docs link to `telegram.me`.
5. **viaSocket:** done. The flow is live and tested; see docs/VIASOCKET.md. The coupon wasn't applied: the free plan covers it. The two test rows were deleted from the sheet on 30 Oct; it holds only the header now.
6. **AI Grants:** the form needs Samarth's WhatsApp (docs/AI_GRANTS.md).

## TigerGraph Final Round (separate repo, FraudLens)
- **Submitted** by email to Devanshu on 30 Oct: frozen commit `65f8a54692d96bc84523ef98c89ee7d7b1de635a` on `round2`.
- **Turn off auto-suspend on the Savanna workspace**, and keep it running until 2 Nov. If it pauses while judges re-run a case, the run can't be reproduced.
- Watch for Devanshu's reply with the freeze, Stage 1 and demo times.

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
- **File:** [`docs/demo.mp4`](docs/demo.mp4): the film version, 3 min 46 s, 1920x1080 at 60 fps. The 2560x1440 master
  for YouTube is `C:\Users\samar\Videos\CheckBeforeYouPay_film_1440p60.mp4` (162 MB, too big for GitHub). Rebuilt
  31 Oct, 02:40 with `tools/demo_bilingual/build_film.py` (dark theme, motion graphics, a virtual camera over the real
  captures, subtitles, Charon narration over two Lyria tracks).
- **Film scenes:** a feed of messages where the scams light up; the ₹22,495 crore number; how the scam works; then
  the earlier scenes below, plus an animated "how it decides" diagram (the claims, the UPI ID and the link light up,
  +50 / +30 / +40 fill a score dial) and a graph of two checks joined by one UPI ID.
- The light-theme version below is the previous cut (`build.py`), kept for reference.
- **What it shows**, with English and Hindi phones side by side throughout (Arjun and Sunita):
  1. the ₹22,495 crore problem, and how the scam works (VIP group, look-alike broker app, personal UPI ID);
  2. both paste the same scam and get high risk in under 4 seconds (real check times), then the evidence;
  3. Listen: the app's own Hindi and English audio;
  4. **a real iPhone voice note** (Risheeth reading a sample scam script, 30 Oct): the spoken UPI ID is caught,
     high risk 90 in both apps;
  5. the next message linked by its UPI ID, the share page and the quiz;
  6. the four real Telegram checks with server times, how it stays trustworthy, and the held-out numbers;
  7. the 40-second build timelapse from the hotel room, narrated day by day, then the QR code.
- **How it was made:** every phone screen is a real capture from fresh local servers at the PR #19 code with the real
  Gemini key; nothing is mocked. `tools/demo_bilingual/` rebuilds it (capture.py, capture_voice.py, build.py). The voice
  note and the timelapse stay outside Git.
- **Fixed on the way:** the TTS model returns a whole WAV file with a provenance chunk at the end, and the first video's
  code played those bytes as sound. That was the click and noise at the end of every narration line.
- **Not in it:** a screen recording of the Telegram chat itself.

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
