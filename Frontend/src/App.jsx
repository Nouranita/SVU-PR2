console.log(" RUNNING App.jsx (NEW) -", new Date().toISOString());

import { useEffect, useMemo, useRef, useState } from "react";
import jsPDF from "jspdf";
//import LoginPage from ".//loginPage";
import { clearToken, getToken, loginWithPassword } from "./auth"; //authHeader

// =================== CONFIG ===================
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

// =================== SMALL UI HELPERS ===================
function prettyLabel(s) {
  if (!s) return "";
  return String(s).replaceAll("_", " ").replaceAll("-", " ");
}

function severityFromPct(pct) {
  if (pct >= 80) return { text: "High", cls: "border-rose-400/40 text-rose-200 bg-rose-900/30" };
  if (pct >= 50) return { text: "Medium", cls: "border-amber-400/40 text-amber-200 bg-amber-900/30" };
  return { text: "Low", cls: "border-sky-400/40 text-sky-200 bg-sky-900/30" };
}

function Donut({ value }) {
  // simple donut (no external libs)
  const r = 46;
  const c = 2 * Math.PI * r;
  const dash = (value / 100) * c;

  return (
    <svg width="140" height="140" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="10" />
      <circle
        cx="60"
        cy="60"
        r={r}
        fill="none"
        stroke="rgba(168,85,247,0.9)"
        strokeWidth="10"
        strokeDasharray={`${dash} ${c - dash}`}
        strokeLinecap="round"
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="56" textAnchor="middle" fontSize="20" fill="white" fontWeight="700">
        {value}%
      </text>
      <text x="60" y="76" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.65)">
        Confidence
      </text>
    </svg>
  );
}

// =================== LOGIN ===================
function Login({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await loginWithPassword(API_BASE, username, password);
      onLoggedIn();
    } catch (ex) {
      setErr(ex?.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen text-white flex items-center justify-center px-6">
      <div className="fixed inset-0 -z-10 bg-[#05050a]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(168,85,247,0.35),transparent_40%),radial-gradient(circle_at_80%_30%,rgba(59,130,246,0.25),transparent_45%),radial-gradient(circle_at_40%_90%,rgba(236,72,153,0.18),transparent_45%)]" />

      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur-xl"
      >
        <h2 className="text-center text-xl tracking-[0.25em] text-white/80">LOGIN</h2>

        <div className="mt-8 space-y-6">
          <div className="border-b border-white/20 pb-2">
            <label className="text-xs text-white/60">Username</label>
            <input
              className="mt-2 w-full bg-transparent outline-none text-white/90"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>

          <div className="border-b border-white/20 pb-2">
            <label className="text-xs text-white/60">Password</label>
            <input
              className="mt-2 w-full bg-transparent outline-none text-white/90"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>


          {err && <div className="text-sm text-rose-300">{err}</div>}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-2xl bg-white/10 hover:bg-white/15 border border-white/10 py-3 font-semibold tracking-wide disabled:opacity-50"
          >
            {loading ? "Logging in..." : "LOGIN"}
          </button>

          <p className="text-xs text-white/50 ">
            The system is locally hosted and protected using JWT authentication.
                  Only one superuser account is created for evaluation.
          </p>
        </div>
      </form>
    </div>
  );
}

// =================== MAIN APP ===================
function SDPSApp({ onLogout }) {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function onFileChange(e) {
    const f = e.target.files?.[0];
    if (!f) return;

    if (!f.type.startsWith("image/")) {
      setErr("Please upload an image file.");
      setFile(null);
      setResult(null);
      e.target.value = "";
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setErr("Image is too large. Maximum allowed size is 10MB.");
      setFile(null);
      setResult(null);
      e.target.value = "";
      return;
    }

    setErr("");
    setFile(f);
    setResult(null);
  }
  
      const confidenceColor = (pct) => {
        // darkest when most confident
        if (pct >= 90) return "#8a0030"; // very dark maroon
        if (pct >= 75) return "#ae1f51"; // dark maroon
        if (pct >= 60) return "#d44678"; // maroon
        if (pct >= 40) return "#f7a6c0"; // lighter maroon
        return "#ffd0df";               // lightest in this palette
    };
    

    
    function fileToDataUrl(f) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result));
            reader.onerror = reject;
            reader.readAsDataURL(f);
        });
    }

async function downloadPDF() {
        console.log("download Function is called!");
        if (!result) {console.log("No results!");  return;}

        const doc = new jsPDF();
        const now = new Date();

        doc.setFontSize(16);
        doc.text("Lung Diseases Prediction Report", 14, 18);

        doc.setFontSize(10);
        doc.text(`Generated: ${now.toLocaleString()}`, 14, 26);

        doc.setFontSize(12);
        doc.text(`File: ${file?.name || "N/A"}`, 14, 38);

        doc.setFontSize(13);
        doc.text(`Top Prediction: ${top1Label}`, 14, 50);
        doc.text(`Confidence: ${top1Pct}%`, 14, 58);

        doc.setFontSize(12);
        doc.text("Top 3 Predictions:", 14, 72);

        let y = 80;
        top3.forEach(([label, p]) => {
            const pct = Math.round(Number(p) * 100);
            doc.text(`- ${label}: ${pct}%`, 18, y);
            y += 8;
        });
    // Add preview image
        if (file) {
            try {
                const dataUrl = await fileToDataUrl(file);
                // detect format for jsPDF
                const fmt = file.type.includes("png") ? "PNG" : "JPEG";
                doc.text("X-ray Preview:", 14, y + 6);
                doc.addImage(dataUrl, fmt, 14, y + 12, 80, 80);
            } catch {
                // ignore image embedding errors
            }
        }

        doc.save(`prediction_${Date.now()}.pdf`);
    }

function authHeader() {
  const token = localStorage.getItem("access_token"); // adjust key if different
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readResponse(res) {
  const ct = res.headers.get("content-type") || "";
  const text = await res.text();

  // If JSON parse it, Otherwise return text.
  if (ct.includes("application/json")) {
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`Invalid JSON from server (status ${res.status}).`);
    }
  }
  // Non-JSON response
  throw new Error(`Server returned non-JSON (status ${res.status}): ${text.slice(0, 200)}`);
}

async function handlePredict() {
  try {
    setErr("");
    setLoading(true);

    const formData = new FormData();
    formData.append("image", file); // MUST be image to match Django

    const res = await fetch(`${API_BASE}/api/predict/`, {
      method: "POST",
      headers: {
        ...authHeader(),
      },
      body: formData,
    });

    const data = await readResponse(res);

    if (!res.ok) {
      // DRF 401 often returns {detail: "..."}
      throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);
    }

    setResult(data);
  } catch (e) {
    setErr(String(e.message || e));
  } finally {
    setLoading(false);
  }
}

    function resetAll() {
        setErr("");
        setFile(null);
        setResult(null);
        setLoading(false);

        // clears the actual file input so I can re-pick same file
        if (fileInputRef.current) fileInputRef.current.value = "";
    }

  const top3 = useMemo(() => {
    const probs = result?.probs || result?.probabilities || {};
    const entries = Object.entries(probs)
      .map(([k, v]) => [k, Number(v)])
      .filter((x) => Number.isFinite(x[1]))
      .sort((a, b) => b[1] - a[1]);
    return entries.slice(0, 3);
  }, [result]);

  const top1 = top3[0] || ["", 0];
  const top1Label = top1[0];
  const top1Pct = Math.round((top1[1] || 0) * 100);
  const sev = severityFromPct(top1Pct);

  const Stroke = confidenceColor(top1Pct);

  return (
    <div className="min-h-screen text-white">
      {/* Background */}
      <div className="fixed inset-0 -z-10 bg-[#05050a]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(168,85,247,0.35),transparent_40%),radial-gradient(circle_at_80%_30%,rgba(59,130,246,0.25),transparent_45%),radial-gradient(circle_at_40%_90%,rgba(236,72,153,0.18),transparent_45%)]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:28px_28px] opacity-40" />

      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight">LUNG DISEASES PREDICTION SYSTEM</h1>
              <p className="mt-2 text-white/70">Upload a Chest X-ray and get top predictions with confidence.</p>
            </div>

            <button
              onClick={onLogout}
              className="rounded-xl border border-white/10 bg-white/10 px-4 py-2 text-sm hover:bg-white/15"
            >
              Logout
            </button>
          </div>

          <p className="mt-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/70">
            <span className="font-medium text-white/80">Note:</span> This system is for educational/experimental use and does not provide a medical diagnosis.
                                                                     Always consult a qualified clinician.
          </p>

          {/* Upload */}
          <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm text-white/60">
                  Select a chest X-ray image <br />
                  (Maximum allowed size is 10MB)
                </p>
                <p className="mt-1 text-sm">
                  {file ? <span className="text-white/90">{file.name}</span> : <span className="text-white/40">No file selected</span>}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <label className={`cursor-pointer rounded-xl border border-white/10 bg-white/10 px-4 py-2 text-sm hover:bg-white/15 ${loading ? "pointer-events-none opacity-50" : ""}`}>
                  Browse
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.png,.jpg,.jpeg,.bmp,.webp"
                    className="hidden"
                    onChange={onFileChange}
                  />
                </label>

                <button
                  onClick={handlePredict}
                  disabled={loading || !file}
                  className="rounded-xl bg-violet-600 px-5 py-2 text-sm font-medium hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? "Predicting..." : "Analyze X-ray"}
                </button>

                <button
                  type="button"
                  onClick={resetAll}
                  disabled={loading || !file}
                  className="rounded-xl bg-rose-950 px-4 py-2 text-sm text-white hover:bg-rose-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Clear
                </button>
              </div>
            </div>

            {err && <p className="mt-4 text-sm text-red-400">{err}</p>}
            {loading && <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/80">Analyzing… please wait.</div>}

            {result && (
              <div className="mt-6 flex flex-col items-center justify-center gap-3">
                <Donut value={top1Pct} />
                <p className="text-xs text-white/50">Confidence reflects the model’s certainty, not a confirmed diagnosis.</p>
              </div>
            )}
          </div>

          {/* Results */}
          {result && (
            <div className="mt-8">
              {/* 2-column grid (ONLY the 2 cards) */}
              <div className="grid gap-6 md:grid-cols-2">
                {/* LEFT: Prediction */}
                <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
                  <p className="text-sm text-white/70">Prediction</p>

                  <div className="mt-2 flex flex-wrap items-center gap-2 text-lg font-semibold">
                    <span>{prettyLabel(top1Label)}</span>
                    <span className="text-white/60 font-normal">— {top1Pct}% confidence</span>
                    <span className={`ml-1 rounded-full border px-2 py-0.5 text-xs ${sev.cls}`}>{sev.text}</span>
                  </div>

                  <div className="mt-6">
                    <p className="text-sm text-white/70">Top Predictions</p>
                    <div className="mt-3 space-y-3">
                      {top3.map(([label, p], idx) => {
                        const pct = Math.round(p * 100);
                        const bar = idx === 0 ? "bg-rose-500" : idx === 1 ? "bg-fuchsia-500" : "bg-slate-400";
                        return (
                          <div key={label} className="rounded-xl border border-white/10 bg-white/5 p-3">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-white/90">{prettyLabel(label)}</span>
                              <span className="text-white/70">{pct}%</span>
                            </div>
                            <div className="mt-2 h-2 w-full rounded-full bg-white/10">
                              <div className={`h-2 rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <details className="mt-5 text-xs text-white/60">
                    <summary className="cursor-pointer hover:text-white/80">Show Payload</summary>
                    <pre className="mt-2 rounded-lg bg-black/40 p-3 overflow-auto">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </details>
                </div>

                {/* RIGHT: X-ray preview */}
                <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
                  <p className="text-sm text-white/70">X-ray preview</p>

                  <div className="mt-3 overflow-hidden rounded-2xl border border-white/10 bg-black/40">
                    {previewUrl ? (
                      <img src={previewUrl} alt="X-ray preview" className="h-72 w-full object-contain" />
                    ) : (
                      <div className="flex h-72 items-center justify-center text-sm text-white/40">
                        No image selected
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex justify-center">
                    <button
                      type="button"
                      onClick={downloadPDF}
                      className="rounded-xl border border-white/50 bg-white/30 px-4 py-2 text-sm hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Download Prediction Report as PDF
                    </button>
                  </div>
                </div>
              </div>

              {/* Education block */}
              {result?.education && (
                <div className="mt-3 p-4 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-lg font-semibold mb-2">
                    Educational summary for: {prettyLabel(result.education.for_label ?? result.prediction)}
                  </h3>
                  <div className="space-y-3 text-sm leading-relaxed text-white/90">
                    <div>
                      <div className="font-semibold text-white">1) Factors that may influence this result</div>
                      <div className="text-white/80 whitespace-pre-line">{result.education.factors}</div>
                    </div>
                    <div>
                      <div className="font-semibold text-white">2) Possibility of improving + recommendations</div>
                      <div className="text-white/80 whitespace-pre-line">{result.education.reversibility}</div>
                    </div>
                    <div>
                      <div className="font-semibold text-white">3) Potential complications if neglected</div>
                      <div className="text-white/80 whitespace-pre-line">{result.education.complications}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =================== SINGLE DEFAULT EXPORT ===================
export default function App() {
  const [authed, setAuthed] = useState(!!getToken());

  function onLoggedIn() {
    setAuthed(true);
  }

  function onLogout() {
    clearToken();
    setAuthed(false);
  }

  return authed ? <SDPSApp onLogout={onLogout} /> : <Login onLoggedIn={onLoggedIn} />;
}
