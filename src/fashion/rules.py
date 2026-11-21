"""Simple, explainable compatibility rules (plan 5.1). Every rule returns (score 0..1, reason)."""
import colorsys
import re
from functools import lru_cache

FAMILIES = ["neutral", "red", "orange", "yellow", "green", "blue", "purple", "pink"]
BOLD = {"stripe", "check", "floral", "print"}
HIGH_NECK = {"high", "round", "boat", "collar", "turtle", "mandarin", "crew", "halter"}
DEEP_NECK = {"v", "deep", "plunge", "sweetheart", "scoop"}
EARRING_W = {"earring", "earrings", "jhumka", "jhumkas", "jhumki", "stud", "studs", "hoop", "hoops",
             "chandbali", "drop", "drops", "danglers"}
NECKLACE_W = {"necklace", "choker", "chain", "pendant", "haar", "mangalsutra"}
HEAVY_FABRIC = {"wool", "velvet", "knit", "leather", "fleece"}
WEIGHTS = {"colour": 0.30, "pattern": 0.15, "formality": 0.25, "jewellery": 0.15, "season": 0.10, "occasion": 0.05}


def toks(s) -> set:
    return set(re.split(r"[^a-z]+", (s or "").lower())) - {""}


@lru_cache(maxsize=8192)
def hsv(hex_: str):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def is_neutral(hex_: str) -> bool:
    _, s, v = hsv(hex_)
    return s < 0.2 or v < 0.18 or (v > 0.9 and s < 0.25)


def family(hex_: str) -> str:
    if is_neutral(hex_):
        return "neutral"
    h = hsv(hex_)[0]
    for lim, name in ((15, "red"), (45, "orange"), (70, "yellow"), (170, "green"), (255, "blue"),
                      (295, "purple"), (345, "pink")):
        if h < lim:
            return name
    return "red"


def _hd(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def colour_harmony(hexes):
    hues = []
    for hx in hexes:
        if not is_neutral(hx) and hsv(hx)[1] >= 0.35:
            h = hsv(hx)[0]
            if all(_hd(h, x) > 25 for x in hues):
                hues.append(h)
    n = len(hues)
    if n <= 1:
        return 1.0, "neutral or single-colour palette"
    if n == 2:
        d = _hd(*hues)
        if d <= 45: return 1.0, "analogous colours"
        if d >= 150: return 0.9, "complementary colours"
        if 100 <= d <= 140: return 0.75, "triadic-style colours"
        return 0.45, "two strong colours that fight"
    if n == 3 and all(90 <= _hd(a, b) <= 150 for i, a in enumerate(hues) for b in hues[i + 1:]):
        return 0.7, "triadic palette"
    return (0.3 if n == 3 else 0.1), f"{n} strong colours is too many"


def pattern_score(gs):
    bold = sum(1 for g in gs if g["pattern"] in BOLD or (g["pattern"] == "embroidered" and g["embellishment_level"] >= 2))
    if bold <= 1: return 1.0, "at most one bold pattern"
    return (0.3 if bold == 2 else 0.1), "pattern clash"


def formality_score(gs, target):
    ds = [abs(g["formality"] - target) for g in gs]
    s = 1 - sum(max(0, d - 1) * 0.35 for d in ds) / len(ds)
    fs = [g["formality"] for g in gs]
    if max(fs) - min(fs) > 1:
        s -= 0.2
    s = max(0.0, min(1.0, s))
    return s, ("formality matches the occasion" if s > 0.85 else "formality is off for the occasion")


def season_score(gs, weather):
    season, temp = weather.get("season", "all"), weather.get("temp_c", 27)
    s, why = 1.0, "suits the weather"
    for g in gs:
        if season != "all" and "all" not in g["seasons"] and season not in g["seasons"]:
            s -= 0.3; why = f"not tagged for {season}"
        if temp >= 30 and toks(g.get("fabric_guess")) & HEAVY_FABRIC:
            s -= 0.3; why = "heavy fabric for hot weather"
    has_layer = any(g["kind"] == "layer" for g in gs)
    if temp <= 16 and not has_layer:
        s -= 0.2; why = "cold weather, no layer"
    if temp >= 30 and has_layer:
        s -= 0.3; why = "layer is too warm for the heat"
    return max(0.0, s), why


def occasion_score(gs, occasion):
    v = [1.0 if occasion in g["occasions"] else (0.5 if not g["occasions"] else 0.2) for g in gs]
    return sum(v) / len(v), "tagged for this occasion" if sum(v) / len(v) > 0.8 else "not tagged for this occasion"


def jtype(j) -> str:
    t = toks(j["subtype"])
    return "earring" if t & EARRING_W else "necklace" if t & NECKLACE_W else "other"


def jewellery_score(gs, js):
    if not js:
        return 0.5, "no jewellery chosen"
    s, why = 0.8, []
    neck = next((toks(g.get("neckline")) for g in gs if g["kind"] in ("top", "dress", "ethnic_wear") and g.get("neckline")), set())
    types = [jtype(j) for j in js]
    has_neck, has_ear = "necklace" in types, "earring" in types
    stmt_ear = any(jtype(j) == "earring" and j["embellishment_level"] >= 2 for j in js)
    if neck & HIGH_NECK:
        if has_neck: s -= 0.4; why.append("necklace crowds a high neckline")
        elif stmt_ear: s += 0.15; why.append("statement earrings suit the high neckline")
    if neck & DEEP_NECK:
        if has_neck: s += 0.15; why.append("necklace frames the deeper neckline")
        else: s -= 0.15; why.append("deep neckline looks bare without a necklace")
    if max(g["embellishment_level"] for g in gs) >= 2 and sum(j["embellishment_level"] for j in js) > 2:
        s -= 0.4; why.append("heavy embroidery needs minimal jewellery")
    tones = {j["metal_tone"] for j in js if j.get("metal_tone") not in (None, "none")}
    if len(tones) > 1 and "mixed" not in tones:
        s -= 0.3; why.append("metal tones are inconsistent")
    return max(0.0, min(1.0, s)), "; ".join(why) or "jewellery is balanced"


def rule_score(gs, js, session, weather, with_jewellery=True) -> dict:
    parts = {
        "colour": colour_harmony([g["primary_color_hex"] for g in gs]),
        "pattern": pattern_score(gs),
        "formality": formality_score(gs, session["formality"]),
        "season": season_score(gs, weather),
        "occasion": occasion_score(gs, session["occasion"]),
    }
    if with_jewellery:
        parts["jewellery"] = jewellery_score(gs, js)
    wsum = sum(WEIGHTS[k] for k in parts)
    score = sum(WEIGHTS[k] * v[0] for k, v in parts.items()) / wsum
    return {"score": score, "comps": {k: round(v[0], 2) for k, v in parts.items()},
            "reasons": [v[1] for v in parts.values()]}
