// /pricing: plans from /api/plans, Dodo's hosted checkout via /api/checkout, and the order status after Dodo sends
// the buyer back to /pricing?order=… . Only Dodo's signed webhook marks an order paid; this page just asks.
import { useEffect, useRef, useState } from 'preact/hooks';
import { apiFetch } from './api.js';
import { html } from './html.js';
import { defaultLang, errorText, strings, uiLang } from './i18n.js';
import { anonId, track } from './session.js';

const POLL_MS = 2000;
const POLL_FOR_MS = 60000;
const PAGE_LANGS = ['en', 'hi', 'hinglish', 'mr'];

const COPY = {
  en: {
    title: 'Plans',
    intro: 'Checking a message is free for everyone, and it stays free. A plan pays for the checker and gives your phone more checks.',
    testMode: 'Test mode: no real money is charged. Use the test card Dodo shows on its checkout page.',
    loading: 'Loading plans…',
    loadError: "Couldn't load the plans. Check your connection and try again.",
    retry: 'Try again',
    perMonth: '/month',
    free: { name: 'Free', price: '₹0', points: ['Check messages, links, UPI IDs, screenshots and voice notes', '8 languages', 'Share the verdict with family, report scams', '30 checks an hour'] },
    family: ['Everything in Free', '300 checks an hour on this phone', 'Keeps the checker free for every family'],
    api: ['The same check from your app, before a payment leaves', 'For brokers, fintechs and banks'],
    checkFree: 'Check a message',
    buy: (name) => `Get ${name}`,
    opening: 'Opening checkout…',
    soon: 'Coming soon',
    paused: 'Payments are paused right now. Checking stays free; please try again later.',
    order: {
      pending: 'Confirming your payment with Dodo…',
      paid: 'Payment received. Thank you! This phone now gets 300 checks an hour.',
      failed: "The payment didn't go through, and you weren't charged. You can try again.",
      slow: "We haven't heard back from Dodo yet. If you paid, it will show here within a few minutes.",
      unknown: "We couldn't find that order.",
      check: 'Check again',
    },
  },
  hi: {
    title: 'प्लान',
    intro: 'मैसेज की जाँच सबके लिए मुफ़्त है और मुफ़्त ही रहेगी। प्लान से यह सेवा चलती है और आपके फ़ोन को ज़्यादा जाँचें मिलती हैं।',
    testMode: 'टेस्ट मोड: कोई असली पैसा नहीं कटेगा। Dodo के चेकआउट पेज पर दिखाया गया टेस्ट कार्ड इस्तेमाल करें।',
    loading: 'प्लान लोड हो रहे हैं…',
    loadError: 'प्लान लोड नहीं हो सके। इंटरनेट देखें और फिर कोशिश करें।',
    retry: 'फिर कोशिश करें',
    perMonth: '/महीना',
    free: { name: 'मुफ़्त', price: '₹0', points: ['मैसेज, लिंक, UPI आईडी, स्क्रीनशॉट और वॉइस नोट की जाँच', '8 भाषाएँ', 'नतीजा परिवार को भेजें, धोखाधड़ी रिपोर्ट करें', 'हर घंटे 30 जाँचें'] },
    family: ['मुफ़्त प्लान की सारी सुविधाएँ', 'इस फ़ोन पर हर घंटे 300 जाँचें', 'हर परिवार के लिए जाँच मुफ़्त बनी रहती है'],
    api: ['पैसे जाने से पहले आपके ऐप से वही जाँच', 'ब्रोकर, फ़िनटेक और बैंकों के लिए'],
    checkFree: 'मैसेज जाँचें',
    buy: (name) => `${name} लें`,
    opening: 'चेकआउट खुल रहा है…',
    soon: 'जल्द आ रहा है',
    paused: 'अभी भुगतान रुका हुआ है। जाँच मुफ़्त चलती रहेगी; थोड़ी देर बाद फिर कोशिश करें।',
    order: {
      pending: 'Dodo से आपका भुगतान पक्का किया जा रहा है…',
      paid: 'भुगतान मिल गया। धन्यवाद! अब इस फ़ोन पर हर घंटे 300 जाँचें मिलेंगी।',
      failed: 'भुगतान नहीं हुआ और आपसे कोई पैसा नहीं कटा। आप फिर कोशिश कर सकते हैं।',
      slow: 'Dodo से अभी जवाब नहीं आया। अगर आपने भुगतान किया है, तो कुछ मिनट में यहाँ दिखेगा।',
      unknown: 'यह ऑर्डर नहीं मिला।',
      check: 'फिर देखें',
    },
  },
  hinglish: {
    title: 'Plans',
    intro: 'Message check karna sabke liye free hai, aur free hi rahega. Plan se ye service chalti hai aur aapke phone ko zyada checks milte hain.',
    testMode: 'Test mode: koi asli paisa nahi katega. Dodo ke checkout page par dikhaya gaya test card use karo.',
    loading: 'Plans load ho rahe hain…',
    loadError: 'Plans load nahi hue. Internet check karo aur phir try karo.',
    retry: 'Phir try karo',
    perMonth: '/mahina',
    free: { name: 'Free', price: '₹0', points: ['Message, link, UPI ID, screenshot aur voice note check karo', '8 bhashayein', 'Result family ko bhejo, scam report karo', 'Har ghante 30 checks'] },
    family: ['Free plan ki saari cheezein', 'Is phone pe har ghante 300 checks', 'Har family ke liye check free rehta hai'],
    api: ['Paisa jaane se pehle aapke app se wahi check', 'Brokers, fintechs aur banks ke liye'],
    checkFree: 'Message check karo',
    buy: (name) => `${name} lo`,
    opening: 'Checkout khul raha hai…',
    soon: 'Jaldi aa raha hai',
    paused: 'Abhi payments ruki hui hain. Check free chalta rahega; thodi der baad try karo.',
    order: {
      pending: 'Dodo se aapka payment confirm ho raha hai…',
      paid: 'Payment mil gaya. Thank you! Ab is phone pe har ghante 300 checks milenge.',
      failed: 'Payment nahi hua, aur aapka koi paisa nahi kata. Aap phir try kar sakte ho.',
      slow: 'Dodo se abhi jawab nahi aaya. Agar aapne pay kiya hai, to kuch minute mein yahan dikhega.',
      unknown: 'Ye order nahi mila.',
      check: 'Phir dekho',
    },
  },
  mr: {
    title: 'प्लॅन',
    intro: 'मेसेज तपासणे सर्वांसाठी मोफत आहे आणि मोफतच राहील. प्लॅनमुळे ही सेवा चालते आणि तुमच्या फोनला जास्त तपासण्या मिळतात.',
    testMode: 'टेस्ट मोड: कोणतेही खरे पैसे कापले जाणार नाहीत. Dodo च्या चेकआउट पानावर दाखवलेले टेस्ट कार्ड वापरा.',
    loading: 'प्लॅन लोड होत आहेत…',
    loadError: 'प्लॅन लोड झाले नाहीत. इंटरनेट तपासा आणि पुन्हा प्रयत्न करा.',
    retry: 'पुन्हा प्रयत्न करा',
    perMonth: '/महिना',
    free: { name: 'मोफत', price: '₹0', points: ['मेसेज, लिंक, UPI आयडी, स्क्रीनशॉट आणि व्हॉइस नोटची तपासणी', '8 भाषा', 'निकाल कुटुंबाला पाठवा, फसवणूक रिपोर्ट करा', 'दर तासाला 30 तपासण्या'] },
    family: ['मोफत प्लॅनमधील सर्व सुविधा', 'या फोनवर दर तासाला 300 तपासण्या', 'प्रत्येक कुटुंबासाठी तपासणी मोफत राहते'],
    api: ['पैसे जाण्याआधी तुमच्या ॲपमधून तीच तपासणी', 'ब्रोकर, फिनटेक आणि बँकांसाठी'],
    checkFree: 'मेसेज तपासा',
    buy: (name) => `${name} घ्या`,
    opening: 'चेकआउट उघडत आहे…',
    soon: 'लवकरच येत आहे',
    paused: 'सध्या पेमेंट थांबले आहे. तपासणी मोफत सुरू राहील; थोड्या वेळाने पुन्हा प्रयत्न करा.',
    order: {
      pending: 'Dodo कडून तुमचे पेमेंट निश्चित करत आहोत…',
      paid: 'पेमेंट मिळाले. धन्यवाद! आता या फोनवर दर तासाला 300 तपासण्या मिळतील.',
      failed: 'पेमेंट झाले नाही आणि तुमचे पैसे कापले गेले नाहीत. तुम्ही पुन्हा प्रयत्न करू शकता.',
      slow: 'Dodo कडून अजून उत्तर आले नाही. तुम्ही पैसे भरले असतील तर काही मिनिटांत इथे दिसेल.',
      unknown: 'ही ऑर्डर सापडली नाही.',
      check: 'पुन्हा पाहा',
    },
  },
};

const PLAN_NAMES = {
  en: { family: 'Family', api: 'API' },
  hi: { family: 'फ़ैमिली', api: 'API' },
  hinglish: { family: 'Family', api: 'API' },
  mr: { family: 'फॅमिली', api: 'API' },
};

const tick = html`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>`;

function Points({ items }) {
  return html`<ul class="plan-points">${items.map((p) => html`<li>${tick}<span>${p}</span></li>`)}</ul>`;
}

/** After Dodo returns the buyer: ask our server (never the URL) whether the webhook has marked the order paid. */
function OrderStatus({ orderId, c }) {
  const [status, setStatus] = useState('pending');
  const [round, setRound] = useState(0);
  const box = useRef(null);
  useEffect(() => {
    let active = true;
    let timer;
    const started = Date.now();
    setStatus('pending');
    const poll = () => apiFetch(`/api/orders/${encodeURIComponent(orderId)}`)
      .then(({ data }) => {
        if (!active) return;
        if (data.status === 'pending' && Date.now() - started < POLL_FOR_MS) { timer = setTimeout(poll, POLL_MS); return; }
        setStatus(data.status === 'pending' ? 'slow' : data.status);
      })
      .catch((e) => active && setStatus(e.status === 404 ? 'unknown' : 'slow'));
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [orderId, round]);
  useEffect(() => { if (status !== 'pending' && box.current) box.current.focus(); }, [status]);
  const tone = status === 'paid' ? 'ok' : status === 'pending' ? 'wait' : 'warn';
  return html`<div class=${`card order-status order-${tone}`} role="status" tabindex="-1" ref=${box}>
    ${status === 'pending' && html`<span class="spinner" aria-hidden="true"></span>`}
    <p>${c.order[status]}</p>
    ${status === 'slow' && html`<button class="button secondary" onClick=${() => setRound((n) => n + 1)}>${c.order.check}</button>`}
  </div>`;
}

export function PricingPage() {
  const lang = PAGE_LANGS.includes(defaultLang()) ? defaultLang() : 'en';
  const c = COPY[lang];
  const t = strings(lang);
  const names = PLAN_NAMES[lang];
  const [state, setState] = useState({ status: 'loading' });
  const [busy, setBusy] = useState(null);
  const [buyError, setBuyError] = useState(null);
  const [reload, setReload] = useState(0);
  const orderId = new URLSearchParams(location.search).get('order');

  useEffect(() => {
    document.documentElement.lang = uiLang(lang);
    track('pricing_view', { props: { returning_from_checkout: Boolean(orderId) } });
    // Dodo appends the buyer's email to the return URL. Keep only the order ID in the address bar and history.
    if (orderId && location.search !== `?order=${encodeURIComponent(orderId)}`) {
      history.replaceState(null, '', `/pricing?order=${encodeURIComponent(orderId)}`);
    }
  }, []);

  useEffect(() => {
    let active = true;
    apiFetch('/api/plans')
      .then(({ data }) => active && setState({ status: 'ready', ...data }))
      .catch((error) => active && setState({ status: 'error', error }));
    return () => { active = false; };
  }, [reload]);

  async function buy(plan) {
    setBusy(plan);
    setBuyError(null);
    try {
      const { data } = await apiFetch('/api/checkout', { method: 'POST', body: { plan, anon_id: anonId } });
      location.assign(data.checkout_url);
    } catch (error) {
      setBusy(null);
      setBuyError(error.code === 'payments_unavailable' ? c.paused : errorText(t, error));
    }
  }

  let body;
  if (state.status === 'loading') {
    body = html`<div class="card empty" role="status"><span class="spinner" aria-hidden="true"></span><p>${c.loading}</p></div>`;
  } else if (state.status === 'error') {
    body = html`<div class="card" role="alert"><p class="error">${c.loadError}</p>
      <button class="button primary block" onClick=${() => { setState({ status: 'loading' }); setReload((n) => n + 1); }}>${c.retry}</button></div>`;
  } else {
    const plans = Object.fromEntries(state.plans.map((p) => [p.id, p]));
    const paid = (id, points, featured) => {
      const p = plans[id];
      if (!p) return null;
      const name = names[id] || p.name;
      return html`<section class=${`card plan${featured ? ' plan-featured' : ''}`} aria-labelledby=${`plan-${id}`}>
        <h2 id=${`plan-${id}`}>${name}</h2>
        <p class="plan-price">₹${p.price_inr}<small>${c.perMonth}</small></p>
        <${Points} items=${points} />
        ${p.available
          ? html`<button class=${`button ${featured ? 'primary' : 'secondary'} block`} disabled=${busy !== null}
              onClick=${() => buy(id)}>${busy === id ? c.opening : c.buy(name)}</button>`
          : html`<button class="button secondary block" disabled aria-disabled="true">${c.soon}</button>`}
      </section>`;
    };
    body = html`
      ${state.test_mode && html`<p class="sample-note">${c.testMode}</p>`}
      ${buyError && html`<p class="error" role="alert">${buyError}</p>`}
      <div class="plans">
        <section class="card plan" aria-labelledby="plan-free">
          <h2 id="plan-free">${c.free.name}</h2>
          <p class="plan-price">${c.free.price}</p>
          <${Points} items=${c.free.points} />
          <a class="button secondary block" href="/">${c.checkFree}</a>
        </section>
        ${paid('family', c.family, true)}
        ${paid('api', c.api, false)}
      </div>`;
  }

  return html`<main class="page pricing-page" lang=${uiLang(lang)}>
    <h1>${c.title}</h1>
    <p class="muted">${c.intro}</p>
    ${orderId && /^ord_[A-Za-z0-9_-]{1,40}$/.test(orderId) && html`<${OrderStatus} orderId=${orderId} c=${c} />`}
    ${body}
  </main>`;
}
