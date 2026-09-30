import { useEffect, useRef, useState } from "react";

const CLASS_META = {
  "Front Breakage": { area: "Front", state: "Breakage", tone: "amber" },
  "Front Crushed": { area: "Front", state: "Crushed", tone: "red" },
  "Front Normal": { area: "Front", state: "Undamaged", tone: "green" },
  "Rear Breakage": { area: "Rear", state: "Breakage", tone: "amber" },
  "Rear Crushed": { area: "Rear", state: "Crushed", tone: "red" },
  "Rear Normal": { area: "Rear", state: "Undamaged", tone: "green" },
};

const FALLBACK_SEVERITY = {
  "Front Breakage": {
    label: "Moderate",
    action: "Front bumper fascia, grille & headlamp housing repair or replacement",
    driveability: "Caution — Verify headlamps & latch integrity",
    driveability_code: "caution",
    cost_estimate: "$650 – $1,850",
    repair_hours: "6 – 14 hrs",
    affected_parts: [
      { part: "Front Bumper Cover & Fascia", status: "Repair / Refinish" },
      { part: "Upper / Lower Grille Assembly", status: "Inspect Mounts" },
      { part: "Headlamp & Fog Lamp Lenses", status: "Alignment Check" },
      { part: "Front Radar / Parking Sensors", status: "Recalibrate" },
    ],
  },
  "Front Crushed": {
    label: "Severe",
    action: "Structural front-end rebuild, crash bar & cooling module replacement",
    driveability: "Do Not Drive — Structural & Cooling Risk",
    driveability_code: "unsafe",
    cost_estimate: "$2,800 – $6,500+",
    repair_hours: "24 – 48 hrs",
    affected_parts: [
      { part: "Front Impact Bar & Crush Cans", status: "Replace" },
      { part: "Hood Panel & Primary Latch", status: "Replace" },
      { part: "Radiator Support & Condenser", status: "Pressure Test / Replace" },
      { part: "Front Rails & Fender Aprons", status: "Frame Bench Measure" },
    ],
  },
  "Front Normal": {
    label: "None",
    action: "No structural or cosmetic front-end repair required",
    driveability: "Cleared for Normal Operation",
    driveability_code: "safe",
    cost_estimate: "$0",
    repair_hours: "0 hrs",
    affected_parts: [
      { part: "Front Bumper & Grille", status: "Intact" },
      { part: "Hood & Fender Panel Gaps", status: "Within Spec" },
      { part: "Headlamp Assemblies", status: "Clear" },
      { part: "Front Structural Zone", status: "No Deformation" },
    ],
  },
  "Rear Breakage": {
    label: "Moderate",
    action: "Rear bumper cover, diffuser & tail lamp assembly repair or replacement",
    driveability: "Caution — Verify tail lamps & trunk seal",
    driveability_code: "caution",
    cost_estimate: "$580 – $1,650",
    repair_hours: "5 – 12 hrs",
    affected_parts: [
      { part: "Rear Bumper Cover & Valance", status: "Repair / Replace" },
      { part: "Tail Lamp / Reflector Housing", status: "Inspect / Replace" },
      { part: "Trunk / Liftgate Weather Seal", status: "Alignment Check" },
      { part: "Ultrasonic Rear Park Sensors", status: "Diagnostic Scan" },
    ],
  },
  "Rear Crushed": {
    label: "Severe",
    action: "Rear quarter panel, trunk floor & rear impact bar structural replacement",
    driveability: "Do Not Drive — Exhaust & Frame Risk",
    driveability_code: "unsafe",
    cost_estimate: "$2,500 – $5,900+",
    repair_hours: "20 – 42 hrs",
    affected_parts: [
      { part: "Rear Impact Reinforcement Bar", status: "Replace" },
      { part: "Trunk Lid / Tailgate & Hinges", status: "Replace" },
      { part: "Rear Quarter & Trunk Floor Pan", status: "Structural Pull / Section" },
      { part: "Exhaust Hangers & Fuel Filler Neck", status: "Safety Inspection" },
    ],
  },
  "Rear Normal": {
    label: "None",
    action: "No structural or cosmetic rear-end repair required",
    driveability: "Cleared for Normal Operation",
    driveability_code: "safe",
    cost_estimate: "$0",
    repair_hours: "0 hrs",
    affected_parts: [
      { part: "Rear Bumper & Valance", status: "Intact" },
      { part: "Trunk / Tailgate Alignment", status: "Within Spec" },
      { part: "Tail Lamp Assemblies", status: "Clear" },
      { part: "Rear Quarter Panels", status: "No Deformation" },
    ],
  },
};

const ORDER = [
  "Front Crushed",
  "Front Breakage",
  "Front Normal",
  "Rear Crushed",
  "Rear Breakage",
  "Rear Normal",
];

const SAMPLE_PRESETS = [
  { key: "f_crushed", label: "Front Crushed", tone: "red", short: "F · Crushed" },
  { key: "f_breakage", label: "Front Breakage", tone: "amber", short: "F · Breakage" },
  { key: "f_normal", label: "Front Normal", tone: "green", short: "F · Normal" },
  { key: "r_crushed", label: "Rear Crushed", tone: "red", short: "R · Crushed" },
  { key: "r_breakage", label: "Rear Breakage", tone: "amber", short: "R · Breakage" },
  { key: "r_normal", label: "Rear Normal", tone: "green", short: "R · Normal" },
];

const API_BASE =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

const fmt = (pct) => `${((pct || 0) * 100).toFixed(1)}%`;

export default function App() {
  const [focus, setFocus] = useState(false);
  const [drag, setDrag] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | loading | done | error
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [engineInfo, setEngineInfo] = useState({ status: "checking", device: null });
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showHud, setShowHud] = useState(true);
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.78);
  const [activeTab, setActiveTab] = useState("overview"); // overview | probabilities | dossier
  const [history, setHistory] = useState([]);
  const [clockStr, setClockStr] = useState("");
  const [copied, setCopied] = useState(false);

  const imgRef = useRef(null);
  const replaceRef = useRef(null);
  const revisit = sessionStorage.getItem("cdd_revisit") === "1";

  // Check API health & live clock
  const checkHealth = () => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => {
        setEngineInfo({
          status: "online",
          device: d.device || { device: "CPU", name: "PyTorch Engine" },
        });
      })
      .catch(() => {
        setEngineInfo({ status: "offline", device: null });
      });
  };

  useEffect(() => {
    checkHealth();
    const tick = () => {
      const now = new Date();
      setClockStr(
        now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })
      );
    };
    tick();
    const tId = setInterval(tick, 1000);
    return () => clearInterval(tId);
  }, []);

  const reset = () => {
    setPreviewUrl(null);
    setResult(null);
    setPhase("idle");
    setError("");
    if (imgRef.current) imgRef.current.value = "";
    if (replaceRef.current) replaceRef.current.value = "";
  };

  const runInspection = (imageFile, sampleMeta = null) => {
    const localUrl = URL.createObjectURL(imageFile);
    setPreviewUrl(localUrl);
    setPhase("loading");
    setError("");

    const fd = new FormData();
    fd.append("file", imageFile);

    fetch(`${API_BASE}/predict`, { method: "POST", body: fd })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Server responded ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const enriched = {
          ...data,
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
          fileName: sampleMeta?.file || imageFile.name || "vehicle-frame.jpg",
          groundTruth: sampleMeta?.groundTruth || null,
          imageUrl: localUrl,
        };
        setResult(enriched);
        setHistory((prev) => [enriched, ...prev.slice(0, 11)]);
        setEngineInfo((prev) => ({
          status: "online",
          device: data.device || prev.device,
        }));
        setPhase("done");
      })
      .catch(() => {
        setError(
          "Couldn't reach the inspection engine. Make sure the FastAPI server is running on port 8000."
        );
        setEngineInfo({ status: "offline", device: null });
        setPhase("error");
      });
  };

  const pickSample = (presetKey) => {
    setPhase("loading");
    setError("");
    fetch(`${API_BASE}/sample/${presetKey}`)
      .then(async (r) => {
        if (!r.ok) throw new Error("Failed to fetch sample");
        const gt = r.headers.get("X-Sample-Class");
        const sf = r.headers.get("X-Sample-File");
        const blob = await r.blob();
        return { blob, gt, sf };
      })
      .then(({ blob, gt, sf }) => {
        const f = new File([blob], sf ? sf.replace("/", "_") : `sample-${presetKey}.jpg`, {
          type: "image/jpeg",
        });
        runInspection(f, { groundTruth: gt, file: sf || `sample-${presetKey}.jpg` });
      })
      .catch(() => {
        setError("Couldn't load a sample photo from the API. Check that port 8000 is running.");
        setPhase("error");
      });
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) runInspection(f);
  };

  const restoreFromHistory = (item) => {
    setPreviewUrl(item.imageUrl);
    setResult(item);
    setPhase("done");
    setError("");
  };

  const copyDossier = () => {
    if (!result) return;
    const sev = FALLBACK_SEVERITY[result.top_class] || {};
    const text = [
      `CRASHSITE FORENSIC DAMAGE REPORT`,
      `Timestamp: ${result.timestamp}`,
      `File: ${result.fileName}`,
      `Primary Verdict: ${result.top_class} (${fmt(result.confidence)} confidence)`,
      `Severity: ${result.severity || sev.label}`,
      `Driveability: ${result.driveability || sev.driveability}`,
      `Estimated Labor: ${result.repair_hours || sev.repair_hours}`,
      `Recommended Action: ${result.action || sev.action}`,
    ].join("\n");
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadJson = () => {
    if (!result) return;
    const payload = { ...result };
    delete payload.heatmap_url;
    delete payload.imageUrl;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `crashsite-report-${result.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    if (phase !== "done") return;
    sessionStorage.setItem("cdd_revisit", "1");
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "Escape" || e.key.toLowerCase() === "r") reset();
      if (e.key.toLowerCase() === "h") setShowHeatmap((v) => !v);
      if (e.key.toLowerCase() === "b") setShowHud((v) => !v);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase]);

  const busy = phase === "loading";
  const displayUrl = result?.imageUrl || previewUrl;

  return (
    <div className={`site ${revisit ? "is-load" : ""}`}>
      <header className="topbar">
        <a className="brand" href="#inspect" onClick={(e) => { e.preventDefault(); reset(); }}>
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32">
              <path
                d="M6 18.5 9.5 11h13L26 18.5V22a1.5 1.5 0 0 1-1.5 1.5H23a1.5 1.5 0 0 1-1.5-1.5v-1h-11v1A1.5 1.5 0 0 1 9 23.5H7.5A1.5 1.5 0 0 1 6 22v-3.5Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
              <circle cx="10.5" cy="18.5" r="1.5" fill="currentColor" />
              <circle cx="21.5" cy="18.5" r="1.5" fill="currentColor" />
            </svg>
          </span>
          <div className="brand-text">
            <span className="brand-name">
              Crash<span>Site</span>
            </span>
            <span className="brand-tag">FORENSIC AI v2.0</span>
          </div>
        </a>

        <nav className="topnav">
          <a href="#inspect">
            <span className="nav-num">01</span> Inspection Bay
          </a>
          {history.length > 0 && (
            <a href="#history">
              <span className="nav-num">02</span> Session Log ({history.length})
            </a>
          )}
          <a href="#engine">
            <span className="nav-num">03</span> Neural Engine
          </a>
        </nav>

        <div className="topbar-telemetry">
          <button
            type="button"
            className={`engine-pill is-${engineInfo.status}`}
            onClick={checkHealth}
            title="Click to refresh API status"
          >
            <span className="status-dot" />
            {engineInfo.status === "online"
              ? `ENGINE ONLINE · ${engineInfo.device?.device || "READY"}`
              : engineInfo.status === "checking"
              ? "CONNECTING..."
              : "ENGINE OFFLINE"}
          </button>
          <div className="clock-readout" title="Live Telemetry Clock">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
            </svg>
            <span>{clockStr || "00:00:00"}</span>
          </div>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="hero-badges">
              <span className="job-num">BAY #0809-A · RESNET-50 + GRAD-CAM</span>
              {engineInfo.device?.name && (
                <span className="gpu-badge">{engineInfo.device.name}</span>
              )}
            </div>
            <h1>
              Vehicle damage,
              <br />
              <span>decoded in milliseconds.</span>
            </h1>
            <p className="lede">
              Drop any front or rear three-quarter vehicle photo for an instant
              deep-learning forensic assessment — complete with Grad-CAM spatial
              attention heatmaps, structural severity grading, component impact
              checklists, and estimated repair tiers.
            </p>
          </div>
          <div className="dials" aria-label="Model Telemetry">
            <figure className="dial-cell">
              <span className="dial-value">6</span>
              <span className="dial-label">Damage Classes</span>
            </figure>
            <figure className="dial-cell">
              <span className="dial-value">1.7k</span>
              <span className="dial-label">Training Frames</span>
            </figure>
            <figure className="dial-cell">
              <span className="dial-value">80%</span>
              <span className="dial-label">Validation Acc.</span>
            </figure>
            <figure className="dial-cell is-accent">
              <span className="dial-value">{history.length}</span>
              <span className="dial-label">Session Scans</span>
            </figure>
          </div>
        </section>

        <section className="workbench" id="inspect">
          <div className="section-bar">
            <h2 className="section-title">
              <span className="rung">01</span> THE INSPECTION BAY
            </h2>
            <div className="shortcut-pills">
              <span><kbd>H</kbd> Toggle Heatmap</span>
              <span><kbd>B</kbd> Toggle HUD Box</span>
              <span><kbd>R</kbd> Reset Bay</span>
            </div>
          </div>

          <div className="bay-grid">
            {/* LEFT COLUMN: Viewport + Sample Presets */}
            <div className="upload-area">
              {phase === "idle" || phase === "error" ? (
                <label
                  className={`dropzone ${focus ? "is-focus" : ""} ${drag ? "is-drag" : ""} ${
                    phase === "error" ? "is-error" : ""
                  }`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={onDrop}
                >
                  <input
                    ref={imgRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => e.target.files?.[0] && runInspection(e.target.files[0])}
                    onFocus={() => setFocus(true)}
                    onBlur={() => setFocus(false)}
                  />
                  <div className="hud-corner tl" />
                  <div className="hud-corner tr" />
                  <div className="hud-corner bl" />
                  <div className="hud-corner br" />

                  <span className="dropzone-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <path
                        d="M12 16V5m0 0L7.5 9.5M12 5l4.5 4.5M5 21h14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  <span className="dz-title">
                    {phase === "error" ? "Inspection Interrupted" : "Drop a vehicle photo into the bay"}
                  </span>
                  <span className="dz-sub">
                    {phase === "error"
                      ? error
                      : "Front or rear three-quarter angle · JPG, PNG, or WebP"}
                  </span>
                  <span className="dz-trigger">
                    {phase === "error" ? "Try another photo" : "Browse local files"}
                  </span>
                </label>
              ) : (
                <div
                  className="viewport-wrap"
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={onDrop}
                >
                  {/* Viewport Toolbar */}
                  <div className="viewport-toolbar">
                    <div className="vp-file-meta">
                      <span className="bay-photo-tag">
                        {busy ? "SCANNING..." : "LOCKED"}
                      </span>
                      <span className="vp-filename" title={result?.fileName}>
                        {result?.fileName || "Analyzing vehicle..."}
                      </span>
                      {result?.image_size && (
                        <span className="vp-dim">
                          {result.image_size.width}×{result.image_size.height}
                        </span>
                      )}
                    </div>

                    <div className="vp-controls">
                      {result?.heatmap_url && (
                        <button
                          type="button"
                          className={`vp-toggle ${showHeatmap ? "is-on" : ""}`}
                          onClick={() => setShowHeatmap((v) => !v)}
                          title="Toggle Grad-CAM Neural Attention Heatmap (H)"
                        >
                          <span className="vp-dot" />
                          Grad-CAM
                        </button>
                      )}
                      {result?.hotspot && (
                        <button
                          type="button"
                          className={`vp-toggle ${showHud ? "is-on" : ""}`}
                          onClick={() => setShowHud((v) => !v)}
                          title="Toggle Primary Impact Reticle (B)"
                        >
                          Reticle HUD
                        </button>
                      )}
                      <label className="vp-upload-btn" title="Upload a different photo">
                        <input
                          ref={replaceRef}
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={(e) =>
                            e.target.files?.[0] && runInspection(e.target.files[0])
                          }
                        />
                        Replace
                      </label>
                    </div>
                  </div>

                  {/* Main Image Canvas */}
                  <figure className={`bay-photo ${busy ? "is-scanning" : ""}`}>
                    {displayUrl && (
                      <img
                        className="base-car-img"
                        src={displayUrl}
                        alt="Vehicle submitted for inspection"
                      />
                    )}

                    {/* Grad-CAM Overlay */}
                    {!busy && result?.heatmap_url && showHeatmap && (
                      <img
                        className="heatmap-overlay-img"
                        src={result.heatmap_url}
                        alt="Grad-CAM model attention heatmap"
                        style={{ opacity: heatmapOpacity }}
                      />
                    )}

                    {/* Scanning Laser Effect */}
                    {busy && <div className="laser-sweep" aria-hidden="true" />}

                    {/* Hotspot Bounding Box & Peak Crosshair */}
                    {!busy && result?.hotspot && showHud && (
                      <div
                        className={`hud-target is-${
                          CLASS_META[result.top_class]?.tone || "amber"
                        }`}
                        style={{
                          left: `${result.hotspot.x * 100}%`,
                          top: `${result.hotspot.y * 100}%`,
                          width: `${result.hotspot.w * 100}%`,
                          height: `${result.hotspot.h * 100}%`,
                        }}
                      >
                        <span className="hud-tag">
                          PEAK ROI · {fmt(result.confidence)}
                        </span>
                      </div>
                    )}

                    {/* Ground-truth badge when testing dataset samples */}
                    {!busy && result?.groundTruth && (
                      <div
                        className={`gt-badge ${
                          result.groundTruth === result.top_class
                            ? "is-match"
                            : "is-diff"
                        }`}
                      >
                        <span>DATASET LABEL: {result.groundTruth}</span>
                        <strong>
                          {result.groundTruth === result.top_class
                            ? "✓ EXACT MATCH"
                            : "≠ MODEL DISAGREES"}
                        </strong>
                      </div>
                    )}
                  </figure>

                  {/* Heatmap Opacity & Legend Bar */}
                  {!busy && result?.heatmap_url && showHeatmap && (
                    <div className="heatmap-bar">
                      <span className="hm-label">GRAD-CAM LAYER4 ATTENTION</span>
                      <div className="hm-scale" title="Low to High Neural Activation">
                        <span>Low</span>
                        <i className="hm-gradient" />
                        <span>Peak Impact</span>
                      </div>
                      <label className="hm-slider">
                        <span>Opacity</span>
                        <input
                          type="range"
                          min="0.15"
                          max="1"
                          step="0.05"
                          value={heatmapOpacity}
                          onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
                        />
                      </label>
                    </div>
                  )}
                </div>
              )}

              {/* Enhanced 6-Class Sample Deck */}
              <div className="sample-deck">
                <div className="sample-deck-head">
                  <span className="sample-label">
                    INSTANT DATASET TEST DECK — LOAD A REAL VALIDATION FRAME:
                  </span>
                  <div className="sample-quick-group">
                    <button
                      type="button"
                      className="sample-btn is-primary"
                      onClick={() => pickSample("front")}
                      disabled={busy}
                    >
                      Random Front
                    </button>
                    <button
                      type="button"
                      className="sample-btn is-primary"
                      onClick={() => pickSample("rear")}
                      disabled={busy}
                    >
                      Random Rear
                    </button>
                    <button
                      type="button"
                      className="sample-btn"
                      onClick={() => pickSample("random")}
                      disabled={busy}
                    >
                      Surprise Me
                    </button>
                  </div>
                </div>

                <div className="sample-chips">
                  {SAMPLE_PRESETS.map((preset) => (
                    <button
                      key={preset.key}
                      type="button"
                      className={`preset-chip tone-${preset.tone}`}
                      onClick={() => pickSample(preset.key)}
                      disabled={busy}
                      title={`Load random ${preset.label} sample`}
                    >
                      <span className="chip-dot" />
                      {preset.short}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: Forensic Report */}
            <div className="report-area">
              {busy || phase === "done" ? (
                <div className={`report ${phase === "done" ? "is-done" : ""}`}>
                  <div className="report-head">
                    <div className="rh-left">
                      <span className="rung">FORENSIC TELEMETRY</span>
                      {!busy && result?.inference_ms && (
                        <span className="latency-pill">
                          {result.inference_ms} ms · {result.device?.device || "CPU"}
                        </span>
                      )}
                    </div>
                    <span className={`scan-state ${busy ? "is-running" : "is-clear"}`}>
                      {busy ? (
                        <>
                          ANALYZING TENSORS
                          <span className="dots" aria-hidden="true">
                            <i />
                            <i />
                            <i />
                          </span>
                        </>
                      ) : (
                        "SCAN COMPLETE"
                      )}
                    </span>
                  </div>

                  {busy ? (
                    <div className="loading-stage">
                      <div className="scan-lines" aria-hidden="true">
                        <i style={{ top: "18%" }} />
                        <i style={{ top: "42%" }} />
                        <i style={{ top: "68%" }} />
                        <i style={{ top: "88%" }} />
                      </div>
                      <div className="loading-center">
                        <div className="spinner-ring" />
                        <p className="loading-title">Running ResNet-50 + Grad-CAM</p>
                        <p className="loading-sub">
                          Extracting Layer4 spatial activations & scoring 6 damage classes...
                        </p>
                      </div>
                    </div>
                  ) : (
                    result && (
                      <ResultReport
                        result={result}
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}
                        onCopy={copyDossier}
                        onDownload={downloadJson}
                        copied={copied}
                      />
                    )
                  )}

                  <div className="report-foot">
                    <button className="btn-new" onClick={reset} disabled={busy}>
                      New inspection
                    </button>
                    {!busy && result && (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => pickSample(result.area?.toLowerCase() === "rear" ? "rear" : "front")}
                      >
                        Scan another {result.area || "car"}
                      </button>
                    )}
                    <span className="hint">Press R to reset</span>
                  </div>
                </div>
              ) : (
                <div className="report-placeholder">
                  <span className="scanner-eye" aria-hidden="true">
                    <svg viewBox="0 0 48 48">
                      <rect
                        x="2"
                        y="16"
                        width="44"
                        height="16"
                        rx="3.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                      />
                      <path
                        d="M7 23h4.5l3-4 4.5 8 4-6 3.5 2h7.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                      />
                      <circle cx="38" cy="24" r="2" fill="currentColor" />
                    </svg>
                  </span>
                  <p className="ph-title">Awaiting Vehicle Frame</p>
                  <p className="ph-sub">
                    Drop a photo on the left or click any preset in the Instant
                    Dataset Test Deck to generate a complete forensic damage
                    dossier with Grad-CAM heatmaps.
                  </p>
                  <div className="ph-features">
                    <span>✓ 6-Class Softmax</span>
                    <span>✓ Grad-CAM Heatmap</span>
                    <span>✓ HUD Target Reticle</span>
                    <span>✓ Part Checklist</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* SECTION 02: SESSION INSPECTION LOG */}
        {history.length > 0 && (
          <section className="history-section" id="history">
            <div className="section-bar">
              <h2 className="section-title">
                <span className="rung">02</span> SESSION INSPECTION LOG ({history.length})
              </h2>
              <button
                type="button"
                className="btn-clear-hist"
                onClick={() => setHistory([])}
              >
                Clear Session Log
              </button>
            </div>

            <div className="history-strip">
              {history.map((item) => {
                const meta = CLASS_META[item.top_class] || { tone: "amber", state: item.top_class };
                const isSelected = result?.id === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`history-card ${isSelected ? "is-active" : ""}`}
                    onClick={() => restoreFromHistory(item)}
                  >
                    <div className="hc-thumb">
                      <img src={item.imageUrl} alt={item.top_class} />
                      <span className={`hc-pill is-${meta.tone}`}>{fmt(item.confidence)}</span>
                    </div>
                    <div className="hc-body">
                      <div className="hc-class">{item.top_class}</div>
                      <div className="hc-meta">
                        <span>{item.timestamp}</span>
                        {item.inference_ms && <span>{item.inference_ms}ms</span>}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {/* SECTION 03: THE ENGINE */}
        <section className="engine" id="engine">
          <div className="engine-row">
            <div>
              <h2 className="section-title">
                <span className="rung">03</span> THE NEURAL ENGINE
              </h2>
            </div>
            <p className="engine-copy">
              Powered by a fine-tuned <strong>ResNet-50</strong> convolutional
              architecture. Early residual stages remain frozen to preserve
              universal edge and surface priors, while <code>layer4</code> and a
              dropout-regularized classification head are trained end-to-end on
              automotive damage geometry — paired with real-time{" "}
              <strong>Grad-CAM</strong> backpropagation for explainable visual
              localization.
            </p>
          </div>

          <ol className="pipeline">
            <li className="pipeline-item">
              <span className="pipe-num">STAGE 01</span>
              <h3>Frame Normalization</h3>
              <p>
                Input frames are resampled to 224×224 RGB tensors and
                standardized against ImageNet channel mean & variance.
              </p>
            </li>
            <li className="pipeline-item">
              <span className="pipe-num">STAGE 02</span>
              <h3>Residual Backbone</h3>
              <p>
                50 convolutional layers extract hierarchical panel contours,
                dent reflections, fracture lines, and lamp symmetry.
              </p>
            </li>
            <li className="pipeline-item">
              <span className="pipe-num">STAGE 03</span>
              <h3>Layer4 Grad-CAM</h3>
              <p>
                Gradients flowing into the final 7×7 convolutional block are
                pooled to synthesize a spatial thermal attention overlay.
              </p>
            </li>
            <li className="pipeline-item">
              <span className="pipe-num">STAGE 04</span>
              <h3>Forensic Verdict</h3>
              <p>
                Softmax probabilities across 6 front/rear classes map directly
                to structural severity, driveability, and repair tiers.
              </p>
            </li>
          </ol>

          <div className="model-strip">
            <span>RESNET-50 CNN</span>
            <span>LAYER4 GRAD-CAM</span>
            <span>6 DAMAGE CLASSES</span>
            <span>PYTORCH + FASTAPI</span>
          </div>
        </section>
      </main>

      <footer className="footer">
        <span className="brand-name">
          Crash<span>Site</span>
        </span>
        <p>AI Vehicle Damage Forensic Inspector · ResNet-50 + Grad-CAM</p>
        <p className="legalese">For demonstration & triage purposes.</p>
      </footer>
    </div>
  );
}

function ResultReport({
  result,
  activeTab,
  setActiveTab,
  onCopy,
  onDownload,
  copied,
}) {
  const meta = CLASS_META[result.top_class] ?? {
    area: result.area || "Vehicle",
    state: result.state || "Assessed",
    tone: "amber",
  };
  const fallback = FALLBACK_SEVERITY[result.top_class] ?? {
    label: "—",
    action: "See inspection notes",
    driveability: "Inspection required",
    driveability_code: "caution",
    repair_hours: "TBD",
    affected_parts: [],
  };

  const sevLabel = result.severity || fallback.label;
  const actionText = result.action || fallback.action;
  const driveability = result.driveability || fallback.driveability;
  const driveCode = result.driveability_code || fallback.driveability_code;
  const repairHours = result.repair_hours || fallback.repair_hours;
  const affectedParts = result.affected_parts || fallback.affected_parts;

  const ranked = Object.entries(result.probabilities ?? {})
    .filter(([k]) => ORDER.includes(k))
    .sort((a, b) => b[1] - a[1]);

  const frontProb =
    result.zone_summary?.front_prob ??
    ["Front Breakage", "Front Crushed", "Front Normal"].reduce(
      (acc, k) => acc + (result.probabilities?.[k] || 0),
      0
    );
  const rearProb =
    result.zone_summary?.rear_prob ??
    ["Rear Breakage", "Rear Crushed", "Rear Normal"].reduce(
      (acc, k) => acc + (result.probabilities?.[k] || 0),
      0
    );
  const damageProb =
    result.zone_summary?.damage_prob ??
    ["Front Breakage", "Front Crushed", "Rear Breakage", "Rear Crushed"].reduce(
      (acc, k) => acc + (result.probabilities?.[k] || 0),
      0
    );

  const confPct = Math.round((result.confidence || 0) * 100);
  const radius = 26;
  const circum = 2 * Math.PI * radius;
  const dashOffset = circum - (confPct / 100) * circum;

  return (
    <div className="verdict" key={result.id || result.top_class}>
      {/* Primary Verdict Header */}
      <div className="verdict-row">
        <div className="verdict-main">
          <span className="v-kicker">PRIMARY VERDICT · {meta.area.toUpperCase()} ZONE</span>
          <div className="v-badge-group">
            <span className={`v-badge is-${meta.tone}`}>{meta.state}</span>
            <span className="v-class-sub">{result.top_class}</span>
          </div>
        </div>

        {/* Radial Confidence Gauge */}
        <div className="verdict-conf-gauge">
          <svg className="conf-ring" viewBox="0 0 64 64">
            <circle
              className="conf-ring-bg"
              cx="32"
              cy="32"
              r={radius}
              strokeWidth="5"
            />
            <circle
              className={`conf-ring-fg is-${meta.tone}`}
              cx="32"
              cy="32"
              r={radius}
              strokeWidth="5"
              strokeDasharray={circum}
              strokeDashoffset={dashOffset}
            />
          </svg>
          <div className="verdict-conf">
            <span className="conf-big">{fmt(result.confidence)}</span>
            <span className="conf-label">certainty</span>
          </div>
        </div>
      </div>

      {/* Interactive Vehicle Blueprint Schematic + Telemetry KPI Strip */}
      <div className="schematic-strip">
        <VehicleSchematic area={meta.area} tone={meta.tone} state={meta.state} />
        <div className="kpi-grid">
          <div className="kpi-box">
            <span className="kpi-kicker">SEVERITY</span>
            <strong className={`kpi-val tone-${meta.tone}`}>{sevLabel}</strong>
          </div>
          <div className="kpi-box">
            <span className="kpi-kicker">IMPACT ZONE</span>
            <strong className="kpi-val">{meta.area} Zone</strong>
          </div>
          <div className="kpi-box">
            <span className="kpi-kicker">EST. LABOR</span>
            <strong className="kpi-val">{repairHours}</strong>
          </div>
        </div>
      </div>

      {/* Report Navigation Tabs */}
      <div className="report-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "overview"}
          className={`rtab ${activeTab === "overview" ? "is-active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          Assessment & Parts
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "probabilities"}
          className={`rtab ${activeTab === "probabilities" ? "is-active" : ""}`}
          onClick={() => setActiveTab("probabilities")}
        >
          6-Class Breakdown
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "dossier"}
          className={`rtab ${activeTab === "dossier" ? "is-active" : ""}`}
          onClick={() => setActiveTab("dossier")}
        >
          Export Dossier
        </button>
      </div>

      {/* TAB 1: OVERVIEW & PARTS */}
      {activeTab === "overview" && (
        <div className="tab-pane">
          <div className={`drive-banner is-${driveCode}`}>
            <span className="drive-dot" />
            <div>
              <span className="drive-kicker">DRIVEABILITY STATUS</span>
              <strong>{driveability}</strong>
            </div>
          </div>

          <div className="verdict-action">
            <span className="action-kicker">RECOMMENDED REMEDIATION</span>
            {actionText}
          </div>

          <div className="parts-list">
            <h4 className="bars-title">ZONE COMPONENT CHECKLIST</h4>
            <div className="parts-grid">
              {affectedParts.map((item) => (
                <div className="part-card" key={item.part}>
                  <span className="part-name">{item.part}</span>
                  <span className={`part-status is-${meta.tone}`}>{item.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: 6-CLASS BREAKDOWN */}
      {activeTab === "probabilities" && (
        <div className="tab-pane">
          <div className="zone-split-row">
            <div className="split-meter">
              <div className="sm-labels">
                <span>FRONT VIEW ({fmt(frontProb)})</span>
                <span>REAR VIEW ({fmt(rearProb)})</span>
              </div>
              <div className="sm-track">
                <div
                  className="sm-fill is-amber"
                  style={{ width: `${Math.round(frontProb * 100)}%` }}
                />
              </div>
            </div>
            <div className="split-meter">
              <div className="sm-labels">
                <span>DAMAGE DETECTED ({fmt(damageProb)})</span>
                <span>INTACT ({fmt(1 - damageProb)})</span>
              </div>
              <div className="sm-track">
                <div
                  className={`sm-fill ${damageProb > 0.5 ? "is-red" : "is-green"}`}
                  style={{ width: `${Math.round(damageProb * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <div className="bars">
            <h4 className="bars-title">MODEL CERTAINTY BY CLASS (SOFTMAX)</h4>
            {ranked.map(([name, p], i) => {
              const rowTone = CLASS_META[name]?.tone || "amber";
              return (
                <div
                  className={`bar-row ${i === 0 ? "is-top" : ""}`}
                  key={name}
                  style={{ "--d": `${i * 60}ms` }}
                >
                  <span className="bar-name">{name}</span>
                  <span className="bar-track">
                    <span
                      className={`bar-fill tone-${rowTone}`}
                      style={{ width: `${Math.max(p * 100, 2)}%`, "--i": i }}
                    />
                  </span>
                  <span className="bar-pct">{fmt(p)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: EXPORT & DOSSIER */}
      {activeTab === "dossier" && (
        <div className="tab-pane">
          <div className="dossier-card">
            <div className="dossier-grid">
              <div>
                <span>FRAME FILE</span>
                <strong>{result.fileName}</strong>
              </div>
              <div>
                <span>SCAN TIME</span>
                <strong>{result.timestamp}</strong>
              </div>
              <div>
                <span>RESOLUTION</span>
                <strong>
                  {result.image_size
                    ? `${result.image_size.width}×${result.image_size.height}px`
                    : "Standard"}
                </strong>
              </div>
              <div>
                <span>INFERENCE LATENCY</span>
                <strong>{result.inference_ms ? `${result.inference_ms} ms` : "—"}</strong>
              </div>
              <div>
                <span>PEAK ROI COORDS</span>
                <strong>
                  {result.hotspot
                    ? `X:${Math.round(result.hotspot.peak_x * 100)}% Y:${Math.round(
                        result.hotspot.peak_y * 100
                      )}%`
                    : "Centered"}
                </strong>
              </div>
              <div>
                <span>COMPUTE ENGINE</span>
                <strong>{result.device?.name || "PyTorch ResNet-50"}</strong>
              </div>
            </div>

            <div className="export-actions">
              <button type="button" className="export-btn is-primary" onClick={onCopy}>
                {copied ? "✓ Copied to Clipboard" : "Copy Summary Text"}
              </button>
              <button type="button" className="export-btn" onClick={onDownload}>
                Download JSON Telemetry
              </button>
              <button
                type="button"
                className="export-btn"
                onClick={() => window.print()}
              >
                Print Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function VehicleSchematic({ area, tone, state }) {
  const isFront = area === "Front";
  const isRear = area === "Rear";

  return (
    <div className="car-schematic" title={`${area} Zone: ${state}`}>
      <svg viewBox="0 0 180 76" className="car-svg">
        {/* Subtle blueprint grid */}
        <line x1="0" y1="38" x2="180" y2="38" stroke="rgba(255,255,255,0.07)" strokeDasharray="3 3" />
        <line x1="90" y1="4" x2="90" y2="72" stroke="rgba(255,255,255,0.07)" strokeDasharray="3 3" />

        {/* Front impact zone highlight */}
        {isFront && (
          <path
            className={`zone-glow is-${tone}`}
            d="M12 16 Q6 38 12 60 L54 62 L54 14 Z"
          />
        )}

        {/* Rear impact zone highlight */}
        {isRear && (
          <path
            className={`zone-glow is-${tone}`}
            d="M126 14 L168 16 Q174 38 168 60 L126 62 Z"
          />
        )}

        {/* Top-down Vehicle Chassis Outline */}
        <rect
          x="16"
          y="16"
          width="148"
          height="44"
          rx="14"
          fill="#14100c"
          stroke="rgba(255,255,255,0.35)"
          strokeWidth="1.6"
        />
        {/* Wheels */}
        <rect x="34" y="11" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)" />
        <rect x="34" y="60" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)" />
        <rect x="122" y="11" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)" />
        <rect x="122" y="60" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)" />

        {/* Cabin / Windshield / Rear Glass */}
        <path
          d="M54 22 L74 20 L122 20 L136 22 L136 54 L122 56 L74 56 L54 54 Z"
          fill="rgba(255,255,255,0.05)"
          stroke="rgba(255,255,255,0.25)"
          strokeWidth="1.2"
        />
        <path
          d="M74 21 L118 21 L118 55 L74 55 Z"
          fill="#1b1612"
          stroke="rgba(255,255,255,0.18)"
          strokeWidth="1"
        />

        {/* Active Zone Marker */}
        <circle
          className={`zone-beacon is-${tone}`}
          cx={isFront ? "30" : "150"}
          cy="38"
          r="6"
        />
      </svg>
      <div className="schem-labels">
        <span className={isFront ? `is-active tone-${tone}` : ""}>FRONT</span>
        <span className={isRear ? `is-active tone-${tone}` : ""}>REAR</span>
      </div>
    </div>
  );
}