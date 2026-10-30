# Submission and launch copy (Fri 30 Oct)

Copy-paste text for the Phase 1 submission and the launch posts. Every number here is also in the README or
docs/EVAL.md. If a number changes there, change it here too.

## Links

| What | Link |
|---|---|
| Live product | https://34-45-129-243.sslip.io |
| Live numbers | https://34-45-129-243.sslip.io/stats (reset to zero at 08:13 on Fri 30 Oct; our own testing never counts) |
| Quiz | https://34-45-129-243.sslip.io/quiz |
| Code | https://github.com/samarthputhraya/check-before-you-pay |
| Demo video (88 s) | https://github.com/samarthputhraya/check-before-you-pay/blob/main/docs/demo.mp4 (upload it to YouTube as unlisted if the form wants a video link) |
| Telegram bot | https://t.me/CheckBeforeYouPayBot (add it only once a real chat reply has been checked) |
| QR code for posters and slides | [`docs/qr-live.png`](qr-live.png), which opens the site with `?ref=u_qr_poster` |
| A4 poster with the QR, ready to print | [`docs/poster.pdf`](poster.pdf) (preview: [`docs/poster.png`](poster.png)); rebuild with `python tools/poster.py` |
| Gallery images for the submission form | [`docs/screenshots/`](screenshots/): 8 phone screenshots of the live site (home, a Hindi verdict with its evidence, the share page, quiz, stats, pricing) |
| Architecture and sequence diagrams | [`docs/diagrams/architecture.png`](diagrams/architecture.png), [`docs/diagrams/sequence.png`](diagrams/sequence.png) |

## Submission fields

**Name:** Check Before You Pay

**Tagline:** Forward any investment tip or payment request and see the red flags in 5 seconds, in your own language.

**The problem**

Indians lost ₹22,495 crore to cyber fraud in 2025, and 76% of it went to fake investment schemes (ThePrint, citing
MHA data). The usual path:
1. Someone is added to an invite-only WhatsApp "VIP stock tips" group.
2. They're sent an app that copies a real broker.
3. They're asked to pay a personal UPI ID.

SEBI warned about these groups on 22 Oct 2026. The official checks exist (SEBI Check, the 1930 helpline), but they're
scattered, and they only know identifiers someone has already reported.

**What it does**

You paste the message, a screenshot or a WhatsApp voice note, in English, Hindi, Hinglish, Marathi, Tamil, Telugu,
Kannada or Bengali.

In about 3 seconds you get a verdict with its evidence: high risk, caution, or "no known scam signals". You can
listen to it, send it to the family WhatsApp group as a card, or report it. A report links that UPI ID, phone number
or website to every future check.

**How it decides**

The score is a fixed formula over facts we check, not the AI's opinion:
- **UPI ID:** is the payment going to a UPI ID that isn't a SEBI `@valid` handle? Registered brokers collect only
  through `@valid` handles since 1 Oct 2025.
- **Website:** does the link copy a real broker's website, and how many days ago was it registered?
- **Earlier checks:** is it linked to earlier high-risk or reported checks through the same UPI ID, phone, website or
  group link?

Gemini reads screenshots and voice notes, pulls out the claims (each quote must appear word for word in the message),
and explains the verdict in your language. It never picks the points. Claims alone are capped at 40 of the 60 needed
for high risk.

**Results (measured, not claimed)**

On 128 held-out messages in 8 languages, written by someone who never saw the code:
- **Scams:** 61 of 64 flagged (95%).
- **Ordinary payment requests:** 0 of 64 flagged. 33 of them ask for money to a personal UPI ID.
- **Speed:** 2.3 s at p50 and 2.8 s at p95.

The method and the misses are in docs/EVAL.md.

**What's live and what isn't**
- **Live:** every check on the link, the evidence, Listen, the share card and share page, reports, the ring links,
  the quiz and `/stats`.
- **Live in test mode:** the Family (₹99 a month) and API (₹999 a month) plans on Dodo. A test purchase was checked end
  to end; only Dodo's signed webhook can mark an order paid.
- **Live on viaSocket:** every report adds a row to a Google Sheet and emails a family contact. A retried delivery never
  adds a second row.
- **Samples:** messages labelled "(sample)" and the quiz questions. They never count in the numbers.

**Challenges we ran into**
- **Listen failed only on the server.** It worked on a laptop, but every request failed on the live server. The audio
  encoder's first run there took 5.2 s against a 2 s limit. We raised the limit, switched to the fastest encoder
  setting, and keep it warm.
- **The model invented history.** It once wrote "linked to old complaints" when nobody had reported anything.
  - Every explanation now passes fixed checks before it's shown. It must not claim reports that don't exist, mix
    scripts, or call anything safe. Otherwise we show our own fixed text.
  - Bengali explanations kept failing those checks until we found that Unicode files Bengali's full stop (।) under
    Devanagari.

**Built with:** FastAPI, SQLite, Preact with htm (no build step), Gemini (Flash-Lite for extraction and
explanation, Gemini TTS for Listen), ffmpeg, Dodo Payments (test mode), the Telegram Bot API, Docker, and Google Cloud
(Compute Engine, Cloud Build) behind Caddy.

**Team**
- **Samarth Puthraya:** product, contract, pitch, deploy.
- **Risheeth S:** check pipeline, signals, ring links, media input, quiz backend.
- **Rishabh Arun:** web app.

Edit this list to match who actually did what before you submit.

## Launch posts

Each post below carries its own `?ref=` tag, so every visit it brings is stored as a `ref_visit` event with that tag.
To tag your own link, add `?ref=u_<name>` (letters, digits, `_` or `-`). Every page carries a 1200x630 preview image
(og:image), which WhatsApp, X and LinkedIn use for link previews.

**X (under 280 characters)**

> Got a "VIP stock tips" message asking you to pay a UPI ID? Paste it here before you pay. In about 3 seconds you
> see the red flags and the proof, in English, Hindi, Marathi, Tamil, Telugu, Kannada, Bengali or Hinglish.
> https://34-45-129-243.sslip.io/?ref=u_x_launch

**LinkedIn**

> Indians lost ₹22,495 crore to cyber fraud in 2025, and 76% of it went to fake investment schemes. The pattern
> repeats: a WhatsApp "VIP" group, an app that copies a real broker, and a request to pay a personal UPI ID.
>
> We built Check Before You Pay at Hacker House Goa. Paste the message, a screenshot or a voice note and get a
> verdict with evidence in your language. The score comes from fixed checks, not the AI's opinion: for example,
> registered brokers collect only through SEBI's @valid UPI handles. On 128 test messages it flagged 61 of 64 scams and 0 of 64 ordinary payment
> requests.
>
> Try it on a message you've received: https://34-45-129-243.sslip.io/?ref=u_li_launch

**WhatsApp forward (Hindi)**

> कोई "VIP स्टॉक टिप्स" ग्रुप पैसे माँग रहा है? भेजने से पहले उनका मैसेज यहाँ पेस्ट करें। लगभग 3 सेकंड में
> धोखाधड़ी के संकेत और उनका सबूत हिंदी में दिखेगा: https://34-45-129-243.sslip.io/?ref=u_wa_hi

**WhatsApp forward (English)**

> Before you pay anyone from a "VIP stock tips" group, paste their message here. In about 3 seconds it shows the red
> flags and the proof: https://34-45-129-243.sslip.io/?ref=u_wa_en

**Instagram caption (for creators; post it only after checking a message you actually received)**

> I pasted a "guaranteed returns" message I got into this. High risk, with the exact lines that gave it away.
> Check yours before you pay: link in bio. Then try the "Spot the scam" quiz.

Link in bio: `https://34-45-129-243.sslip.io/?ref=u_ig_bio`. Quiz: `https://34-45-129-243.sslip.io/quiz?ref=u_ig_quiz`.
