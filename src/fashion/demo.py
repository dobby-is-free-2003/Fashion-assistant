"""Synthetic wardrobe (41 items, drawn shapes) so everything runs with no API key and no photos."""
from pathlib import Path

from PIL import Image, ImageDraw

from . import config, db

# name, kind, hex, pattern, formality, neckline, seasons, occasions, embellishment, metal
T = "top"; B = "bottom"; D = "dress"; L = "layer"; E = "ethnic_wear"; J = "jewellery"
cas, col, off, fes, wed, par, eng = "casual", "college", "office", "festive", "wedding_guest", "party", "engagement_evening"
SPECS = [
    ("white shirt", T, "#F4F4F0", "solid", 3, "collar", ["all"], [off, col, cas], 0, None),
    ("navy blouse", T, "#1F3A5F", "solid", 3, "round", ["all"], [off, par], 0, None),
    ("black fitted top", T, "#1A1A1A", "solid", 3, "v", ["all"], [par, cas, off], 0, None),
    ("mustard top", T, "#D9A21B", "solid", 2, "round", ["summer", "all"], [cas, col], 0, None),
    ("striped tee", T, "#DDE3F0", "stripe", 2, "round", ["summer", "all"], [cas, col], 0, None),
    ("floral blouse", T, "#E48CA0", "floral", 3, "v", ["summer", "monsoon", "all"], [cas, par], 0, None),
    ("sage top", T, "#9CAF88", "solid", 3, "boat", ["all"], [off, cas, par], 0, None),
    ("maroon satin top", T, "#7B1E2B", "solid", 4, "v", ["all"], [par, eng, fes], 1, None),
    ("blue jeans", B, "#3B5B8C", "solid", 2, None, ["all"], [cas, col], 0, None),
    ("black trousers", B, "#202020", "solid", 3, None, ["all"], [off, par], 0, None),
    ("beige palazzo", B, "#D8C8A8", "solid", 3, None, ["all"], [off, cas, fes], 0, None),
    ("white skirt", B, "#F2F2F2", "solid", 3, None, ["summer", "all"], [cas, par], 0, None),
    ("olive pants", B, "#6B7040", "solid", 2, None, ["all"], [cas, col], 0, None),
    ("lavender pleated skirt", B, "#C9A9E0", "solid", 4, None, ["all"], [par, fes, eng], 0, None),
    ("black cocktail dress", D, "#151515", "solid", 4, "v", ["all"], [par, eng], 1, None),
    ("emerald dress", D, "#0B6E4F", "solid", 4, "round", ["all"], [par, eng, wed], 1, None),
    ("floral sundress", D, "#F0A6B5", "floral", 2, "round", ["summer", "monsoon"], [cas], 0, None),
    ("navy shift dress", D, "#22304F", "solid", 3, "round", ["all"], [off], 0, None),
    ("red evening gown", D, "#B01E2E", "solid", 5, "deep", ["all"], [eng, par], 2, None),
    ("denim jacket", L, "#5A7BA8", "solid", 2, None, ["winter", "all"], [cas, col], 0, None),
    ("black blazer", L, "#1C1C1C", "solid", 4, None, ["winter", "all"], [off, par], 0, None),
    ("cream cardigan", L, "#EFE6D2", "solid", 2, None, ["winter", "all"], [cas, off], 0, None),
    ("grey shawl", L, "#9A9A9A", "solid", 3, None, ["winter", "all"], [fes, wed], 0, None),
    ("maroon anarkali", E, "#7A1530", "embroidered", 4, "round", ["all"], [fes, wed, eng], 2, None),
    ("pastel green kurti set", E, "#B9D8B0", "solid", 3, "round", ["all"], [fes, off, cas], 1, None),
    ("royal blue saree", E, "#1E3F9E", "embroidered", 5, "v", ["all"], [wed, eng, fes], 3, None),
    ("yellow kurta", E, "#F0C020", "solid", 3, "mandarin", ["summer", "all"], [fes, cas], 1, None),
    ("pink lehenga", E, "#E58BB0", "embroidered", 5, "deep", ["all"], [wed, eng], 3, None),
    ("white chikankari kurta", E, "#F6F4EE", "embroidered", 3, "round", ["summer", "all"], [cas, fes, off], 1, None),
    ("black straight kurta", E, "#1F1F1F", "solid", 3, "high", ["all"], [off, fes, par], 0, None),
    ("gold jhumkas", J, "#D4A53A", "solid", 4, None, ["all"], [fes, wed, eng], 2, "gold"),
    ("silver studs", J, "#C0C0C8", "solid", 3, None, ["all"], [off, cas, par], 0, "silver"),
    ("oxidised hoops", J, "#6E6E72", "solid", 2, None, ["all"], [cas, col, fes], 1, "oxidised"),
    ("gold studs", J, "#D4A53A", "solid", 3, None, ["all"], [off, cas, par], 0, "gold"),
    ("pearl drop earrings", J, "#EDE6D8", "solid", 4, None, ["all"], [par, eng, off], 1, "gold"),
    ("gold chandbali earrings", J, "#D4A53A", "solid", 5, None, ["all"], [wed, eng], 3, "gold"),
    ("gold choker necklace", J, "#D4A53A", "solid", 4, None, ["all"], [par, eng, wed], 2, "gold"),
    ("silver chain necklace", J, "#C0C0C8", "solid", 3, None, ["all"], [off, cas, par], 0, "silver"),
    ("oxidised necklace", J, "#6E6E72", "solid", 3, None, ["all"], [fes, cas], 2, "oxidised"),
    ("pearl necklace", J, "#EDE6D8", "solid", 4, None, ["all"], [par, eng, off], 1, "gold"),
    ("gold temple haar", J, "#D4A53A", "solid", 5, None, ["all"], [wed], 3, "gold"),
]


def _draw(kind, subtype, hex_, path: Path):
    im = Image.new("RGBA", (400, 500), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col, ol = hex_, "#00000040"
    st = subtype.lower()
    if kind == "top":
        d.polygon([(110, 60), (160, 40), (240, 40), (290, 60), (360, 160), (310, 190), (290, 150), (290, 440), (110, 440), (110, 150), (90, 190), (40, 160)], fill=col, outline=ol)
    elif kind == "bottom":
        if "skirt" in st:
            d.polygon([(130, 40), (270, 40), (350, 460), (50, 460)], fill=col, outline=ol)
        else:
            d.polygon([(110, 40), (290, 40), (320, 470), (215, 470), (200, 160), (185, 470), (80, 470)], fill=col, outline=ol)
    elif kind == "dress":
        d.polygon([(150, 30), (250, 30), (270, 170), (360, 470), (40, 470), (130, 170)], fill=col, outline=ol)
    elif kind == "layer":
        d.polygon([(100, 50), (170, 35), (200, 110), (230, 35), (300, 50), (370, 400), (320, 420), (300, 200), (300, 460), (100, 460), (100, 200), (80, 420), (30, 400)], fill=col, outline=ol)
    elif kind == "ethnic_wear":
        d.polygon([(130, 30), (270, 30), (290, 160), (330, 480), (70, 480), (110, 160)], fill=col, outline=ol)
        d.line([(200, 40), (200, 470)], fill="#FFFFFF60", width=3)
    else:
        if any(w in st for w in ("earring", "jhumka", "stud", "hoop", "chandbali", "drop")):
            d.ellipse([170, 100, 230, 160], fill=col, outline=ol)
            d.polygon([(200, 160), (165, 300), (235, 300)], fill=col, outline=ol)
        else:
            d.arc([40, 60, 360, 420], 20, 160, fill=col, width=18)
            d.ellipse([180, 380, 220, 430], fill=col)
    im.save(path, "PNG")


def seed_demo(c=None) -> int:
    config.ensure_dirs()
    c = c or db.conn()
    for n, (name, kind, hx, pat, form, neck, seas, occ, emb, metal) in enumerate(SPECS):
        iid = f"demo{n:02d}"
        p = config.CUTOUT_DIR / f"{iid}.png"
        _draw(kind, name, hx, p)
        tags = {"kind": kind, "subtype": name, "primary_color_hex": hx, "secondary_color_hex": None, "pattern": pat,
                "fabric_guess": "cotton", "neckline": neck, "sleeve": None, "length": None, "fit": None, "formality": form,
                "seasons": seas, "occasions": occ, "embellishment_level": emb, "metal_tone": metal, "style_tags": []}
        db.add_item(c, iid, p, p, tags, "demo", "synthetic", reviewed=1)
    return len(SPECS)
