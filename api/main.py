import io
import random
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.responses import FileResponse, Response

from model_helper import CLASS_NAMES, predict_proba, get_device_info

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent


def _find_model():
    candidates = [
        PROJECT_ROOT / "model" / "saved_model.pth",
        PROJECT_ROOT / "saved_model.pth",
        PROJECT_ROOT.parent / "model" / "saved_model.pth",
        PROJECT_ROOT.parent / "FRONT END" / "model" / "saved_model.pth",
        PROJECT_ROOT.parent / "saved_model.pth",
    ]
    for c in candidates:
        if c.exists():
            return c
    return PROJECT_ROOT / "model" / "saved_model.pth"


def _find_sample_dirs():
    candidates = [
        PROJECT_ROOT / "samples",
        PROJECT_ROOT.parent / "samples",
        PROJECT_ROOT / "dataset",
        PROJECT_ROOT.parent / "dataset",
    ]
    return [c for c in candidates if c.exists()]


MODEL_PATH = _find_model()

SAMPLE_DIRS = {
    "front": ["F_Breakage", "F_Crushed", "F_Normal"],
    "rear": ["R_Breakage", "R_Crushed", "R_Normal"],
    "random": ["F_Breakage", "F_Crushed", "F_Normal", "R_Breakage", "R_Crushed", "R_Normal"],
    "f_breakage": ["F_Breakage"],
    "f_crushed": ["F_Crushed"],
    "f_normal": ["F_Normal"],
    "r_breakage": ["R_Breakage"],
    "r_crushed": ["R_Crushed"],
    "r_normal": ["R_Normal"],
}

FOLDER_TO_CLASS = {
    "F_Breakage": "Front Breakage",
    "F_Crushed": "Front Crushed",
    "F_Normal": "Front Normal",
    "R_Breakage": "Rear Breakage",
    "R_Crushed": "Rear Crushed",
    "R_Normal": "Rear Normal",
}

app = FastAPI(title="CrashSite — Vehicle Damage Detection API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Sample-Class", "X-Sample-File"],
)

SEVERITY = {
    "Front Breakage": {
        "area": "Front",
        "state": "Breakage",
        "condition": "Surface & Panel Damage",
        "severity": "Moderate",
        "action": "Front bumper fascia, grille & headlamp housing repair or replacement",
        "driveability": "Caution — Verify headlamps & latch integrity",
        "driveability_code": "caution",
        "cost_estimate": "$650 – $1,850",
        "repair_hours": "6 – 14 hrs",
        "affected_parts": [
            {"part": "Front Bumper Cover & Fascia", "status": "Repair / Refinish"},
            {"part": "Upper / Lower Grille Assembly", "status": "Inspect Mounts"},
            {"part": "Headlamp & Fog Lamp Lenses", "status": "Alignment Check"},
            {"part": "Front Radar / Parking Sensors", "status": "Recalibrate"},
        ],
    },
    "Front Crushed": {
        "area": "Front",
        "state": "Crushed",
        "condition": "Severe Structural Impact",
        "severity": "Severe",
        "action": "Structural front-end rebuild, crash bar & cooling module replacement",
        "driveability": "Do Not Drive — Structural & Cooling Risk",
        "driveability_code": "unsafe",
        "cost_estimate": "$2,800 – $6,500+",
        "repair_hours": "24 – 48 hrs",
        "affected_parts": [
            {"part": "Front Impact Bar & Crush Cans", "status": "Replace"},
            {"part": "Hood Panel & Primary Latch", "status": "Replace"},
            {"part": "Radiator Support & Condenser", "status": "Pressure Test / Replace"},
            {"part": "Front Rails & Fender Aprons", "status": "Frame Bench Measure"},
        ],
    },
    "Front Normal": {
        "area": "Front",
        "state": "Undamaged",
        "condition": "Factory / Clear Condition",
        "severity": "None",
        "action": "No structural or cosmetic front-end repair required",
        "driveability": "Cleared for Normal Operation",
        "driveability_code": "safe",
        "cost_estimate": "$0",
        "repair_hours": "0 hrs",
        "affected_parts": [
            {"part": "Front Bumper & Grille", "status": "Intact"},
            {"part": "Hood & Fender Panel Gaps", "status": "Within Spec"},
            {"part": "Headlamp Assemblies", "status": "Clear"},
            {"part": "Front Structural Zone", "status": "No Deformation"},
        ],
    },
    "Rear Breakage": {
        "area": "Rear",
        "state": "Breakage",
        "condition": "Surface & Panel Damage",
        "severity": "Moderate",
        "action": "Rear bumper cover, diffuser & tail lamp assembly repair or replacement",
        "driveability": "Caution — Verify tail lamps & trunk seal",
        "driveability_code": "caution",
        "cost_estimate": "$580 – $1,650",
        "repair_hours": "5 – 12 hrs",
        "affected_parts": [
            {"part": "Rear Bumper Cover & Valance", "status": "Repair / Replace"},
            {"part": "Tail Lamp / Reflector Housing", "status": "Inspect / Replace"},
            {"part": "Trunk / Liftgate Weather Seal", "status": "Alignment Check"},
            {"part": "Ultrasonic Rear Park Sensors", "status": "Diagnostic Scan"},
        ],
    },
    "Rear Crushed": {
        "area": "Rear",
        "state": "Crushed",
        "condition": "Severe Structural Impact",
        "severity": "Severe",
        "action": "Rear quarter panel, trunk floor & rear impact bar structural replacement",
        "driveability": "Do Not Drive — Exhaust & Frame Risk",
        "driveability_code": "unsafe",
        "cost_estimate": "$2,500 – $5,900+",
        "repair_hours": "20 – 42 hrs",
        "affected_parts": [
            {"part": "Rear Impact Reinforcement Bar", "status": "Replace"},
            {"part": "Trunk Lid / Tailgate & Hinges", "status": "Replace"},
            {"part": "Rear Quarter & Trunk Floor Pan", "status": "Structural Pull / Section"},
            {"part": "Exhaust Hangers & Fuel Filler Neck", "status": "Safety Inspection"},
        ],
    },
    "Rear Normal": {
        "area": "Rear",
        "state": "Undamaged",
        "condition": "Factory / Clear Condition",
        "severity": "None",
        "action": "No structural or cosmetic rear-end repair required",
        "driveability": "Cleared for Normal Operation",
        "driveability_code": "safe",
        "cost_estimate": "$0",
        "repair_hours": "0 hrs",
        "affected_parts": [
            {"part": "Rear Bumper & Valance", "status": "Intact"},
            {"part": "Trunk / Tailgate Alignment", "status": "Within Spec"},
            {"part": "Tail Lamp Assemblies", "status": "Clear"},
            {"part": "Rear Quarter Panels", "status": "No Deformation"},
        ],
    },
}


@app.get("/health")
def health():
    return {
        "name": "Vehicle Damage Detection API",
        "version": "2.0.0",
        "status": "ok",
        "device": get_device_info(),
        "classes": CLASS_NAMES,
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    top, probs, extras = predict_proba(image, MODEL_PATH, with_gradcam=True)
    meta = SEVERITY[top]

    front_prob = sum(probs.get(c, 0.0) for c in ["Front Breakage", "Front Crushed", "Front Normal"])
    rear_prob = sum(probs.get(c, 0.0) for c in ["Rear Breakage", "Rear Crushed", "Rear Normal"])
    damage_prob = sum(
        probs.get(c, 0.0)
        for c in ["Front Breakage", "Front Crushed", "Rear Breakage", "Rear Crushed"]
    )
    normal_prob = sum(probs.get(c, 0.0) for c in ["Front Normal", "Rear Normal"])

    return {
        "top_class": top,
        "confidence": round(probs[top], 4),
        "area": meta["area"],
        "state": meta["state"],
        "condition": meta["condition"],
        "severity": meta["severity"],
        "action": meta["action"],
        "driveability": meta["driveability"],
        "driveability_code": meta["driveability_code"],
        "cost_estimate": meta["cost_estimate"],
        "repair_hours": meta["repair_hours"],
        "affected_parts": meta["affected_parts"],
        "probabilities": probs,
        "zone_summary": {
            "front_prob": round(front_prob, 4),
            "rear_prob": round(rear_prob, 4),
            "damage_prob": round(damage_prob, 4),
            "normal_prob": round(normal_prob, 4),
        },
        "inference_ms": extras["inference_ms"],
        "image_size": extras["image_size"],
        "heatmap_url": extras["heatmap_url"],
        "hotspot": extras["hotspot"],
        "device": extras["device"],
    }


@app.get("/sample/{view}")
def sample(view: str):
    """Return a random sample photo for the requested view or class preset."""
    dirs = SAMPLE_DIRS.get(view.lower())
    if not dirs:
        raise HTTPException(404, "Unknown sample preset")
    candidates = []
    for root_dir in _find_sample_dirs():
        for d in dirs:
            folder = root_dir / d
            if folder.exists():
                for p in folder.glob("*.jpg"):
                    candidates.append((d, p))
        if candidates:
            break
    if not candidates:
        raise HTTPException(404, "no sample images found")
    chosen_dir, path = random.choice(candidates)
    gt_class = FOLDER_TO_CLASS.get(chosen_dir, chosen_dir)
    return Response(
        path.read_bytes(),
        media_type="image/jpeg",
        headers={
            "X-Sample-Class": gt_class,
            "X-Sample-File": f"{chosen_dir}/{path.name}",
            "Cache-Control": "no-store",
        },
    )


# Mount built React SPA if web/dist exists (for unified single-port cloud deployment)
WEB_DIST = PROJECT_ROOT / "web" / "dist"
if (WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")


@app.get("/")
def root():
    index_file = WEB_DIST / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return health()