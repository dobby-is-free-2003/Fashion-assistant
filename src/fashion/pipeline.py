"""Ingest one photo: copy, cutout, tag, store, embed."""
import hashlib
import shutil
from pathlib import Path

from . import config, db, imaging, tagger, vectors
from .schema import ItemTags


def ingest_image(path: Path, store: vectors.VectorStore | None = None, c=None) -> str:
    config.ensure_dirs()
    c = c or db.conn()
    item_id = hashlib.sha1(Path(path).read_bytes()).hexdigest()[:12]
    if db.get_item(c, item_id):
        return item_id  # idempotent: skip duplicates (saves quota)
    raw = config.RAW_DIR / f"{item_id}{Path(path).suffix.lower()}"
    shutil.copy(path, raw)
    cutout = imaging.make_cutout(raw, config.CUTOUT_DIR / f"{item_id}.png")
    tags: ItemTags = tagger.tag_image(cutout)
    d = tags.model_dump()
    db.add_item(c, item_id, raw, cutout, d, tagger.PROMPT_VERSION, config.VISION_MODEL)
    if store is not None:
        store.upsert(item_id, vectors.embed_text(vectors.tags_to_text(d)), {"kind": d["kind"]})
    return item_id
