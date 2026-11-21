"""Level 1 visualisation: collage on a neutral canvas with fixed layout and soft shadows."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, BG = 900, 1100, (246, 243, 238)
ORDER = {"layer": 0, "top": 1, "dress": 1, "ethnic_wear": 1, "bottom": 2}


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _place(canvas, path, box, label=""):
    x0, y0, x1, y1 = box
    img = Image.open(path).convert("RGBA")
    img.thumbnail((x1 - x0 - 20, y1 - y0 - 50))
    x, y = x0 + (x1 - x0 - img.width) // 2, y0 + (y1 - y0 - 40 - img.height) // 2
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: int(v * 0.28))
    sh.paste(Image.new("RGBA", img.size, (0, 0, 0, 255)), (x + 8, y + 10), a)
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    canvas.alpha_composite(img, (x, y))
    if label:
        d = ImageDraw.Draw(canvas)
        f = _font(20)
        d.text(((x0 + x1) // 2, y1 - 24), label, fill=(90, 85, 80), font=f, anchor="mm")


def compose(garments, jewels, title="") -> Image.Image:
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    gs = sorted(garments, key=lambda g: ORDER.get(g["kind"], 3))
    zone_top, zone_bot = 80, H - 30
    rh = (zone_bot - zone_top) // max(len(gs), 1)
    for i, g in enumerate(gs):
        _place(canvas, g["cutout_path"], (30, zone_top + i * rh, 600, zone_top + (i + 1) * rh), g["subtype"])
    for i, j in enumerate(jewels[:4]):
        _place(canvas, j["cutout_path"], (630, zone_top + i * 250, 880, zone_top + (i + 1) * 250), j["subtype"])
    if title:
        ImageDraw.Draw(canvas).text((30, 38), title, fill=(60, 55, 50), font=_font(32), anchor="lm")
    return canvas.convert("RGB")


def save_collage(garments, jewels, path: Path, title="") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    compose(garments, jewels, title).save(path, "PNG")
    return path
