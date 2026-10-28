// Anonymous identity and usage events (BUILD_BRIEF section 12). No login, no personal data.

const KEY = 'cbyp_anon_id';
const ID_RE = /^u_[A-Za-z0-9_-]{1,40}$/;

function safeGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode or blocked storage: the ID lives for this page load only */
  }
}

function randomId() {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return 'u_' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

const stored = safeGet(KEY);
export const isReturning = Boolean(stored && ID_RE.test(stored));
export const anonId = isReturning ? stored : randomId();
if (!isReturning) safeSet(KEY, anonId);

const refParam = new URLSearchParams(location.search).get('ref');
/** The anon_id of whoever shared the link that brought this user here, if any. */
export const ref = refParam && ID_RE.test(refParam) && refParam !== anonId ? refParam : null;

/** Fire-and-forget usage event. Never blocks or breaks the UI. */
export function track(event, { checkId = null, props = {} } = {}) {
  const body = { anon_id: anonId, event, check_id: checkId, ref, props };
  try {
    fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* ignore */
  }
}

export function savedLang() {
  return safeGet('cbyp_lang');
}

export function saveLang(lang) {
  safeSet('cbyp_lang', lang);
}
