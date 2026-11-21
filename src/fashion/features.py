"""Look -> feature vector for the preference learner."""
from .rules import FAMILIES, BOLD, family, jtype

NAMES = [f"colour_{f}" for f in FAMILIES] + ["formality", "embellishment", "jewellery_boldness", "bold_pattern",
        "trend", "anchor_dress", "anchor_ethnic", "anchor_topbottom", "has_layer", "jewellery_count"]
DIM = len(NAMES)


def vector(gs, js, trend: float) -> list[float]:
    core = [g for g in gs if g["kind"] != "layer"]
    x = [0.0] * len(FAMILIES)
    for g in core:
        x[FAMILIES.index(family(g["primary_color_hex"]))] += 1 / len(core)
    kinds = {g["kind"] for g in gs}
    x += [sum(g["formality"] for g in gs) / len(gs) / 5,
          sum(g["embellishment_level"] for g in gs) / len(gs) / 3,
          (sum(j["embellishment_level"] for j in js) / len(js) / 3) if js else 0.0,
          1.0 if any(g["pattern"] in BOLD for g in gs) else 0.0,
          float(trend),
          float("dress" in kinds), float("ethnic_wear" in kinds), float("top" in kinds),
          float("layer" in kinds), len(js) / 2]
    return x
