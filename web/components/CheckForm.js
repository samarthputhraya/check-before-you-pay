import { useRef, useState } from 'preact/hooks';
import { html } from './html.js';
import { LANGS } from './i18n.js';

const MAX_TEXT = 5000;
const MAX_FILE = 5 * 1024 * 1024;
const IMAGE_MIMES = ['image/png', 'image/jpeg'];
const AUDIO_MIMES = ['audio/ogg', 'audio/mp4', 'audio/mpeg'];
const EXT_MIME = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
  ogg: 'audio/ogg', oga: 'audio/ogg', opus: 'audio/ogg',
  m4a: 'audio/mp4', mp4: 'audio/mp4', mp3: 'audio/mpeg',
};
const MIME_ALIASES = { 'audio/opus': 'audio/ogg', 'audio/x-m4a': 'audio/mp4', 'audio/m4a': 'audio/mp4', 'audio/mp3': 'audio/mpeg' };

// WhatsApp voice notes often arrive with an empty or unusual MIME type, so fall back to the extension.
function mimeOf(file) {
  const type = (file.type || '').toLowerCase();
  if (MIME_ALIASES[type]) return MIME_ALIASES[type];
  if (IMAGE_MIMES.includes(type) || AUDIO_MIMES.includes(type)) return type;
  const ext = (file.name.split('.').pop() || '').toLowerCase();
  return EXT_MIME[ext] || type;
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function CheckForm({ lang, onLang, onSubmit, onEdit, busy, serverError, t }) {
  const [text, setText] = useState('');
  const [attachment, setAttachment] = useState(null);
  const [localError, setLocalError] = useState(null);
  const imageInput = useRef(null);
  const audioInput = useRef(null);

  function edited() {
    setLocalError(null);
    if (onEdit) onEdit();
  }

  async function pick(kind, file) {
    edited();
    if (!file) return;
    const mime = mimeOf(file);
    const allowed = kind === 'image' ? IMAGE_MIMES : AUDIO_MIMES;
    if (!allowed.includes(mime)) {
      setLocalError(kind === 'image' ? t.imageType : t.audioType);
      return;
    }
    if (file.size > MAX_FILE) {
      setLocalError(t.fileTooBig);
      return;
    }
    try {
      const b64 = await readBase64(file);
      if (attachment && attachment.preview) URL.revokeObjectURL(attachment.preview);
      const preview = kind === 'image' ? URL.createObjectURL(file) : null;
      setAttachment({ kind, name: file.name, size: file.size, mime, b64, preview });
    } catch {
      setLocalError(t.readFailed);
    }
  }

  function clearAttachment() {
    if (attachment && attachment.preview) URL.revokeObjectURL(attachment.preview);
    setAttachment(null);
    if (imageInput.current) imageInput.current.value = '';
    if (audioInput.current) audioInput.current.value = '';
  }

  function onPaste(e) {
    const item = Array.from((e.clipboardData && e.clipboardData.items) || []).find((i) => i.type.startsWith('image/'));
    if (item) {
      e.preventDefault();
      pick('image', item.getAsFile());
    }
  }

  function submit(e) {
    e.preventDefault();
    if (busy) return;
    const trimmed = text.trim();
    if (!trimmed && !attachment) return setLocalError(t.emptyInput);
    if (trimmed.length > MAX_TEXT) return setLocalError(t.tooLong);
    setLocalError(null);
    const isImage = attachment && attachment.kind === 'image';
    const isAudio = attachment && attachment.kind === 'audio';
    onSubmit(
      {
        text: trimmed || null,
        image_b64: isImage ? attachment.b64 : null,
        image_mime: isImage ? attachment.mime : null,
        audio_b64: isAudio ? attachment.b64 : null,
        audio_mime: isAudio ? attachment.mime : null,
      },
      attachment ? attachment.kind : 'text',
    );
  }

  const error = localError || serverError;
  const over = text.length > MAX_TEXT;

  return html`
    <form class="card check-form" onSubmit=${submit} novalidate aria-busy=${busy}>
      <div class="field-row">
        <label for="lang" class="label">${t.language}</label>
        <select id="lang" value=${lang} onChange=${(e) => onLang(e.target.value)} disabled=${busy}>
          ${LANGS.map((l) => html`<option value=${l.code}>${l.name}</option>`)}
        </select>
      </div>

      <label for="msg" class="label">${t.inputLabel}</label>
      <textarea
        id="msg"
        rows="6"
        placeholder=${t.placeholder}
        value=${text}
        onInput=${(e) => {
          setText(e.target.value);
          edited();
        }}
        onPaste=${onPaste}
        disabled=${busy}
        aria-invalid=${over}
      ></textarea>
      ${text.length > MAX_TEXT - 1000 &&
      html`<p class=${'counter' + (over ? ' over' : '')}>${text.length.toLocaleString()} / 5,000</p>`}

      ${attachment &&
      html`<div class="attachment">
        ${attachment.preview
          ? html`<img src=${attachment.preview} alt="" width="48" height="48" />`
          : html`<span class="attachment-icon" aria-hidden="true">${micIcon}</span>`}
        <span class="attachment-name">${attachment.name}<small>${formatSize(attachment.size)}</small></span>
        <button type="button" class="button ghost small" onClick=${clearAttachment} disabled=${busy}>${t.remove}</button>
      </div>`}

      <div class="file-buttons">
        <label class=${'button secondary' + (busy ? ' disabled' : '')}>
          ${imageIcon}<span>${t.addScreenshot}</span>
          <input ref=${imageInput} type="file" accept="image/png,image/jpeg" class="visually-hidden"
            disabled=${busy} onChange=${(e) => pick('image', e.target.files[0])} />
        </label>
        <label class=${'button secondary' + (busy ? ' disabled' : '')}>
          ${micIcon}<span>${t.addVoice}</span>
          <input ref=${audioInput} type="file" accept="audio/ogg,audio/mp4,audio/mpeg,.ogg,.opus,.m4a,.mp3"
            class="visually-hidden" disabled=${busy} onChange=${(e) => pick('audio', e.target.files[0])} />
        </label>
      </div>

      ${error && html`<p class="error" role="alert">${error}</p>`}

      <button type="submit" class="button primary block" disabled=${busy}>
        ${busy ? html`<span class="spinner" aria-hidden="true"></span>${t.checking}` : t.submit}
      </button>
      <p class="fine">${t.privacy}</p>
    </form>
  `;
}

const imageIcon = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/>
  <circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/></svg>`;

const micIcon = html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/>
  <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4"/></svg>`;
