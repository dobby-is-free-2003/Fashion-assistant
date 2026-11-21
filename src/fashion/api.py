"""FastAPI service (plan 5.1): run with  uvicorn fashion.api:app --port 8000"""
from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from . import db, privacy, trends, tryon
from .service import StylistService

app = FastAPI(title="Fashion Assistant")
svc = StylistService()


class LooksReq(BaseModel):
    occasion: str
    formality: int | None = None
    avoid_colours: list[str] = []
    wear_colours: list[str] = []


class ChoiceReq(BaseModel):
    session_id: str
    look_id: str | None = None
    reason: str = ""


@app.get("/health")
def health():
    return {"ok": True, "items": svc.wardrobe_summary()["total"]}


@app.get("/items")
def items():
    return [{"item_id": i["item_id"], **i["tags"]} for i in db.list_items(svc.c)]


@app.post("/looks")
def looks(r: LooksReq):
    try:
        p = svc.plan_looks(r.occasion, r.formality, r.avoid_colours, r.wear_colours)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"session_id": p["session_id"], "looks": [{k: v for k, v in l.items() if k not in ("garments", "jewels")} for l in p["looks"]]}


@app.post("/choice")
def choice(r: ChoiceReq):
    return svc.choose(r.session_id, r.look_id, r.reason)


@app.post("/tryon/{look_id}")
def do_tryon(look_id: str, provider: str = "hf_space"):
    return tryon.preview(svc.c, svc.get_look(look_id), tryon.PROVIDERS[provider]())


@app.get("/trends")
def get_trends():
    return [{k: n[k] for k in ("note_id", "tags", "summary", "source_url", "source_name", "observed_at", "weight")} for n in trends.active_notes(svc.c)]


@app.post("/trends/refresh")
def refresh_trends():
    return {"added": trends.refresh(svc.c)}


@app.post("/privacy/consent")
def consent():
    privacy.record_consent(svc.c)
    return {"ok": True}


@app.post("/privacy/photo")
async def photo(f: UploadFile):
    try:
        privacy.save_user_photo(svc.c, await f.read())
    except PermissionError as e:
        raise HTTPException(403, str(e))
    return {"ok": True}


@app.post("/privacy/delete")
def delete_all():
    return svc.delete_everything()
