"""Fixes from the live QA sweep, 29 Oct: emoji between words, explanation guards, readable localized evidence,
next steps when nothing was flagged, and overlapping quotes."""
from __future__ import annotations

import pytest

from backend import language
from backend.extraction import Claim, Extraction, normalize, regex_extract, verified_extraction
from backend.schemas import Evidence, Signal
from backend.signals import evaluate


def test_emoji_between_words_do_not_hide_a_claim():
    text = '🚀 VIP 💰 Stock Tips 📈 300% 🔥🔥 guaranteed profit, pay ₹10,000 to qa.emoji.desk@ybl'
    claimed = verified_extraction(Extraction(claims=[Claim(type='guaranteed_returns', quote='300% guaranteed profit')]), text)
    assert [c.type for c in claimed.claims] == ['guaranteed_returns']
    assert normalize('₹10,000 🔥 at 5%') == '₹10,000 at 5%'  # currency and percent stay


@pytest.mark.parametrize(('text', 'lang', 'band', 'ok'), [
    ('ఈ సందేశంలో నకిలీ డొమైన్ ఉంది.', 'te', 'high_risk', True),
    ('ఈ సందేశంలో నకిలీ ম డొమైన్ ఉంది.', 'te', 'high_risk', False),  # a Bengali letter inside Telugu
    ('This looks safe to pay.', 'en', 'no_known_signals', False),
    ('यह भुगतान सुरक्षित है।', 'hi', 'no_known_signals', False),
    ('इसमें धोखाधड़ी के संकेत हैं।', 'hi', 'high_risk', True),
    ('Is message mein scam ke signals hain.', 'hinglish', 'high_risk', True),
    ('Is message mein स्कैम ke signals hain.', 'hinglish', 'high_risk', False),
    # Seen live: a Hindi check answered in Latin letters.
    ('li…@ybl yha paisa bhejna theek nhi h kyuki ye SEBI ke rule ke khilaf hai aur VIP group me 30% pakka munafa '
     'milne ka daawa kiya gya h.', 'hi', 'high_risk', False),
    # IDs, links and acronyms in Latin letters are fine inside a Hindi or Tamil sentence.
    ('tr…@ybl SEBI का @valid हैंडल नहीं है, और kite-zerodha-pro.in असली Zerodha नहीं है।', 'hi', 'high_risk', True),
    ('tr…@ybl என்பது SEBI-யின் @valid UPI முகவரி அல்ல.', 'ta', 'high_risk', True),
    ('This UPI ID is not a SEBI @valid handle.', 'mr', 'high_risk', False),
    # Bengali ends sentences with the danda, which Unicode files under Devanagari.
    ('এই সাইটে পেমেন্টের নাম সঠিক নয় এবং নিশ্চিত ৩০ শতাংশ লাভের কথা বলা হয়েছে।', 'bn', 'high_risk', True),
    # A made-up ID in Telugu letters (seen live) is not the masked ID from the evidence.
    ('ఈ సైట్లో ట్రే3@వైబిఎల్ లాంటి తప్పుడు పేమెంట్ ఐడీ ఉంది.', 'te', 'high_risk', False),
    ('tr…@ybl SEBI का @valid हैंडल नहीं है।', 'hi', 'high_risk', True),
    ('The payment ID tr…@ybl is not a SEBI @validhdfc-style handle.', 'en', 'high_risk', True),
    ('tr…@ybl-க்கு ₹499 அனுப்பச் சொல்கிறது, இது SEBI-யின் @valid முகவரி அல்ல.', 'ta', 'high_risk', True),  # case ending
])
def test_explanation_guard(text, lang, band, ok):
    assert language.explanation_ok(text, lang, band) is ok


@pytest.mark.parametrize(('text', 'lang'), [
    ('यह पेमेंट हैंडल सही नहीं है और पुरानी शिकायतों से जुड़ा है।', 'hi'),  # seen live
    ('Yeh pehle bhi report ho chuka hai aur 30% profit ka daawa karta hai.', 'hinglish'),
    ('இது 4 முந்தைய புகார்களுடன் தொடர்புடையது.', 'ta'),
])
def test_earlier_checks_are_not_called_complaints(text, lang):
    assert language.explanation_ok(text, lang, 'high_risk') is False
    assert language.explanation_ok(text, lang, 'high_risk', reports=2) is True  # people did report it


def signal(id, text, kind='lookup'):
    return Signal(id=id, points=10, label='x', evidence=Evidence(kind=kind, text=text, source_url=None))


def test_localized_domain_evidence_reads_naturally():
    s2, s3 = language.localize([signal('S2', 'kite-zerodha-pro.in is not zerodha.com'),
                                signal('S3', 'kite-zerodha-pro.in: registered 12 days ago')], 'hi')
    assert s2.evidence.text == 'kite-zerodha-pro.in असली zerodha.com नहीं है'
    assert s3.evidence.text == 'kite-zerodha-pro.in सिर्फ़ 12 दिन पहले रजिस्टर हुई है'
    bn = language.localize([signal('S2', 'a.in is not zerodha.com')], 'bn')[0]
    assert 'সরকারি' not in bn.evidence.text  # it said "government domain"


@pytest.mark.parametrize('lang', list(language.COPY))
def test_nothing_flagged_never_says_dont_pay(lang):
    _, _, steps = language.fallback('no_known_signals', lang, [])
    assert steps[0].text == language.NO_SIGNAL_STEPS[lang][0]
    assert steps[2].url == 'https://cybercrime.gov.in'
    high = language.fallback('high_risk', lang, [])[2]
    assert high[0].text == language.COPY[lang][5]


def test_overlapping_quotes_are_shown_once():
    text = 'Join now: 30% guaranteed monthly returns, 30% guaranteed. Pay to x.desk@ybl for stock tips'
    claims = [Claim(type='guaranteed_returns', quote='30% guaranteed monthly returns'),
              Claim(type='urgency_pressure', quote='Join now'), Claim(type='vip_or_institutional_account', quote='30% guaranteed')]
    s6 = next(s for s in evaluate(text, verified_extraction(Extraction(claims=claims), text), {}) if s.id == 'S6')
    assert s6.evidence.text.count('30% guaranteed') == 1


@pytest.mark.parametrize('text', [
    'USDT डबल प्लान 🚀 ₹20,000 लगाओ, 15 दिन में ₹40,000 पक्का। पेमेंट: cryptoking.amit@paytm',
    'பங்கு சந்தை டிப்ஸ்: 30% லாபம் உறுதி. பேமெண்ட்: ravi.tips@ybl',
])
def test_payment_written_as_a_loanword_still_counts(text):
    # Held-out h_hi_s04 scored only 30: "पेमेंट" and "लगाओ" were not read as asking for money.
    found = verified_extraction(Extraction(claims=[]), text)
    assert 'S1' in [s.id for s in evaluate(text, found, {})]


@pytest.mark.parametrize(('text', 'lang', 'ok'), [
    ("Don't pay; report this on 1930.", 'en', True),  # advice to report is fine
    ('पैसे न भेजें, 1930 पर रिपोर्ट करें।', 'hi', True),
    ('This UPI ID has been reported before.', 'en', False),  # nobody reported it
    ('यह आईडी पहले की रिपोर्टों से जुड़ी है।', 'hi', False),
])
def test_advice_to_report_is_not_a_claim_of_reports(text, lang, ok):
    assert language.explanation_ok(text, lang, 'high_risk') is ok


def test_a_fee_to_a_personal_upi_id_is_a_payment_request():
    # Live, 30 Oct: "Premium group fee Rs 4,999 to x@ybl" had no S1 because "fee" wasn't read as asking for money.
    text = '(sample) Bank Nifty jackpot call tomorrow, 40% up. Premium group fee Rs 4,999 to review.fix@ybl'
    assert 'S1' in [s.id for s in evaluate(text, verified_extraction(Extraction(claims=[]), text), {})]
