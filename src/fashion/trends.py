"""Trend notes: paraphrased, dated, sourced. Never copied text or images. No Pinterest scraping."""
import json
import re
import uuid
from datetime import date

from . import config, db
from .llm_client import client, with_backoff
from .rules import FAMILIES, toks

NAME_TO_FAMILY = {"sage": "green", "olive": "green", "emerald": "green", "mint": "green", "teal": "blue",
    "navy": "blue", "cobalt": "blue", "indigo": "blue", "blush": "pink", "rose": "pink", "fuchsia": "pink",
    "lavender": "purple", "lilac": "purple", "mustard": "yellow", "rust": "orange", "terracotta": "orange",
    "maroon": "red", "burgundy": "red", "wine": "red", "cream": "neutral", "ivory": "neutral", "beige": "neutral",
    "black": "neutral", "white": "neutral", "grey": "neutral", "gray": "neutral", "brown": "orange"}
SEEDS = [  # placeholders so the demo works offline; replace by running the trend agent
    (["palette:sage", "silhouette:anarkali"], "Muted greens paired with flowing anarkali cuts."),
    (["palette:black", "pairing:oxidised"], "Dark outfits with oxidised silver jewellery."),
    (["silhouette:kurti", "pairing:minimal"], "Simple kurti sets with very light jewellery."),
]


def add_note(c, tags, summary, source_url="", source_name="", observed_at=None, base_weight=1.0) -> str:
    nid = uuid.uuid4().hex[:10]
    c.execute("INSERT INTO trend_note VALUES(?,?,?,?,?,?,?)", (nid, json.dumps(tags), summary, source_url,
              source_name, observed_at or str(date.today()), base_weight))
    c.commit()
    return nid


def seed(c) -> None:
    if not c.execute("SELECT 1 FROM trend_note").fetchone():
        for tags, s in SEEDS:
            add_note(c, tags, s, source_name="manual placeholder (not a real source)")


def active_notes(c, today: date | None = None) -> list[dict]:
    today = today or date.today()
    out = []
    for r in c.execute("SELECT * FROM trend_note"):
        age = (today - date.fromisoformat(r["observed_at"])).days
        out.append({**dict(r), "tags": json.loads(r["tags_json"]), "weight": r["base_weight"] * 0.5 ** (max(age, 0) / 30)})
    return out


def look_tokens(gs, js) -> set:
    t = set()
    for g in gs:
        from .rules import family
        t.add(("palette", family(g["primary_color_hex"])))
        for w in toks(g["subtype"]) | toks(g["kind"]) | {s for x in g.get("style_tags", []) for s in toks(x)}:
            t.add(("silhouette", w))
    for j in js:
        for w in toks(j["subtype"]) | toks(j.get("metal_tone")):
            t.add(("pairing", w))
        if j["embellishment_level"] <= 1:
            t.add(("pairing", "minimal"))
    return t


def _tag_match(tag: str, tokens: set) -> bool:
    cat, _, val = tag.partition(":")
    words = toks(val)
    if cat == "palette":
        fams = {NAME_TO_FAMILY.get(w, w) for w in words}
        return any((cat, f) in tokens for f in fams if f in FAMILIES)
    return any((cat, w) in tokens for w in words)


def trend_score(gs, js, notes) -> float:
    if not notes:
        return 0.0
    tokens = look_tokens(gs, js)
    s = sum(n["weight"] * sum(_tag_match(t, tokens) for t in n["tags"]) / max(len(n["tags"]), 1) for n in notes)
    return min(1.0, s)


def refresh(c, region="India", n=5) -> int:
    """Trend agent: Gemini + Google Search grounding -> paraphrased notes with sources."""
    from google.genai import types
    prompt = (config.PROMPT_DIR / "trends_v1.md").read_text(encoding="utf-8").replace("{region}", region).replace("{n}", str(n))
    cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
    resp = with_backoff(lambda: client().models.generate_content(model=config.VISION_MODEL, contents=prompt, config=cfg))
    m = re.search(r"\[.*\]", resp.text or "", re.S)
    if not m:
        return 0
    chunks = []
    try:
        chunks = [(g.web.uri, g.web.title) for g in resp.candidates[0].grounding_metadata.grounding_chunks if g.web]
    except Exception:  # noqa: BLE001
        pass
    added = 0
    for i, o in enumerate(json.loads(m.group(0))[:n]):
        url, name = (o.get("source_url") or "", o.get("source_name") or "")
        if not url and chunks:
            url, name = chunks[min(i, len(chunks) - 1)]
        add_note(c, o.get("tags", []), (o.get("summary") or "")[:200], url, name)
        added += 1
    return added
