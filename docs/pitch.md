# Pitch: Check Before You Pay (draft)

**Status: draft, written overnight on 29 Oct.** The skill's rule is to pitch only what works, so the opening, "Today", the numbers and the hard questions are written; the **demo and "how" sections get written once the real check works end to end**. Owner: Samarth. Rewrite any line that doesn't sound like you talking.

Times are for 3:00. Rescale for Edge City's demo day and the Finale once their limits are announced.

## 1. Opening 30 seconds (memorise word for word)

> This winter, a 68-year-old businessman in Mumbai was added to a WhatsApp group called "Trader Titan VIP Group".
> The group was full of people posting profits. They sent him a trading app that showed him profits too.
> Between December and January, he paid nearly ₹11 crore into it.
> *(pause)*
> He's not unusual. Last year Indians lost ₹22,495 crore to cyber fraud, and three quarters of it went to fake investment schemes like this one.
> Every one of those payments had a moment before it. That's where we work.

Sources: NewsBytes, Jan 2026 (the ₹11 crore case); ThePrint, citing Ministry of Home Affairs data (2025 losses, 76% investment fraud).

## 2. Full script

| Time | Who | What |
|---|---|---|
| 0:00-0:30 | Samarth | The opening above |
| 0:30-0:50 | Samarth | **Today.** "SEBI warned about exactly these groups on 22 October. Look at what a family can check today. SEBI Check needs you to know it exists. The 1930 helpline is for after the money's gone. The I4C registry only knows numbers someone already reported, and scammers make a new UPI ID every day. Truecaller screens calls, not a stock-tip group's payment request." |
| 0:50-2:00 | *(demo driver)* | **Demo:** write after the check works (see 3) |
| 2:00-2:30 | *(B)* | **How:** write after the check works. The likely line: "The risk score is a fixed formula over facts we check, like whether the UPI ID is a SEBI @valid handle and whether the link copies a real broker. The AI only reads the message and explains the result, so the same message always gets the same score." |
| 2:30-3:00 | Samarth | **Close:** "Families pay ₹49 a month to cover everyone's phones. Brokers and banks can call the same check before a payment leaves. Next we take it into the WhatsApp groups where these scams start. Sunita's son forwards her the next VIP group message, and this time she sees the red flags before she pays." Use real usage numbers here once we have them: users, checks, shares. |

## 3. Demo path (live, on a phone, about 70 seconds)

**Before going on stage:**
- Open https://34-45-129-243.sslip.io on the demo phone. Set the language to **हिन्दी**.
- Copy both messages below into the phone's notes app.
- Keep WhatsApp logged in.
- Have the backup video open in another tab: [`docs/demo.mp4`](demo.mp4) (88 s, narrated, the same two messages; re-record with `tools/demo_video.py` after the stats reset).

**Message 1, Sunita's** (sample; every ID is made up):

> (नमूना) 🔥 VIP Stock Tips ग्रुप 🔥 हर महीने 30% पक्का मुनाफ़ा। इंस्टीट्यूशनल अकाउंट खोलने के लिए आज ही ₹50,000 tradepro.desk@ybl पर भेजें और ऐप यहाँ से डाउनलोड करें: kite-zerodha-pro.in. सिर्फ़ 3 सीटें बची हैं!

**Message 2, a different group** (sample): a new message, but the same UPI ID:

> (sample) Bank Nifty jackpot call kal 40% upar jayega. Premium group join karne ke liye ₹4,999 tradepro.desk@ybl pe bhejo.

| Step | Tap | Say |
|---|---|---|
| 1 | Paste message 1, tap **पैसे भेजने से पहले जाँचें** | "This is the message Sunita got. She reads Hindi, so we check in Hindi." |
| 2 | The verdict appears (High risk) | "Under five seconds. Point at the evidence: this UPI ID isn't a SEBI @valid handle, the app link copies Zerodha, and here is the exact line where they promise 30% a month. The AI didn't decide this score. Fixed checks did, and every point has its proof." |
| 3 | Tap **परिवार को भेजें** | "One tap sends this card to the family group on WhatsApp. That's how the warning travels as fast as the scam." |
| 4 | Tap **दूसरा मैसेज जाँचें**, paste message 2, check | "A different message, from a different group, the next day." |
| 5 | Point at "Linked to 1 earlier check through the same UPI ID" | "Scammers change messages every day. They can't hide that the money goes to the same place. Every check makes the next one smarter." |
| 6 | Open `/stats` | "And this is live: real people, real checks, in these languages, since Friday." |

**What the judge should notice:** the language, the speed, the evidence quotes, and the ring link in step 5.

**Fallback line:** "The venue Wi-Fi is fighting us, so here's the same check recorded this morning." Then play the video from the same step.

**Before the demo:**
- Run message 1 once in the morning, so step 5 has a link to show.
- Never run message 2 first.

## 4. Hard questions (2-sentence answers)

1. **How is this different from Truecaller or SEBI Check?**
   - Truecaller screens calls and SMS senders; SEBI Check verifies a broker if you already know to look.
   - We take the message itself (screenshot, voice note or text), check every payment detail in it in one place, in your language, before you pay.
2. **What's real and what's mocked?**
   - Every check, ring link, report and quiz score on the live URL is real, and so are the numbers on /stats (sample data is excluded).
   - Messages labelled "(sample)" and the quiz messages are written by us; payments run in Dodo's test mode, so no real money moves.
3. **Who pays, and why would they switch?**
   - Families pay ₹49 a month because one stopped scam is worth years of it.
   - Brokers and banks pay per check, because every scam payment that leaves through them becomes a dispute and a complaint.
4. **What happens when the AI is wrong?**
   - The AI never decides the score: a fixed formula over checked facts does, and every signal shows its evidence.
   - We never say "safe". The lowest band says no known signals and that this doesn't prove it's genuine.
5. **What would you build in the next 30 days?**
   - A WhatsApp-native way to forward a message to us.
   - Partnerships with two regional creators.
   - Tie-ups with one broker so their customers can check payment requests.
6. **Why your team?**
   - We've built fraud investigation on graphs before; we're also in TigerGraph's six-team final for it.
   - We ship in days, and we're using the product with our own families this week.
7. **Isn't this just a ChatGPT wrapper?**
   - The verdict comes from deterministic checks the model can't change: the SEBI @valid rule, look-alike broker domains, domain age, and links to earlier reports.
   - The model only reads screenshots and voice notes and explains the result in eight languages.
8. **How do you know it works?**
   - On 128 messages we never tuned on, written blind, in eight languages, it flagged 61 of 64 scams and none of 64 ordinary payments, including 33 bills and family requests to personal UPI IDs.
   - Before this week's changes it caught 39%; the method, the data and the three misses are public in the repo.
9. **How do you stop people gaming it, or scammers testing against it?**
   - Scammers can change UPI IDs but not the rule that real brokers collect through @valid handles.
   - Every new identifier links back to earlier reports through the same scripts and links.

## 5. One slide of numbers

| | | Source |
|---|---|---|
| Lost to cyber fraud in India, 2025 | ₹22,495 crore | ThePrint, Ministry of Home Affairs data |
| Share from investment fraud | 76% | same |
| Cases in 2025 | 28.15 lakh | same |
| SEBI's warning on WhatsApp tip groups | 22 Oct 2026 | Business Today |
| SEBI-registered brokers collect through | @valid UPI handles (since 1 Oct 2025) | SEBI circular, 11 June 2025 |
| Scams flagged, 128 held-out messages in 8 languages | 61 of 64 (95%) | docs/EVAL.md |
| Ordinary payments flagged (bills, rent, family, real brokers) | 0 of 64 | docs/EVAL.md |
| Before this week's scoring changes | 25 of 64 (39%) | same set, same day |
| Time per check | 2.8 s typical, 4.3 s slowest 1 in 20 | same run |

## Delivery notes

- Memorise the opening 30 seconds. Shaky hands usually settle once the first lines are on autopilot.
- Slow down by about 20%. Pause after "₹11 crore".
- Do at least 3 timed run-throughs, including one where the demo "fails" and you switch to the video.
