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
        ['Investment payment handle','Look-alike domain','New domain','Earlier reports','Similar script','Claims in the message','Phishing feed'],
        'This investment payment handle does not start with @valid: {facts}', '{facts} is not an official domain',
        '{facts} days since domain registration', '{facts} earlier checks linked', '{facts} earlier checks match this script',
        'A URL matches a verified online PhishTank report.'],
 'hi': ['पैसे न भेजें: जोखिम के कई संकेत', 'सावधान: पैसे भेजने से पहले जाँचें',
        'धोखाधड़ी के ज्ञात संकेत नहीं मिले। इससे असली होने का प्रमाण नहीं मिलता।', 'कुछ जाँचें पूरी नहीं हो सकीं।',
        'मिले जोखिम संकेतों के प्रमाण नीचे दिए गए हैं।', 'जाँच पूरी होने तक पैसे न भेजें।',
        'SEBI Check पर सत्यापित करें', '1930 या cybercrime.gov.in पर रिपोर्ट करें',
        ['निवेश भुगतान का UPI हैंडल','मिलता-जुलता डोमेन','नया डोमेन','पिछली रिपोर्टों से संबंध','मिलता-जुलता संदेश','संदेश में दावे','फ़िशिंग सूची'],
        'इस निवेश भुगतान के हैंडल की शुरुआत @valid से नहीं होती: {facts}', '{facts} आधिकारिक डोमेन नहीं है',
        'डोमेन पंजीकरण के बाद दिन: {facts}', 'जुड़ी पिछली जाँचें: {facts}', 'इसी संदेश से मिलती पिछली जाँचें: {facts}',
        'एक URL, PhishTank की सत्यापित सक्रिय फ़िशिंग रिपोर्ट से मेल खाता है।'],
 'mr': ['पैसे पाठवू नका: धोक्याचे अनेक संकेत', 'सावधान: पैसे पाठवण्यापूर्वी तपासा',
        'फसवणुकीचे ज्ञात संकेत आढळले नाहीत. यामुळे अस्सल असल्याचे सिद्ध होत नाही.', 'काही तपासण्या पूर्ण होऊ शकल्या नाहीत.',
        'आढळलेल्या धोक्यांच्या संकेतांचे पुरावे खाली दिले आहेत.', 'पडताळणी होईपर्यंत पैसे पाठवू नका.',
        'SEBI Check वर पडताळा', '1930 किंवा cybercrime.gov.in वर तक्रार करा',
        ['गुंतवणूक भरण्याचा UPI हँडल','सारखा दिसणारा डोमेन','नवीन डोमेन','आधीच्या तक्रारी','सारखा संदेश','संदेशातील दावे','फिशिंग यादी'],
        'या गुंतवणूक भरण्याच्या हँडलची सुरुवात @valid ने होत नाही: {facts}', '{facts} अधिकृत डोमेन नाही',
        'डोमेन नोंदणीनंतरचे दिवस: {facts}', 'जोडलेल्या आधीच्या तपासण्या: {facts}', 'या संदेशाशी जुळणाऱ्या आधीच्या तपासण्या: {facts}',
        'एक URL PhishTank मधील पडताळलेल्या सक्रिय फिशिंग नोंदीशी जुळतो.'],
 'ta': ['பணம் அனுப்ப வேண்டாம்: பல அபாய அறிகுறிகள்', 'எச்சரிக்கை: பணம் செலுத்தும் முன் சரிபார்க்கவும்',
        'அறியப்பட்ட மோசடி அறிகுறிகள் இல்லை. இது உண்மையானது என்பதற்கான சான்றல்ல.', 'சில சோதனைகளை முடிக்க முடியவில்லை.',
        'கண்டறியப்பட்ட அபாய அறிகுறிகளுக்கான சான்றுகள் கீழே உள்ளன.', 'சரிபார்க்கும் வரை பணம் அனுப்ப வேண்டாம்.',
        'SEBI Check மூலம் சரிபார்க்கவும்', '1930 அல்லது cybercrime.gov.in இல் புகாரளிக்கவும்',
        ['முதலீட்டுப் பணத்தின் UPI முகவரி','ஒத்த தோற்றமுள்ள இணைய முகவரி','புதிய இணைய முகவரி','முந்தைய புகார்கள்','ஒத்த செய்தி','செய்தியில் உள்ள கூற்றுகள்','ஃபிஷிங் பட்டியல்'],
        'இந்த முதலீட்டு UPI முகவரி @valid எனத் தொடங்கவில்லை: {facts}', '{facts} அதிகாரப்பூர்வ இணைய முகவரி அல்ல',
        'இணைய முகவரி பதிவு செய்யப்பட்டு கடந்த நாட்கள்: {facts}', 'இணைக்கப்பட்ட முந்தைய சோதனைகள்: {facts}', 'இந்தச் செய்தியுடன் பொருந்தும் முந்தைய சோதனைகள்: {facts}',
        'ஒரு URL, PhishTank இன் சரிபார்க்கப்பட்ட செயலில் உள்ள ஃபிஷிங் பதிவுடன் பொருந்துகிறது.'],
 'te': ['డబ్బు పంపవద్దు: పలు ప్రమాద సంకేతాలు', 'జాగ్రత్త: చెల్లించే ముందు తనిఖీ చేయండి',
        'తెలిసిన మోసపు సంకేతాలు లేవు. ఇది నిజమైనదని రుజువు కాదు.', 'కొన్ని తనిఖీలు పూర్తి కాలేదు.',
        'కనిపించిన ప్రమాద సంకేతాలకు ఆధారాలు క్రింద ఉన్నాయి.', 'నిర్ధారించే వరకు డబ్బు పంపవద్దు.',
        'SEBI Check లో ధృవీకరించండి', '1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి',
        ['పెట్టుబడి చెల్లింపు UPI చిరునామా','పోలి ఉన్న డొమైన్','కొత్త డొమైన్','గత నివేదికలు','పోలి ఉన్న సందేశం','సందేశంలోని వాదనలు','ఫిషింగ్ జాబితా'],
        'ఈ పెట్టుబడి చెల్లింపు చిరునామా @valid తో మొదలవదు: {facts}', '{facts} అధికారిక డొమైన్ కాదు',
        'డొమైన్ నమోదు తర్వాత రోజులు: {facts}', 'అనుసంధానమైన గత తనిఖీలు: {facts}', 'ఈ సందేశంతో సరిపోలిన గత తనిఖీలు: {facts}',
        'ఒక URL, PhishTank ధృవీకరించిన క్రియాశీల ఫిషింగ్ నివేదికతో సరిపోలింది.'],
 'kn': ['ಹಣ ಕಳುಹಿಸಬೇಡಿ: ಹಲವು ಅಪಾಯದ ಸಂಕೇತಗಳು', 'ಎಚ್ಚರಿಕೆ: ಪಾವತಿಸುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ',
        'ತಿಳಿದಿರುವ ವಂಚನೆ ಸಂಕೇತಗಳಿಲ್ಲ. ಇದು ನಿಜವೆಂಬುದಕ್ಕೆ ಪುರಾವೆಯಲ್ಲ.', 'ಕೆಲವು ಪರಿಶೀಲನೆಗಳನ್ನು ಪೂರ್ಣಗೊಳಿಸಲಾಗಲಿಲ್ಲ.',
        'ಕಂಡುಬಂದ ಅಪಾಯದ ಸಂಕೇತಗಳ ಪುರಾವೆಗಳು ಕೆಳಗಿವೆ.', 'ಪರಿಶೀಲಿಸುವವರೆಗೆ ಹಣ ಕಳುಹಿಸಬೇಡಿ.',
        'SEBI Check ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ', '1930 ಅಥವಾ cybercrime.gov.in ನಲ್ಲಿ ವರದಿ ಮಾಡಿ',
        ['ಹೂಡಿಕೆ ಪಾವತಿಯ UPI ವಿಳಾಸ','ಹೋಲುವ ಡೊಮೇನ್','ಹೊಸ ಡೊಮೇನ್','ಹಿಂದಿನ ವರದಿಗಳು','ಹೋಲುವ ಸಂದೇಶ','ಸಂದೇಶದ ಹೇಳಿಕೆಗಳು','ಫಿಶಿಂಗ್ ಪಟ್ಟಿ'],
        'ಈ ಹೂಡಿಕೆ ಪಾವತಿಯ ವಿಳಾಸ @valid ನಿಂದ ಆರಂಭವಾಗುವುದಿಲ್ಲ: {facts}', '{facts} ಅಧಿಕೃತ ಡೊಮೇನ್ ಅಲ್ಲ',
        'ಡೊಮೇನ್ ನೋಂದಣಿಯ ನಂತರದ ದಿನಗಳು: {facts}', 'ಸಂಬಂಧಿತ ಹಿಂದಿನ ಪರಿಶೀಲನೆಗಳು: {facts}', 'ಈ ಸಂದೇಶಕ್ಕೆ ಹೋಲುವ ಹಿಂದಿನ ಪರಿಶೀಲನೆಗಳು: {facts}',
        'ಒಂದು URL, PhishTank ನ ಪರಿಶೀಲಿತ ಸಕ್ರಿಯ ಫಿಶಿಂಗ್ ವರದಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ.'],
 'bn': ['টাকা পাঠাবেন না: একাধিক ঝুঁকির সংকেত', 'সতর্কতা: টাকা দেওয়ার আগে যাচাই করুন',
        'পরিচিত প্রতারণার সংকেত মেলেনি। এটি আসল হওয়ার প্রমাণ নয়।', 'কিছু পরীক্ষা সম্পূর্ণ করা যায়নি।',
        'পাওয়া ঝুঁকির সংকেতগুলির প্রমাণ নিচে দেওয়া আছে।', 'যাচাই না হওয়া পর্যন্ত টাকা পাঠাবেন না।',
        'SEBI Check-এ যাচাই করুন', '1930 বা cybercrime.gov.in-এ রিপোর্ট করুন',
        ['বিনিয়োগের UPI ঠিকানা','একই রকম দেখতে ডোমেন','নতুন ডোমেন','আগের রিপোর্ট','একই রকম বার্তা','বার্তার দাবি','ফিশিং তালিকা'],
        'এই বিনিয়োগের UPI ঠিকানা @valid দিয়ে শুরু হয় না: {facts}', '{facts} সরকারি ডোমেন নয়',
        'ডোমেন নিবন্ধনের পর দিন: {facts}', 'যুক্ত আগের পরীক্ষার সংখ্যা: {facts}', 'এই বার্তার সঙ্গে মেলা আগের পরীক্ষার সংখ্যা: {facts}',
        'একটি URL, PhishTank-এর যাচাই করা সক্রিয় ফিশিং রিপোর্টের সঙ্গে মিলেছে।'],
 'hinglish': ['Paise na bhejein: kai risk signals mile', 'Savdhaan: paise dene se pehle jaanchein',
        'Koi jaana-pehchana scam signal nahi mila. Isse asli hone ka saboot nahi milta.', 'Kuch jaanch poori nahi ho saki.',
        'Mile hue risk signals ke saboot neeche hain.', 'Verify hone tak paise na bhejein.',
        'SEBI Check par verify karein', '1930 ya cybercrime.gov.in par report karein',
        ['Investment payment UPI handle','Milta-julta domain','Naya domain','Purani reports se link','Milta-julta message','Message ke daave','Phishing list'],
        'Is investment payment handle ki shuruaat @valid se nahi hoti: {facts}', '{facts} official domain nahi hai',
        'Domain registration ke baad din: {facts}', 'Judi hui purani checks: {facts}', 'Is message se milti purani checks: {facts}',
        'Ek URL, PhishTank ki verified active phishing report se milta hai.'],
}


def fallback(band: Band, lang: Lang, unchecked: list[str]) -> tuple[str, str, list[NextStep]]:
    c = COPY[lang]
    headline = c[{'high_risk':0, 'caution':1, 'no_known_signals':2}[band]]
    explanation = (c[2] if band == 'no_known_signals' else c[4]) + (' ' + c[3] if unchecked else '')
    steps = [NextStep(text=c[5], url=None), NextStep(text=c[6], url='https://siportal.sebi.gov.in/intermediary/sebi-check'),
             NextStep(text=c[7], url='https://cybercrime.gov.in')]
    return headline, explanation, steps


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
            text = '; '.join(c[10].format(facts=p.replace(' is not ', ' ≠ ')) for p in text.split('; '))
        elif s.id == 'S3':
            text = c[11].format(facts=text.replace(': registered ', ': ').replace(' days ago', ''))
        elif s.id in ('S4','S5'):
            numbers = re.findall(r'\d+', text)
            text = c[12 if s.id == 'S4' else 13].format(facts=numbers[0] if numbers else '0')
        elif s.id == 'S7':
            text = c[14]
        result.append(s.model_copy(update={'label':c[8][int(s.id[1:]) - 1],
            'evidence':s.evidence.model_copy(update={'text':text})}))
    return result
