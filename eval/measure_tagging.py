"""Tagging accuracy of the MODEL's original tags (auto_tags), never the corrected ones.
Ground truth: either a hand-label CSV (item_id,kind,primary_color_hex,formality)
or --from-reviewed (your corrections in the review screen are the labels).
Usage: python eval/measure_tagging.py [--labels labels.csv | --from-reviewed]"""
import csv
import json
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import db, config  # noqa: E402
from fashion.imaging import hex_distance  # noqa: E402

COLOUR_TOL = 60.0  # RGB euclidean distance counted as "same colour"; document any change


def score(pairs: list[tuple[dict, dict]]) -> dict:
    n = len(pairs)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "kind_acc": sum(a["kind"] == g["kind"] for a, g in pairs) / n,
        "colour_acc": sum(hex_distance(a["primary_color_hex"], g["primary_color_hex"]) <= COLOUR_TOL for a, g in pairs) / n,
        "formality_exact": sum(a["formality"] == int(g["formality"]) for a, g in pairs) / n,
        "formality_within1": sum(abs(a["formality"] - int(g["formality"])) <= 1 for a, g in pairs) / n,
    }


if __name__ == "__main__":
    c = db.conn()
    items = {i["item_id"]: i for i in db.list_items(c)}
    if "--labels" in sys.argv:
        rows = list(csv.DictReader(open(sys.argv[sys.argv.index("--labels") + 1], encoding="utf-8")))
        pairs = [(items[r["item_id"]]["auto_tags"], r) for r in rows if r["item_id"] in items]
        truth = "hand labels"
    else:
        pairs = [(i["auto_tags"], i["tags"]) for i in items.values() if i["tags_reviewed"]]
        truth = "owner-reviewed tags"
    res = {"date": str(date.today()), "model": config.VISION_MODEL, "ground_truth": truth, **score(pairs)}
    out = Path("eval/reports"); out.mkdir(parents=True, exist_ok=True)
    (out / f"tagging_{res['date']}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
