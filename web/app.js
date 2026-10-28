import { render } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { apiFetch } from './components/api.js';
import { CheckForm } from './components/CheckForm.js';
import { html } from './components/html.js';
import { defaultLang, strings } from './components/i18n.js';
import { anonId, isReturning, ref, saveLang, track } from './components/session.js';
import { Verdict } from './components/Verdict.js';

function Header() {
  return html`<header class="site-header">
    <a href="/" class="brand"><img src="/icon.svg" alt="" width="28" height="28" /><span>Check Before You Pay</span></a>
  </header>`;
}

function Footer() {
  return html`<footer class="site-footer">
    <p>An independent tool. It is not run by SEBI, NPCI or any bank.</p>
  </footer>`;
}

function CheckPage() {
  const [lang, setLang] = useState(defaultLang());
  const [state, setState] = useState({ status: 'idle' });
  const t = strings(lang);

  useEffect(() => {
    document.documentElement.lang = lang === 'hinglish' ? 'hi' : lang;
  }, [lang]);

  function chooseLang(code) {
    setLang(code);
    saveLang(code);
  }

  async function submit(input, inputType) {
    setState({ status: 'loading' });
    track('check_started', { props: { lang, input_type: inputType } });
    const started = performance.now();
    try {
      const { data, sample } = await apiFetch('/api/check', {
        method: 'POST',
        body: { lang, anon_id: anonId, ref, input },
        timeoutMs: 30000,
      });
      track('check_done', {
        checkId: data.check_id,
        props: { latency_ms: Math.round(performance.now() - started), band: data.band, lang, input_type: inputType },
      });
      setState({ status: 'done', result: data, sample });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      setState({ status: 'error', error: e.message });
    }
  }

  return html`
    <main class="page">
      <p class="tagline">${t.tagline}</p>
      ${state.status === 'done'
        ? html`<${Verdict} result=${state.result} sample=${state.sample} t=${t} onReset=${() => setState({ status: 'idle' })} />`
        : html`<${CheckForm}
            lang=${lang}
            onLang=${chooseLang}
            onSubmit=${submit}
            busy=${state.status === 'loading'}
            serverError=${state.status === 'error' ? state.error : null}
            t=${t}
          />`}
    </main>
  `;
}

function SoonPage() {
  const t = strings(defaultLang());
  return html`<main class="page"><div class="card empty">
    <p>${t.soon}</p>
    <a class="button secondary" href="/">${t.back}</a>
  </div></main>`;
}

function App() {
  const page = location.pathname === '/' ? html`<${CheckPage} />` : html`<${SoonPage} />`;
  return html`<${Header} />${page}<${Footer} />`;
}

track('visit', { props: { path: location.pathname } });
if (isReturning) track('return_visit');
if (ref) track('ref_visit');

const root = document.getElementById('app');
root.textContent = ''; // drop the static "Loading…" placeholder
render(html`<${App} />`, root);
