import time
from pathlib import Path
import torch
import torch.nn.functional as F
from torch import nn
from torchvision import models, transforms
from PIL import Image, ImageDraw

trained_model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class_names = [
    "Front Breakage",
    "Front Crushed",
    "Front Normal",
    "Rear Breakage",
    "Rear Crushed",
    "Rear Normal",
]

CLASS_META = {
    "Front Breakage": {
        "area": "Front",
        "state": "Breakage",
        "tone": "amber",
        "color_rgb": (255, 179, 0),
        "severity": "Moderate",
        "driveability": "Caution — Verify headlamps & latch integrity",
        "driveability_code": "caution",
        "cost_estimate": "$650 – $1,850",
        "repair_hours": "6 – 14 hrs",
        "action": "Front bumper fascia, grille & headlamp housing repair or replacement",
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
        "tone": "red",
        "color_rgb": (255, 77, 82),
        "severity": "Severe",
        "driveability": "Do Not Drive — Structural & Cooling Risk",
        "driveability_code": "unsafe",
        "cost_estimate": "$2,800 – $6,500+",
        "repair_hours": "24 – 48 hrs",
        "action": "Structural front-end rebuild, crash bar & cooling module replacement",
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
        "tone": "green",
        "color_rgb": (82, 209, 124),
        "severity": "None",
        "driveability": "Cleared for Normal Operation",
        "driveability_code": "safe",
        "cost_estimate": "$0",
        "repair_hours": "0 hrs",
        "action": "No structural or cosmetic front-end repair required",
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
        "tone": "amber",
        "color_rgb": (255, 179, 0),
        "severity": "Moderate",
        "driveability": "Caution — Verify tail lamps & trunk seal",
        "driveability_code": "caution",
        "cost_estimate": "$580 – $1,650",
        "repair_hours": "5 – 12 hrs",
        "action": "Rear bumper cover, diffuser & tail lamp assembly repair or replacement",
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
        "tone": "red",
        "color_rgb": (255, 77, 82),
        "severity": "Severe",
        "driveability": "Do Not Drive — Exhaust & Frame Risk",
        "driveability_code": "unsafe",
        "cost_estimate": "$2,500 – $5,900+",
        "repair_hours": "20 – 42 hrs",
        "action": "Rear quarter panel, trunk floor & rear impact bar structural replacement",
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
        "tone": "green",
        "color_rgb": (82, 209, 124),
        "severity": "None",
        "driveability": "Cleared for Normal Operation",
        "driveability_code": "safe",
        "cost_estimate": "$0",
        "repair_hours": "0 hrs",
        "action": "No structural or cosmetic rear-end repair required",
        "affected_parts": [
            {"part": "Rear Bumper & Valance", "status": "Intact"},
            {"part": "Trunk / Tailgate Alignment", "status": "Within Spec"},
            {"part": "Tail Lamp Assemblies", "status": "Clear"},
            {"part": "Rear Quarter Panels", "status": "No Deformation"},
        ],
    },
}


class CarClassifierResNet(nn.Module):
    def __init__(self, num_classes=6):
        super().__init__()
        self.model = models.resnet50(weights="DEFAULT")
        for param in self.model.parameters():
            param.requires_grad = False

        for param in self.model.layer4.parameters():
            param.requires_grad = True

        self.model.fc = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(self.model.fc.in_features, num_classes),
        )

    def forward(self, x):
        return self.model(x)


def _resolve_model_path():
    here = Path(__file__).resolve().parent
    candidates = [
        here / "model" / "saved_model.pth",
        here / "saved_model.pth",
        here.parent / "model" / "saved_model.pth",
        here.parent / "saved_model.pth",
        here / "FRONT END" / "model" / "saved_model.pth",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find saved_model.pth in model/ or project root.")


def get_device_info():
    if torch.cuda.is_available():
        return {
            "device": "CUDA",
            "name": torch.cuda.get_device_name(0),
            "cuda": True,
        }
    return {"device": "CPU", "name": "PyTorch Cloud CPU Engine", "cuda": False}


def _get_model():
    global trained_model
    if trained_model is None:
        model_path = _resolve_model_path()
        trained_model = CarClassifierResNet()
        state = torch.load(str(model_path), map_location=device, weights_only=True)
        trained_model.load_state_dict(state)
        trained_model.to(device)
        trained_model.eval()
    return trained_model


def _compute_cam_and_hotspot(cam_tensor, orig_size):
    cam_up = F.interpolate(
        cam_tensor.unsqueeze(0).unsqueeze(0),
        size=(224, 224),
        mode="bicubic",
        align_corners=False,
    )[0, 0].clamp(0.0, 1.0).cpu()

    peak_idx = int(torch.argmax(cam_up).item())
    peak_y = round((peak_idx // 224) / 224.0, 3)
    peak_x = round((peak_idx % 224) / 224.0, 3)

    mask = cam_up >= 0.55
    if mask.any():
        ys, xs = torch.where(mask)
        x0 = float(xs.min().item()) / 224.0
        x1 = float(xs.max().item()) / 224.0
        y0 = float(ys.min().item()) / 224.0
        y1 = float(ys.max().item()) / 224.0
        hotspot = {
            "x": round(max(0.02, x0), 3),
            "y": round(max(0.02, y0), 3),
            "w": round(min(0.94, max(0.16, x1 - x0)), 3),
            "h": round(min(0.94, max(0.16, y1 - y0)), 3),
            "peak_x": peak_x,
            "peak_y": peak_y,
        }
    else:
        hotspot = {
            "x": round(max(0.1, peak_x - 0.15), 3),
            "y": round(max(0.1, peak_y - 0.15), 3),
            "w": 0.3,
            "h": 0.3,
            "peak_x": peak_x,
            "peak_y": peak_y,
        }

    r = torch.zeros_like(cam_up)
    g = torch.zeros_like(cam_up)
    b = torch.zeros_like(cam_up)
    a = torch.zeros_like(cam_up)

    m1 = (cam_up >= 0.20) & (cam_up < 0.55)
    t1 = ((cam_up[m1] - 0.20) / 0.35).clamp(0, 1)
    r[m1] = 255.0 * t1
    g[m1] = 180.0 * t1
    b[m1] = 40.0 * (1.0 - t1)
    a[m1] = 150.0 * (t1 ** 1.2)

    m2 = (cam_up >= 0.55) & (cam_up < 0.80)
    t2 = ((cam_up[m2] - 0.55) / 0.25).clamp(0, 1)
    r[m2] = 255.0
    g[m2] = 180.0 - 110.0 * t2
    b[m2] = 20.0 * t2
    a[m2] = 150.0 + 55.0 * t2

    m3 = cam_up >= 0.80
    t3 = ((cam_up[m3] - 0.80) / 0.20).clamp(0, 1)
    r[m3] = 255.0
    g[m3] = 70.0 - 45.0 * (1.0 - t3) + 90.0 * t3
    b[m3] = 30.0 + 110.0 * t3
    a[m3] = 205.0 + 35.0 * t3

    rgba = torch.stack([r, g, b, a], dim=-1).to(torch.uint8).numpy()
    overlay_rgba = Image.fromarray(rgba, mode="RGBA").resize(
        orig_size, resample=Image.Resampling.BICUBIC
    )
    return overlay_rgba, hotspot


def render_viewport_image(
    base_img,
    overlay_rgba=None,
    hotspot=None,
    top_class="Front Crushed",
    confidence=0.95,
    show_heatmap=True,
    heatmap_opacity=0.78,
    show_hud=True,
):
    """Compose the vehicle photo with optional Grad-CAM overlay and HUD target reticle."""
    canvas = base_img.convert("RGBA")
    w, h = canvas.size

    if show_heatmap and overlay_rgba is not None:
        scaled_overlay = overlay_rgba.copy()
        if heatmap_opacity < 0.99:
            r, g, b, a = scaled_overlay.split()
            a = a.point(lambda p: int(p * heatmap_opacity))
            scaled_overlay = Image.merge("RGBA", (r, g, b, a))
        canvas = Image.alpha_composite(canvas, scaled_overlay)

    if show_hud and hotspot is not None:
        hud_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(hud_layer)
        color = CLASS_META.get(top_class, {}).get("color_rgb", (255, 179, 0))

        x0 = int(hotspot["x"] * w)
        y0 = int(hotspot["y"] * h)
        x1 = int((hotspot["x"] + hotspot["w"]) * w)
        y1 = int((hotspot["y"] + hotspot["h"]) * h)

        # Subtle inner tint
        draw.rectangle([x0, y0, x1, y1], fill=(color[0], color[1], color[2], 26))
        # Outer frame
        line_w = max(2, int(min(w, h) * 0.004))
        draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 210), width=line_w)

        # Corner HUD brackets
        c_len = max(14, int(min(x1 - x0, y1 - y0) * 0.18))
        b_w = max(3, line_w + 2)
        b_col = (color[0], color[1], color[2], 255)
        # Top-left
        draw.line([(x0, y0), (x0 + c_len, y0)], fill=b_col, width=b_w)
        draw.line([(x0, y0), (x0, y0 + c_len)], fill=b_col, width=b_w)
        # Top-right
        draw.line([(x1 - c_len, y0), (x1, y0)], fill=b_col, width=b_w)
        draw.line([(x1, y0), (x1, y0 + c_len)], fill=b_col, width=b_w)
        # Bottom-left
        draw.line([(x0, y1 - c_len), (x0, y1)], fill=b_col, width=b_w)
        draw.line([(x0, y1), (x0 + c_len, y1)], fill=b_col, width=b_w)
        # Bottom-right
        draw.line([(x1 - c_len, y1), (x1, y1)], fill=b_col, width=b_w)
        draw.line([(x1, y1 - c_len), (x1, y1)], fill=b_col, width=b_w)

        # Peak crosshair
        px = int(hotspot["peak_x"] * w)
        py = int(hotspot["peak_y"] * h)
        r_cross = max(6, int(min(w, h) * 0.015))
        draw.ellipse(
            [px - r_cross, py - r_cross, px + r_cross, py + r_cross],
            outline=(255, 255, 255, 230),
            width=max(2, line_w),
        )

        # Tag pill
        tag_h = max(22, int(h * 0.045))
        tag_w = max(135, int(w * 0.26))
        ty0 = max(4, y0 - tag_h - 4)
        draw.rectangle(
            [x0, ty0, x0 + tag_w, ty0 + tag_h],
            fill=(17, 14, 11, 230),
            outline=b_col,
            width=max(1, line_w - 1),
        )
        draw.text(
            (x0 + 8, ty0 + max(3, (tag_h - 12) // 2)),
            f"PEAK ROI · {confidence * 100:.1f}%",
            fill=b_col,
        )
        canvas = Image.alpha_composite(canvas, hud_layer)

    return canvas.convert("RGB")


def predict_detailed(image_input):
    t0 = time.perf_counter()
    if isinstance(image_input, (str, Path)):
        image = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        image = image_input.convert("RGB")
    else:
        image = Image.open(image_input).convert("RGB")

    orig_size = image.size
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
            ),
        ]
    )
    image_tensor = transform(image).unsqueeze(0).to(device)
    model = _get_model()

    activations = []
    gradients = []

    h1 = model.model.layer4[-1].register_forward_hook(
        lambda _m, _i, out: activations.append(out.detach())
    )
    h2 = model.model.layer4[-1].register_full_backward_hook(
        lambda _m, _gi, go: gradients.append(go[0].detach())
    )

    try:
        with torch.enable_grad():
            image_tensor.requires_grad_(True)
            output = model(image_tensor)
            probs = torch.softmax(output, dim=1)[0]
            _, predicted_class = torch.max(probs, 0)
            top_idx = int(predicted_class.item())
            model.zero_grad()
            output[0, top_idx].backward()
    finally:
        h1.remove()
        h2.remove()

    overlay_rgba = None
    hotspot = None
    if activations and gradients:
        act = activations[0][0]
        grad = gradients[0][0]
        weights = grad.mean(dim=(1, 2), keepdim=True)
        cam = F.relu((weights * act).sum(dim=0))
        cmin, cmax = cam.min(), cam.max()
        if (cmax - cmin) > 1e-6:
            cam = (cam - cmin) / (cmax - cmin)
        overlay_rgba, hotspot = _compute_cam_and_hotspot(cam, orig_size)

    prob_dict = {class_names[i]: float(probs[i].item()) for i in range(len(class_names))}
    top_name = class_names[top_idx]
    meta = CLASS_META[top_name]

    front_prob = sum(prob_dict[c] for c in ["Front Breakage", "Front Crushed", "Front Normal"])
    rear_prob = sum(prob_dict[c] for c in ["Rear Breakage", "Rear Crushed", "Rear Normal"])
    damage_prob = sum(
        prob_dict[c]
        for c in ["Front Breakage", "Front Crushed", "Rear Breakage", "Rear Crushed"]
    )
    normal_prob = sum(prob_dict[c] for c in ["Front Normal", "Rear Normal"])

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    dev_info = get_device_info()

    return {
        "top_class": top_name,
        "confidence": prob_dict[top_name],
        "area": meta["area"],
        "state": meta["state"],
        "tone": meta["tone"],
        "severity": meta["severity"],
        "driveability": meta["driveability"],
        "driveability_code": meta["driveability_code"],
        "cost_estimate": meta["cost_estimate"],
        "repair_hours": meta["repair_hours"],
        "action": meta["action"],
        "affected_parts": meta["affected_parts"],
        "probabilities": prob_dict,
        "zone_summary": {
            "front_prob": round(front_prob, 4),
            "rear_prob": round(rear_prob, 4),
            "damage_prob": round(damage_prob, 4),
            "normal_prob": round(normal_prob, 4),
        },
        "overlay_rgba": overlay_rgba,
        "hotspot": hotspot,
        "original_image": image,
        "image_size": {"width": orig_size[0], "height": orig_size[1]},
        "inference_ms": elapsed_ms,
        "device": dev_info,
    }


def predict(image_path):
    return predict_detailed(image_path)["top_class"]
