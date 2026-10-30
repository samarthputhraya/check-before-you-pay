// Public numbers page (/stats). Everything shown comes from /api/stats, which excludes labelled sample data.
import { useEffect, useState } from 'preact/hooks';
import { apiFetch } from './api.js';
import { html } from './html.js';
import { defaultLang, LANGS, uiLang } from './i18n.js';

const REFRESH_MS = 30000;

const COPY = {
  en: {
    title: 'Live numbers',
    intro: 'Every number here comes from people using this site. Sample data is left out.',
    loading: 'Loading the numbers…',
    error: "Couldn't load the numbers. Check your connection and try again.",
    retry: 'Try again',
    empty: 'No checks yet. Be the first to check a message.',
    check: 'Check a message',
    users: 'People who visited',
    checks: 'Messages checked',
    reports: 'Reports sent',
    rings: 'Linked groups of high-risk checks',
    quiz: 'Quiz plays',
    shared: 'Verdicts shared',
    kFactor: 'New people per sharer',
    speed: 'Typical check time',
    slow: 'Slowest 1 in 20 checks',
    languages: 'Languages used',
    updated: (time) => `Updated ${time}. Refreshes every 30 seconds.`,
    seconds: (ms) => (ms < 100 ? '<0.1 s' : `${(ms / 1000).toFixed(1)} s`),
  },
  hi: {
    title: 'लाइव आंकड़े',
    intro: 'ये सारे आंकड़े इस साइट के असली इस्तेमाल से आते हैं। नमूना डेटा शामिल नहीं है।',
    loading: 'आंकड़े लोड हो रहे हैं…',
    error: 'आंकड़े लोड नहीं हो सके। इंटरनेट देखें और फिर कोशिश करें।',
    retry: 'फिर कोशिश करें',
    empty: 'अभी तक कोई जाँच नहीं हुई। पहला मैसेज आप जाँचें।',
    check: 'मैसेज जाँचें',
    users: 'साइट पर आए लोग',
    checks: 'जाँचे गए मैसेज',
    reports: 'भेजी गई रिपोर्टें',
    rings: 'ज़्यादा ख़तरे वाली जुड़ी जाँचों के समूह',
    quiz: 'क्विज़ खेली गई',
    shared: 'शेयर किए गए नतीजे',
    kFactor: 'हर शेयर करने वाले से आए नए लोग',
    speed: 'आम तौर पर जाँच का समय',
    slow: 'सबसे धीमी 20 में से 1 जाँच',
    languages: 'इस्तेमाल हुई भाषाएँ',
    updated: (time) => `${time} पर अपडेट हुआ। हर 30 सेकंड में ताज़ा होता है।`,
    seconds: (ms) => (ms < 100 ? '<0.1 सेकंड' : `${(ms / 1000).toFixed(1)} सेकंड`),
  },
  mr: {
    title: 'लाइव्ह आकडे',
    intro: 'इथला प्रत्येक आकडा ही साइट वापरणाऱ्या लोकांकडून येतो. नमुना डेटा धरलेला नाही.',
    loading: 'आकडे लोड होत आहेत…',
    error: 'आकडे लोड झाले नाहीत. इंटरनेट तपासा आणि पुन्हा प्रयत्न करा.',
    retry: 'पुन्हा प्रयत्न करा',
    empty: 'अजून एकही तपासणी झालेली नाही. पहिला मेसेज तुम्ही तपासा.',
    check: 'मेसेज तपासा',
    users: 'साइटला भेट दिलेले लोक',
    checks: 'तपासलेले मेसेज',
    reports: 'पाठवलेले रिपोर्ट',
    rings: 'जास्त धोक्याच्या जोडलेल्या तपासण्यांचे गट',
    quiz: 'क्विझ किती वेळा खेळली',
    shared: 'शेअर केलेले निकाल',
    kFactor: 'प्रत्येक शेअर करणाऱ्यामुळे आलेले नवीन लोक',
    speed: 'साधारण तपासणीचा वेळ',
    slow: '20 पैकी सर्वात हळू 1 तपासणी',
    languages: 'वापरलेल्या भाषा',
    updated: (time) => `${time} ला अपडेट झाले. दर 30 सेकंदांनी ताजे होते.`,
    seconds: (ms) => (ms < 100 ? '<0.1 सेकंद' : `${(ms / 1000).toFixed(1)} सेकंद`),
  },
  hinglish: {
    title: 'Live numbers',
    intro: 'Yahan ka har number is site ko use karne waalon se aata hai. Sample data shaamil nahi hai.',
    loading: 'Numbers load ho rahe hain…',
    error: 'Numbers load nahi hue. Internet check karo aur phir try karo.',
    retry: 'Phir try karo',
    empty: 'Abhi tak koi check nahi hua. Pehla message aap check karo.',
    check: 'Message check karo',
    users: 'Site pe aaye log',
    checks: 'Check kiye gaye messages',
    reports: 'Bheji gayi reports',
    rings: 'High-risk checks ke jude hue groups',
    quiz: 'Quiz kitni baar khela gaya',
    shared: 'Share kiye gaye verdicts',
    kFactor: 'Har share karne waale se aaye naye log',
    speed: 'Aam taur pe check ka time',
    slow: '20 mein se sabse dheemi 1 check',
    languages: 'Use hui bhashayein',
    updated: (time) => `${time} pe update hua. Har 30 second mein refresh hota hai.`,
    seconds: (ms) => (ms < 100 ? '<0.1 s' : `${(ms / 1000).toFixed(1)} s`),
  },
};
const TIME_LOCALE = { hi: 'hi-IN', mr: 'mr-IN' };

const number = new Intl.NumberFormat('en-IN');
const languageName = (code) => (LANGS.find((l) => l.code === code) || { name: code }).name;

function Tile({ label, value }) {
  return html`<div class="stat"><p class="stat-value">${value}</p><p class="stat-label">${label}</p></div>`;
}

export function StatsPage() {
  const lang = COPY[defaultLang()] ? defaultLang() : 'en';
  const c = COPY[lang];
  const [state, setState] = useState({ status: 'loading' });
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    const load = () => apiFetch('/api/stats')
      .then(({ data }) => active && setState({ status: 'ready', stats: data }))
      .catch((error) => active && setState((prev) => (prev.status === 'ready' ? prev : { status: 'error', error })));
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => { active = false; clearInterval(timer); };
  }, [reload]);

  let body;
  if (state.status === 'loading') {
    body = html`<div class="card empty" role="status"><span class="spinner" aria-hidden="true"></span><p>${c.loading}</p></div>`;
  } else if (state.status === 'error') {
    body = html`<div class="card" role="alert"><p class="error">${c.error}</p>
      <button class="button primary block" onClick=${() => { setState({ status: 'loading' }); setReload((n) => n + 1); }}>${c.retry}</button></div>`;
  } else if (!state.stats.checks) {
    body = html`<div class="card empty"><p>${c.empty}</p><a class="button primary" href="/">${c.check}</a></div>`;
  } else {
    const s = state.stats;
    const langs = Object.entries(s.languages || {}).sort((a, b) => b[1] - a[1]);
    const top = langs.length ? langs[0][1] : 1;
    body = html`
      <section class="stat-grid" aria-live="polite">
        <${Tile} label=${c.users} value=${number.format(s.users)} />
        <${Tile} label=${c.checks} value=${number.format(s.checks)} />
        <${Tile} label=${c.reports} value=${number.format(s.reports)} />
        <${Tile} label=${c.rings} value=${number.format(s.rings)} />
        ${typeof s.quiz_plays === 'number' && html`<${Tile} label=${c.quiz} value=${number.format(s.quiz_plays)} />`}
        <${Tile} label=${c.shared} value=${`${Math.round(s.share_rate * 100)}%`} />
        <${Tile} label=${c.kFactor} value=${s.k_factor.toFixed(2)} />
        <${Tile} label=${c.speed} value=${c.seconds(s.p50_ms)} />
        <${Tile} label=${c.slow} value=${c.seconds(s.p95_ms)} />
      </section>
      ${langs.length > 0 && html`<section class="card stat-langs">
        <h2>${c.languages}</h2>
        <ul>${langs.map(([code, n]) => html`<li>
          <span class="stat-lang-name">${languageName(code)}</span>
          <span class="stat-bar" aria-hidden="true"><span style=${`width:${Math.max(4, Math.round((n / top) * 100))}%`}></span></span>
          <span class="stat-lang-count">${number.format(n)}</span>
        </li>`)}</ul>
      </section>`}
      <p class="fine">${c.updated(new Date(s.updated_at).toLocaleTimeString(TIME_LOCALE[lang] || 'en-IN', { hour: '2-digit', minute: '2-digit' }))}</p>`;
  }

  return html`<main class="page stats-page" lang=${uiLang(lang)}>
    <h1>${c.title}</h1>
    <p class="muted">${c.intro}</p>
    ${body}
  </main>`;
}
