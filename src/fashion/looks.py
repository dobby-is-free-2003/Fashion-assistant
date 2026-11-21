"""Candidate generation, scoring, and diversity-aware selection of three looks (taste / trend / explore)."""
import itertools
from datetime import date, datetime

import numpy as np

from . import features, rules, trends
from .rules import family, jtype

GATE = 0.55          # minimum rule score for a look to be shown
W_PREF = 4.0          # weight of learned preference vs rule score (tuned on the simulated persona, see eval)


def _ok(it, session):
    return abs(it["formality"] - session["formality"]) <= 1 or session["occasion"] in it["occasions"]


def _pool(items, session, avoid):
    p = [i for i in items if _ok(i, session)] or items
    q = [i for i in p if family(i["primary_color_hex"]) not in avoid]
    return q or p


def build_candidates(items, session, weather, rng, notes=(), today: date | None = None, top_garment=60, per_combo=6):
    today = today or date.today()
    avoid, want = set(session.get("avoid_colours", [])), set(session.get("wear_colours", []))
    by = lambda k: [i for i in items if i["kind"] == k]  # noqa: E731
    dresses, ethnic = _pool(by("dress"), session, avoid) if by("dress") else [], _pool(by("ethnic_wear"), session, avoid) if by("ethnic_wear") else []
    tops = _pool(by("top"), session, avoid) if by("top") else []
    bottoms = _pool(by("bottom"), session, avoid) if by("bottom") else []
    layers = by("layer")
    temp = weather.get("temp_c", 27)
    layer_opts = [None] if temp >= 30 or not layers else (layers if temp <= 16 else [None] + layers)
    anchors = [(d,) for d in dresses] + [(e,) for e in ethnic] + [(t, b) for t in tops for b in bottoms]
    combos = []
    for a in anchors:
        for l in layer_opts:
            gs = list(a) + ([l] if l else [])
            combos.append((rules.rule_score(gs, [], session, weather, with_jewellery=False)["score"] + rng.random() * 1e-6, gs, a))
    combos.sort(key=lambda t: -t[0])
    jewels = [i for i in items if i["kind"] == "jewellery"]
    ears = [j for j in jewels if jtype(j) == "earring"]
    necks = [j for j in jewels if jtype(j) == "necklace"]
    pick = lambda xs: [xs[i] for i in rng.permutation(len(xs))[:6]] if xs else []  # noqa: E731
    out = []
    for _, gs, a in combos[:top_garment]:
        E, N = pick(ears), pick(necks)
        jopts = [()] + [(e,) for e in E] + [(n,) for n in N] + list(itertools.product(E, N))
        scored = sorted(((rules.jewellery_score(gs, list(j))[0], j) for j in jopts), key=lambda t: -t[0])[:per_combo]
        for _, j in scored:
            out.append(_make(gs, list(j), a, session, weather, notes, want, today))
    return out


def _make(gs, js, anchor, session, weather, notes, want, today):
    r = rules.rule_score(gs, js, session, weather)
    tr = trends.trend_score(gs, js, notes)
    core = [g for g in gs if g["kind"] != "layer"]
    rec = 0.0
    for g in core:
        if g["last_worn"] and (today - date.fromisoformat(g["last_worn"])).days <= 7:
            rec += 0.3
    return {
        "ids": [x["item_id"] for x in gs + js], "garments": gs, "jewels": js,
        "anchor_ids": tuple(sorted(x["item_id"] for x in anchor)),
        "anchor_family": family(anchor[0]["primary_color_hex"]),
        "rule": r["score"], "comps": r["comps"], "reasons": r["reasons"], "trend": tr,
        "novelty": sum(1 / (1 + g["times_worn"]) for g in core) / len(core), "recency": min(rec, 0.6),
        "want": 0.1 if want & {family(g["primary_color_hex"]) for g in gs} else 0.0,
        "x": features.vector(gs, js, tr),
    }


def differ(a, b, strict=True) -> bool:
    same_set = set(a["ids"]) == set(b["ids"])
    if not strict:
        return not same_set
    jac = len(set(a["ids"]) & set(b["ids"])) / len(set(a["ids"]) | set(b["ids"]))
    return (a["anchor_ids"] != b["anchor_ids"] or a["anchor_family"] != b["anchor_family"]) and jac < 0.75


def select_three(cands, learner, rng, accept=lambda c: True, max_reviews=4):
    """A = best match to learned taste, B = most trend-aligned, C = Thompson-sampling exploration."""
    if not cands:
        return []
    good = [c for c in cands if c["rule"] >= GATE] or cands
    base = lambda c: c["rule"] - c["recency"] + c["want"]  # noqa: E731
    taste = lambda c: base(c) + W_PREF * learner.score(c["x"]) + 0.15 * c["novelty"]  # noqa: E731
    has_trend = any(c["trend"] > 0 for c in good)
    trendy = (lambda c: 1.0 * c["trend"] + 0.5 * base(c) + 0.5 * learner.score(c["x"])) if has_trend else taste  # noqa: E731
    ws = learner.sample(rng)
    explore = lambda c: base(c) + W_PREF * learner.score_with(ws, c["x"]) + 0.1 * c["novelty"]  # noqa: E731

    def first(key, taken):
        order = sorted(good, key=key, reverse=True)
        for strict in (True, False):
            n = 0
            for c in order:
                if any(not differ(c, t, strict) for t in taken):
                    continue
                n += 1
                if accept(c):
                    return c
                if n >= max_reviews:
                    break
        return None

    chosen, picks = [], []
    for slot, key in (("taste", taste), ("trend", trendy), ("explore", explore)):
        c = first(key, chosen)
        if c is not None:
            chosen.append(c)
            picks.append((slot, c))
    return picks
