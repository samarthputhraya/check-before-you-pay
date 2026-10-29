import { useEffect, useRef, useState } from 'preact/hooks';
import { apiFetch } from './api.js';
import { html } from './html.js';
import { contentLang, errorText } from './i18n.js';
import { createShareCard } from './shareCard.js';
import { anonId, track } from './session.js';

const BAND_ICON = {
  high_risk: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>
    <path d="M12 9v4M12 17h.01"/></svg>`,
  caution: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  no_known_signals: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`,
};

function Evidence({ evidence, t }) {
  if (evidence.kind === 'quote') return html`<blockquote>“${evidence.text}”</blockquote>`;
  return html`<p class="lookup">
    ${evidence.text}
    ${evidence.source_url && html` <a href=${evidence.source_url} target="_blank" rel="noopener">${t.source}</a>`}
  </p>`;
}

async function shareResult(result, bandLabel, t) {
  const { url, card_title: title } = result.share;
  if (navigator.share && navigator.canShare) {
    try {
      const file = await createShareCard(result, bandLabel, { riskScore: t.cardScore, footer: t.cardFooter });
      const payload = { title, text: title, url, files: [file] };
      if (navigator.canShare({ files: [file] })) {
        await navigator.share(payload);
        track('share_clicked', { checkId: result.check_id, props: { method: 'image' } });
        return;
      }
    } catch (e) {
      if (e && e.name === 'AbortError') return; // the user closed the share sheet
    }
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(`${title}\n${url}`)}`, '_blank', 'noopener');
  track('share_clicked', { checkId: result.check_id, props: { method: 'wa_link' } });
}

// A report links this check's identifiers to future checks (S4) and fires the viaSocket alert. Text is kept only with
// explicit consent, and only the server's short-lived copy from the same anon_id can be saved.
function ReportBox({ checkId, t }) {
  const [state, setState] = useState({ status: 'closed' });
  const [consent, setConsent] = useState(false);
  const trigger = useRef(null);
  const consentBox = useRef(null);
  const doneMsg = useRef(null);
  const errorMsg = useRef(null);
  const opened = useRef(false);
  const r = t.report;
  // Keep keyboard and screen-reader focus with the flow: into the form, onto the result, back to the button.
  useEffect(() => {
    if (state.status === 'open') { opened.current = true; consentBox.current && consentBox.current.focus(); }
    if (state.status === 'done' && doneMsg.current) doneMsg.current.focus();
    if (state.status === 'error' && errorMsg.current) errorMsg.current.focus();
    if (state.status === 'closed' && opened.current && trigger.current) trigger.current.focus();
  }, [state.status]);
  if (state.status === 'closed') {
    return html`<button type="button" class="button ghost block report-open" ref=${trigger} aria-expanded="false"
      onClick=${() => setState({ status: 'open' })}>${r.open}</button>`;
  }
  if (state.status === 'done') {
    return html`<p class="report-done" role="status" tabindex="-1" ref=${doneMsg}>${state.textLost ? r.doneNoText : r.done}</p>`;
  }
  async function send() {
    setState({ status: 'sending' });
    try {
      const { data } = await apiFetch('/api/report', { method: 'POST', body: { check_id: checkId, anon_id: anonId, consent_store_text: consent, note: null } });
      setState({ status: 'done', textLost: consent && data && data.text_saved === false });
    } catch (error) {
      setState({ status: 'error', error });
    }
  }
  const busy = state.status === 'sending';
  return html`<div class="report-box" aria-busy=${busy}>
    <p class="small" id="report-why">${r.why}</p>
    <label class="report-consent"><input type="checkbox" ref=${consentBox} checked=${consent} disabled=${busy}
      aria-describedby="report-why" onChange=${(e) => setConsent(e.currentTarget.checked)} /> ${r.consent}</label>
    ${state.status === 'error' && html`<p class="error" role="alert" tabindex="-1" ref=${errorMsg}>${errorText(t, state.error)}</p>`}
    <div class="actions">
      <button type="button" class="button primary" disabled=${busy} onClick=${send}>${busy ? r.sending : r.send}</button>
      <button type="button" class="button secondary" disabled=${busy} onClick=${() => setState({ status: 'closed' })}>${r.cancel}</button>
    </div>
  </div>`;
}

export function Verdict({ result, sample, t, onReset }) {
  const heading = useRef(null);
  useEffect(() => {
    if (heading.current) heading.current.focus();
  }, [result.check_id]);

  const { ring } = result;
  const linked = ring.linked_checks + ring.linked_reports > 0;
  const total = result.signals.reduce((sum, s) => sum + s.points, 0);
  // S1 only scores a non-@valid UPI ID when the message is about investing. Otherwise say what that ID does and
  // doesn't tell you, so "no signals" is never read as "this UPI ID is fine for a trading account".
  const plainHandle = !result.signals.some((s) => s.id === 'S1') &&
    result.entities.some((e) => e.type === 'upi' && !/@valid[a-z]*$/i.test(e.masked));

  return html`
    <section class=${`card verdict band-${result.band}`} aria-labelledby="verdict-headline" lang=${contentLang(result.lang)}>
      ${sample && html`<p class="sample-note">${t.sample}</p>`}
      <div class="verdict-head">
        <span class="band-pill">${BAND_ICON[result.band]}${t.band[result.band]}</span>
        <span class="score" aria-label=${`${t.cardScore}: ${result.score} / 100`}>${result.score}<small>/100</small></span>
      </div>
      <h1 id="verdict-headline" tabindex="-1" ref=${heading}>${result.headline}</h1>
      <p class="explanation">${result.explanation}</p>

      ${result.signals.length > 0 &&
      html`<h2 class="verdict-section">${t.signals}</h2>
        <ul class="signals">
          ${result.signals.map(
            (s) => html`<li key=${s.id}>
              <span class="pts">+${s.points}</span>
              <div><strong>${s.label}</strong><${Evidence} evidence=${s.evidence} t=${t} /></div>
            </li>`,
          )}
        </ul>`}
      ${total > 100 && html`<p class="muted small">${t.capped.replace('{sum}', total)}</p>`}
      ${plainHandle && html`<p class="note">${t.handleNote}</p>`}

      ${linked &&
      html`<p class="ring">
        ${t.ring(ring.linked_checks, ring.linked_reports)}${ring.via.length > 0 &&
        ` ${t.through} ${ring.via.map((v) => t.via[v] || v).join(', ')}`}
      </p>`}

      ${result.unchecked.length > 0 && html`<p class="muted small">${t.unchecked(result.unchecked.map((c) => t.checks[c] || c).join(', '))}</p>`}

      ${result.transcript &&
      html`<details class="transcript"><summary>${t.transcript}</summary><p>${result.transcript}</p></details>`}

      <h2 class="verdict-section">${t.nextSteps}</h2>
      <ol class="steps">
        ${result.next_steps.map(
          (st) => html`<li>${st.url ? html`<a href=${st.url} target="_blank" rel="noopener">${st.text}</a>` : st.text}</li>`,
        )}
      </ol>

      <div class="actions">
        <button type="button" class="button primary" onClick=${() => shareResult(result, t.band[result.band], t)}>${shareIcon}${t.share}</button>
        <button type="button" class="button secondary" onClick=${onReset}>${t.another}</button>
      </div>
      ${!sample && html`<${ReportBox} checkId=${result.check_id} t=${t} key=${result.check_id} />`}
    </section>
  `;
}

const shareIcon = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>
  <circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/></svg>`;
