import React, { useState, useEffect, useCallback } from "react";
import { auth, reports, trends as trendsAPI, dashboard as dashAPI, setToken, getToken, isLoggedIn } from "../lib/api.js";

// ═══════════════════════════════════════════════════
//  Design tokens
// ═══════════════════════════════════════════════════
const T = {
  teal50: "#f0fdfa", teal100: "#ccfbf1", teal200: "#99f6e4", teal400: "#2dd4bf",
  teal500: "#14b8a6", teal600: "#0d9488", teal700: "#0f766e", teal800: "#115e59", teal900: "#134e4a",
  green50: "#f0fdf4", green100: "#dcfce7", green500: "#22c55e", green700: "#15803d",
  amber50: "#fffbeb", amber100: "#fef3c7", amber500: "#f59e0b", amber600: "#d97706",
  red50: "#fef2f2", red100: "#fee2e2", red500: "#ef4444", red600: "#dc2626",
  slate50: "#f8fafc", slate100: "#f1f5f9", slate200: "#e2e8f0", slate300: "#cbd5e1",
  slate400: "#94a3b8", slate500: "#64748b", slate700: "#334155", slate800: "#1e293b", slate900: "#0f172a",
  font: "'Inter',-apple-system,system-ui,sans-serif",
  radius: 12, radiusSm: 8,
};

const STATUS_COLORS = {
  normal: { bg: T.green50, border: T.green500, text: T.green700, badge: T.green100 },
  high: { bg: T.amber50, border: T.amber500, text: T.amber600, badge: T.amber100 },
  low: { bg: T.amber50, border: T.amber500, text: T.amber600, badge: T.amber100 },
  critical_high: { bg: T.red50, border: T.red500, text: T.red600, badge: T.red100 },
  critical_low: { bg: T.red50, border: T.red500, text: T.red600, badge: T.red100 },
};

const CATEGORY_LABELS = {
  blood_sugar: "🩸 Blood Sugar", lipid: "💧 Lipid Panel", liver: "🫁 Liver",
  kidney: "💎 Kidney", cbc: "🔬 Blood Count", thyroid: "🦋 Thyroid",
  vitamins: "✨ Vitamins & Minerals", general: "📋 General",
};

// ═══════════════════════════════════════════════════
//  Shared styles
// ═══════════════════════════════════════════════════
const card = { background: "#fff", borderRadius: T.radius, border: `1px solid ${T.slate200}`, boxShadow: "0 1px 3px rgba(0,0,0,0.04)", padding: "20px 24px", marginBottom: 16 };
const btn = (bg, color = "#fff") => ({ padding: "12px 24px", borderRadius: T.radiusSm, border: "none", background: bg, color, fontWeight: 600, fontSize: 14, cursor: "pointer", fontFamily: T.font, width: "100%", transition: "all 0.15s" });
const input = { width: "100%", padding: "12px 16px", borderRadius: T.radiusSm, border: `1.5px solid ${T.slate200}`, fontSize: 14, fontFamily: T.font, boxSizing: "border-box", background: T.slate50, transition: "border 0.2s" };

// ═══════════════════════════════════════════════════
//  Components
// ═══════════════════════════════════════════════════

function StatusBadge({ status }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS.normal;
  return <span style={{ fontSize: 11, fontWeight: 700, background: c.badge, color: c.text, padding: "3px 10px", borderRadius: 99, textTransform: "uppercase" }}>{status.replace("_", " ")}</span>;
}

function MarkerCard({ m }) {
  const c = STATUS_COLORS[m.status] || STATUS_COLORS.normal;
  const pct = m.ref_low != null && m.ref_high != null
    ? Math.min(100, Math.max(0, ((m.value - m.ref_low) / (m.ref_high - m.ref_low)) * 100))
    : 50;
  return (
    <div style={{ ...card, borderLeft: `4px solid ${c.border}`, background: c.bg, padding: "16px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: T.slate800 }}>{m.display_name}</span>
        <StatusBadge status={m.status} />
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color: c.text, marginBottom: 4 }}>
        {m.value} <span style={{ fontSize: 13, fontWeight: 500, color: T.slate400 }}>{m.unit}</span>
      </div>
      {m.ref_low != null && m.ref_high != null && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ height: 6, background: T.slate200, borderRadius: 3, position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pct}%`, background: c.border, borderRadius: 3, transition: "width 0.5s" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: T.slate400, marginTop: 3 }}>
            <span>{m.ref_low}</span><span>Normal range</span><span>{m.ref_high}</span>
          </div>
        </div>
      )}
      <p style={{ fontSize: 13, color: T.slate700, lineHeight: 1.6, margin: 0 }}>{m.interpretation}</p>
    </div>
  );
}

function TrendChart({ trend }) {
  if (!trend.points || trend.points.length < 2) return null;
  const vals = trend.points.map(p => p.value);
  const min = Math.min(...vals, trend.ref_low || Infinity) * 0.9;
  const max = Math.max(...vals, trend.ref_high || -Infinity) * 1.1;
  const range = max - min || 1;
  const w = 280, h = 100, pad = 20;

  const pts = trend.points.map((p, i) => ({
    x: pad + (i / (trend.points.length - 1)) * (w - 2 * pad),
    y: pad + (1 - (p.value - min) / range) * (h - 2 * pad),
    ...p,
  }));
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");

  return (
    <div style={{ ...card, padding: "16px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>{trend.display_name}</span>
        <span style={{ fontSize: 12, color: trend.direction === "stable" ? T.green700 : T.amber600, fontWeight: 600 }}>
          {trend.direction === "increasing" ? "↑" : trend.direction === "decreasing" ? "↓" : "→"} {trend.direction}
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: h }}>
        {trend.ref_low != null && <line x1={pad} x2={w-pad} y1={pad + (1-(trend.ref_low-min)/range)*(h-2*pad)} y2={pad + (1-(trend.ref_low-min)/range)*(h-2*pad)} stroke={T.green500} strokeDasharray="4 3" strokeWidth="1" opacity="0.5"/>}
        {trend.ref_high != null && <line x1={pad} x2={w-pad} y1={pad + (1-(trend.ref_high-min)/range)*(h-2*pad)} y2={pad + (1-(trend.ref_high-min)/range)*(h-2*pad)} stroke={T.red500} strokeDasharray="4 3" strokeWidth="1" opacity="0.5"/>}
        <path d={line} fill="none" stroke={T.teal600} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill="#fff" stroke={T.teal600} strokeWidth="2"/>)}
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: T.slate400 }}>
        {pts.map((p, i) => <span key={i}>{p.date.slice(5)}</span>)}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
//  Pages
// ═══════════════════════════════════════════════════

function AuthPage({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const data = isLogin
        ? await auth.login(email, password)
        : await auth.register(email, password, name);
      setToken(data.access_token);
      onAuth(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: `linear-gradient(135deg, ${T.teal800}, ${T.teal600})`, padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 400, background: "#fff", borderRadius: 20, padding: "40px 32px", boxShadow: "0 20px 40px rgba(0,0,0,0.15)" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>🔬</div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: T.teal800, margin: 0 }}>LabLens</h1>
          <p style={{ color: T.slate500, fontSize: 14, margin: "4px 0 0" }}>AI-powered lab report insights</p>
        </div>
        <form onSubmit={handleSubmit}>
          {!isLogin && <input placeholder="Full name" value={name} onChange={e => setName(e.target.value)} style={{ ...input, marginBottom: 12 }} />}
          <input placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} required style={{ ...input, marginBottom: 12 }} />
          <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} style={{ ...input, marginBottom: 16 }} />
          {error && <p style={{ color: T.red500, fontSize: 13, margin: "0 0 12px" }}>{error}</p>}
          <button type="submit" disabled={loading} style={btn(`linear-gradient(135deg, ${T.teal600}, ${T.green500})`)}>
            {loading ? "..." : isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>
        <p style={{ textAlign: "center", fontSize: 13, color: T.slate500, marginTop: 16, cursor: "pointer" }} onClick={() => { setIsLogin(!isLogin); setError(""); }}>
          {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </p>
      </div>
    </div>
  );
}

function MainApp({ user, onLogout }) {
  const [page, setPage] = useState("home");
  const [result, setResult] = useState(null);
  const [reportList, setReportList] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [dash, setDash] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const loadDash = useCallback(async () => { try { setDash(await dashAPI.get()); } catch {} }, []);
  const loadReports = useCallback(async () => { try { setReportList(await reports.list()); } catch {} }, []);
  const loadTrends = useCallback(async () => { try { const d = await trendsAPI.get(); setTrendData(d.trends || []); } catch {} }, []);

  useEffect(() => { loadDash(); loadReports(); loadTrends(); }, [loadDash, loadReports, loadTrends]);

  async function handleUpload(e) {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setError(""); setResult(null);
    try {
      const data = await reports.upload(file);
      setResult(data);
      setPage("result");
      loadDash(); loadReports(); loadTrends();
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }

  const nav = [["home", "🏠"], ["result", "📊"], ["history", "📁"], ["trends", "📈"]];

  return (
    <div style={{ fontFamily: T.font, background: T.slate50, minHeight: "100vh", paddingBottom: 80 }}>
      {/* Header */}
      <header style={{ background: `linear-gradient(135deg, ${T.teal800}, ${T.teal700})`, color: "#fff", padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 22 }}>🔬</span>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>LabLens</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 12, opacity: 0.8 }}>{user?.full_name || user?.email}</span>
          <button onClick={onLogout} style={{ background: "rgba(255,255,255,0.15)", border: "none", color: "#fff", padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Logout</button>
        </div>
      </header>

      <main style={{ maxWidth: 600, margin: "0 auto", padding: "20px 16px" }}>
        {/* Home */}
        {page === "home" && (
          <>
            {dash && (
              <div style={{ ...card, background: `linear-gradient(135deg, ${T.teal600}, ${T.green500})`, color: "#fff", border: "none" }}>
                <p style={{ fontSize: 13, opacity: 0.8, margin: "0 0 4px" }}>Your health at a glance</p>
                <p style={{ fontSize: 28, fontWeight: 800, margin: "0 0 8px" }}>{dash.total_reports} report{dash.total_reports !== 1 ? "s" : ""}</p>
                {dash.latest_summary && <p style={{ fontSize: 13, lineHeight: 1.6, margin: 0, opacity: 0.9 }}>{dash.latest_summary.slice(0, 200)}</p>}
              </div>
            )}

            <div style={{ ...card, textAlign: "center", padding: "32px 24px", border: `2px dashed ${T.teal300}`, background: T.teal50 }}>
              <p style={{ fontSize: 36, margin: "0 0 8px" }}>📄</p>
              <p style={{ fontSize: 16, fontWeight: 600, color: T.teal800, margin: "0 0 4px" }}>Upload lab report</p>
              <p style={{ fontSize: 13, color: T.slate500, margin: "0 0 16px" }}>PDF or text file — AI analysis in seconds</p>
              <label style={{ ...btn(`linear-gradient(135deg, ${T.teal600}, ${T.green500})`), display: "inline-block", width: "auto", padding: "12px 32px", cursor: "pointer" }}>
                {uploading ? "Analyzing..." : "Choose file"}
                <input type="file" accept=".pdf,.txt,.text" onChange={handleUpload} style={{ display: "none" }} disabled={uploading} />
              </label>
              {error && <p style={{ color: T.red500, fontSize: 13, marginTop: 12 }}>{error}</p>}
            </div>

            {trendData.length > 0 && (
              <>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: T.slate800, margin: "20px 0 12px" }}>📈 Your trends</h3>
                {trendData.slice(0, 3).map(t => <TrendChart key={t.name} trend={t} />)}
              </>
            )}
          </>
        )}

        {/* Result */}
        {page === "result" && result && (
          <>
            <div style={{ ...card, background: result.critical_count > 0 ? T.red50 : result.abnormal_count > 0 ? T.amber50 : T.green50, border: "none" }}>
              <p style={{ fontSize: 14, fontWeight: 700, color: T.slate800, margin: "0 0 8px" }}>Summary</p>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: T.slate700, margin: 0, whiteSpace: "pre-line" }}>{result.summary}</p>
            </div>

            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              {[["✅", result.normal_count, "Normal", T.green100], ["⚠️", result.abnormal_count, "Watch", T.amber100], ["🔴", result.critical_count, "Action", T.red100]].map(([emoji, count, label, bg]) => (
                <div key={label} style={{ flex: 1, background: bg, borderRadius: T.radiusSm, padding: "12px 8px", textAlign: "center" }}>
                  <div style={{ fontSize: 20 }}>{emoji}</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: T.slate800 }}>{count}</div>
                  <div style={{ fontSize: 11, color: T.slate500 }}>{label}</div>
                </div>
              ))}
            </div>

            {Object.entries(result.categories || {}).map(([cat, markers]) => (
              <div key={cat}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: T.slate700, margin: "16px 0 8px" }}>
                  {CATEGORY_LABELS[cat] || cat}
                </h3>
                {markers.map((m, i) => <MarkerCard key={i} m={m} />)}
              </div>
            ))}
          </>
        )}

        {/* History */}
        {page === "history" && (
          <>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: T.slate800, margin: "0 0 16px" }}>📁 Report history</h2>
            {reportList.length === 0 && <p style={{ color: T.slate400, textAlign: "center", padding: 40 }}>No reports yet. Upload your first lab report!</p>}
            {reportList.map(r => (
              <div key={r.report_id} style={{ ...card, cursor: "pointer" }} onClick={async () => { const d = await reports.get(r.report_id); setResult({ ...d, categories: {} }); setPage("result"); }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, margin: 0, color: T.slate800 }}>{r.filename}</p>
                    <p style={{ fontSize: 12, color: T.slate400, margin: "4px 0 0" }}>{r.report_date?.slice(0, 10) || "No date"}</p>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, background: r.status === "processed" ? T.green100 : T.amber100, color: r.status === "processed" ? T.green700 : T.amber600, padding: "3px 10px", borderRadius: 99 }}>{r.status}</span>
                </div>
              </div>
            ))}
          </>
        )}

        {/* Trends */}
        {page === "trends" && (
          <>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: T.slate800, margin: "0 0 16px" }}>📈 Biomarker trends</h2>
            {trendData.length === 0 && <p style={{ color: T.slate400, textAlign: "center", padding: 40 }}>Upload at least 2 reports to see trends.</p>}
            {trendData.map(t => <TrendChart key={t.name} trend={t} />)}
          </>
        )}
      </main>

      {/* Bottom nav */}
      <nav style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: "#fff", borderTop: `1px solid ${T.slate200}`, display: "flex", justifyContent: "space-around", padding: "8px 0 12px", zIndex: 100 }}>
        {nav.map(([key, icon]) => (
          <button key={key} onClick={() => setPage(key)}
            style={{ background: "none", border: "none", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, cursor: "pointer", color: page === key ? T.teal600 : T.slate400, fontSize: 11, fontWeight: 600, fontFamily: T.font, padding: "4px 16px" }}>
            <span style={{ fontSize: 20 }}>{icon}</span>
            {key.charAt(0).toUpperCase() + key.slice(1)}
          </button>
        ))}
      </nav>

      <style>{`* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: ${T.font}; -webkit-font-smoothing: antialiased; } input:focus { outline: none; border-color: ${T.teal400} !important; box-shadow: 0 0 0 3px ${T.teal100}; }`}</style>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (getToken()) {
      auth.me().then(setUser).catch(() => setToken(null)).finally(() => setChecking(false));
    } else { setChecking(false); }
  }, []);

  if (checking) return <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: T.font }}>Loading...</div>;
  if (!user) return <AuthPage onAuth={(d) => setUser({ email: d.email, full_name: d.full_name })} />;
  return <MainApp user={user} onLogout={() => { setToken(null); setUser(null); }} />;
}
