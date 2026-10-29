"""Deterministic scoring. No provider calls or model-supplied scores."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

from backend import weights
from backend.config import ROOT
from backend.extraction import Extraction, normalize, sebi_valid_handle, source_text
from backend.privacy import mask_text
from backend.schemas import Band, Evidence, Signal

SEBI_SOURCE = 'https://www.sebi.gov.in/legal/circulars/jun-2025/adoption-of-standardised-validated-and-exclusive-upi-ids-for-payment-collection-by-sebi-registered-intermediaries-from-investors_94535.html'
# Tip-group wording as sent: crypto, forex, F&O and "5% daily profit" pitches, in English, Hinglish and Indian scripts.
# Words that also fit shop bills, fees or "share this" (traders, profit, return, portfolio, शेयर करें) only count
# inside an investment phrase, because S1 alone is 35 points.
_GAIN = r'(?:returns?|profits?|munafa|income)'
_FIRM = r'(?!\s+(?:co\b|company|corp\w*|enterprises?|agency|firm|stores?|house|traders?))'  # "Ganesh Trading Co."
INVESTMENT = re.compile(
    r'\b(invest(?!igat|itur)\w*|nivesh\s+(?:kar\w*|plan|scheme)|trading' + _FIRM
    + r'|traders?\s+(?:group|club|community)|expert\s+traders?|trade\s+kar\w*'
    r'|(?:stock|share|sebi[\s-]*registered)[\s-]*broker\w*|broker(?:age)?\s+(?:account|app|platform)|mutual\s+funds?|ipo'
    r'|institutional\s+(?:accounts?|investors?|trading|desk|quota|club|group)|share\s*market'
    r'|stocks?\s+(?:market|tips?|calls?|trading|picks?|advice|recommendations?)|stock\s*exchange'
    r'|(?:buy|sell)\s+(?:this|these)\s+stocks?|(?:buy|sell)\s+stocks?\s+(?:now|today|tomorrow)|penny\s+stocks?|multibagger|upper\s+circuit|stop\s*loss|\d+\s+shares'
    r'|(?:share|ipo)s?\s+allotment|allotment\s+of\s+\d+\s+shares?|allotted\s+shares?|jackpot\s+(?:calls?|tips?)'
    r'|crypto\w*|bitcoin|usdt|binance|forex(?!\s+card)|bank\s*nifty|nifty\s*(?:50|bank|options?|calls?|tips|futures?|trading)'
    r'|sensex|intraday|demat|f&o|futures?\s+(?:and|&)\s+options|options?\s+(?:tips|trading|calls)'
    r'|(?:vip|premium|market|trading)\s+(?:tips|calls|signals?)|(?:guaranteed|assured|monthly)\s+dividends?|dividend\s+(?:stocks?|shares?|yield)|equity\s+(?:shares?|funds?|market|trading)'
    r'|commodity\s+(?:tips|trading|calls)|mcx|sebi|fund\s+manager|double\s+(?:your\s+)?money|pais[ae]\s+(?:double|dabal)'
    r'|(?:guaranteed|assured|fixed|pakka)\s+' + _GAIN + r'|' + _GAIN + r'\s+(?:guaranteed|assured|pakka)'
    + r'|(?:high|double)\s+(?:returns?|profits?)|(?:daily|weekly)\s+profits?'
    r'|profits?\s+(?:daily|guaranteed|assured|every\s+(?:day|week|month))|munafa\s+pakka|roz(?:ana)?\s+(?:ka\s+)?munafa'
    r'|(?:release|withdraw)\w*\s+(?:your\s+)?(?:profits?|returns?|earnings)'
    r'|\d+(?:\.\d+)?\s*%\s*(?:(?:daily|weekly|monthly)\s+)?(?:returns?|profits?|munafa|gain)(?!\s+(?:policy|accepted|within))'
    r'|\d+(?:\.\d+)?\s*%\s*(?:daily|weekly|per\s+(?:day|week)|roz\w*))\b'
    # "This share will be up 40% tomorrow" or "yesterday's call gave 18%", in any script. Outside \b…\b: "%" is not
    # a word character.
    r'|(?:call|tip)s?\s+(?:gave|given|delivered|hit)\s+\d+(?:\.\d+)?\s*%'
    r'|(?:this|ye|yeh|is|यह|ये|इस|हा|ఈ|এই|இந்த)\s+(?:share|शेयर|शेअर|షేర్|শেয়ার|ஷேர்)\S*\s+(?:\S+\s+){0,3}\d+(?:\.\d+)?\s*%'
    r'|निवेश|इन्वेस्ट|शेयर\s*(?:मार्केट|बाज)|ट्रेडिंग(?!\s*कं)|स्टॉक\s*(?:मार्केट|टिप)|क्रिप्टो|म्यूचुअल\s*फंड|आईपीओ|निफ्टी'
    r'|डीमैट|सेबी|(?:गारंटी\S*|पक्का|फिक्स्ड|निश्चित)\s*(?:रिटर्न|मुनाफ|प्रॉफिट)'
    r'|(?:रिटर्न|मुनाफ\S*|प्रॉफिट)\s*(?:की\s*)?(?:गारंटी|पक्का)|रोज\S*\s*(?:का\s*)?मुनाफ|पैस[ाे]\s*डबल'
    r'|\d+(?:\.\d+)?\s*%\s*(?:का\s*)?(?:रिटर्न|मुनाफ|प्रॉफिट|नफ|லாபம்|లాభం|ಲಾಭ|লাভ|মুনাফা)'
    r'|गुंतवणूक|शेअर\s*(?:मार्केट|बाजार)|முதலீ|(?:பங்கு(?:ச்)?|ஷேர்)\s*(?:சந்தை|மார்க்கெட்)'
    r'|(?:டிரேடிங்|ட்ரேடிங்)(?!\s*(?:கம்பெனி|நிறுவன))|పెట్టుబడి|షేర్\s*మార్కెట్|స్టాక్\s*(?:మార్కెట్|టిప్స్)'
    r'|ట్రేడింగ్(?!\s*కంపెనీ)|ಹೂಡಿಕೆ|(?:ಷೇರು|ಶೇರ್)\s*(?:ಮಾರುಕಟ್ಟೆ|ಮಾರ್ಕೆಟ್)|ಸ್ಟಾಕ್\s*ಮಾರ್ಕೆಟ್|ಟ್ರೇಡಿಂಗ್(?!\s*ಕಂಪನಿ)'
    r'|বিনিয়োগ|(?:শেয়ার|স্টক)\s*(?:বাজার|মার্কেট)|ট্রেডিং(?!\s*কোম্পানি)', re.I)
# A verified quote for one of these claims puts the payment request in an investment context on its own.
INVESTMENT_CLAIMS = {'guaranteed_returns', 'vip_or_institutional_account', 'ipo_allotment', 'withdrawal_fee',
                     'insider_tip'}
PAYMENT = re.compile(r'\b(pay\w*|send|deposit|transfer|remit|recharge|top[\s-]?up|bhej\w*|jama|bharo|daal\s*do|dalo'
                     r'|de\s*do|dena|deni)\b|भेज|भुगतान|जमा|डाल\s*दो|पाठवा|भरा|செலுத்த|அனுப்ப|చెల్లించ|పంప|ಪಾವತಿ|ಕಳುಹಿ'
                     r'|জমা|পাঠা|পেমেন্ট'
                     # "पेमेंट: x@paytm" and "₹20,000 लगाओ" (put money in) ask for money as plainly as "pay".
                     r'|पेमेंट|பேமெண்ட்|పేమెంట్|ಪೇಮೆಂಟ್|लगा(?:ओ|एं|इए|ना)', re.I)
_BRAND_AFFIXES = frozenset(('app', 'apps', 'apk', 'trade', 'trading', 'broker', 'stocks',
    'invest', 'investment', 'pay', 'payment', 'login', 'secure', 'support', 'vip', 'pro', 'official', 'download'))
_LOOKALIKE = str.maketrans({'а':'a','е':'e','о':'o','р':'p','с':'c','х':'x','і':'i','у':'y','ѕ':'s','ӏ':'l','ο':'o','ι':'i','0':'o','1':'l'})


@lru_cache(maxsize=1)
def brokers() -> list[dict]:
    return json.loads((ROOT / 'seed/brokers.json').read_text(encoding='utf-8'))


def _skeleton(value: str) -> str:
    try:
        value = value.encode('ascii').decode('idna')
    except (UnicodeError, UnicodeEncodeError):
        pass
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()).translate(_LOOKALIKE)
                   if c.isalnum())


def _one_edit(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        mismatch = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(mismatch) <= 1 or (len(mismatch) == 2 and mismatch[1] == mismatch[0] + 1
                                     and a[mismatch[0]] == b[mismatch[1]] and a[mismatch[1]] == b[mismatch[0]])
    if len(a) > len(b):
        a, b = b, a
    return any(a == b[:i] + b[i + 1:] for i in range(len(b)))


def lookalike(host: str) -> str | None:
    host = host.lower().rstrip('.')
    # A real, explicitly allowed domain is not suspicious just because another brand resembles it.
    if any(host == d or host.endswith('.' + d) for b in brokers() for d in b['domains']):
        return None
    try:
        host = host.encode('ascii').decode('idna')
    except UnicodeError:
        pass
    tokens = [_skeleton(t) for t in re.split(r'[.-]', host)]
    for broker in brokers():
        for alias in broker['aliases']:
            name = _skeleton(alias)
            def brand_token(token: str) -> bool:
                if _one_edit(name, token):
                    return True
                if name in token:
                    prefix, _, suffix = token.partition(name)
                    return (not prefix or prefix in _BRAND_AFFIXES) and (not suffix or suffix in _BRAND_AFFIXES)
                return False
            if len(name) >= 4 and any(brand_token(t) for t in tokens):
                return broker['domains'][0]
    return None


def signal(id: str, points: int, label: str, text: str, source: str | None = None,
           kind: str = 'lookup') -> Signal:
    return Signal(id=id, points=points, label=label,
                  evidence=Evidence(kind=kind, text=mask_text(text), source_url=source))


def score(signals: list[Signal]) -> tuple[int, Band]:
    total = max(0, min(100, sum(s.points for s in signals)))
    return total, 'high_risk' if total >= 60 else 'caution' if total >= 30 else 'no_known_signals'


def evaluate(text: str, extracted: Extraction, domain_ages: dict[str, tuple[int, str]],
             phishing_hits: list[str] | None = None) -> list[Signal]:
    result = []
    clean = normalize(source_text(text))
    invalid = [u for u in extracted.entities.upi_ids if not sebi_valid_handle(u)]
    # The sender picks the UPI name, and "mahalaxmi.trading@okicici" is a shop: only the message says it's investing.
    context = clean
    for upi in extracted.entities.upi_ids:
        context = context.replace(upi, ' ')
    investment = INVESTMENT.search(context) or any(
        c.type in INVESTMENT_CLAIMS and normalize(c.quote) in clean for c in extracted.claims)
    if invalid and investment and PAYMENT.search(context):
        result.append(signal('S1', weights.S1, 'Investment payment handle',
                             f"{', '.join(invalid)} does not use a SEBI @valid handle (registered brokers use @valid plus their bank's name, "
                             "like @validhdfc). Verify the payment destination on SEBI Check.", SEBI_SOURCE))
    matches = [(d, lookalike(d)) for d in extracted.entities.domains]
    matches = [(d, official) for d, official in matches if official]
    if matches:
        result.append(signal('S2', weights.S2, 'Look-alike domain',
                             '; '.join(f'{d} is not {official}' for d, official in matches),
                             'https://' + matches[0][1]))
    ages = [(d, age, url) for d, (age, url) in domain_ages.items() if 0 <= age < 180]
    if ages:
        domain, age, url = min(ages, key=lambda x: (x[1], x[0]))
        result.append(signal('S3', weights.S3_NEW if age < 30 else weights.S3_RECENT,
                             'Recently registered domain', f'{domain}: registered {age} days ago', url))
    claims = []
    seen = set()
    for claim in extracted.claims:
        group = 'vip_or_institutional_account' if claim.type == 'ipo_allotment' else claim.type
        if group not in weights.CLAIMS or group in seen:
            continue
        if group == 'sebi_registered_claim' and extracted.entities.sebi_reg_numbers:
            continue  # number presence is not verification; never give a positive endorsement
        if normalize(claim.quote) not in clean:
            continue
        seen.add(group)
        claims.append((weights.CLAIMS[group], claim.quote))
    if claims:
        quotes = [q for _, q in claims]
        shown = [q for i, q in enumerate(quotes) if not any(
            normalize(q) in normalize(other) and (normalize(q) != normalize(other) or j < i) for j, other in enumerate(quotes) if j != i)]
        result.append(signal('S6', min(weights.S6_CAP, sum(p for p, _ in claims)),
                             'Claims in the message', ' | '.join(shown), kind='quote'))
    if phishing_hits:
        result.append(signal('S7', weights.S7, 'Public phishing feed match',
                             'A URL matches a verified, online PhishTank report.', 'https://phishtank.org'))
    return sorted(result, key=lambda s: s.id)
