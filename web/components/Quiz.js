import { useEffect, useState } from 'preact/hooks';
import { apiFetch } from './api.js';
import { html } from './html.js';
import { defaultLang, LANGS, uiLang } from './i18n.js';
import { anonId, track } from './session.js';

const QUIZ_LANGS = ['en', 'hi', 'hinglish', 'mr']; // the languages with a quiz set; others start in English

const COPY = {
  en: {
    title: 'Spot the scam', intro: 'Read each message and decide: Scam or Genuine? All messages are examples written by us.', loading: 'Loading quiz…',
    empty: 'There are no quiz messages available right now.', question: (n, total) => `Message ${n} of ${total}`,
    scam: 'Scam', genuine: 'Genuine', submit: 'See my score', scoring: 'Checking your answers…',
    score: (score, total) => `You spotted ${score}/${total}.`, sample: 'Sample quiz result', share: 'Share score', youSaid: (answer) => `You said ${answer}`, answer: 'Answer',
    shareText: (score, total) => `I spotted ${score}/${total}. Can you?`, again: 'Play again', back: 'Back to checking',
    error: 'Could not load the quiz. Check your connection and try again.', answerError: 'Could not save your answers. Please try again.', retry: 'Try again', explanation: 'Why',
  },
  hinglish: {
    title: 'Scam pehchano', intro: 'Har message padho aur batao: Scam ya Genuine? Saare messages humne example ke liye likhe hain.', loading: 'Quiz load ho raha hai…',
    empty: 'Abhi koi quiz message nahi hai.', question: (n, total) => `Message ${n} / ${total}`,
    scam: 'Scam', genuine: 'Genuine', submit: 'Mera score dekho', scoring: 'Aapke jawab check ho rahe hain…',
    score: (score, total) => `Aapne ${score}/${total} pehchane.`, sample: 'Sample quiz result', share: 'Score share karo', youSaid: (answer) => `Aapne ${answer} chuna`, answer: 'Sahi jawab',
    shareText: (score, total) => `Maine ${score}/${total} pehchane. Kya aap pehchan sakte ho?`, again: 'Phir khelo', back: 'Check pe wapas jao',
    error: 'Quiz load nahi hua. Internet check karo aur phir try karo.', answerError: 'Jawab save nahi hue. Phir try karo.', retry: 'Phir try karo', explanation: 'Kyun',
  },
  hi: {
    title: 'धोखाधड़ी पहचानें', intro: 'हर संदेश पढ़ें और चुनें: धोखाधड़ी या सही? ये सभी संदेश उदाहरण हैं, जो हमने लिखे हैं।', loading: 'क्विज़ लोड हो रही है…',
    empty: 'अभी कोई क्विज़ संदेश उपलब्ध नहीं है।', question: (n, total) => `संदेश ${n} / ${total}`,
    scam: 'धोखाधड़ी', genuine: 'सही', submit: 'मेरा स्कोर देखें', scoring: 'जवाब जाँचे जा रहे हैं…',
    score: (score, total) => `आपने ${score}/${total} पहचाने।`, sample: 'नमूना क्विज़ नतीजा', share: 'स्कोर साझा करें', youSaid: (answer) => `आपने ${answer} चुना`, answer: 'सही जवाब',
    shareText: (score, total) => `मैंने ${score}/${total} पहचाने। क्या आप पहचान सकते हैं?`, again: 'फिर खेलें', back: 'जाँच पर वापस जाएँ',
    error: 'क्विज़ लोड नहीं हो सकी। इंटरनेट देखें और फिर कोशिश करें।', answerError: 'जवाब सेव नहीं हो सके। फिर कोशिश करें।', retry: 'फिर कोशिश करें', explanation: 'क्यों',
  },
  mr: {
    title: 'फसवणूक ओळखा', intro: 'प्रत्येक संदेश वाचा आणि ठरवा: फसवणूक की खरा? हे सर्व संदेश आम्ही लिहिलेली उदाहरणे आहेत.', loading: 'क्विझ लोड होत आहे…',
    empty: 'सध्या क्विझचे संदेश उपलब्ध नाहीत.', question: (n, total) => `संदेश ${n} / ${total}`,
    scam: 'फसवणूक', genuine: 'खरा', submit: 'माझा गुण पाहा', scoring: 'तुमची उत्तरे तपासत आहे…',
    score: (score, total) => `तुम्ही ${score}/${total} ओळखले.`, sample: 'नमुना क्विझ निकाल', share: 'गुण शेअर करा', youSaid: (answer) => `तुम्ही ${answer} निवडले`, answer: 'योग्य उत्तर',
    shareText: (score, total) => `मी ${score}/${total} ओळखले. तुम्ही ओळखू शकता का?`, again: 'पुन्हा खेळा', back: 'तपासणीवर परत जा',
    error: 'क्विझ लोड झाली नाही. इंटरनेट तपासून पुन्हा प्रयत्न करा.', answerError: 'तुमची उत्तरे जतन झाली नाहीत. पुन्हा प्रयत्न करा.', retry: 'पुन्हा प्रयत्न करा', explanation: 'का',
  },
};

function text(lang, key, ...args) {
  const table = COPY[lang] || COPY.en;
  const value = table[key];
  return typeof value === 'function' ? value(...args) : value;
}

function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[char]);
}

async function createQuizCard(score, total, caption) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
    <rect width="1080" height="1350" fill="#f6f7f5"/><rect x="48" y="48" width="984" height="1254" rx="32" fill="#fff" stroke="#d9dfda" stroke-width="3"/>
    <rect x="48" y="48" width="984" height="20" rx="10" fill="#0b6839"/><text x="92" y="170" class="brand">Check Before You Pay</text>
    <text x="92" y="420" class="score">${Number(score)}/${Number(total)}</text><text x="92" y="540" class="caption">${escapeXml(caption)}</text>
    <line x1="92" y1="1110" x2="988" y2="1110" stroke="#d9dfda" stroke-width="3"/><text x="92" y="1190" class="footer">Check evidence before you pay.</text>
    <text x="92" y="1250" class="url">${escapeXml(location.host)}</text>
    <style>text{font-family:system-ui,-apple-system,'Segoe UI',sans-serif}.brand{font-size:38px;font-weight:700;fill:#16201b}.score{font-size:180px;font-weight:800;fill:#0b6839}.caption{font-size:48px;font-weight:600;fill:#16201b}.footer{font-size:30px;fill:#344054}.url{font-size:26px;fill:#5b675f}</style>
  </svg>`;
  const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
  try {
    const image = new Image();
    await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; image.src = url; });
    const canvas = document.createElement('canvas');
    canvas.width = 1080; canvas.height = 1350;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas is unavailable.');
    context.drawImage(image, 0, 0);
    const blob = await new Promise((resolve, reject) => canvas.toBlob((value) => value ? resolve(value) : reject(new Error('Could not render the share card.')), 'image/png'));
    return new File([blob], 'quiz-score.png', { type: 'image/png' });
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function QuizPage() {
  const [lang, setLang] = useState(() => (QUIZ_LANGS.includes(defaultLang()) ? defaultLang() : 'en'));
  const [state, setState] = useState({ status: 'loading' });
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [reload, setReload] = useState(0);

  useEffect(() => {
    document.documentElement.lang = uiLang(lang);
    let active = true;
    setState({ status: 'loading' });
    setAnswers({});
    setIndex(0);
    apiFetch(`/api/quiz?lang=${encodeURIComponent(lang)}`)
      .then(({ data, sample }) => active && setState({ status: 'ready', quiz: data, sample }))
      .catch((error) => active && setState({ status: 'error', error }));
    return () => { active = false; };
  }, [lang, reload]);

  async function answer(value) {
    const next = { ...answers, [state.quiz.items[index].id]: value };
    setAnswers(next);
    if (index + 1 < state.quiz.items.length) {
      setIndex(index + 1);
      return;
    }
    setState({ ...state, status: 'submitting' });
    try {
      const { data } = await apiFetch('/api/quiz/answer', {
        method: 'POST',
        body: { quiz_id: state.quiz.quiz_id, anon_id: anonId, answers: next },
      });
      track('quiz_done', { props: { score: data.score } });
      setState({ status: 'done', quiz: state.quiz, result: data, answers: next, sample: state.sample });
    } catch (error) {
      setState({ status: 'answer_error', quiz: state.quiz, sample: state.sample, error });
    }
  }

  async function share() {
    const { score, total, share: shareInfo } = state.result;
    const caption = text(lang, 'shareText', score, total);
    try {
      if (navigator.share) {
        let file;
        try { file = await createQuizCard(score, total, caption); } catch { file = null; }
        const payload = { title: shareInfo.card_title, text: shareInfo.card_title, url: shareInfo.url };
        if (file && navigator.canShare?.({ files: [file] })) payload.files = [file];
        await navigator.share(payload);
        track('quiz_shared', { props: { score } });
        return;
      }
    } catch (error) {
      if (error?.name === 'AbortError') return;
    }
    const url = `https://wa.me/?text=${encodeURIComponent(`${shareInfo.card_title}\n${shareInfo.url}`)}`;
    const opened = window.open(url, '_blank', 'noopener');
    if (opened) track('quiz_shared', { props: { score } });
  }

  function restart() {
    setAnswers({});
    setIndex(0);
    setState({ status: 'loading' });
    setReload((value) => value + 1);
  }

  const label = (key, ...args) => text(lang, key, ...args);
  const languageOptions = LANGS.filter(({ code }) => QUIZ_LANGS.includes(code));
  const quiz = state.quiz;

  return html`<main class="page quiz-page" lang=${uiLang(lang)}>
    <div class="field-row"><label class="label" for="quiz-language">${lang === 'hi' || lang === 'mr' ? 'भाषा' : lang === 'hinglish' ? 'Bhasha' : 'Language'}</label>
      <select id="quiz-language" value=${lang} disabled=${state.status === 'loading' || state.status === 'submitting'} onChange=${(event) => setLang(event.currentTarget.value)}>
        ${languageOptions.map((option) => html`<option value=${option.code}>${option.name}</option>`)}
      </select></div>
    <h1>${label('title')}</h1><p class="muted">${label('intro')}</p>
    ${state.status === 'loading' || state.status === 'submitting'
      ? html`<div class="card empty" role="status"><span class="spinner" aria-hidden="true"></span><p>${state.status === 'submitting' ? label('scoring') : label('loading')}</p></div>`
      : state.status === 'error'
        ? html`<div class="card" role="alert"><p class="error">${label('error')}</p><button class="button primary block" onClick=${() => setReload((value) => value + 1)}>${label('retry')}</button></div>`
        : !quiz?.items?.length
          ? html`<div class="card empty"><p>${label('empty')}</p></div>`
          : state.status === 'done'
            ? html`<section class="card quiz-result" aria-live="polite">
                ${state.sample && html`<p class="sample-note">${label('sample')}</p>`}
                <p class="quiz-score">${label('score', state.result.score, state.result.total)}</p>
                <ol class="quiz-review">${state.result.results.map((item) => html`<li class=${item.correct ? 'correct' : 'incorrect'}>
                  <strong>${label('youSaid', state.answers[item.id] === 'scam' ? label('scam') : label('genuine'))} · ${label('answer')}: ${item.answer === 'scam' ? label('scam') : label('genuine')}</strong><p>${item.why}</p></li>`)}</ol>
                <div class="quiz-actions"><button class="button primary" onClick=${share}>${label('share')}</button><button class="button secondary" onClick=${restart}>${label('again')}</button></div>
              </section>`
            : state.status === 'answer_error'
              ? html`<div class="card" role="alert"><p class="error">${label('answerError')}</p><button class="button primary block" onClick=${() => answer(answers[quiz.items[index].id])}>${label('retry')}</button></div>`
              : html`<section class="card quiz-question" aria-live="polite">
                  ${state.sample && html`<p class="sample-note">${label('sample')}</p>`}
                  <p class="muted">${label('question', index + 1, quiz.items.length)}</p>
                  <progress max=${quiz.items.length} value=${index + 1} aria-label=${label('question', index + 1, quiz.items.length)}></progress>
                  <blockquote>${quiz.items[index].text}</blockquote>
                  ${quiz.items[index].image_url && html`<img class="quiz-image" src=${quiz.items[index].image_url} alt="" />`}
                  <div class="quiz-actions">
                    <button class="button secondary" onClick=${() => answer('scam')}>${label('scam')}</button>
                    <button class="button primary" onClick=${() => answer('genuine')}>${label('genuine')}</button>
                  </div>
                </section>`}
    <p class="quiz-back"><a href="/">${label('back')}</a></p>
  </main>`;
}
