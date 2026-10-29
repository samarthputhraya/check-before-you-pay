// UI text. The verdict itself comes back from the server in the chosen language; these strings are only
// the app's own labels. Languages without a table here fall back to English for the labels.
import { savedLang } from './session.js';

export const LANGS = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'हिन्दी' },
  { code: 'hinglish', name: 'Hinglish' },
  { code: 'mr', name: 'मराठी' },
  { code: 'ta', name: 'தமிழ்' },
  { code: 'te', name: 'తెలుగు' },
  { code: 'kn', name: 'ಕನ್ನಡ' },
  { code: 'bn', name: 'বাংলা' },
];

const EN = {
  tagline: 'Forward any investment tip or payment request and see the red flags in 5 seconds.',
  language: 'Language',
  inputLabel: 'Paste the message, link or UPI ID',
  placeholder: 'For example: VIP Stock Tips. 300% guaranteed returns. Pay ₹50,000 to …',
  addScreenshot: 'Add screenshot',
  addVoice: 'Add voice note',
  remove: 'Remove',
  submit: 'Check before you pay',
  checking: 'Checking… usually under 5 seconds',
  privacy: "We don't store your message unless you choose to report it.",
  emptyInput: 'Paste a message, or add a screenshot or a voice note.',
  tooLong: 'Messages can be at most 5,000 characters.',
  fileTooBig: 'Files can be at most 5 MB.',
  imageType: 'Screenshots must be PNG or JPEG.',
  audioType: 'Voice notes must be OGG, OPUS, M4A or MP3.',
  readFailed: 'Could not read that file. Please try another one.',
  tryAgain: 'Try again',
  band: {
    high_risk: 'High risk',
    caution: 'Caution',
    no_known_signals: 'No known scam signals',
  },
  noProof: "This doesn't prove it's genuine.",
  signals: 'Risk signals',
  ring: (c, r) => `Linked to ${c} earlier check${c === 1 ? '' : 's'} and ${r} report${r === 1 ? '' : 's'}`,
  via: {
    same_upi: 'same UPI ID',
    same_phone: 'same phone number',
    same_domain: 'same website',
    same_group_link: 'same group link',
    same_wallet: 'same wallet',
    same_script: 'same message script',
  },
  through: 'through',
  nextSteps: 'What to do',
  unchecked: (list) => `Some checks couldn't run (${list}), so they added 0 points.`,
  checks: {
    claims: 'claims in the message',
    domain_age: 'website age',
    links: 'earlier reports',
    script_similarity: 'similar messages',
    phishing_feed: 'phishing list',
    transcription: 'reading the file',
  },
  transcript: 'What we read',
  share: 'Share with family',
  copied: 'Link copied',
  another: 'Check another message',
  sample: 'Sample result: the real check is still being built, so this verdict is an example.',
  soon: 'This page is coming soon.',
  back: 'Back to the check',
  errors: {
    empty_input: 'Paste a message, or add a screenshot or a voice note.',
    input_too_large: 'That is too large. Messages can be 5,000 characters and files 5 MB.',
    unsupported_media: 'That file type is not supported. Use PNG or JPEG screenshots, or OGG, M4A or MP3 voice notes.',
    rate_limited: 'Too many checks in a short time. Please wait a few minutes and try again.',
    timeout: 'This is taking too long. Check your connection and try again.',
    network: 'Could not reach the server. Check your connection and try again.',
    internal_error: 'Something went wrong on our side. Please try again.',
    check_unavailable: 'The check is unavailable right now. Please try again in a minute.',
  },
};

const HI = {
  ...EN,
  tagline: 'कोई भी निवेश टिप या पैसे की माँग यहाँ भेजें और 5 सेकंड में ख़तरे के संकेत देखें।',
  language: 'भाषा',
  inputLabel: 'मैसेज, लिंक या UPI आईडी यहाँ पेस्ट करें',
  placeholder: 'जैसे: VIP Stock Tips. 300% गारंटीड रिटर्न। ₹50,000 भेजें …',
  addScreenshot: 'स्क्रीनशॉट जोड़ें',
  addVoice: 'वॉइस नोट जोड़ें',
  remove: 'हटाएँ',
  submit: 'पैसे भेजने से पहले जाँचें',
  checking: 'जाँच हो रही है… आमतौर पर 5 सेकंड से कम',
  privacy: 'जब तक आप रिपोर्ट न करें, हम आपका मैसेज सेव नहीं करते।',
  emptyInput: 'कोई मैसेज पेस्ट करें, या स्क्रीनशॉट या वॉइस नोट जोड़ें।',
  tooLong: 'मैसेज 5,000 अक्षरों से लंबा नहीं हो सकता।',
  fileTooBig: 'फ़ाइल 5 MB से बड़ी नहीं हो सकती।',
  imageType: 'स्क्रीनशॉट PNG या JPEG होना चाहिए।',
  audioType: 'वॉइस नोट OGG, OPUS, M4A या MP3 होना चाहिए।',
  readFailed: 'यह फ़ाइल नहीं पढ़ी जा सकी। कोई दूसरी फ़ाइल आज़माएँ।',
  tryAgain: 'फिर से कोशिश करें',
  band: {
    high_risk: 'ज़्यादा ख़तरा',
    caution: 'सावधान',
    no_known_signals: 'कोई जाना-पहचाना संकेत नहीं',
  },
  noProof: 'इसका मतलब यह नहीं कि यह असली है।',
  signals: 'ख़तरे के संकेत',
  ring: (c, r) => `पहले की ${c} जाँचों और ${r} रिपोर्टों से जुड़ा`,
  via: {
    same_upi: 'वही UPI आईडी',
    same_phone: 'वही फ़ोन नंबर',
    same_domain: 'वही वेबसाइट',
    same_group_link: 'वही ग्रुप लिंक',
    same_wallet: 'वही वॉलेट',
    same_script: 'वही मैसेज',
  },
  through: 'इसके ज़रिए:',
  nextSteps: 'अब क्या करें',
  unchecked: (list) => `कुछ जाँचें नहीं हो सकीं (${list}), इसलिए उनके 0 अंक जुड़े।`,
  checks: {
    claims: 'मैसेज के दावे',
    domain_age: 'वेबसाइट की उम्र',
    links: 'पिछली रिपोर्टें',
    script_similarity: 'मिलते-जुलते मैसेज',
    phishing_feed: 'फ़िशिंग सूची',
    transcription: 'फ़ाइल पढ़ना',
  },
  transcript: 'हमने यह पढ़ा',
  share: 'परिवार को भेजें',
  copied: 'लिंक कॉपी हो गया',
  another: 'दूसरा मैसेज जाँचें',
  sample: 'नमूना नतीजा: असली जाँच अभी बन रही है, इसलिए यह सिर्फ़ एक उदाहरण है।',
  soon: 'यह पेज जल्द आ रहा है।',
  back: 'जाँच पर वापस जाएँ',
  errors: {
    empty_input: 'कोई मैसेज पेस्ट करें, या स्क्रीनशॉट या वॉइस नोट जोड़ें।',
    input_too_large: 'यह बहुत बड़ा है। मैसेज 5,000 अक्षर और फ़ाइल 5 MB तक हो सकती है।',
    unsupported_media: 'यह फ़ाइल टाइप नहीं चलता। PNG या JPEG स्क्रीनशॉट, या OGG, M4A या MP3 वॉइस नोट भेजें।',
    rate_limited: 'थोड़े समय में बहुत ज़्यादा जाँचें हो गईं। कुछ मिनट रुककर फिर कोशिश करें।',
    timeout: 'इसमें बहुत समय लग रहा है। अपना इंटरनेट देखें और फिर कोशिश करें।',
    network: 'सर्वर से जुड़ नहीं पाए। अपना इंटरनेट देखें और फिर कोशिश करें।',
    internal_error: 'हमारी तरफ़ से कुछ गड़बड़ हुई। फिर से कोशिश करें।',
    check_unavailable: 'अभी जाँच नहीं हो पा रही। एक मिनट बाद फिर कोशिश करें।',
  },
};

const TABLES = { en: EN, hi: HI };

export function strings(lang) {
  return TABLES[lang] || EN;
}

/** The language the labels are actually shown in (for <html lang>, so screen readers pick the right voice). */
export function uiLang(lang) {
  return TABLES[lang] ? lang : 'en';
}

/** BCP 47 tag for content written in `lang` (Hinglish is Hindi in Latin script). */
export function contentLang(lang) {
  return lang === 'hinglish' ? 'hi-Latn' : lang;
}

/** A server or network error in the user's language, falling back to the server's own message. */
export function errorText(t, err) {
  return (err && t.errors[err.code]) || (err && err.message) || t.errors.internal_error;
}

export function defaultLang() {
  const saved = savedLang();
  if (saved && LANGS.some((l) => l.code === saved)) return saved;
  const nav = (navigator.language || 'en').toLowerCase().split('-')[0];
  return LANGS.some((l) => l.code === nav) ? nav : 'en';
}
