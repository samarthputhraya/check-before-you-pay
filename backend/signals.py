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
INVESTMENT = re.compile(r'\b(invest\w*|trad(?:e|ing)|stock\w*|broker\w*|mutual\s+fund|ipo|institutional|nivesh|share\s+market)\b|निवेश|शेयर|ट्रेड|गुंतवणूक|முதலீ|பங்கு|పెట్టుబడి|షేర్|ಹೂಡಿಕೆ|ಷೇರು|বিনিয়োগ|শেয়ার', re.I)
PAYMENT = re.compile(r'\b(pay\w*|send|deposit|transfer|remit|bhej\w*|jama|bharo)\b|भेज|भुगतान|जमा|पाठवा|भरा|செலுத்த|அனுப்பு|చెల్లించ|పంప|ಪಾವತಿ|ಕಳುಹಿ|জমা|পাঠান|পেমেন্ট', re.I)
INVESTMENT = re.compile(INVESTMENT.pattern +
    r'|\b(crypto\w*|bitcoin|usdt|profits?|returns?|guaranteed|tips?|nifty|sensex|options?|futures?|forex|dividends?)\b'
    r'|स्टॉक|मुनाफ|मुनाफ़|रिटर्न|क्रिप्टो|निफ्टी|ऑप्शन|फॉरेक्स|गारंट|नफा|परतावा'
    r'|லாபம்|வருமானம்|லாபம்|లాభం|రాబడి|ಲಾಭ|ಆದಾಯ|লাভ|মুনাফা|রিটার্ন', re.I)
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
    invalid = [u for u in extracted.entities.upi_ids if not u.split('@')[-1].startswith('valid')]
    if invalid and INVESTMENT.search(clean) and PAYMENT.search(clean):
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
