import { useEffect, useRef } from 'preact/hooks';
import { html } from './html.js';
import { contentLang } from './i18n.js';
import { createShareCard } from './shareCard.js';
import { track } from './session.js';

const BAND_ICON = {
  high_risk: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>
    <path d="M12 9v4M12 17h.01"/></svg>`,
  caution: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  no_known_signals: html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`,
};

function Evidence({ evidence }) {
  if (evidence.kind === 'quote') return html`<blockquote>“${evidence.text}”</blockquote>`;
  return html`<p class="lookup">
    ${evidence.text}
    ${evidence.source_url && html` <a href=${evidence.source_url} target="_blank" rel="noopener">Source</a>`}
  </p>`;
}

async function shareResult(result, bandLabel, t) {
  const { url, card_title: title } = result.share;
  if (navigator.share && navigator.canShare) {
    try {
      const file = await createShareCard(result, bandLabel, t.noProof);
      const payload = { title, text: title, url, files: [file] };
      if (navigator.canShare({ files: [file] })) {
        track('share_clicked', { checkId: result.check_id, props: { method: 'image' } });
        await navigator.share(payload);
        return;
      }
    } catch (e) {
      if (e && e.name === 'AbortError') return; // the user closed the share sheet
    }
  }
  track('share_clicked', { checkId: result.check_id, props: { method: 'wa_link' } });
  window.open(`https://wa.me/?text=${encodeURIComponent(`${title}\n${url}`)}`, '_blank', 'noopener');
}

export function Verdict({ result, sample, t, onReset }) {
  const heading = useRef(null);
  useEffect(() => {
    if (heading.current) heading.current.focus();
  }, [result.check_id]);

  const { ring } = result;
  const linked = ring.linked_checks + ring.linked_reports > 0;

  return html`
    <section class=${`card verdict band-${result.band}`} aria-labelledby="verdict-headline" lang=${contentLang(result.lang)}>
      ${sample && html`<p class="sample-note">${t.sample}</p>`}
      <div class="verdict-head">
        <span class="band-pill">${BAND_ICON[result.band]}${t.band[result.band]}</span>
        <span class="score" aria-label=${`Risk score ${result.score} out of 100`}>${result.score}<small>/100</small></span>
      </div>
      <h1 id="verdict-headline" tabindex="-1" ref=${heading}>${result.headline}</h1>
      ${result.band === 'no_known_signals' && html`<p class="muted">${t.noProof}</p>`}
      <p class="explanation">${result.explanation}</p>

      ${result.signals.length > 0 &&
      html`<h3>${t.signals}</h3>
        <ul class="signals">
          ${result.signals.map(
            (s) => html`<li key=${s.id}>
              <span class="pts">+${s.points}</span>
              <div><strong>${s.label}</strong><${Evidence} evidence=${s.evidence} /></div>
            </li>`,
          )}
        </ul>`}

      ${linked &&
      html`<p class="ring">
        ${t.ring(ring.linked_checks, ring.linked_reports)}${ring.via.length > 0 &&
        ` ${t.through} ${ring.via.map((v) => t.via[v] || v).join(', ')}`}
      </p>`}

      ${result.unchecked.length > 0 && html`<p class="muted small">${t.unchecked(result.unchecked.join(', '))}</p>`}

      ${result.transcript &&
      html`<details class="transcript"><summary>${t.transcript}</summary><p>${result.transcript}</p></details>`}

      <h3>${t.nextSteps}</h3>
      <ol class="steps">
        ${result.next_steps.map(
          (st) => html`<li>${st.url ? html`<a href=${st.url} target="_blank" rel="noopener">${st.text}</a>` : st.text}</li>`,
        )}
      </ol>

      <div class="actions">
        <button type="button" class="button primary" onClick=${() => shareResult(result, t.band[result.band], t)}>${shareIcon}${t.share}</button>
        <button type="button" class="button secondary" onClick=${onReset}>${t.another}</button>
      </div>
    </section>
  `;
}

const shareIcon = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>
  <circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/></svg>`;
