// Thin fetch wrapper. Every failure becomes an ApiError with a plain-English message from the
// contract's error envelope: {"error": {"code", "message"}}.

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function apiFetch(path, { method = 'GET', body, timeoutMs = 20000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    const sample = res.headers.get('X-Sample') === 'true';
    if (res.status === 204) return { data: null, sample };
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) {
      const err = data && data.error;
      throw new ApiError(
        (err && err.code) || 'http_error',
        (err && err.message) || `The request failed (${res.status}). Please try again.`,
        res.status,
      );
    }
    return { data, sample };
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e && e.name === 'AbortError') {
      throw new ApiError('timeout', 'This is taking too long. Check your connection and try again.', 0);
    }
    throw new ApiError('network', 'Could not reach the server. Check your connection and try again.', 0);
  } finally {
    clearTimeout(timer);
  }
}
