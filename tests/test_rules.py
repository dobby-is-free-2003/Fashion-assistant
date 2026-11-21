from fashion import rules


def g(kind="top", hx="#1F3A5F", pat="solid", f=3, neck="round", emb=0, **kw):
    return {"kind": kind, "subtype": kw.get("subtype", "x"), "primary_color_hex": hx, "pattern": pat, "formality": f,
            "neckline": neck, "embellishment_level": emb, "seasons": ["all"], "occasions": [], "fabric_guess": "cotton",
            "metal_tone": kw.get("metal"), "style_tags": []}


S = {"occasion": "party", "formality": 3}
W = {"temp_c": 25, "season": "all"}


def test_families():
    assert rules.family("#000000") == "neutral" and rules.family("#FFFFFF") == "neutral"
    assert rules.family("#1E3F9E") == "blue" and rules.family("#B01E2E") == "red"


def test_colour_harmony_penalises_many_strong_colours():
    ok, _ = rules.colour_harmony(["#1E3F9E", "#F0C020"])      # blue + yellow
    bad, _ = rules.colour_harmony(["#FF0000", "#00FF00", "#0000FF", "#FFFF00"])
    assert bad < 0.2 < ok and rules.colour_harmony(["#111111", "#FFFFFF"])[0] == 1.0


def test_pattern_clash():
    assert rules.pattern_score([g(pat="floral"), g(kind="bottom", pat="stripe")])[0] < 0.5
    assert rules.pattern_score([g(pat="floral"), g(kind="bottom", pat="micro")])[0] == 1.0


def test_formality_one_level_tolerance():
    assert rules.formality_score([g(f=4)], 3)[0] > 0.9 and rules.formality_score([g(f=1)], 4)[0] < 0.7


def test_jewellery_rules():
    hi = [g(neck="high")]; deep = [g(neck="v")]
    neck = {"subtype": "gold choker necklace", "embellishment_level": 1, "metal_tone": "gold"}
    ear = {"subtype": "gold jhumkas", "embellishment_level": 2, "metal_tone": "gold"}
    assert rules.jewellery_score(hi, [ear])[0] > rules.jewellery_score(hi, [neck])[0]
    assert rules.jewellery_score(deep, [neck])[0] > rules.jewellery_score(deep, [ear])[0]
    heavy = [g(kind="ethnic_wear", emb=3, neck="round")]
    assert rules.jewellery_score(heavy, [ear, neck])[0] < rules.jewellery_score(heavy, [{**ear, "embellishment_level": 0}])[0]
    silver = {**neck, "metal_tone": "silver"}
    assert rules.jewellery_score(deep, [ear, silver])[0] < rules.jewellery_score(deep, [ear, neck])[0]


def test_season():
    assert rules.season_score([g()], {"temp_c": 12, "season": "winter"})[0] < 1.0
    assert rules.season_score([g(), g(kind="layer")], {"temp_c": 33, "season": "summer"})[0] < 1.0


def test_rule_score_range():
    r = rules.rule_score([g(), g(kind="bottom", hx="#202020")], [], S, W)
    assert 0 <= r["score"] <= 1 and r["reasons"]
