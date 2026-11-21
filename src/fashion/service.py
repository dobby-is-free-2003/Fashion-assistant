"""Orchestrates one styling session and the feedback loop. Tools return {ok, data, error}."""
import json
import logging
import time
import uuid
from datetime import date, datetime
from pathlib import Path

import numpy as np

from . import config, context, critic, db, looks, privacy, render, trends
from .learner import PreferenceLearner

log = logging.getLogger("fashion.service")
SLOT_TITLE = {"taste": "Look A: your taste", "trend": "Look B: on trend", "explore": "Look C: something new"}


class StylistService:
    def __init__(self, c=None, seed=None, today: date | None = None):
        self.c = c or db.conn()
        self.rng = np.random.default_rng(seed)
        self.today = today
        self.learner = PreferenceLearner.from_json(db.kv_get(self.c, "learner"))
        self.last_plan = None
        config.ensure_dirs()

    def _items(self):
        return [db.flat(i) for i in db.list_items(self.c)]

    def plan_looks(self, occasion, formality=None, avoid_colours=(), wear_colours=(), weather=None, render_collage=True) -> dict:
        t0 = time.time()
        formality = int(formality or config.OCCASION_FORMALITY.get(occasion, 3))
        session = {"occasion": occasion, "formality": formality, "avoid_colours": list(avoid_colours), "wear_colours": list(wear_colours)}
        weather = weather or context.get_weather()
        items = self._items()
        if not any(i["kind"] in ("dress", "ethnic_wear", "top") for i in items):
            raise ValueError("Wardrobe has no dresses, ethnic wear or tops yet. Add items or run scripts/seed_demo.py.")
        notes = trends.active_notes(self.c, self.today)
        cands = looks.build_candidates(items, session, weather, self.rng, notes, self.today)
        cache = {}

        def accept(c):
            k = tuple(c["ids"])
            if k not in cache:
                cache[k] = critic.review(c, session, weather)
            return cache[k].coherent

        picks = looks.select_three(cands, self.learner, self.rng, accept)
        t_gen = time.time() - t0
        sid = uuid.uuid4().hex[:10]
        self.c.execute("INSERT INTO session VALUES(?,?,?,?,?,?)", (sid, occasion, formality, json.dumps(weather),
                       json.dumps(session), datetime.now().isoformat(timespec="seconds")))
        out, t1 = [], time.time()
        for slot, c in picks:
            lid = uuid.uuid4().hex[:10]
            v = cache.get(tuple(c["ids"])) or critic.review(c, session, weather)
            path = render.save_collage(c["garments"], c["jewels"], config.RENDER_DIR / f"{lid}.png", SLOT_TITLE[slot]) if render_collage else ""
            scores = {"rule": round(c["rule"], 3), "preference": round(self.learner.score(c["x"]), 3), "trend": round(c["trend"], 3),
                      "novelty": round(c["novelty"], 3), "recency_penalty": c["recency"], "components": c["comps"]}
            self.c.execute("INSERT INTO look(look_id,session_id,item_ids_json,scores_json,features_json,slot,rationale,collage_path) VALUES(?,?,?,?,?,?,?,?)",
                           (lid, sid, json.dumps(c["ids"]), json.dumps(scores), json.dumps(c["x"]), slot, v.rationale, str(path)))
            out.append({"look_id": lid, "slot": slot, "title": SLOT_TITLE[slot], "item_ids": c["ids"], "scores": scores,
                        "rationale": v.rationale, "collage_path": str(path), "garments": c["garments"], "jewels": c["jewels"],
                        "reasons": c["reasons"]})
        self.c.commit()
        db.log_metric(self.c, "look_generation_s", t_gen, {"candidates": len(cands)})
        db.log_metric(self.c, "collage_render_s", time.time() - t1)
        diverse = len(picks) == 3 and all(looks.differ(x[1], y[1]) for x, y in ((picks[0], picks[1]), (picks[0], picks[2]), (picks[1], picks[2])))
        db.log_metric(self.c, "diverse", float(diverse))
        self.last_plan = {"session_id": sid, "session": session, "weather": weather, "looks": out}
        return self.last_plan

    def choose(self, session_id, look_id=None, reason="") -> dict:
        rows = self.c.execute("SELECT * FROM look WHERE session_id=?", (session_id,)).fetchall()
        if not rows:
            return {"ok": False, "data": None, "error": "unknown session"}
        shown = [r["look_id"] for r in rows]
        self.c.execute("INSERT INTO choice_event(session_id,shown_json,chosen,reason,ts) VALUES(?,?,?,?,?)",
                       (session_id, json.dumps(shown), look_id, reason, datetime.now().isoformat(timespec="seconds")))
        if look_id:
            chosen = next(r for r in rows if r["look_id"] == look_id)
            self.learner.update(json.loads(chosen["features_json"]), [json.loads(r["features_json"]) for r in rows if r["look_id"] != look_id])
            db.kv_set(self.c, "learner", self.learner.to_json())
            db.mark_worn(self.c, json.loads(chosen["item_ids_json"]), str(self.today or date.today()))
        self.c.commit()
        return {"ok": True, "data": {"learned": bool(look_id), "n_updates": self.learner.n}, "error": None}

    def rate_look(self, look_id, rating: int) -> None:
        self.c.execute("UPDATE look SET rating=? WHERE look_id=?", (rating, look_id))
        self.c.commit()

    def get_look(self, look_id) -> dict:
        r = self.c.execute("SELECT * FROM look WHERE look_id=?", (look_id,)).fetchone()
        by = {i["item_id"]: i for i in self._items()}
        ids = json.loads(r["item_ids_json"])
        its = [by[i] for i in ids if i in by]
        return {"look_id": look_id, "collage_path": r["collage_path"], "garments": [i for i in its if i["kind"] != "jewellery"],
                "jewels": [i for i in its if i["kind"] == "jewellery"], "slot": r["slot"]}

    def wardrobe_summary(self) -> dict:
        items = self._items()
        kinds = {}
        for i in items:
            kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
        return {"total": len(items), "by_kind": kinds}

    def delete_everything(self, store=None) -> dict:
        res = privacy.delete_everything(self.c, store)
        self.learner = PreferenceLearner()
        return res
