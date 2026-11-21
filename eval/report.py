"""Summary of measured results from the app's own logs.
  python eval/report.py export-ratings   # writes eval/look_ratings.csv: rate 30 looks 1-5 (you + 3 friends)
  python eval/report.py summary          # diversity %, latency p50/p95, look ratings mean/spread"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import db  # noqa: E402


def pct(name, c):
    v = [r["value"] for r in c.execute("SELECT value FROM metric WHERE name=?", (name,))]
    return {"n": len(v), "p50": float(np.percentile(v, 50)), "p95": float(np.percentile(v, 95))} if v else {"n": 0}


if __name__ == "__main__":
    c = db.conn()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "export-ratings":
        rows = c.execute("SELECT look_id, slot, collage_path, rating FROM look ORDER BY rowid DESC LIMIT 30").fetchall()
        with open("eval/look_ratings.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["look_id", "slot", "collage_path", "rating_1_to_5"])
            w.writerows([[r["look_id"], r["slot"], r["collage_path"], r["rating"] or ""] for r in rows])
        print("wrote eval/look_ratings.csv; fill the last column (average several raters), then run summary --ratings")
    else:
        div = [r["value"] for r in c.execute("SELECT value FROM metric WHERE name='diverse'")]
        res = {"date": str(date.today()), "sessions": len(div), "diversity_pct": 100 * float(np.mean(div)) if div else None,
               "look_generation_s": pct("look_generation_s", c), "collage_render_s": pct("collage_render_s", c),
               "tryon_s": pct("tryon_s", c)}
        qa = [r["value"] for r in c.execute("SELECT value FROM metric WHERE name='tryon_qa'")]
        res["tryon_pass_rate"] = float(np.mean([q >= 3 for q in qa])) if qa else None
        rt = [r["rating"] for r in c.execute("SELECT rating FROM look WHERE rating IS NOT NULL")]
        if "--ratings" in sys.argv:
            rt = [float(r["rating_1_to_5"]) for r in csv.DictReader(open("eval/look_ratings.csv")) if r["rating_1_to_5"]]
        res["look_rating"] = {"n": len(rt), "mean": float(np.mean(rt)), "sd": float(np.std(rt))} if rt else None
        Path("eval/reports").mkdir(parents=True, exist_ok=True)
        Path(f"eval/reports/summary_{res['date']}.json").write_text(json.dumps(res, indent=2))
        print(json.dumps(res, indent=2))
