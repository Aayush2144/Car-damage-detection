import importlib
import json
import random
from datetime import datetime
from pathlib import Path
import streamlit as st
import model_helper

if not hasattr(model_helper, "CLASS_META"):
    importlib.reload(model_helper)

from model_helper import (
    CLASS_META,
    get_device_info,
    predict_detailed,
    render_viewport_image,
)

st.set_page_config(
    page_title="CrashSite — Vehicle Damage Inspection AI",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject Google Font Barlow + CrashSite Forensic v2.0 Stylesheet
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700;800&display=swap');
:root {
  --bg: #110e0b;
  --bg-2: #0c0907;
  --panel: #191511;
  --panel-2: #211b15;
  --line: rgba(255, 255, 255, 0.11);
  --line-strong: rgba(255, 255, 255, 0.22);
  --ink: #f4eee3;
  --ink-dim: #a89f92;
  --ink-faint: #6f675d;
  --amber: #ffb300;
  --amber-soft: rgba(255, 179, 0, 0.14);
  --red: #ff4d52;
  --red-soft: rgba(239, 68, 74, 0.16);
  --green: #52d17c;
  --green-soft: rgba(82, 209, 124, 0.15);
  --hazard: repeating-linear-gradient(
    -45deg,
    rgba(255, 179, 0, 0.045) 0 14px,
    transparent 14px 28px
  );
}

html, body, .stApp {
  background: radial-gradient(circle at 18% 0%, rgba(255, 179, 0, 0.06), transparent 45%), #110e0b !important;
  color: #f4eee3 !important;
  font-family: "Barlow", system-ui, -apple-system, sans-serif !important;
}

header[data-testid="stHeader"] {
  background: transparent !important;
}

.block-container {
  padding-top: 1rem !important;
  padding-bottom: 3rem !important;
  max-width: 1380px !important;
}

/* Topbar */
.cs-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 22px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(17, 14, 11, 0.92);
  backdrop-filter: blur(12px);
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 14px;
}

.cs-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.cs-brand-mark {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #ffc42e, #ff9900);
  border-radius: 9px;
  color: #14100c;
  box-shadow: 0 4px 16px rgba(255, 179, 0, 0.25);
}

.cs-brand-name {
  font-weight: 800;
  font-size: 20px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #f4eee3;
}

.cs-brand-name span {
  color: #ffb300;
}

.cs-brand-tag {
  border: 1px solid rgba(255, 179, 0, 0.45);
  background: rgba(255, 179, 0, 0.1);
  color: #ffb300;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
  padding: 2px 7px;
  border-radius: 4px;
}

.cs-nav {
  display: flex;
  gap: 24px;
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-dim);
}

.cs-nav span b {
  color: #ffb300;
  margin-right: 4px;
}

.cs-engine-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #191511;
  border: 1px solid rgba(82, 209, 124, 0.38);
  color: #b7f0c9;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  padding: 6px 12px;
  border-radius: 999px;
}

.cs-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #52d17c;
  box-shadow: 0 0 8px #52d17c;
}

/* Hero */
.cs-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 32px;
  padding: 12px 4px 34px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.cs-hero-copy {
  max-width: 720px;
}

.cs-badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.cs-job-num {
  background: var(--amber-soft);
  border: 1px solid rgba(255, 179, 0, 0.38);
  color: #ffb300;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  padding: 4px 10px;
  border-radius: 4px;
}

.cs-gpu-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--line-strong);
  color: var(--ink-dim);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  padding: 4px 10px;
  border-radius: 4px;
  text-transform: uppercase;
}

.cs-h1 {
  margin: 0;
  font-size: clamp(34px, 4.6vw, 64px);
  line-height: 0.98;
  font-weight: 800;
  letter-spacing: -0.015em;
  text-transform: uppercase;
  color: #f4eee3;
}

.cs-h1 span {
  color: #ffb300;
}

.cs-lede {
  margin: 16px 0 0;
  font-size: 16px;
  color: var(--ink-dim);
  line-height: 1.55;
}

.cs-dials {
  display: grid;
  grid-template-columns: repeat(4, minmax(105px, 1fr));
  gap: 10px;
}

.cs-dial {
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: linear-gradient(180deg, #211b15, #191511);
  text-align: center;
}

.cs-dial.is-accent {
  border-color: rgba(255, 179, 0, 0.4);
  background: linear-gradient(180deg, rgba(255, 179, 0, 0.14), #191511);
}

.cs-dial-val {
  display: block;
  font-weight: 800;
  font-size: 26px;
  line-height: 1;
  color: #f4eee3;
}

.cs-dial.is-accent .cs-dial-val {
  color: #ffb300;
}

.cs-dial-lbl {
  display: block;
  margin-top: 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-dim);
}

.cs-sec-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--ink-dim);
}

.cs-rung {
  color: #ffb300;
  font-weight: 800;
}

/* Streamlit Buttons Override */
div.stButton > button {
  background: #191511 !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  color: #f4eee3 !important;
  border-radius: 7px !important;
  font-weight: 700 !important;
  font-size: 12px !important;
  letter-spacing: 0.05em !important;
  padding: 0.45rem 0.75rem !important;
  transition: all 0.15s ease !important;
}

div.stButton > button:hover {
  border-color: #ffb300 !important;
  background: #ffb300 !important;
  color: #14100c !important;
}

/* Report Card */
.cs-report-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #191511;
  overflow: hidden;
  margin-bottom: 14px;
}

.cs-report-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.25);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.cs-latency {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--ink-dim);
  margin-left: 8px;
}

.cs-verdict-body {
  padding: 18px;
}

.cs-verdict-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}

.cs-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--ink-faint);
  display: block;
  margin-bottom: 6px;
}

.cs-badge {
  display: inline-block;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 4px 12px;
  border-radius: 7px;
}

.cs-badge.tone-amber {
  background: var(--amber-soft);
  color: #ffb300;
  border: 1px solid rgba(255, 179, 0, 0.45);
}
.cs-badge.tone-red {
  background: var(--red-soft);
  color: #ff7074;
  border: 1px solid rgba(239, 68, 74, 0.5);
}
.cs-badge.tone-green {
  background: var(--green-soft);
  color: #52d17c;
  border: 1px solid rgba(82, 209, 124, 0.45);
}

.cs-schematic-strip {
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #0c0907;
  display: grid;
  grid-template-columns: 165px 1fr;
  gap: 12px;
  align-items: center;
}

.cs-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.cs-kpi-box {
  padding: 8px 10px;
  border-radius: 6px;
  background: #191511;
  border: 1px solid var(--line);
}

.cs-kpi-kicker {
  display: block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--ink-faint);
  margin-bottom: 3px;
}

.cs-kpi-val {
  font-size: 13px;
  font-weight: 700;
  color: #f4eee3;
}

.cs-drive-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 13px;
  border-radius: 8px;
  border: 1px solid var(--line);
  margin-bottom: 12px;
}
.cs-drive-banner.is-safe {
  border-color: rgba(82, 209, 124, 0.4);
  background: rgba(82, 209, 124, 0.08);
}
.cs-drive-banner.is-caution {
  border-color: rgba(255, 179, 0, 0.4);
  background: rgba(255, 179, 0, 0.08);
}
.cs-drive-banner.is-unsafe {
  border-color: rgba(255, 77, 82, 0.45);
  background: rgba(255, 77, 82, 0.1);
}

.cs-action-box {
  padding: 10px 13px;
  border-left: 3px solid #ffb300;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 0 8px 8px 0;
  font-size: 14px;
  margin-bottom: 12px;
}

.cs-parts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.cs-part-card {
  padding: 8px 10px;
  border-radius: 6px;
  background: #0c0907;
  border: 1px solid var(--line);
}

.cs-bar-row {
  display: grid;
  grid-template-columns: 110px 1fr 54px;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.cs-bar-track {
  height: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  overflow: hidden;
}

.cs-bar-fill {
  height: 100%;
  border-radius: 4px;
}

.cs-pipeline {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 20px;
}

.cs-pipe-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 18px;
  background: #191511;
}

.cs-gt-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 12px;
  border-radius: 6px;
  background: #191511;
  border: 1px solid var(--line-strong);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  margin-top: 6px;
}

@media (max-width: 900px) {
  .cs-dials, .cs-pipeline, .cs-schematic-strip {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
""",
    unsafe_allow_html=True,
)

# Resolve sample image directories (checks bundled samples/ first, then dataset/)
HERE = Path(__file__).resolve().parent
SAMPLE_ROOT = HERE / "samples" if (HERE / "samples").exists() else HERE.parent / "dataset"
if not SAMPLE_ROOT.exists() and (HERE / "dataset").exists():
    SAMPLE_ROOT = HERE / "dataset"

FOLDER_TO_CLASS = {
    "F_Breakage": "Front Breakage",
    "F_Crushed": "Front Crushed",
    "F_Normal": "Front Normal",
    "R_Breakage": "Rear Breakage",
    "R_Crushed": "Rear Crushed",
    "R_Normal": "Rear Normal",
}

PRESET_DIRS = {
    "front": ["F_Breakage", "F_Crushed", "F_Normal"],
    "rear": ["R_Breakage", "R_Crushed", "R_Normal"],
    "random": ["F_Breakage", "F_Crushed", "F_Normal", "R_Breakage", "R_Crushed", "R_Normal"],
    "f_crushed": ["F_Crushed"],
    "f_breakage": ["F_Breakage"],
    "f_normal": ["F_Normal"],
    "r_crushed": ["R_Crushed"],
    "r_breakage": ["R_Breakage"],
    "r_normal": ["R_Normal"],
}

if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "history" not in st.session_state:
    st.session_state.history = []
if "last_uploaded_name" not in st.session_state:
    st.session_state.last_uploaded_name = None


def run_scan(img_input, file_label="uploaded-vehicle.jpg", ground_truth=None):
    res = predict_detailed(img_input)
    res["id"] = f"{int(datetime.now().timestamp() * 1000)}"
    res["timestamp"] = datetime.now().strftime("%H:%M:%S")
    res["fileName"] = file_label
    res["groundTruth"] = ground_truth
    st.session_state.current_result = res
    st.session_state.history = [res] + st.session_state.history[:11]


def pick_sample_preset(preset_key):
    folders = PRESET_DIRS.get(preset_key, PRESET_DIRS["random"])
    candidates = []
    for d in folders:
        folder_path = SAMPLE_ROOT / d
        if folder_path.exists():
            for p in folder_path.glob("*.jpg"):
                candidates.append((d, p))
    if candidates:
        chosen_dir, chosen_path = random.choice(candidates)
        gt = FOLDER_TO_CLASS.get(chosen_dir, chosen_dir)
        run_scan(chosen_path, file_label=f"{chosen_dir}/{chosen_path.name}", ground_truth=gt)


# Auto-load an initial sample on very first visit so the dashboard looks rich immediately
if st.session_state.current_result is None and SAMPLE_ROOT.exists():
    pick_sample_preset("f_crushed")

dev_info = get_device_info()
now_clock = datetime.now().strftime("%H:%M:%S")

# ---------------- TOPBAR ----------------
st.markdown(
    f"""
<div class="cs-topbar">
  <div class="cs-brand">
    <div class="cs-brand-mark">
      <svg width="22" height="22" viewBox="0 0 32 32">
        <path d="M6 18.5 9.5 11h13L26 18.5V22a1.5 1.5 0 0 1-1.5 1.5H23a1.5 1.5 0 0 1-1.5-1.5v-1h-11v1A1.5 1.5 0 0 1 9 23.5H7.5A1.5 1.5 0 0 1 6 22v-3.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="10.5" cy="18.5" r="1.5" fill="currentColor"/>
        <circle cx="21.5" cy="18.5" r="1.5" fill="currentColor"/>
      </svg>
    </div>
    <span class="cs-brand-name">Crash<span>Site</span></span>
    <span class="cs-brand-tag">FORENSIC AI v2.0</span>
  </div>
  <div class="cs-nav">
    <span><b>01</b> Inspection Bay</span>
    <span><b>02</b> Session Log ({len(st.session_state.history)})</span>
    <span><b>03</b> Neural Engine</span>
  </div>
  <div class="cs-engine-pill">
    <span class="cs-dot"></span>
    ENGINE ONLINE · {dev_info['device']} · {now_clock}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------- HERO ----------------
st.markdown(
    f"""
<div class="cs-hero">
  <div class="cs-hero-copy">
    <div class="cs-badges">
      <span class="cs-job-num">BAY #0809-A · RESNET-50 + GRAD-CAM</span>
      <span class="cs-gpu-badge">{dev_info['name']}</span>
    </div>
    <h1 class="cs-h1">Vehicle damage,<br><span>decoded in milliseconds.</span></h1>
    <p class="cs-lede">
      Drop any front or rear three-quarter vehicle photo for an instant deep-learning forensic
      assessment — complete with Grad-CAM spatial attention heatmaps, HUD target reticles,
      structural severity grading, component impact checklists, and estimated repair tiers.
    </p>
  </div>
  <div class="cs-dials">
    <div class="cs-dial">
      <span class="cs-dial-val">6</span>
      <span class="cs-dial-lbl">Damage Classes</span>
    </div>
    <div class="cs-dial">
      <span class="cs-dial-val">1.7k</span>
      <span class="cs-dial-lbl">Training Frames</span>
    </div>
    <div class="cs-dial">
      <span class="cs-dial-val">80%</span>
      <span class="cs-dial-lbl">Validation Acc.</span>
    </div>
    <div class="cs-dial is-accent">
      <span class="cs-dial-val">{len(st.session_state.history)}</span>
      <span class="cs-dial-lbl">Session Scans</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------- SECTION 01: THE INSPECTION BAY ----------------
st.markdown(
    '<div class="cs-sec-title"><span class="cs-rung">01</span> THE INSPECTION BAY</div>',
    unsafe_allow_html=True,
)

bay_left, bay_right = st.columns([1.12, 1], gap="large")

with bay_left:
    uploaded = st.file_uploader(
        "Drop a vehicle photo into the bay (Front or Rear three-quarter angle · JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if uploaded is not None:
        sig = f"{uploaded.name}-{uploaded.size}"
        if st.session_state.last_uploaded_name != sig:
            st.session_state.last_uploaded_name = sig
            run_scan(uploaded, file_label=uploaded.name, ground_truth=None)

    # Viewport Controls & Canvas
    res = st.session_state.current_result
    if res is not None:
        vc1, vc2, vc3 = st.columns([1, 1, 1.4])
        with vc1:
            show_heatmap = st.checkbox("🔥 Grad-CAM Heatmap", value=True)
        with vc2:
            show_hud = st.checkbox("🎯 Reticle HUD Box", value=True)
        with vc3:
            hm_opacity = st.slider("Heatmap Opacity", 0.15, 1.0, 0.78, 0.05)

        composed_img = render_viewport_image(
            base_img=res["original_image"],
            overlay_rgba=res["overlay_rgba"],
            hotspot=res["hotspot"],
            top_class=res["top_class"],
            confidence=res["confidence"],
            show_heatmap=show_heatmap,
            heatmap_opacity=hm_opacity,
            show_hud=show_hud,
        )
        st.image(
            composed_img,
            caption=f"LOCKED FRAME: {res['fileName']} ({res['image_size']['width']}×{res['image_size']['height']}px)",
            use_container_width=True,
        )

        if res.get("groundTruth"):
            matched = res["groundTruth"] == res["top_class"]
            match_color = "#52d17c" if matched else "#ffb300"
            match_text = "✓ EXACT MATCH" if matched else "≠ MODEL DISAGREES"
            st.markdown(
                f"""
                <div class="cs-gt-banner" style="border-color:{match_color}66;">
                  <span>DATASET LABEL: <strong>{res['groundTruth']}</strong></span>
                  <strong style="color:{match_color};">{match_text}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 6-Class Instant Dataset Test Deck
    st.markdown(
        '<div style="margin-top:14px; font-size:10.5px; font-weight:700; letter-spacing:0.16em; color:#a89f92;">INSTANT DATASET TEST DECK — LOAD A VALIDATION FRAME:</div>',
        unsafe_allow_html=True,
    )
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("⚡ Random Front", use_container_width=True):
            pick_sample_preset("front")
            st.rerun()
    with q2:
        if st.button("⚡ Random Rear", use_container_width=True):
            pick_sample_preset("rear")
            st.rerun()
    with q3:
        if st.button("🎲 Surprise Me", use_container_width=True):
            pick_sample_preset("random")
            st.rerun()

    p_cols = st.columns(6)
    presets_ui = [
        ("f_crushed", "🔴 F·Crushed"),
        ("f_breakage", "🟡 F·Breakage"),
        ("f_normal", "🟢 F·Normal"),
        ("r_crushed", "🔴 R·Crushed"),
        ("r_breakage", "🟡 R·Breakage"),
        ("r_normal", "🟢 R·Normal"),
    ]
    for idx, (pkey, plabel) in enumerate(presets_ui):
        with p_cols[idx]:
            if st.button(plabel, key=f"preset_{pkey}", use_container_width=True):
                pick_sample_preset(pkey)
                st.rerun()

with bay_right:
    res = st.session_state.current_result
    if res is not None:
        tone = res["tone"]
        stroke_col = "#ff4d52" if tone == "red" else "#52d17c" if tone == "green" else "#ffb300"
        fill_col = (
            "rgba(255,77,82,0.28)"
            if tone == "red"
            else "rgba(82,209,124,0.25)"
            if tone == "green"
            else "rgba(255,179,0,0.28)"
        )
        conf_pct = round(res["confidence"] * 100, 1)
        circum = 163.36
        dash_offset = round(circum - (conf_pct / 100.0) * circum, 2)

        is_front = res["area"] == "Front"
        zone_path = (
            f'<path d="M12 16 Q6 38 12 60 L54 62 L54 14 Z" fill="{fill_col}" stroke="{stroke_col}" stroke-width="1.3"/>'
            if is_front
            else f'<path d="M126 14 L168 16 Q174 38 168 60 L126 62 Z" fill="{fill_col}" stroke="{stroke_col}" stroke-width="1.3"/>'
        )
        beacon_cx = "30" if is_front else "150"

        st.markdown(
            f"""
<div class="cs-report-card">
  <div class="cs-report-head">
    <div>
      <span class="cs-rung">FORENSIC TELEMETRY</span>
      <span class="cs-latency">{res['inference_ms']} ms · {res['device']['device']}</span>
    </div>
    <span style="color:#52d17c;">● SCAN COMPLETE</span>
  </div>
  <div class="cs-verdict-body">
    <div class="cs-verdict-row">
      <div>
        <span class="cs-kicker">PRIMARY VERDICT · {res['area'].upper()} ZONE</span>
        <span class="cs-badge tone-{tone}">{res['state']}</span>
        <span style="margin-left:10px; font-size:14px; font-weight:600; color:#a89f92;">{res['top_class']}</span>
      </div>
      <div style="display:flex; align-items:center; gap:10px;">
        <svg width="54" height="54" viewBox="0 0 64 64" style="transform:rotate(-90deg);">
          <circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="5"/>
          <circle cx="32" cy="32" r="26" fill="none" stroke="{stroke_col}" stroke-width="5" stroke-linecap="round" stroke-dasharray="{circum}" stroke-dashoffset="{dash_offset}"/>
        </svg>
        <div style="text-align:right;">
          <div style="font-size:26px; font-weight:800; line-height:1;">{conf_pct}%</div>
          <div style="font-size:9.5px; font-weight:700; letter-spacing:0.18em; color:#6f675d; margin-top:3px;">CERTAINTY</div>
        </div>
      </div>
    </div>
    <div class="cs-schematic-strip">
      <div style="text-align:center;">
        <svg viewBox="0 0 180 76" style="width:100%; height:56px;">
          <line x1="0" y1="38" x2="180" y2="38" stroke="rgba(255,255,255,0.07)" stroke-dasharray="3 3"/>
          <line x1="90" y1="4" x2="90" y2="72" stroke="rgba(255,255,255,0.07)" stroke-dasharray="3 3"/>
          {zone_path}
          <rect x="16" y="16" width="148" height="44" rx="14" fill="#14100c" stroke="rgba(255,255,255,0.35)" stroke-width="1.6"/>
          <rect x="34" y="11" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)"/>
          <rect x="34" y="60" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)"/>
          <rect x="122" y="11" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)"/>
          <rect x="122" y="60" width="24" height="5" rx="2" fill="rgba(255,255,255,0.45)"/>
          <path d="M54 22 L74 20 L122 20 L136 22 L136 54 L122 56 L74 56 L54 54 Z" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.2"/>
          <circle cx="{beacon_cx}" cy="38" r="6" fill="{stroke_col}"/>
        </svg>
        <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; letter-spacing:0.16em; padding:0 8px; color:#6f675d;">
          <span style="color:{stroke_col if is_front else '#6f675d'};">FRONT</span>
          <span style="color:{stroke_col if not is_front else '#6f675d'};">REAR</span>
        </div>
      </div>
      <div class="cs-kpi-grid">
        <div class="cs-kpi-box">
          <span class="cs-kpi-kicker">SEVERITY</span>
          <strong class="cs-kpi-val" style="color:{stroke_col};">{res['severity']}</strong>
        </div>
        <div class="cs-kpi-box">
          <span class="cs-kpi-kicker">IMPACT ZONE</span>
          <strong class="cs-kpi-val">{res['area']} Zone</strong>
        </div>
        <div class="cs-kpi-box">
          <span class="cs-kpi-kicker">EST. LABOR</span>
          <strong class="cs-kpi-val">{res['repair_hours']}</strong>
        </div>
      </div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        tab_over, tab_probs, tab_export = st.tabs(
            ["🛠️ Assessment & Parts", "📊 6-Class Breakdown", "📁 Export Dossier"]
        )

        with tab_over:
            parts_html = "".join(
                f"""
                <div class="cs-part-card">
                  <div style="font-size:12px; font-weight:600; color:#f4eee3;">{p['part']}</div>
                  <div style="font-size:10px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:{stroke_col}; margin-top:2px;">{p['status']}</div>
                </div>
                """
                for p in res["affected_parts"]
            )
            st.markdown(
                f"""
                <div class="cs-drive-banner is-{res['driveability_code']}">
                  <span style="width:10px; height:10px; border-radius:50%; background:{stroke_col}; box-shadow:0 0 8px {stroke_col}; flex-shrink:0;"></span>
                  <div>
                    <span style="display:block; font-size:9px; font-weight:700; letter-spacing:0.16em; color:#a89f92;">DRIVEABILITY STATUS</span>
                    <strong>{res['driveability']}</strong>
                  </div>
                </div>
                <div class="cs-action-box">
                  <span style="display:block; font-size:9.5px; font-weight:700; letter-spacing:0.18em; color:#ffb300; margin-bottom:2px;">RECOMMENDED REMEDIATION</span>
                  {res['action']}
                </div>
                <div style="font-size:10px; font-weight:700; letter-spacing:0.18em; color:#6f675d; margin-bottom:8px;">ZONE COMPONENT CHECKLIST</div>
                <div class="cs-parts-grid">{parts_html}</div>
                """,
                unsafe_allow_html=True,
            )

        with tab_probs:
            zs = res["zone_summary"]
            f_pct = round(zs["front_prob"] * 100, 1)
            r_pct = round(zs["rear_prob"] * 100, 1)
            d_pct = round(zs["damage_prob"] * 100, 1)
            n_pct = round(zs["normal_prob"] * 100, 1)
            dmg_col = "#ff4d52" if d_pct >= 50 else "#52d17c"

            ranked = sorted(res["probabilities"].items(), key=lambda x: x[1], reverse=True)
            bars_html = ""
            for i, (cls_name, prob) in enumerate(ranked):
                p_val = round(prob * 100, 1)
                w_val = max(p_val, 2.0)
                c_tone = CLASS_META.get(cls_name, {}).get("tone", "amber")
                b_col = (
                    "#ff4d52"
                    if (i == 0 and c_tone == "red")
                    else "#52d17c"
                    if (i == 0 and c_tone == "green")
                    else "#ffb300"
                    if i == 0
                    else "rgba(255,255,255,0.28)"
                )
                name_wt = "700" if i == 0 else "500"
                name_col = "#f4eee3" if i == 0 else "#a89f92"
                bars_html += f"""
                <div class="cs-bar-row">
                  <span style="font-size:12.5px; font-weight:{name_wt}; color:{name_col}; text-align:right;">{cls_name}</span>
                  <div class="cs-bar-track"><div class="cs-bar-fill" style="width:{w_val}%; background:{b_col};"></div></div>
                  <span style="font-size:12.5px; font-weight:600; text-align:right;">{p_val}%</span>
                </div>
                """

            st.markdown(
                f"""
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">
                  <div style="padding:9px 11px; border-radius:7px; background:#0c0907; border:1px solid var(--line);">
                    <div style="display:flex; justify-content:space-between; font-size:9.5px; font-weight:700; color:#a89f92; margin-bottom:6px;">
                      <span>FRONT ({f_pct}%)</span><span>REAR ({r_pct}%)</span>
                    </div>
                    <div class="cs-bar-track"><div class="cs-bar-fill" style="width:{f_pct}%; background:#ffb300;"></div></div>
                  </div>
                  <div style="padding:9px 11px; border-radius:7px; background:#0c0907; border:1px solid var(--line);">
                    <div style="display:flex; justify-content:space-between; font-size:9.5px; font-weight:700; color:#a89f92; margin-bottom:6px;">
                      <span>DAMAGED ({d_pct}%)</span><span>INTACT ({n_pct}%)</span>
                    </div>
                    <div class="cs-bar-track"><div class="cs-bar-fill" style="width:{d_pct}%; background:{dmg_col};"></div></div>
                  </div>
                </div>
                <div style="font-size:10px; font-weight:700; letter-spacing:0.18em; color:#6f675d; margin-bottom:8px;">MODEL CERTAINTY BY CLASS (SOFTMAX)</div>
                {bars_html}
                """,
                unsafe_allow_html=True,
            )

        with tab_export:
            export_dict = {
                "id": res["id"],
                "timestamp": res["timestamp"],
                "fileName": res["fileName"],
                "top_class": res["top_class"],
                "confidence": round(res["confidence"], 4),
                "severity": res["severity"],
                "driveability": res["driveability"],
                "repair_hours": res["repair_hours"],
                "action": res["action"],
                "probabilities": res["probabilities"],
                "zone_summary": res["zone_summary"],
                "hotspot": res["hotspot"],
                "inference_ms": res["inference_ms"],
                "device": res["device"],
            }
            st.json(export_dict, expanded=False)
            st.download_button(
                "⬇️ Download JSON Forensic Telemetry",
                data=json.dumps(export_dict, indent=2),
                file_name=f"crashsite-report-{res['id']}.json",
                mime="application/json",
                use_container_width=True,
            )

# ---------------- SECTION 02: SESSION INSPECTION LOG ----------------
if len(st.session_state.history) > 1:
    st.markdown("<hr style='border-color:rgba(255,255,255,0.1); margin:28px 0;'>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="cs-sec-title"><span class="cs-rung">02</span> SESSION INSPECTION LOG ({len(st.session_state.history)})</div>',
        unsafe_allow_html=True,
    )
    h_cols = st.columns(min(6, len(st.session_state.history)))
    for idx, item in enumerate(st.session_state.history[:6]):
        with h_cols[idx]:
            st.image(item["original_image"], use_container_width=True)
            st.caption(f"**{item['top_class']}** · {item['confidence']*100:.1f}% ({item['timestamp']})")

# ---------------- SECTION 03: THE NEURAL ENGINE ----------------
st.markdown("<hr style='border-color:rgba(255,255,255,0.1); margin:28px 0;'>", unsafe_allow_html=True)
st.markdown(
    """
<div class="cs-sec-title"><span class="cs-rung">03</span> THE NEURAL ENGINE</div>
<p style="color:#a89f92; max-width:70ch; margin:0;">
  Powered by a fine-tuned <strong>ResNet-50</strong> convolutional architecture. Early residual stages remain frozen to preserve universal edge and surface priors, while <code style="color:#ffb300;">layer4</code> and a dropout-regularized classification head are trained end-to-end on automotive damage geometry — paired with real-time <strong>Grad-CAM</strong> backpropagation for explainable visual localization.
</p>
<div class="cs-pipeline">
  <div class="cs-pipe-card">
    <div style="font-size:11px; font-weight:800; letter-spacing:0.16em; color:#ffb300; margin-bottom:8px;">STAGE 01</div>
    <div style="font-size:17px; font-weight:700; margin-bottom:6px;">Frame Normalization</div>
    <div style="font-size:13.5px; color:#a89f92;">Input frames are resampled to 224×224 RGB tensors and standardized against ImageNet channel statistics.</div>
  </div>
  <div class="cs-pipe-card">
    <div style="font-size:11px; font-weight:800; letter-spacing:0.16em; color:#ffb300; margin-bottom:8px;">STAGE 02</div>
    <div style="font-size:17px; font-weight:700; margin-bottom:6px;">Residual Backbone</div>
    <div style="font-size:13.5px; color:#a89f92;">50 convolutional layers extract hierarchical panel contours, dent reflections, fracture lines, and lamp symmetry.</div>
  </div>
  <div class="cs-pipe-card">
    <div style="font-size:11px; font-weight:800; letter-spacing:0.16em; color:#ffb300; margin-bottom:8px;">STAGE 03</div>
    <div style="font-size:17px; font-weight:700; margin-bottom:6px;">Layer4 Grad-CAM</div>
    <div style="font-size:13.5px; color:#a89f92;">Gradients flowing into the final 7×7 convolutional block are pooled to synthesize a spatial thermal attention overlay.</div>
  </div>
  <div class="cs-pipe-card">
    <div style="font-size:11px; font-weight:800; letter-spacing:0.16em; color:#ffb300; margin-bottom:8px;">STAGE 04</div>
    <div style="font-size:17px; font-weight:700; margin-bottom:6px;">Forensic Verdict</div>
    <div style="font-size:13.5px; color:#a89f92;">Softmax probabilities across 6 front/rear classes map directly to structural severity, driveability, and repair tiers.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
