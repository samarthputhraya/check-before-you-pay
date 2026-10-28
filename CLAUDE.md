# HHGoa 2026 finals

**Building: "Check Before You Pay".** No brand name, just the phrase. Read `docs/BUILD_BRIEF.md` and `API_CONTRACT.md` before any work. They're the source of truth for scope, architecture, roles and the quality bar.

Source of truth: the organizers' Notion page (Hacker House Goa 2026) and its inauguration PDF.

## Deadlines (IST)
- Wed 28 Oct, 9:00 PM: idea locked at headcount
- Thu 29 Oct, by night: working product, end to end
- Fri 30 Oct, daytime: Phase 1, submit the live product, then launch on socials. House of NGMI creators help in the morning and film on Day 3.
- Sat 31 Oct, 9:59 AM: **final submission closes, no extensions.** Aim to submit by 7:59 AM.
- Sat 31 Oct, 11:00 AM: checkout
- Sat 31 Oct: Edge City picks the top 5 to pitch at its demo day
- 31 Oct to 2 Nov: partner tracks judged remotely
- Mon 2 Nov, 2-6 PM: Finale, where the top 20 pitch online to Davin Dong (Cookiy AI, who founded Instagram's Growth Science team)
- After the Finale: top teams go to the VC network (up to $2M in funding-round support)
- Headcount: 9 PM on Days 1-3, mandatory
- Core freeze: Fri morning, before Phase 1

## How judging works
- One submission, which every judge sees.
- Every round after 9:59 AM asks the same three questions: is it live, does it work, and is anyone using it. Measure users, shares and returns from the first user.
- Partner track names and judging briefs come out in the builder group. Read them the moment they drop.

## Prizes (mostly credits)
- Wispr Flow: $75K, which is 1 month of Pro for 5,000 registrants, not a team prize
- viaSocket: $50K in credits; the top 3 on its track get 12 months free
- Dodo: $15K in credits. "Day 3 is launch day. Put a price on what you built."
- AI Grants India: $10K in credits (apply at aigrants.in)
- TigerGraph: the prize is its own **Final Round**, a separate submission (brief: https://hhgoa-tg-round2.vercel.app/).
  - 6 finalist teams, picked from 215 in Round 1. Prizes: ₹20,000 / ₹15,000 / ₹10,000 for the top 3.
  - Task: a bank fraud-investigation agent answers 18 hidden cases. 9 of them are legitimate, and blocking an innocent customer scores 0 for that case.
  - Submit: a frozen commit, 18 answer JSONs, a one-command runner, a resilience statement and an innovation claim.
  - Judging includes live resilience drills and a 5-minute demo. The freeze and demo times are confirmed on the day.
  - Contact: Devanshu (TigerGraph DevRel). Send him the org ID for Savanna credits.
- Cake Wallet: travel for 5 builders plus 247 airdrops
- Edge City: the top 5 pitch at its demo day

"Socket" is **viaSocket** (AI automation and MCP, from Indore), not socket.dev. Coupon: HHGOA26-VIASOCKET.

No ranked 1st/2nd/3rd prizes are published anywhere: Devfolio's prize list is empty and the Notion page lists only partner prizes. Ask in the builder group.

## Idea (locked)
"Check Before You Pay." Users forward a stock-tip group message, trading-app link, UPI ID or wallet and get a verdict with evidence, in their language, in about 5 seconds. It leads with investment scams (76% of the ₹22,495 crore lost in 2025). SEBI warned about invitation-only WhatsApp tip groups on 22 Oct 2026.
- Fixed checks, not LLM guesses:
  - Real brokers collect through @valid UPI handles (SEBI rule since 1 Oct 2025).
  - Look-alike broker domains, and how old the domain is.
  - Links to earlier reports through the SQLite link tables. This app has no TigerGraph; TigerGraph is Samarth's separate Final Round entry (FraudLens repo).
  - The LLM pulls claims out of the message and quotes the evidence.
- Link out to SEBI Check, the I4C registry and the 1930 helpline. Never scrape government sites.
- Growth: verdict cards forwarded to family on WhatsApp, plus a "Spot the scam" quiz for creators.

## Resources
- The organizers provided a Gemini API key. It lives in `.env` as `GEMINI_API_KEY`, backend only. Never commit it or log it.
- Before launch, check the key's quota in AI Studio. All LLM calls go through one wrapper module so we can fall back to the AI Grants OpenAI credits.

## Rules
- Every line of code gets written at the house. Commit small and often.
- Never call a person a fraud. Show risk signals and evidence. Hash identifiers, and store raw messages only when the user reports them.
