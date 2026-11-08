// Talking to an app's back end. Every app's routes live under /api/<app-id>/.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function handle(r) {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(data.error || `HTTP ${r.status}`, r.status);
  return data;
}

export async function getJSON(path, { signal } = {}) {
  return handle(await fetch(path, { signal, credentials: 'same-origin' }));
}

export async function postJSON(path, body = {}, { signal } = {}) {
  return handle(await fetch(path, {
    method: 'POST',
    signal,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

/** api('/api/burrow') → { get('/docs'), post('/upload', {...}) } */
export function api(base) {
  return {
    get: (p, o) => getJSON(base + p, o),
    post: (p, b, o) => postJSON(base + p, b, o),
    url: (p) => base + p,
  };
}

/** Read a File as base64 (no data: prefix). The hub only takes JSON, so uploads travel this way. */
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(',')[1] || '');
    r.onerror = () => reject(new Error(`could not read ${file.name}`));
    r.readAsDataURL(file);
  });
}

/** localStorage that never throws (private windows, blocked storage…). */
export const store = {
  get(key, fallback) {
    try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* ignore */ }
  },
};
