import base64
import io
import time
import torch
import torch.nn.functional as F
from torch import nn
from torchvision import models, transforms
from PIL import Image

CLASS_NAMES = [
    "Front Breakage",
    "Front Crushed",
    "Front Normal",
    "Rear Breakage",
    "Rear Crushed",
    "Rear Normal",
]

_trained_model = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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


def _transform():
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
            ),
        ]
    )


def get_device_info():
    if torch.cuda.is_available():
        return {
            "device": "CUDA",
            "name": torch.cuda.get_device_name(0),
            "cuda": True,
        }
    return {"device": "CPU", "name": "PyTorch CPU Engine", "cuda": False}


def load_model(model_path):
    global _trained_model
    if _trained_model is None:
        _trained_model = CarClassifierResNet()
        _trained_model.load_state_dict(
            torch.load(model_path, map_location=_device, weights_only=True)
        )
        _trained_model.to(_device)
        _trained_model.eval()
    return _trained_model


def _compute_gradcam_overlay(cam_tensor, orig_size):
    """
    Convert a 2D normalized Grad-CAM tensor [H, W] in [0, 1] into:
    1) A base64 RGBA PNG overlay with smooth thermal coloring
    2) A normalized hotspot bounding box {x, y, w, h, peak_x, peak_y}
    """
    # Upsample to 224x224 first in torch for smooth bicubic interpolation
    cam_up = F.interpolate(
        cam_tensor.unsqueeze(0).unsqueeze(0),
        size=(224, 224),
        mode="bicubic",
        align_corners=False,
    )[0, 0].clamp(0.0, 1.0)

    # Find peak and bounding region where cam >= 0.55
    peak_idx = torch.argmax(cam_up)
    peak_y_idx = int(peak_idx // 224)
    peak_x_idx = int(peak_idx % 224)
    peak_x = round(peak_x_idx / 224.0, 3)
    peak_y = round(peak_y_idx / 224.0, 3)

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
            "w": round(min(0.96, max(0.15, x1 - x0)), 3),
            "h": round(min(0.96, max(0.15, y1 - y0)), 3),
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

    # Build RGBA thermal colormap tensor [224, 224, 4]
    v = cam_up.cpu()
    r = torch.zeros_like(v)
    g = torch.zeros_like(v)
    b = torch.zeros_like(v)
    a = torch.zeros_like(v)

    # Low-mid (0.20 -> 0.55): deep amber/cyan glow to warm gold
    m1 = (v >= 0.20) & (v < 0.55)
    t1 = ((v[m1] - 0.20) / 0.35).clamp(0, 1)
    r[m1] = 255.0 * t1
    g[m1] = 180.0 * t1
    b[m1] = 40.0 * (1.0 - t1)
    a[m1] = 150.0 * (t1 ** 1.2)

    # Mid-high (0.55 -> 0.80): warm gold (#ffb300) to bright orange-red (#ff4d2a)
    m2 = (v >= 0.55) & (v < 0.80)
    t2 = ((v[m2] - 0.55) / 0.25).clamp(0, 1)
    r[m2] = 255.0
    g[m2] = 180.0 - 110.0 * t2
    b[m2] = 20.0 * t2
    a[m2] = 150.0 + 55.0 * t2

    # High (0.80 -> 1.00): crimson/white-hot core
    m3 = v >= 0.80
    t3 = ((v[m3] - 0.80) / 0.20).clamp(0, 1)
    r[m3] = 255.0
    g[m3] = 70.0 - 45.0 * (1.0 - t3) + 90.0 * t3
    b[m3] = 30.0 + 110.0 * t3
    a[m3] = 205.0 + 35.0 * t3

    rgba = torch.stack([r, g, b, a], dim=-1).to(torch.uint8).numpy()
    overlay_img = Image.fromarray(rgba, mode="RGBA").resize(
        orig_size, resample=Image.Resampling.BICUBIC
    )
    buf = io.BytesIO()
    overlay_img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}", hotspot


def predict_proba(image, model_path, with_gradcam=True):
    """Run inference and return (top_class_name, probabilities dict, extras dict)."""
    t0 = time.perf_counter()
    if isinstance(image, str):
        image = Image.open(image).convert("RGB")
    elif isinstance(image, Image.Image):
        image = image.convert("RGB")
    else:
        raise TypeError("image must be a path or a PIL Image")

    orig_size = image.size  # (width, height)
    model = load_model(model_path)
    image_tensor = _transform()(image).unsqueeze(0).to(_device)

    activations = []
    gradients = []

    def fwd_hook(_module, _inp, out):
        activations.append(out.detach())

    def bwd_hook(_module, _grad_in, grad_out):
        gradients.append(grad_out[0].detach())

    target_layer = model.model.layer4[-1]
    h1 = target_layer.register_forward_hook(fwd_hook)
    h2 = target_layer.register_full_backward_hook(bwd_hook)

    try:
        with torch.enable_grad():
            image_tensor.requires_grad_(True)
            logits = model(image_tensor)
            probabilities = torch.softmax(logits, dim=1)[0]
            top_idx = int(torch.argmax(probabilities).item())

            if with_gradcam:
                model.zero_grad()
                logits[0, top_idx].backward()
    finally:
        h1.remove()
        h2.remove()

    probs = {CLASS_NAMES[i]: float(probabilities[i].item()) for i in range(len(CLASS_NAMES))}
    top_name = CLASS_NAMES[top_idx]

    heatmap_url = None
    hotspot = None
    if with_gradcam and activations and gradients:
        try:
            act = activations[0][0]  # [C, 7, 7]
            grad = gradients[0][0]   # [C, 7, 7]
            weights = grad.mean(dim=(1, 2), keepdim=True)
            cam = F.relu((weights * act).sum(dim=0))
            cam_min, cam_max = cam.min(), cam.max()
            if (cam_max - cam_min) > 1e-6:
                cam = (cam - cam_min) / (cam_max - cam_min)
            heatmap_url, hotspot = _compute_gradcam_overlay(cam, orig_size)
        except Exception:
            heatmap_url = None
            hotspot = None

    inference_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    extras = {
        "inference_ms": inference_ms,
        "image_size": {"width": orig_size[0], "height": orig_size[1]},
        "heatmap_url": heatmap_url,
        "hotspot": hotspot,
        "device": get_device_info(),
    }
    return top_name, probs, extras