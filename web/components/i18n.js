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
  transcript: 'What we read',
  share: 'Share with family',
  copied: 'Link copied',
  another: 'Check another message',
  sample: 'Sample result: the real check is still being built, so this verdict is an example.',
  soon: 'This page is coming soon.',
  back: 'Back to the check',
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
  transcript: 'हमने यह पढ़ा',
  share: 'परिवार को भेजें',
  copied: 'लिंक कॉपी हो गया',
  another: 'दूसरा मैसेज जाँचें',
  sample: 'नमूना नतीजा: असली जाँच अभी बन रही है, इसलिए यह सिर्फ़ एक उदाहरण है।',
  soon: 'यह पेज जल्द आ रहा है।',
  back: 'जाँच पर वापस जाएँ',
};

const TABLES = { en: EN, hi: HI };

export function strings(lang) {
  return TABLES[lang] || EN;
}

export function defaultLang() {
  const saved = savedLang();
  if (saved && LANGS.some((l) => l.code === saved)) return saved;
  const nav = (navigator.language || 'en').toLowerCase().split('-')[0];
  return LANGS.some((l) => l.code === nav) ? nav : 'en';
}
