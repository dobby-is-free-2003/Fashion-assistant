"""Learning curve: a simulated persona with hidden preferences makes 200 choices.
Reports how often Look A (best match to learned taste) is the persona's pick, in rolling windows.
Usage: python eval/simulate_persona.py [--sessions 200] [--seed 0]"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import config, db, demo, features, looks, trends  # noqa: E402
from fashion.learner import PreferenceLearner  # noqa: E402
from fashion.rules import FAMILIES  # noqa: E402

OCC = ["casual", "office", "party", "festive", "wedding_guest", "college", "engagement_evening"]


def hidden_persona():
    w = np.zeros(features.DIM)
    N = features.NAMES
    # Deliberately idiosyncratic: likes pink/purple, bold jewellery, patterns and layers; dislikes blue and ethnic wear.
    w[N.index("colour_pink")] = 3.0; w[N.index("colour_purple")] = 2.5; w[N.index("colour_blue")] = -2.5
    w[N.index("jewellery_boldness")] = 3.0; w[N.index("bold_pattern")] = 2.0; w[N.index("anchor_ethnic")] = -2.5
    w[N.index("has_layer")] = 1.5; w[N.index("formality")] = -1.0
    return w


def run(sessions=200, seed=0, mem_db=True):
    rng = np.random.default_rng(seed)
    c = db.conn(":memory:")
    config.ensure_dirs(); demo.seed_demo(c); trends.seed(c)
    notes = trends.active_notes(c, date(2026, 1, 1))
    items = [db.flat(i) for i in db.list_items(c)]
    learner, w_star, hits, pcts = PreferenceLearner(), hidden_persona(), [], []
    weather = {"temp_c": 24, "season": "all"}
    for _ in range(sessions):
        occ = OCC[rng.integers(len(OCC))]
        sess = {"occasion": occ, "formality": config.OCCASION_FORMALITY[occ], "avoid_colours": [], "wear_colours": []}
        cands = looks.build_candidates(items, sess, weather, rng, notes, today=date(2026, 1, 1))
        picks = looks.select_three(cands, learner, rng)
        if len(picks) < 3:
            continue
        allu = np.array([w_star @ np.array(c_["x"]) for c_ in cands])
        a_u = w_star @ np.array(picks[0][1]["x"])
        pcts.append(float((allu < a_u).mean()))  # share of candidates the persona likes less than Look A
        util = [w_star @ np.array(c_["x"]) + rng.gumbel() * 0.3 for _, c_ in picks]
        k = int(np.argmax(util))
        hits.append(1 if picks[k][0] == "taste" else 0)
        learner.update(picks[k][1]["x"], [p[1]["x"] for i, p in enumerate(picks) if i != k])
    return hits, pcts


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--sessions", type=int, default=200); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    hits, pcts = run(a.sessions, a.seed)
    win = 20
    curve = [float(np.mean(hits[max(0, i - win):i])) for i in range(win, len(hits) + 1)]
    out = Path("eval/reports"); out.mkdir(parents=True, exist_ok=True)
    res = {"date": str(date.today()), "sessions": len(hits), "random_baseline": 1 / 3,
           "look_A_pick_rate_first_40": float(np.mean(hits[:40])), "look_A_pick_rate_last_40": float(np.mean(hits[-40:])),
           "look_A_utility_percentile_first_10": float(np.mean(pcts[:10])), "look_A_utility_percentile_last_40": float(np.mean(pcts[-40:]))}
    pc = [float(np.mean(pcts[max(0, i - win):i])) for i in range(win, len(pcts) + 1)]
    (out / "learning_curve.json").write_text(json.dumps({**res, "pick_rate_curve": curve, "percentile_curve": pc}, indent=2))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7, 4)); plt.plot(range(win, len(hits) + 1), curve, label=f"Look A pick rate ({win}-session window)")
    plt.plot(range(win, len(pcts) + 1), pc, label="Look A utility percentile among all candidates")
    plt.axhline(1 / 3, ls="--", c="grey", label="random (1/3)"); plt.ylim(0, 1); plt.xlabel("session"); plt.ylabel("persona picks Look A")
    plt.legend(); plt.title("Simulated persona learning curve"); plt.tight_layout(); plt.savefig(out / "learning_curve.png", dpi=130)
    print(json.dumps(res, indent=2))
