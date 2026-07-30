const BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : "/api";

let _token = localStorage.getItem("lablens_token") || null;

export function setToken(t) { _token = t; if (t) localStorage.setItem("lablens_token", t); else localStorage.removeItem("lablens_token"); }
export function getToken() { return _token; }
export function isLoggedIn() { return !!_token; }

async function _fetch(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;
  if (!(opts.body instanceof FormData) && opts.body) headers["Content-Type"] = "application/json";
  const r = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (r.status === 401) { setToken(null); throw new Error("Session expired. Please log in again."); }
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Error ${r.status}`); }
  return r.json();
}

export const auth = {
  register: (email, password, full_name = "") => _fetch("/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
  login: (email, password) => {
    const body = new URLSearchParams(); body.set("username", email); body.set("password", password);
    return fetch(`${BASE}/auth/login`, { method: "POST", body, headers: { "Content-Type": "application/x-www-form-urlencoded" } }).then(async r => { if (!r.ok) throw new Error("Invalid credentials"); return r.json(); });
  },
  me: () => _fetch("/auth/me"),
};

export const reports = {
  upload: (file, reportDate) => {
    const fd = new FormData(); fd.append("file", file);
    if (reportDate) fd.append("report_date", reportDate);
    return _fetch("/reports/upload", { method: "POST", body: fd });
  },
  list: () => _fetch("/reports"),
  get: (id) => _fetch(`/reports/${id}`),
};

export const trends = { get: () => _fetch("/trends") };
export const dashboard = { get: () => _fetch("/dashboard") };
