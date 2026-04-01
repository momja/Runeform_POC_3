"""Real-ESRGAN upscaling for low-resolution hero images via spandrel."""

from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import torch
from PIL import Image

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_NAME = "RealESRGAN_x4plus.pth"
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

_model = None


def _ensure_model() -> Path:
    """Download model weights if not present."""
    model_path = MODEL_DIR / MODEL_NAME
    if not model_path.exists():
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[upscale] Downloading {MODEL_NAME}...")
        urlretrieve(MODEL_URL, model_path)
        print(f"[upscale] Downloaded to {model_path}")
    return model_path


def _get_model():
    global _model
    if _model is not None:
        return _model

    import spandrel

    model_path = _ensure_model()
    descriptor = spandrel.ModelLoader().load_from_file(model_path).eval()

    if torch.backends.mps.is_available():
        descriptor = descriptor.to("mps")
    elif torch.cuda.is_available():
        descriptor = descriptor.to("cuda")

    _model = descriptor
    return _model


def upscale(img: Image.Image) -> Image.Image:
    """4x upscale via Real-ESRGAN."""
    print(f"[upscale] Running ESRGAN on {img.width}x{img.height}")

    rgb = img.convert("RGB")
    arr = np.array(rgb).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # BCHW

    descriptor = _get_model()
    tensor = tensor.to(descriptor.device)

    with torch.no_grad():
        output = descriptor(tensor)

    output = output.squeeze(0).permute(1, 2, 0).cpu().clamp(0, 1).numpy()
    result = Image.fromarray((output * 255).astype(np.uint8))

    print(f"[upscale] Upscaled to {result.width}x{result.height}")
    return result


def upscale_if_needed(path: Path, target_size: int = 1080) -> Path:
    """Upscale an image file if it's too small for the canvas. Returns path to the
    (possibly upscaled) image. Result is cached next to the original."""
    img = Image.open(path)
    if min(img.width, img.height) >= target_size:
        return path

    cached = path.parent / f"{path.stem}_esrgan{path.suffix}"
    if cached.exists():
        print(f"[upscale] Using cached {cached.name}")
        return cached

    result = upscale(img)
    result.save(cached)
    return cached
