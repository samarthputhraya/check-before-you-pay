"""Deterministic verdict wording and localized fallbacks when explanation generation fails."""
from __future__ import annotations

import re

from backend.schemas import Band, Lang, NextStep, Signal

# high, caution, low, incomplete, explanation, pause, verify, report, labels S1..S7,
# payment-handle evidence, domain mismatch, domain age, prior links, script match, feed match.
COPY = {
 'en': ["Don't pay: several risk signals", 'Caution: verify before paying',
        "No known scam signals. This doesn't prove it's genuine.", 'Some checks could not be completed.',
        'The evidence below explains the risk signals found.', "Don't pay until you verify.",
        'Verify on SEBI Check', 'Report on 1930 or cybercrime.gov.in',
        ['Investment payment handle','Look-alike domain','New domain','Linked to earlier high-risk checks','Similar script','Claims in the message','Phishing feed'],
        'This investment payment handle is not a SEBI @valid handle: {facts}', '{domain} is not {official}',
        '{domain}: registered {age} days ago', '{facts} earlier checks linked', '{facts} earlier checks match this script',
        'A URL matches a verified online PhishTank report.'],
 'hi': ['पैसे न भेजें: जोखिम के कई संकेत', 'सावधान: पैसे भेजने से पहले जाँचें',
        'धोखाधड़ी के ज्ञात संकेत नहीं मिले। इससे असली होने का प्रमाण नहीं मिलता।', 'कुछ जाँचें पूरी नहीं हो सकीं।',
        'मिले जोखिम संकेतों के प्रमाण नीचे दिए गए हैं।', 'जाँच पूरी होने तक पैसे न भेजें।',
        'SEBI Check पर सत्यापित करें', '1930 या cybercrime.gov.in पर रिपोर्ट करें',
        ['निवेश भुगतान का UPI हैंडल','मिलता-जुलता डोमेन','नया डोमेन','पहले की संदिग्ध जाँचों से संबंध','मिलता-जुलता संदेश','संदेश में दावे','फ़िशिंग सूची'],
        'यह निवेश भुगतान हैंडल SEBI का @valid हैंडल नहीं है: {facts}', '{domain} असली {official} नहीं है',
        '{domain} सिर्फ़ {age} दिन पहले रजिस्टर हुई है', 'पहले की संदिग्ध जाँचों से जुड़ा: {facts}', 'इसी संदेश से मिलती पिछली जाँचें: {facts}',
        'एक URL, PhishTank की सत्यापित सक्रिय फ़िशिंग रिपोर्ट से मेल खाता है।'],
 'mr': ['पैसे पाठवू नका: धोक्याचे अनेक संकेत', 'सावधान: पैसे पाठवण्यापूर्वी तपासा',
        'फसवणुकीचे ज्ञात संकेत आढळले नाहीत. यामुळे अस्सल असल्याचे सिद्ध होत नाही.', 'काही तपासण्या पूर्ण होऊ शकल्या नाहीत.',
        'आढळलेल्या धोक्यांच्या संकेतांचे पुरावे खाली दिले आहेत.', 'पडताळणी होईपर्यंत पैसे पाठवू नका.',
        'SEBI Check वर पडताळा', '1930 किंवा cybercrime.gov.in वर तक्रार करा',
        ['गुंतवणुकीच्या पेमेंटचा UPI हँडल','सारखा दिसणारा डोमेन','नवीन डोमेन','आधीच्या संशयास्पद तपासण्यांशी संबंध','सारखा संदेश','संदेशातील दावे','फिशिंग यादी'],
        'गुंतवणुकीच्या पेमेंटचा हा हँडल SEBI चा @valid हँडल नाही: {facts}', '{domain} हे खरे {official} नाही',
        '{domain} फक्त {age} दिवसांपूर्वी नोंदवले गेले', 'जोडलेल्या आधीच्या तपासण्या: {facts}', 'या संदेशाशी जुळणाऱ्या आधीच्या तपासण्या: {facts}',
        'एक URL PhishTank मधील पडताळलेल्या सक्रिय फिशिंग नोंदीशी जुळतो.'],
 'ta': ['பணம் அனுப்ப வேண்டாம்: பல அபாய அறிகுறிகள்', 'எச்சரிக்கை: பணம் செலுத்தும் முன் சரிபார்க்கவும்',
        'அறியப்பட்ட மோசடி அறிகுறிகள் இல்லை. இது உண்மையானது என்பதற்கான சான்றல்ல.', 'சில சோதனைகளை முடிக்க முடியவில்லை.',
        'கண்டறியப்பட்ட அபாய அறிகுறிகளுக்கான சான்றுகள் கீழே உள்ளன.', 'சரிபார்க்கும் வரை பணம் அனுப்ப வேண்டாம்.',
        'SEBI Check மூலம் சரிபார்க்கவும்', '1930 அல்லது cybercrime.gov.in இல் புகாரளிக்கவும்',
        ['முதலீட்டுப் பணத்தின் UPI முகவரி','ஒத்த தோற்றமுள்ள இணைய முகவரி','புதிய இணைய முகவரி','முந்தைய ஆபத்தான சரிபார்ப்புகளுடன் தொடர்பு','ஒத்த செய்தி','செய்தியில் உள்ள கூற்றுகள்','ஃபிஷிங் பட்டியல்'],
        'இந்த முதலீட்டு UPI முகவரி SEBI-யின் @valid முகவரி அல்ல: {facts}', '{domain} உண்மையான {official} அல்ல',
        '{domain} {age} நாட்களுக்கு முன்புதான் பதிவு செய்யப்பட்டது', 'இணைக்கப்பட்ட முந்தைய சோதனைகள்: {facts}', 'இந்தச் செய்தியுடன் பொருந்தும் முந்தைய சோதனைகள்: {facts}',
        'ஒரு URL, PhishTank இன் சரிபார்க்கப்பட்ட செயலில் உள்ள ஃபிஷிங் பதிவுடன் பொருந்துகிறது.'],
 'te': ['డబ్బు పంపవద్దు: పలు ప్రమాద సంకేతాలు', 'జాగ్రత్త: చెల్లించే ముందు తనిఖీ చేయండి',
        'తెలిసిన మోసపు సంకేతాలు లేవు. ఇది నిజమైనదని రుజువు కాదు.', 'కొన్ని తనిఖీలు పూర్తి కాలేదు.',
        'కనిపించిన ప్రమాద సంకేతాలకు ఆధారాలు క్రింద ఉన్నాయి.', 'నిర్ధారించే వరకు డబ్బు పంపవద్దు.',
        'SEBI Check లో ధృవీకరించండి', '1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి',
        ['పెట్టుబడి చెల్లింపు UPI చిరునామా','పోలి ఉన్న డొమైన్','కొత్త డొమైన్','గత ప్రమాదకర తనిఖీలతో సంబంధం','పోలి ఉన్న సందేశం','సందేశంలోని వాదనలు','ఫిషింగ్ జాబితా'],
        'ఈ పెట్టుబడి చెల్లింపు చిరునామా SEBI @valid చిరునామా కాదు: {facts}', '{domain} అసలు {official} కాదు',
        '{domain} కేవలం {age} రోజుల క్రితం నమోదైంది', 'అనుసంధానమైన గత తనిఖీలు: {facts}', 'ఈ సందేశంతో సరిపోలిన గత తనిఖీలు: {facts}',
        'ఒక URL, PhishTank ధృవీకరించిన క్రియాశీల ఫిషింగ్ నివేదికతో సరిపోలింది.'],
 'kn': ['ಹಣ ಕಳುಹಿಸಬೇಡಿ: ಹಲವು ಅಪಾಯದ ಸಂಕೇತಗಳು', 'ಎಚ್ಚರಿಕೆ: ಪಾವತಿಸುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ',
        'ತಿಳಿದಿರುವ ವಂಚನೆ ಸಂಕೇತಗಳಿಲ್ಲ. ಇದು ನಿಜವೆಂಬುದಕ್ಕೆ ಪುರಾವೆಯಲ್ಲ.', 'ಕೆಲವು ಪರಿಶೀಲನೆಗಳನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಾಗಲಿಲ್ಲ.',
        'ಕಂಡುಬಂದ ಅಪಾಯದ ಸಂಕೇತಗಳ ಪುರಾವೆಗಳು ಕೆಳಗಿವೆ.', 'ಪರಿಶೀಲಿಸುವವರೆಗೆ ಹಣ ಕಳುಹಿಸಬೇಡಿ.',
        'SEBI Check ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ', '1930 ಅಥವಾ cybercrime.gov.in ನಲ್ಲಿ ವರದಿ ಮಾಡಿ',
        ['ಹೂಡಿಕೆ ಪಾವತಿಯ UPI ವಿಳಾಸ','ಹೋಲುವ ಡೊಮೇನ್','ಹೊಸ ಡೊಮೇನ್','ಹಿಂದಿನ ಅಪಾಯಕಾರಿ ಪರಿಶೀಲನೆಗಳೊಂದಿಗೆ ಸಂಬಂಧ','ಹೋಲುವ ಸಂದೇಶ','ಸಂದೇಶದ ಹೇಳಿಕೆಗಳು','ಫಿಶಿಂಗ್ ಪಟ್ಟಿ'],
        'ಈ ಹೂಡಿಕೆ ಪಾವತಿಯ ವಿಳಾಸ SEBI @valid ವಿಳಾಸವಲ್ಲ: {facts}', '{domain} ನಿಜವಾದ {official} ಅಲ್ಲ',
        '{domain} ಕೇವಲ {age} ದಿನಗಳ ಹಿಂದೆ ನೋಂದಾಯಿಸಲಾಗಿದೆ', 'ಸಂಬಂಧಿತ ಹಿಂದಿನ ಪರಿಶೀಲನೆಗಳು: {facts}', 'ಈ ಸಂದೇಶಕ್ಕೆ ಹೋಲುವ ಹಿಂದಿನ ಪರಿಶೀಲನೆಗಳು: {facts}',
        'ಒಂದು URL, PhishTank ನ ಪರಿಶೀಲಿತ ಸಕ್ರಿಯ ಫಿಶಿಂಗ್ ವರದಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ.'],
 'bn': ['টাকা পাঠাবেন না: একাধিক ঝুঁকির সংকেত', 'সতর্কতা: টাকা দেওয়ার আগে যাচাই করুন',
        'পরিচিত প্রতারণার সংকেত মেলেনি। এটি আসল হওয়ার প্রমাণ নয়।', 'কিছু পরীক্ষা সম্পূর্ণ করা যায়নি।',
        'পাওয়া ঝুঁকির সংকেতগুলির প্রমাণ নিচে দেওয়া আছে।', 'যাচাই না হওয়া পর্যন্ত টাকা পাঠাবেন না।',
        'SEBI Check-এ যাচাই করুন', '1930 বা cybercrime.gov.in-এ রিপোর্ট করুন',
        ['বিনিয়োগের UPI ঠিকানা','একই রকম দেখতে ডোমেন','নতুন ডোমেন','আগের ঝুঁকিপূর্ণ যাচাইয়ের সঙ্গে যোগ','একই রকম বার্তা','বার্তার দাবি','ফিশিং তালিকা'],
        'এই বিনিয়োগের UPI ঠিকানা SEBI-র @valid ঠিকানা নয়: {facts}', '{domain} আসল {official} নয়',
        '{domain} মাত্র {age} দিন আগে নিবন্ধিত হয়েছে', 'যুক্ত আগের পরীক্ষার সংখ্যা: {facts}', 'এই বার্তার সঙ্গে মেলা আগের পরীক্ষার সংখ্যা: {facts}',
        'একটি URL, PhishTank-এর যাচাই করা সক্রিয় ফিশিং রিপোর্টের সঙ্গে মিলেছে।'],
 'hinglish': ['Paise na bhejein: kai risk signals mile', 'Savdhaan: paise dene se pehle jaanchein',
        'Koi jaana-pehchana scam signal nahi mila. Isse asli hone ka saboot nahi milta.', 'Kuch jaanch poori nahi ho saki.',
        'Mile hue risk signals ke saboot neeche hain.', 'Verify hone tak paise na bhejein.',
        'SEBI Check par verify karein', '1930 ya cybercrime.gov.in par report karein',
        ['Investment payment UPI handle','Milta-julta domain','Naya domain','Purane high-risk checks se link','Milta-julta message','Message ke daave','Phishing list'],
        'Ye investment payment handle SEBI ka @valid handle nahi hai: {facts}', '{domain} asli {official} nahi hai',
        '{domain} sirf {age} din pehle register hua hai', 'Judi hui purani checks: {facts}', 'Is message se milti purani checks: {facts}',
        'Ek URL, PhishTank ki verified active phishing report se milta hai.'],
}


# Unicode blocks for each language's script. An explanation that mixes in another Indian script (the model once put
# a Bengali letter in a Telugu sentence) is replaced by the fixed text.
_SCRIPTS = {'hi': (0x0900, 0x097F), 'mr': (0x0900, 0x097F), 'bn': (0x0980, 0x09FF), 'ta': (0x0B80, 0x0BFF),
            'te': (0x0C00, 0x0C7F), 'kn': (0x0C80, 0x0CFF)}
_INDIC = (0x0900, 0x0DFF)
_SAFE = re.compile(r'\b(?:safe|genuine)\b|सुरक्षित|பாதுகாப்பான|సురక్షితం|ಸುರಕ್ಷಿತ|নিরাপদ|\bsurakshit', re.I)


# Masked IDs, links and acronyms (li…@ybl, kite-zerodha-pro.in, SEBI, UPI) are Latin in every language.
_LATIN_TOKENS = re.compile(r'\S*[.@…/]\S*|\b[A-Z]{2,}\b')


def explanation_ok(text: str, lang: Lang, band: Band) -> bool:
    own = _SCRIPTS.get(lang)
    native = 0
    for ch in text:
        code = ord(ch)
        if _INDIC[0] <= code <= _INDIC[1]:
            if not (own and own[0] <= code <= own[1]):
                return False
            native += 1
    # The model once answered a Hindi check in SMS-style Latin letters ("paisa bhejna theek nhi h"): that is the
    # Hinglish option, not Hindi, and the speech for it sounds wrong. Most letters must be in the language's script.
    latin = sum(ch.isascii() and ch.isalpha() for ch in _LATIN_TOKENS.sub(' ', text))
    if own and native <= latin:
        return False
    return not (band == 'no_known_signals' and _SAFE.search(text))


# Shown when nothing was flagged: no "don't pay" for a dinner bill, but the same two links.
NO_SIGNAL_STEPS = {
    'en': ('Before paying anyone for an investment, verify them.', 'If you already lost money, call 1930 or report on cybercrime.gov.in'),
    'hi': ('निवेश के लिए किसी को पैसे देने से पहले उसकी जाँच करें।', 'अगर पैसे जा चुके हैं, तो 1930 पर कॉल करें या cybercrime.gov.in पर रिपोर्ट करें'),
    'mr': ('गुंतवणुकीसाठी कोणालाही पैसे देण्याआधी खात्री करा.', 'पैसे गेले असतील तर 1930 वर कॉल करा किंवा cybercrime.gov.in वर तक्रार करा'),
    'ta': ('முதலீட்டுக்காக யாருக்கும் பணம் கொடுக்கும் முன் சரிபாருங்கள்.', 'பணம் போயிருந்தால், 1930-க்கு அழையுங்கள் அல்லது cybercrime.gov.in-ல் புகார் செய்யுங்கள்'),
    'te': ('పెట్టుబడి కోసం ఎవరికైనా డబ్బు ఇచ్చే ముందు ధృవీకరించండి.', 'డబ్బు పోయి ఉంటే, 1930కి కాల్ చేయండి లేదా cybercrime.gov.inలో ఫిర్యాదు చేయండి'),
    'kn': ('ಹೂಡಿಕೆಗಾಗಿ ಯಾರಿಗಾದರೂ ಹಣ ಕೊಡುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ.', 'ಹಣ ಹೋಗಿದ್ದರೆ, 1930ಕ್ಕೆ ಕರೆ ಮಾಡಿ ಅಥವಾ cybercrime.gov.in ನಲ್ಲಿ ದೂರು ನೀಡಿ'),
    'bn': ('বিনিয়োগের জন্য কাউকে টাকা দেওয়ার আগে যাচাই করুন।', 'টাকা চলে গিয়ে থাকলে 1930-এ ফোন করুন বা cybercrime.gov.in-এ অভিযোগ করুন'),
    'hinglish': ('Investment ke liye kisi ko paise dene se pehle verify karo.', 'Agar paise ja chuke hain, to 1930 pe call karo ya cybercrime.gov.in pe report karo'),
}


def fallback(band: Band, lang: Lang, unchecked: list[str]) -> tuple[str, str, list[NextStep]]:
    c = COPY[lang]
    headline = c[{'high_risk':0, 'caution':1, 'no_known_signals':2}[band]]
    explanation = (c[2] if band == 'no_known_signals' else c[4]) + (' ' + c[3] if unchecked else '')
    first, report = (NO_SIGNAL_STEPS[lang] if band == 'no_known_signals' else (c[5], c[7]))
    steps = [NextStep(text=first, url=None), NextStep(text=c[6], url='https://siportal.sebi.gov.in/intermediary/sebi-check'),
             NextStep(text=report, url='https://cybercrime.gov.in')]
    return headline, explanation, steps


UNREGISTERED = {
    'en': 'This website is not registered',
    'hi': 'यह वेबसाइट पंजीकृत नहीं है',
    'mr': 'या वेबसाइटची नोंदणी झालेली नाही',
    'ta': 'இந்த இணையதளம் பதிவு செய்யப்படவில்லை',
    'te': 'ఈ వెబ్‌సైట్ నమోదు కాలేదు',
    'kn': 'ಈ ವೆಬ್‌ಸೈಟ್ ನೋಂದಣಿಯಾಗಿಲ್ಲ',
    'bn': 'এই ওয়েবসাইটটি নিবন্ধিত নয়',
    'hinglish': 'Yeh website registered nahi hai',
}


def unregistered(domain: str, source_url: str, lang: Lang) -> Signal:
    from backend.schemas import Evidence
    return Signal(id='S3', label=UNREGISTERED[lang], points=0,
                  evidence=Evidence(kind='lookup', text=domain, source_url=source_url))


def localize(signals: list[Signal], lang: Lang) -> list[Signal]:
    if lang == 'en':
        return signals
    c = COPY[lang]
    result = []
    for s in signals:
        text = s.evidence.text
        if s.id == 'S1':
            text = c[9].format(facts=text.split(' does not ')[0])
        elif s.id == 'S2':
            pairs = [p.split(' is not ', 1) for p in text.split('; ')]
            text = '; '.join(c[10].format(domain=d, official=o) if o else d for d, o in ((p + [''])[:2] for p in pairs))
        elif s.id == 'S3':
            found = re.fullmatch(r'(.+): registered (\d+) days ago', text)
            text = c[11].format(domain=found[1], age=found[2]) if found else text
        elif s.id in ('S4','S5'):
            numbers = re.findall(r'\d+', text)
            text = c[12 if s.id == 'S4' else 13].format(facts=numbers[0] if numbers else '0')
        elif s.id == 'S7':
            text = c[14]
        result.append(s.model_copy(update={'label':c[8][int(s.id[1:]) - 1],
            'evidence':s.evidence.model_copy(update={'text':text})}))
    return result
