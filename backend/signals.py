"""Deterministic scoring. No provider calls or model-supplied scores."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

from backend import weights
from backend.config import ROOT
from backend.extraction import Extraction, normalize, source_text
from backend.privacy import mask_text
from backend.schemas import Band, Evidence, Signal

SEBI_SOURCE = 'https://www.sebi.gov.in/legal/circulars/jun-2025/adoption-of-standardised-validated-and-exclusive-upi-ids-for-payment-collection-by-sebi-registered-intermediaries-from-investors_94535.html'
# Tip-group wording as sent: crypto, forex, F&O and "5% daily profit" pitches, in English, Hinglish and Indian scripts.
INVESTMENT = re.compile(
    r'\b(invest\w*|trad(?:e|ers?|ing)|stock\w*|broker\w*|mutual\s+fund|ipo|institutional|nivesh|share\s*market'
    r'|crypto\w*|bitcoin|btc|usdt|forex|nifty|banknifty|sensex|intraday|demat|f&o|options?\s+(?:tips|trading|calls)'
    r'|(?:vip|premium|market)\s+(?:tips|calls|signals?)|(?<!non-)(?<!non )profits?|munaf\w*|portfolio|dividends?|equity|commodity|mcx'
    r'|nse|bse|sebi|fund\s+manager|double\s+(?:your\s+)?money|paisa\s+double'
    r'|(?:guaranteed|assured|fixed|daily|weekly|monthly|high|double)\s+(?:returns?|income)'
    r'|\d+\s*%\s*(?:returns?|daily|weekly|monthly|per\s+(?:day|week|month)|guaranteed))\b'
    r'|निवेश|इन्वेस्ट|शेयर|ट्रेड|स्टॉक|मुनाफ|नफ़?ा|प्रॉफिट|रिटर्न|क्रिप्टो|म्यूचुअल|आईपीओ|निफ्टी|डीमैट'
    r'|गुंतवणूक|शेअर|முதலீ|பங்கு|லாபம்|டிரேடிங்|పెట్టుబడి|షేర్|లాభం|ట్రేడింగ్|ಹೂಡಿಕೆ|ಷೇರು|ಲಾಭ|ಟ್ರೇಡಿಂಗ್'
    r'|বিনিয়োগ|শেয়ার|মুনাফা|লাভ|ট্রেডিং', re.I)
# A verified quote for one of these claims puts the payment request in an investment context on its own.
INVESTMENT_CLAIMS = {'guaranteed_returns', 'vip_or_institutional_account', 'ipo_allotment', 'withdrawal_fee'}
PAYMENT = re.compile(r'\b(pay\w*|send|deposit|transfer|remit|bhej\w*|jama|bharo)\b|भेज|भुगतान|जमा|पाठवा|भरा|செலுத்த|அனுப்பு|చెల్లించ|పంప|ಪಾವತಿ|ಕಳುಹಿ|জমা|পাঠান|পেমেন্ট', re.I)
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
    full = _skeleton(host)
    tokens = [_skeleton(t) for t in re.split(r'[.-]', host)]
    for broker in brokers():
        for alias in broker['aliases']:
            name = _skeleton(alias)
            if len(name) >= 4 and (name in full or any(_one_edit(name, t) for t in tokens)):
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
    invalid = [u for u in extracted.entities.upi_ids if not u.split('@')[-1].startswith('valid')]
    investment = INVESTMENT.search(clean) or any(
        c.type in INVESTMENT_CLAIMS and normalize(c.quote) in clean for c in extracted.claims)
    if invalid and investment and PAYMENT.search(clean):
        result.append(signal('S1', weights.S1, 'Investment payment handle',
                             f"{', '.join(invalid)} does not use a SEBI @valid handle. Verify the payment destination on SEBI Check.", SEBI_SOURCE))
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
        result.append(signal('S6', min(weights.S6_CAP, sum(p for p, _ in claims)),
                             'Claims in the message', ' | '.join(q for _, q in claims), kind='quote'))
    if phishing_hits:
        result.append(signal('S7', weights.S7, 'Public phishing feed match',
                             'A URL matches a verified, online PhishTank report.', 'https://phishtank.org'))
    return sorted(result, key=lambda s: s.id)
