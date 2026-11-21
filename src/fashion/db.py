"""SQLite store. item.auto_tags_json is immutable (model output) so tagging accuracy stays honest."""
import json
import sqlite3
from datetime import datetime
from typing import Optional

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS item(
 item_id TEXT PRIMARY KEY, image_path TEXT, cutout_path TEXT, kind TEXT, tags_json TEXT,
 auto_tags_json TEXT, tags_reviewed INTEGER DEFAULT 0, times_worn INTEGER DEFAULT 0,
 last_worn TEXT, prompt_version TEXT, model TEXT);
CREATE TABLE IF NOT EXISTS session(session_id TEXT PRIMARY KEY, occasion TEXT, formality INTEGER,
 weather_json TEXT, constraints_json TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS look(look_id TEXT PRIMARY KEY, session_id TEXT, item_ids_json TEXT,
 scores_json TEXT, features_json TEXT, slot TEXT, rationale TEXT, collage_path TEXT, rating INTEGER);
CREATE TABLE IF NOT EXISTS choice_event(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
 shown_json TEXT, chosen TEXT, reason TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS trend_note(note_id TEXT PRIMARY KEY, tags_json TEXT, summary TEXT,
 source_url TEXT, source_name TEXT, observed_at TEXT, base_weight REAL DEFAULT 1);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS metric(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, value REAL, ts TEXT, meta TEXT);
"""


def conn(path=None) -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def add_item(c, item_id, image_path, cutout_path, tags: dict, prompt_version="", model="", reviewed=0) -> None:
    js = json.dumps(tags)
    c.execute("INSERT OR REPLACE INTO item(item_id,image_path,cutout_path,kind,tags_json,auto_tags_json,"
              "tags_reviewed,prompt_version,model) VALUES(?,?,?,?,?,?,?,?,?)",
              (item_id, str(image_path), str(cutout_path), tags["kind"], js, js, reviewed, prompt_version, model))
    c.commit()


def update_tags(c, item_id, tags: dict, reviewed=True) -> None:
    c.execute("UPDATE item SET tags_json=?, kind=?, tags_reviewed=? WHERE item_id=?",
              (json.dumps(tags), tags["kind"], int(reviewed), item_id))
    c.commit()


def get_item(c, item_id) -> Optional[dict]:
    r = c.execute("SELECT * FROM item WHERE item_id=?", (item_id,)).fetchone()
    return _row(r) if r else None


def list_items(c, reviewed: Optional[bool] = None) -> list[dict]:
    q, a = "SELECT * FROM item", ()
    if reviewed is not None:
        q, a = q + " WHERE tags_reviewed=?", (int(reviewed),)
    return [_row(r) for r in c.execute(q + " ORDER BY rowid", a)]


def delete_item(c, item_id) -> None:
    c.execute("DELETE FROM item WHERE item_id=?", (item_id,))
    c.commit()


def mark_worn(c, item_ids, day: str) -> None:
    for i in item_ids:
        c.execute("UPDATE item SET times_worn=times_worn+1, last_worn=? WHERE item_id=?", (day, i))
    c.commit()


def flat(item: dict) -> dict:
    """Item row -> flat dict used by rules and look generation."""
    return {**item["tags"], "item_id": item["item_id"], "cutout_path": item["cutout_path"],
            "times_worn": item["times_worn"], "last_worn": item["last_worn"]}


def kv_get(c, key, default=None):
    r = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def kv_set(c, key, value) -> None:
    c.execute("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, json.dumps(value)))
    c.commit()


def log_metric(c, name: str, value: float, meta: dict | None = None) -> None:
    c.execute("INSERT INTO metric(name,value,ts,meta) VALUES(?,?,?,?)",
              (name, value, datetime.now().isoformat(timespec="seconds"), json.dumps(meta or {})))
    c.commit()


def _row(r) -> dict:
    d = dict(r)
    d["tags"] = json.loads(d.pop("tags_json"))
    d["auto_tags"] = json.loads(d.pop("auto_tags_json"))
    return d
