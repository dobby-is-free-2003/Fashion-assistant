"""Consent, encrypted user photo, and delete-everything."""
import shutil
from datetime import datetime

from cryptography.fernet import Fernet

from . import config, db


def _fernet() -> Fernet:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.KEY_PATH.exists():
        config.KEY_PATH.write_bytes(Fernet.generate_key())
    return Fernet(config.KEY_PATH.read_bytes())


def record_consent(c) -> None:
    db.kv_set(c, "consent_at", datetime.now().isoformat(timespec="seconds"))


def has_consent(c) -> bool:
    return db.kv_get(c, "consent_at") is not None


def person_photos_allowed(c) -> tuple[bool, str]:
    if not has_consent(c):
        return False, "No consent recorded."
    if not config.ALLOW_PERSON_PHOTOS:
        return False, "ALLOW_PERSON_PHOTOS is false. Set it true only after switching to a paid, no-training Gemini config."
    return True, "ok"


def save_user_photo(c, data: bytes) -> None:
    if not has_consent(c):
        raise PermissionError("Record consent before saving a photo.")
    config.USER_DIR.mkdir(parents=True, exist_ok=True)
    (config.USER_DIR / "photo.enc").write_bytes(_fernet().encrypt(data))
    db.kv_set(c, "photo_saved_at", datetime.now().isoformat(timespec="seconds"))


def load_user_photo(c) -> bytes | None:
    p = config.USER_DIR / "photo.enc"
    return _fernet().decrypt(p.read_bytes()) if p.exists() else None


def delete_everything(c, store=None, wipe_wardrobe=True) -> dict:
    """Removes photo, key, sessions, looks, choices, learned weights, renders, try-on files, and (default) the wardrobe."""
    n = {}
    for d in (config.USER_DIR, config.RENDER_DIR, config.TRYON_JOBS, config.TRYON_RESULTS):
        n[d.name] = d.exists()
        shutil.rmtree(d, ignore_errors=True)
    for t in ("session", "look", "choice_event", "kv", "metric"):
        n[t] = c.execute(f"DELETE FROM {t}").rowcount
    if wipe_wardrobe:
        for it in db.list_items(c):
            if store is not None:
                try: store.delete(it["item_id"])
                except Exception: pass  # noqa: BLE001
            for k in ("image_path", "cutout_path"):
                try:
                    import pathlib; pathlib.Path(it[k]).unlink(missing_ok=True)
                except OSError: pass
        n["item"] = c.execute("DELETE FROM item").rowcount
    c.commit()
    config.KEY_PATH.unlink(missing_ok=True)
    return n
