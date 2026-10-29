"""GET /c/{check_id}: the page a shared verdict opens. Server-rendered, so WhatsApp can read its Open Graph tags.

Every value is HTML-escaped. The page shows masked entities only, never the raw message.
"""
from __future__ import annotations

from html import escape

from backend.schemas import CheckView

BAND_EN = {
    "high_risk": ("High risk", "Don't pay. This message has several scam signals."),
    "caution": ("Caution", "Some warning signs. Verify before you pay."),
    "no_known_signals": ("No known scam signals", "No known scam signals. This doesn't prove it's genuine."),
}


# The page body speaks the check's language; the Open Graph tags stay English for WhatsApp's preview (brief, F3).
# (pill labels for high_risk, caution, no_known_signals; "Risk signals"; "What to do"; call to action)
PAGE_TEXT = {
    "en": (("High risk", "Caution", "No known scam signals"), "Risk signals", "What to do", "Check a message yourself"),
    "hi": (("ज़्यादा ख़तरा", "सावधान", "कोई जाना-पहचाना संकेत नहीं"), "ख़तरे के संकेत", "अब क्या करें", "ख़ुद कोई मैसेज जाँचें"),
    "mr": (("जास्त धोका", "सावधान", "ओळखीचे संकेत नाहीत"), "धोक्याचे संकेत", "आता काय करावे", "स्वतः मेसेज तपासा"),
    "hinglish": (("Zyada khatra", "Saavdhaan", "Koi jaana-pehchaana signal nahi"), "Khatre ke signals", "Ab kya karein",
                 "Khud koi message check karo"),
    "ta": (("அதிக ஆபத்து", "கவனம்", "தெரிந்த அறிகுறிகள் இல்லை"), "ஆபத்து அறிகுறிகள்", "இப்போது என்ன செய்வது",
           "நீங்களே ஒரு மெசேஜை சரிபாருங்கள்"),
    "te": (("ఎక్కువ ప్రమాదం", "జాగ్రత్త", "తెలిసిన సంకేతాలు లేవు"), "ప్రమాద సంకేతాలు", "ఇప్పుడు ఏం చేయాలి",
           "మీరే ఒక మెసేజ్ చెక్ చేయండి"),
    "kn": (("ಹೆಚ್ಚು ಅಪಾಯ", "ಎಚ್ಚರಿಕೆ", "ತಿಳಿದ ಸೂಚನೆಗಳಿಲ್ಲ"), "ಅಪಾಯದ ಸೂಚನೆಗಳು", "ಈಗ ಏನು ಮಾಡಬೇಕು",
           "ನೀವೇ ಒಂದು ಮೆಸೇಜ್ ಪರಿಶೀಲಿಸಿ"),
    "bn": (("বেশি ঝুঁকি", "সাবধান", "জানা কোনো সংকেত নেই"), "বিপদের সংকেত", "এখন কী করবেন", "নিজেই একটি মেসেজ যাচাই করুন"),
}
_BAND_INDEX = {"high_risk": 0, "caution": 1, "no_known_signals": 2}


def render_share_page(view: CheckView, page_url: str, ref: str | None = None) -> str:
    """`ref` is the sharer's validated anon_id; the call to action carries it so the new visit is credited."""
    # The visitor lands on the check page in the sharer's language, and the sharer is credited.
    cta_href = f"/?lang={escape(view.lang)}" + (f"&amp;ref={escape(ref)}" if ref else "")
    pills, signals_heading, steps_heading, cta = PAGE_TEXT.get(view.lang, PAGE_TEXT["en"])
    html_lang = "hi-Latn" if view.lang == "hinglish" else view.lang
    band_title, band_line = BAND_EN[view.band]
    n = len(view.signals)
    og_title = f"Check Before You Pay: {band_title}"
    og_desc = f"{band_line} {n} risk signal{'s' if n != 1 else ''} found. Check any investment tip before you pay."
    # A picture preview in WhatsApp (bilingual card per band in web/og/); same origin as the page.
    og_image = f"{page_url.rsplit('/c/', 1)[0]}/og/{view.band}.png"
    signals = "\n".join(
        f'<li><span class="pts">+{s.points}</span><div><strong>{escape(s.label)}</strong>'
        f'<p>{escape(s.evidence.text)}</p></div></li>'
        for s in view.signals
    )
    steps = "\n".join(
        f'<li><a href="{escape(st.url)}" rel="noopener" target="_blank">{escape(st.text)}</a></li>' if st.url
        else f"<li>{escape(st.text)}</li>"
        for st in view.next_steps
    )
    return f"""<!doctype html>
<html lang="{escape(html_lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(og_title)}</title>
<meta name="description" content="{escape(og_desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Check Before You Pay">
<meta property="og:title" content="{escape(og_title)}">
<meta property="og:description" content="{escape(og_desc)}">
<meta property="og:url" content="{escape(page_url)}">
<meta property="og:image" content="{escape(og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(band_title)}: {escape(band_line)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="/styles.css">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<script type="module" src="/share.js"></script>
</head>
<body>
<main class="page share-page">
  <p class="eyebrow">Check Before You Pay</p>
  <section class="verdict band-{escape(view.band)}">
    <div class="verdict-head">
      <span class="band-pill">{escape(pills[_BAND_INDEX[view.band]])}</span>
      <span class="score">{view.score}<small>/100</small></span>
    </div>
    <h1>{escape(view.headline)}</h1>
    <p class="explanation">{escape(view.explanation)}</p>
    {f'<h2>{escape(signals_heading)}</h2><ul class="signals">{signals}</ul>' if view.signals else ''}
    <h2>{escape(steps_heading)}</h2>
    <ul class="steps">{steps}</ul>
  </section>
  <a class="button primary" href="{cta_href}">{escape(cta)}</a>
</main>
</body>
</html>"""


def render_not_found() -> str:
    """A shared link that no longer resolves (mistyped, or from a reset test database) still lands a person somewhere
    useful instead of on a JSON error."""
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Check Before You Pay</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="/styles.css">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
</head>
<body>
<main class="page share-page">
  <p class="eyebrow">Check Before You Pay</p>
  <section class="card empty">
    <h1>We couldn't find this check</h1>
    <p class="muted">The link may be mistyped. You can check the message yourself in a few seconds.</p>
    <p class="muted" lang="hi">यह जाँच नहीं मिली। आप ख़ुद कुछ सेकंड में मैसेज जाँच सकते हैं।</p>
    <a class="button primary" href="/">Check a message</a>
  </section>
</main>
</body>
</html>"""
