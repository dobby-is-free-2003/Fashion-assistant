"""Background removal and simple colour helpers."""
from pathlib import Path
import numpy as np
from PIL import Image


def make_cutout(src: Path, dst: Path, max_side: int = 1024) -> Path:
    from rembg import remove  # lazy: heavy import, downloads a model on first use
    img = Image.open(src).convert("RGB")
    img.thumbnail((max_side, max_side))
    remove(img).save(dst, "PNG")
    return dst


def dominant_hex(cutout: Path) -> str:
    """Most common coarse colour among opaque pixels (sanity check against model output)."""
    a = np.array(Image.open(cutout).convert("RGBA"))
    px = a[a[..., 3] > 200][:, :3]
    if len(px) == 0:
        return "#808080"
    q = (px // 32) * 32 + 16
    vals, counts = np.unique(q, axis=0, return_counts=True)
    r, g, b = vals[counts.argmax()]
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_distance(a: str, b: str) -> float:
    pa = np.array([int(a[i:i + 2], 16) for i in (1, 3, 5)])
    pb = np.array([int(b[i:i + 2], 16) for i in (1, 3, 5)])
    return float(np.linalg.norm(pa - pb))
