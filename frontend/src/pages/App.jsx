import React, { useState, useEffect, useCallback } from "react";
import { auth, reports, trends as trendsAPI, dashboard as dashAPI, setToken, getToken, isLoggedIn } from "../lib/api.js";

// ═══════════════════════════════════════════════════
//  Design tokens (Forest Green Theme)
// ═══════════════════════════════════════════════════
const T = {
  brandPrimary: "#006D5B",
  brandDark: "#004D40",
  brandLight: "#E6F0EE",
  brandAccent: "#55EFB0",
  
  successBg: "#69F0AE",
  successText: "#004D40",
  successMuted: "#E8F5E9",
  
  watchBg: "#FFF8E1",
  watchText: "#FF8F00",
  watchMuted: "#FFF3E0",
  
  actionBg: "#FFEBEE",
  actionText: "#D32F2F",
  actionMuted: "#FFEBEE",

  slate50: "#F8FAFC", slate100: "#F1F5F9", slate200: "#E2E8F0", 
  slate300: "#CBD5E1", slate400: "#94A3B8", slate500: "#64748B", 
  slate700: "#334155", slate800: "#1E293B", slate900: "#0F172A",
  
  font: "'Inter',-apple-system,system-ui,sans-serif",
  radius: 20, radiusSm: 12,
};

const STATUS_COLORS = {
  normal: { bg: "#fff", border: T.brandPrimary, text: T.slate800, badgeBg: T.brandLight, badgeText: T.brandPrimary },
  high: { bg: "#fff", border: T.watchText, text: T.slate800, badgeBg: T.watchMuted, badgeText: T.watchText },
  low: { bg: "#fff", border: T.watchText, text: T.slate800, badgeBg: T.watchMuted, badgeText: T.watchText },
  critical_high: { bg: "#fff", border: T.actionText, text: T.slate800, badgeBg: T.actionMuted, badgeText: T.actionText },
  critical_low: { bg: "#fff", border: T.actionText, text: T.slate800, badgeBg: T.actionMuted, badgeText: T.actionText },
};

const CATEGORY_LABELS = {
  blood_sugar: "BLOOD SUGAR", lipid: "LIPID PANEL", liver: "LIVER",
  kidney: "KIDNEY", cbc: "BLOOD COUNT", thyroid: "THYROID",
  vitamins: "VITAMINS", urine: "URINE ANALYSIS", general: "GENERAL",
};

// ═══════════════════════════════════════════════════
//  Shared styles
// ═══════════════════════════════════════════════════
const card = { background: "#fff", borderRadius: T.radius, boxShadow: "0 4px 12px rgba(0,0,0,0.03)", padding: "20px", marginBottom: 16 };
const btn = (bg, color = "#fff") => ({ padding: "14px 24px", borderRadius: 99, border: "none", background: bg, color, fontWeight: 600, fontSize: 15, cursor: "pointer", fontFamily: T.font, width: "100%", transition: "all 0.2s", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 });
const input = { width: "100%", padding: "14px 16px", borderRadius: T.radiusSm, border: `1.5px solid ${T.slate200}`, fontSize: 15, fontFamily: T.font, boxSizing: "border-box", background: T.slate50, transition: "border 0.2s" };

// ═══════════════════════════════════════════════════
//  Icons (SVG)
// ═══════════════════════════════════════════════════
const Icons = {
  Home: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>,
  Results: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>,
  History: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>,
  Trends: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>,
  Upload: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>,
  Check: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
};

// ═══════════════════════════════════════════════════
//  Components
// ═══════════════════════════════════════════════════

function StatusBadge({ status }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS.normal;
  return (
    <span style={{ fontSize: 10, fontWeight: 700, background: c.badgeBg, color: c.badgeText, padding: "4px 10px", borderRadius: 99, textTransform: "uppercase", display: "inline-flex", alignItems: "center", gap: 4 }}>
      {status === "normal" && <Icons.Check />}
      {status.replace("_", " ")}
    </span>
  );
}

function MarkerCard({ m }) {
  const c = STATUS_COLORS[m.status] || STATUS_COLORS.normal;
  const pct = m.ref_low != null && m.ref_high != null
    ? Math.min(100, Math.max(0, ((m.value - m.ref_low) / (m.ref_high - m.ref_low)) * 100))
    : 50;
    
  return (
    <div style={{ ...card, padding: 0, overflow: "hidden", display: "flex" }}>
      <div style={{ width: 6, background: c.border, flexShrink: 0 }}></div>
      <div style={{ padding: "16px", flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: T.slate800 }}>{m.display_name}</span>
          <StatusBadge status={m.status} />
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.slate900, marginBottom: 8, display: "flex", alignItems: "baseline", gap: 4 }}>
          {m.value} <span style={{ fontSize: 12, fontWeight: 500, color: T.slate500 }}>{m.unit}</span>
        </div>
        
        {m.ref_low != null && m.ref_high != null && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ flex: 1, height: 6, background: T.slate200, borderRadius: 3, position: "relative" }}>
              <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pct}%`, background: c.border, borderRadius: 3 }} />
              {/* Target mark */}
              <div style={{ position: "absolute", left: "50%", top: -2, bottom: -2, width: 2, background: "#fff" }} />
            </div>
          </div>
        )}
        {m.ref_low == null && m.ref_text && (
          <div style={{ fontSize: 12, color: T.slate500, fontStyle: "italic" }}>
            Expected: {m.ref_text}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
//  Pages
// ═══════════════════════════════════════════════════

function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      if (mode === "login") {
        const data = await auth.login(email, password);
        setToken(data.access_token);
        onAuth(data);
      } else if (mode === "register") {
        const data = await auth.register(email, password, name);
        setToken(data.access_token);
        onAuth(data);
      }
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: T.brandLight, padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 400, background: "#fff", borderRadius: 24, padding: "40px 32px", boxShadow: "0 20px 40px rgba(0,0,0,0.05)" }}>
        <div style={{ textAlign: "center", marginBottom: 32, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ width: 64, height: 64, background: T.brandPrimary, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", marginBottom: 16 }}>
             <Icons.Results />
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: T.brandDark, margin: 0 }}>LabLens</h1>
        </div>
        <form onSubmit={handleSubmit}>
          {mode === "register" && <input placeholder="Full name" value={name} onChange={e => setName(e.target.value)} style={{ ...input, marginBottom: 12 }} />}
          <input placeholder="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} required style={{ ...input, marginBottom: 12 }} />
          <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} style={{ ...input, marginBottom: 16 }} />
          {error && <p style={{ color: T.actionText, fontSize: 13, margin: "0 0 12px" }}>{error}</p>}
          <button type="submit" disabled={loading} style={btn(T.brandPrimary)}>
            {loading ? "..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
        <p style={{ textAlign: "center", fontSize: 14, color: T.slate500, marginTop: 24, cursor: "pointer" }} onClick={() => {setMode(mode==="login"?"register":"login"); setError("");}}>
          {mode === "login" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </p>
      </div>
    </div>
  );
}

function MainApp({ user, onLogout }) {
  const [page, setPage] = useState("home");
  const [result, setResult] = useState(null);
  const [reportList, setReportList] = useState([]);
  const [dash, setDash] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const loadDash = useCallback(async () => { try { setDash(await dashAPI.get()); } catch {} }, []);
  const loadReports = useCallback(async () => { try { setReportList(await reports.list()); } catch {} }, []);

  useEffect(() => { loadDash(); loadReports(); }, [loadDash, loadReports]);

  async function handleUpload(e) {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setError(""); setResult(null);
    try {
      const data = await reports.upload(file);
      const markers = data.markers || [];
      if (data.normal_count == null) data.normal_count = markers.filter(m => m.status === "normal").length;
      if (data.abnormal_count == null) data.abnormal_count = markers.filter(m => m.status === "high" || m.status === "low").length;
      if (data.critical_count == null) data.critical_count = markers.filter(m => m.status === "critical_high" || m.status === "critical_low").length;
      setResult(data);
      setPage("result");
      loadDash(); loadReports();
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }

  const nav = [
    ["home", <Icons.Home />], 
    ["result", <Icons.Results />], 
    ["history", <Icons.History />], 
    ["trends", <Icons.Trends />]
  ];

  return (
    <div style={{ fontFamily: T.font, background: T.slate50, minHeight: "100vh", paddingBottom: 80 }}>
      {/* Header */}
      <header style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#fff", borderBottom: `1px solid ${T.slate200}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: T.brandDark }}>
          <div style={{ width: 24, height: 24, background: T.brandLight, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icons.Results />
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>LabLens</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={onLogout} style={{ background: "none", border: "none", color: T.slate500, fontSize: 13, cursor: "pointer" }}>Logout</button>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: T.brandPrimary, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: "bold" }}>
             {user?.full_name?.charAt(0) || user?.email?.charAt(0).toUpperCase()}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 500, margin: "0 auto", padding: "20px 16px" }}>
        
        {/* ================= HOME ================= */}
        {page === "home" && (
          <>
            <div style={{ ...card, background: T.brandPrimary, color: "#fff", position: "relative", overflow: "hidden", padding: "24px 20px" }}>
              <div style={{ position: "absolute", right: -20, top: -20, opacity: 0.1, transform: "scale(2)" }}>
                 <Icons.Results />
              </div>
              <p style={{ fontSize: 11, letterSpacing: 1, textTransform: "uppercase", fontWeight: 700, margin: "0 0 4px", opacity: 0.9 }}>Your Health At A Glance</p>
              <p style={{ fontSize: 32, fontWeight: 700, margin: "0 0 12px" }}>{dash?.total_reports || 0} report{dash?.total_reports !== 1 ? "s" : ""}</p>
              <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.1)", padding: "10px 12px", borderRadius: 8 }}>
                <Icons.Check />
                <p style={{ fontSize: 12, margin: 0, lineHeight: 1.4 }}>All your lab values are within normal ranges. Keep up the good work!</p>
              </div>
            </div>

            <div style={{ ...card, textAlign: "center", padding: "32px 24px", border: `2px dashed ${T.slate300}`, background: "#fff", boxShadow: "none" }}>
              <div style={{ width: 48, height: 48, background: T.brandLight, color: T.brandDark, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <Icons.Upload />
              </div>
              <p style={{ fontSize: 18, fontWeight: 600, color: T.slate800, margin: "0 0 8px" }}>Upload lab report</p>
              <p style={{ fontSize: 14, color: T.slate500, margin: "0 0 24px" }}>PDF or text file — <span style={{ color: T.brandPrimary, fontWeight: 600 }}>AI analysis in seconds</span></p>
              
              <label style={btn(T.brandPrimary)}>
                <Icons.Upload />
                {uploading ? "Analyzing..." : "Choose file"}
                <input type="file" accept=".pdf,.txt,.text" onChange={handleUpload} style={{ display: "none" }} disabled={uploading} />
              </label>
              {error && <p style={{ color: T.actionText, fontSize: 13, marginTop: 12 }}>{error}</p>}
            </div>

            <div style={{ ...card, background: "#F3F0EB", display: "flex", gap: 16, alignItems: "flex-start", padding: "20px" }}>
               <div style={{ padding: 8, background: "#E8DED1", borderRadius: 8, color: "#8C6A48" }}>💡</div>
               <div>
                 <p style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px", color: "#4A3C31" }}>Did you know?</p>
                 <p style={{ fontSize: 13, margin: 0, color: "#7A6855", lineHeight: 1.5 }}>LabLens can identify trends across multiple reports to help you spot changes before they become issues.</p>
               </div>
            </div>
          </>
        )}

        {/* ================= RESULT ================= */}
        {page === "result" && result && (
          <>
            {result.status === "invalid_report" ? (
              <div style={{ ...card, background: T.actionMuted, border: `1px solid ${T.actionText}`, textAlign: "center" }}>
                <p style={{ fontSize: 16, fontWeight: 700, color: T.actionText, margin: "0 0 8px" }}>Invalid Document</p>
                <p style={{ fontSize: 14, color: T.slate700, margin: 0 }}>{result.summary}</p>
              </div>
            ) : (
              <>
                <div style={{ ...card, background: result.critical_count > 0 ? T.actionMuted : result.abnormal_count > 0 ? T.watchMuted : T.successBg, position: "relative", overflow: "hidden", color: result.critical_count > 0 ? T.actionText : result.abnormal_count > 0 ? T.watchText : T.successText }}>
                  <div style={{ position: "absolute", right: -10, top: 10, opacity: 0.15, transform: "scale(3)" }}><Icons.Check /></div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <Icons.Check />
                    <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
                      Health Status: {result.critical_count > 0 ? "Critical" : result.abnormal_count > 0 ? "Attention Needed" : "Optimal"}
                    </h2>
                  </div>
                  <p style={{ fontSize: 14, lineHeight: 1.5, margin: 0, position: "relative", zIndex: 1, opacity: 0.9 }}>{result.summary}</p>
                </div>

                <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                  {[
                    [result.normal_count, "NORMAL", T.successBg, T.successText],
                    [result.abnormal_count, "WATCH", T.watchText, T.watchText],
                    [result.critical_count, "ACTION", T.actionText, T.actionText]
                  ].map(([count, label, color, textColor]) => (
                    <div key={label} style={{ flex: 1, background: "#fff", borderRadius: T.radiusSm, padding: "16px 8px", textAlign: "center", border: `1px solid ${T.slate200}`, borderTop: `4px solid ${color}`, boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
                      <div style={{ fontSize: 16, color: color, marginBottom: 4 }}>
                        {label === "NORMAL" ? <Icons.Check /> : "!"}
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 800, color: T.slate800 }}>{count}</div>
                      <div style={{ fontSize: 10, fontWeight: 600, color: T.slate500, letterSpacing: 0.5 }}>{label}</div>
                    </div>
                  ))}
                </div>
                
                {/* AI Insights block */}
                {(result.diet_suggestions || result.doctor_recommendation) && (
                  <>
                    <h3 style={{ fontSize: 12, fontWeight: 700, color: T.slate500, letterSpacing: 1, margin: "24px 0 12px" }}>AI INSIGHTS</h3>
                    <div style={{ ...card, background: T.brandDark, color: "#fff", border: "none" }}>
                      <div style={{ display: "flex", gap: 12 }}>
                        <div style={{ width: 36, height: 36, borderRadius: 8, background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          💡
                        </div>
                        <div>
                          <p style={{ fontSize: 14, fontWeight: 600, margin: "0 0 6px" }}>Smart Observation</p>
                          {result.diet_suggestions && <p style={{ fontSize: 13, lineHeight: 1.5, opacity: 0.9, margin: "0 0 8px" }}>{result.diet_suggestions}</p>}
                          {result.doctor_recommendation && <p style={{ fontSize: 13, lineHeight: 1.5, opacity: 0.9, margin: 0 }}>{result.doctor_recommendation}</p>}
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {Object.entries(result.categories || {}).map(([cat, markers]) => (
                  <div key={cat}>
                    <h3 style={{ fontSize: 12, fontWeight: 700, color: T.slate500, letterSpacing: 1, margin: "24px 0 12px", display: "flex", justifyContent: "space-between" }}>
                      <span>{CATEGORY_LABELS[cat] || cat.toUpperCase()}</span>
                      <span style={{ color: T.brandPrimary, textTransform: "none" }}>Last updated: {result.report_date?.slice(5,10) || "Today"}</span>
                    </h3>
                    {markers.map((m, i) => <MarkerCard key={i} m={m} />)}
                  </div>
                ))}
              </>
            )}
          </>
        )}

        {/* ================= HISTORY ================= */}
        {page === "history" && (
          <>
            <div style={{ position: "relative", marginBottom: 16 }}>
              <span style={{ position: "absolute", left: 14, top: 14, color: T.slate400 }}><Icons.Results /></span>
              <input placeholder="Search reports..." style={{ ...input, paddingLeft: 44, borderRadius: 99, background: T.slate100, border: "none" }} />
            </div>

            <div style={{ display: "flex", gap: 8, marginBottom: 24, overflowX: "auto", paddingBottom: 4 }}>
              <button style={{ padding: "8px 16px", borderRadius: 99, border: "none", background: T.brandDark, color: "#fff", fontSize: 13, fontWeight: 600 }}>∞ All</button>
              <button style={{ padding: "8px 16px", borderRadius: 99, border: "none", background: T.slate200, color: T.slate700, fontSize: 13, fontWeight: 600 }}>✓ Processed</button>
              <button style={{ padding: "8px 16px", borderRadius: 99, border: "none", background: T.slate200, color: T.slate700, fontSize: 13, fontWeight: 600 }}>↻ Analyzing</button>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: T.slate800, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                 📁 Report History
              </h2>
              <span style={{ background: T.slate200, padding: "4px 10px", borderRadius: 99, fontSize: 11, fontWeight: 600, color: T.slate600 }}>{reportList.length} Total</span>
            </div>

            {reportList.length === 0 && <p style={{ color: T.slate400, textAlign: "center", padding: 40 }}>No reports yet.</p>}
            {reportList.map(r => (
              <div key={r.report_id} style={{ ...card, padding: 0, cursor: "pointer", display: "flex", overflow: "hidden" }} onClick={async () => { const d = await reports.get(r.report_id); setResult(d); setPage("result"); }}>
                <div style={{ width: 4, background: r.status === "processed" ? T.brandPrimary : T.slate300, flexShrink: 0 }}></div>
                <div style={{ padding: "16px", flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 700, color: T.slate500, letterSpacing: 0.5, margin: "0 0 4px", textTransform: "uppercase" }}>{r.filename.split("_")[0] || "REPORT"}</p>
                    <p style={{ fontSize: 16, fontWeight: 600, margin: "0 0 12px", color: T.slate800 }}>{r.filename.length > 20 ? r.filename.slice(0, 20) + "..." : r.filename}</p>
                    <p style={{ fontSize: 13, color: T.slate500, margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
                       📅 {new Date(r.report_date || Date.now()).toLocaleDateString('en-US', { month: 'long', day: '2-digit', year: 'numeric' })}
                    </p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 24 }}>
                     <span style={{ fontSize: 10, fontWeight: 700, background: r.status === "processed" ? T.successBg : T.slate200, color: r.status === "processed" ? T.successText : T.slate600, padding: "4px 10px", borderRadius: 99, display: "flex", alignItems: "center", gap: 4 }}>
                       {r.status === "processed" ? <Icons.Check /> : "↻"} {r.status.toUpperCase()}
                     </span>
                     <span style={{ color: T.slate400 }}>{'>'}</span>
                  </div>
                </div>
              </div>
            ))}

            {/* FAB */}
            <div style={{ position: "fixed", bottom: 80, right: 20, width: 56, height: 56, background: T.brandPrimary, borderRadius: "16px", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 24, boxShadow: "0 8px 16px rgba(0,77,64,0.3)", cursor: "pointer" }}>
              +
            </div>
          </>
        )}
        
        {/* ================= TRENDS (Stub) ================= */}
        {page === "trends" && (
           <div style={{ padding: 40, textAlign: "center", color: T.slate400 }}>Trends coming soon.</div>
        )}

      </main>

      {/* Bottom nav */}
      <nav style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: "#fff", borderTop: `1px solid ${T.slate200}`, display: "flex", justifyContent: "space-around", padding: "12px 0 16px", zIndex: 100 }}>
        {nav.map(([key, icon]) => (
          <button key={key} onClick={() => setPage(key)}
            style={{ background: "none", border: "none", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, cursor: "pointer", color: page === key ? T.brandPrimary : T.slate400, fontSize: 11, fontWeight: 600, fontFamily: T.font, padding: "4px 16px" }}>
            {icon}
            {key.charAt(0).toUpperCase() + key.slice(1)}
          </button>
        ))}
      </nav>

      <style>{`* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: ${T.font}; -webkit-font-smoothing: antialiased; } input:focus { outline: none; border-color: ${T.brandPrimary} !important; box-shadow: 0 0 0 3px ${T.brandLight}; }`}</style>
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
