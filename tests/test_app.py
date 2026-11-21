import numpy as np
import pytest
from datetime import date

from fashion import config, db, demo, looks, trends, render, privacy, tryon, features
from fashion.learner import PreferenceLearner
from fashion.service import StylistService

W = {"temp_c": 25, "season": "all"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    for k, v in {"DATA_DIR": tmp_path, "RAW_DIR": tmp_path / "raw", "CUTOUT_DIR": tmp_path / "cut", "QDRANT_PATH": tmp_path / "q",
                 "RENDER_DIR": tmp_path / "ren", "USER_DIR": tmp_path / "user", "KEY_PATH": tmp_path / "k.key",
                 "TRYON_JOBS": tmp_path / "jobs", "TRYON_RESULTS": tmp_path / "res", "GEMINI_API_KEY": ""}.items():
        monkeypatch.setattr(config, k, v)
    c = db.conn(tmp_path / "t.db")
    demo.seed_demo(c)
    return c


def sess(occ="party", f=4):
    return {"occasion": occ, "formality": f, "avoid_colours": [], "wear_colours": []}


def test_three_distinct_looks(env):
    items = [db.flat(i) for i in db.list_items(env)]
    rng = np.random.default_rng(1)
    for occ, f in (("office", 3), ("party", 4), ("wedding_guest", 4), ("casual", 2)):
        picks = looks.select_three(looks.build_candidates(items, sess(occ, f), W, rng), PreferenceLearner(), rng)
        assert len(picks) == 3
        cs = [p[1] for p in picks]
        assert all(looks.differ(a, b) for i, a in enumerate(cs) for b in cs[i + 1:])
        assert all(c["rule"] >= looks.GATE for c in cs)


def test_avoid_colour_respected(env):
    items = [db.flat(i) for i in db.list_items(env)]
    rng = np.random.default_rng(2)
    s = {**sess(), "avoid_colours": ["red", "yellow"]}
    for _, c in looks.select_three(looks.build_candidates(items, s, W, rng), PreferenceLearner(), rng):
        assert all(looks.family(g["primary_color_hex"]) not in ("red", "yellow") for g in c["garments"])


def test_learner_moves_toward_choice():
    lr = PreferenceLearner()
    a, b = [1.0] + [0.0] * (features.DIM - 1), [0.0, 1.0] + [0.0] * (features.DIM - 2)
    assert lr.score(a) == 0
    for _ in range(10):
        lr.update(a, [b])
    assert lr.score(a) > lr.score(b) + 0.2


def test_persona_learning_curve_rises():
    import sys; sys.path.insert(0, "eval")
    from eval.simulate_persona import run
    hits, pcts = run(sessions=120, seed=3)
    assert np.mean(pcts[-40:]) > 0.9 and np.mean(pcts[-40:]) >= np.mean(pcts[:10]) - 0.02


def test_trend_notes_change_ranking(env):
    items = [db.flat(i) for i in db.list_items(env)]
    rng = np.random.default_rng(4)
    base = looks.build_candidates(items, sess("party", 4), W, rng)
    notes = [{"tags": ["palette:emerald", "silhouette:dress"], "weight": 1.0}]
    with_t = looks.build_candidates(items, sess("party", 4), W, np.random.default_rng(4), notes)
    best = lambda cs: max(cs, key=lambda c: c["trend"] + 0.5 * c["rule"])  # noqa: E731
    assert max(c["trend"] for c in with_t) > 0 and max(c["trend"] for c in base) == 0
    top_trend = [g["subtype"] for g in best(with_t)["garments"]]
    assert "emerald dress" in top_trend


def test_trend_decay(env):
    trends.add_note(env, ["palette:blue"], "x", observed_at="2026-01-01")
    n = trends.active_notes(env, today=date(2026, 3, 2))[0]
    assert 0.2 < n["weight"] < 0.3  # ~2 half-lives


def test_service_end_to_end_and_learning(env):
    svc = StylistService(env, seed=5, today=date(2026, 6, 1))
    p = svc.plan_looks("engagement_evening", weather=W)
    assert len(p["looks"]) == 3 and all(l["rationale"] and l["collage_path"] for l in p["looks"])
    pick = p["looks"][1]["look_id"]
    r = svc.choose(p["session_id"], pick)
    assert r["ok"] and svc.learner.n == 1
    worn = [i for i in db.list_items(env) if i["times_worn"] == 1]
    assert worn and all(i["last_worn"] == "2026-06-01" for i in worn)
    assert svc.choose(p["session_id"], None, "too formal")["data"]["learned"] is False
    assert PreferenceLearner.from_json(db.kv_get(env, "learner")).n == 1


def test_collage_renders(env, tmp_path):
    items = [db.flat(i) for i in db.list_items(env)]
    img = render.compose([i for i in items if i["kind"] == "dress"][:1], [i for i in items if i["kind"] == "jewellery"][:2], "t")
    assert img.size == (900, 1100)


def test_privacy_consent_encrypt_delete(env):
    with pytest.raises(PermissionError):
        privacy.save_user_photo(env, b"x")
    privacy.record_consent(env)
    privacy.save_user_photo(env, b"secret-bytes")
    assert b"secret-bytes" not in (config.USER_DIR / "photo.enc").read_bytes()
    assert privacy.load_user_photo(env) == b"secret-bytes"
    privacy.delete_everything(env)
    assert not config.USER_DIR.exists() and privacy.load_user_photo(env) is None and db.list_items(env) == []


def test_tryon_gate_and_fallback(env, monkeypatch):
    look = {"look_id": "l1", "collage_path": "c.png", "garments": [{"kind": "dress", "cutout_path": "x.png"}]}
    r = tryon.preview(env, look, tryon.VertexProvider())
    assert r["mode"] == "collage" and "consent" in r["reason"].lower()
    privacy.record_consent(env); monkeypatch.setattr(config, "ALLOW_PERSON_PHOTOS", True)
    privacy.save_user_photo(env, b"png")

    class P(tryon.TryOnProvider):
        def run(self, person, garment, job_id): return garment
    assert tryon.preview(env, look, P(), qa=lambda a, b: tryon.QA(score=2, reason="wrong colour"))["mode"] == "collage"
    assert tryon.preview(env, look, P(), qa=lambda a, b: tryon.QA(score=5))["mode"] == "tryon"
    assert tryon.preview(env, look, tryon.VertexProvider())["mode"] == "collage"
