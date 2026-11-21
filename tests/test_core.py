import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fashion import db, llm_client
from fashion.schema import ItemTags
from fashion.imaging import hex_distance
from eval.measure_tagging import score

GOOD = dict(kind="ethnic_wear", subtype="kurti", primary_color_hex="#a1b2c3", formality=9)


def test_schema_normalises():
    t = ItemTags(**GOOD)
    assert t.primary_color_hex == "#A1B2C3" and t.formality == 5


def test_schema_rejects_bad_hex_and_kind():
    with pytest.raises(ValueError):
        ItemTags(**{**GOOD, "primary_color_hex": "blue"})
    with pytest.raises(ValueError):
        ItemTags(**{**GOOD, "kind": "hat"})


def test_db_keeps_auto_tags_immutable(tmp_path):
    c = db.conn(tmp_path / "t.db")
    tags = ItemTags(**GOOD).model_dump()
    db.add_item(c, "x1", "a.jpg", "a.png", tags)
    fixed = {**tags, "kind": "top"}
    db.update_tags(c, "x1", fixed)
    it = db.get_item(c, "x1")
    assert it["tags"]["kind"] == "top" and it["auto_tags"]["kind"] == "ethnic_wear" and it["tags_reviewed"] == 1


def test_backoff_retries_on_429_then_succeeds():
    llm_client.Counter.requests = 0
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"
    assert llm_client.with_backoff(flaky, sleep=lambda s: None) == "ok" and calls["n"] == 3


def test_backoff_does_not_retry_other_errors():
    with pytest.raises(ValueError):
        llm_client.with_backoff(lambda: (_ for _ in ()).throw(ValueError("bad")), sleep=lambda s: None)


def test_scoring():
    a = ItemTags(**GOOD).model_dump()
    g = {"kind": "ethnic_wear", "primary_color_hex": "#A1B2C0", "formality": 4}
    r = score([(a, g)])
    assert r["kind_acc"] == 1 and r["colour_acc"] == 1 and r["formality_within1"] == 1
    assert hex_distance("#000000", "#FFFFFF") > 400
