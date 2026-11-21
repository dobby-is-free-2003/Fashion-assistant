"""Level 2 (try-on) and Level 3 (jewellery overlay). Optional layers: always fall back to the collage."""
import io
import time
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageFilter
from pydantic import BaseModel

from . import config, privacy
from .llm_client import client, with_backoff


class ProviderUnavailable(RuntimeError):
    pass


class TryOnProvider(ABC):
    name = "base"

    @abstractmethod
    def run(self, person: Path, garment: Path, job_id: str) -> Path: ...


class HFSpaceProvider(TryOnProvider):
    """Public Hugging Face Space via gradio_client. Space API signatures change: check the Space's 'Use via API' page.
    A public Space is a THIRD PARTY. Use a stock model photo, not your own."""
    name = "hf_space"

    def run(self, person, garment, job_id):
        try:
            from gradio_client import Client, handle_file
            out = Client(config.TRYON_SPACE).predict(
                dict={"background": handle_file(str(person)), "layers": [], "composite": None},
                garm_img=handle_file(str(garment)), garment_des="", is_checked=True, is_checked_crop=False,
                denoise_steps=30, seed=42, api_name="/tryon")
            return Path(out[0] if isinstance(out, (list, tuple)) else out)
        except Exception as e:  # noqa: BLE001
            raise ProviderUnavailable(f"HF Space failed ({e.__class__.__name__}): {e}") from e


class ColabNotebookProvider(TryOnProvider):
    """Manual batch: writes jobs to data/tryon_jobs/<job>/, you run the try-on model in Colab/Kaggle,
    drop <job>.png into data/tryon_results/, and the next call picks it up."""
    name = "colab"

    def run(self, person, garment, job_id):
        res = config.TRYON_RESULTS / f"{job_id}.png"
        if res.exists():
            return res
        d = config.TRYON_JOBS / job_id
        d.mkdir(parents=True, exist_ok=True)
        Image.open(person).convert("RGB").save(d / "person.png")
        Image.open(garment).convert("RGBA").save(d / "garment.png")
        config.TRYON_RESULTS.mkdir(parents=True, exist_ok=True)
        raise ProviderUnavailable(f"Job queued in {d}. Run it in Colab and save the output as {res}.")


class VertexProvider(TryOnProvider):
    name = "vertex"

    def run(self, *a, **k):
        raise ProviderUnavailable("Vertex AI Virtual Try-On is the paid managed option: not implemented in the free build.")


PROVIDERS = {"hf_space": HFSpaceProvider, "colab": ColabNotebookProvider, "vertex": VertexProvider}


class QA(BaseModel):
    score: int
    reason: str = ""


def qa_score(result: Path, garment: Path) -> QA:
    """Gemini vision: does the garment in the result match the garment cutout? 1 to 5."""
    from google.genai import types
    parts = [types.Part.from_bytes(data=Path(p).read_bytes(), mime_type="image/png" if str(p).endswith("png") else "image/jpeg")
             for p in (garment, result)]
    prompt = "Image 1 is a garment. Image 2 is a person wearing a garment. Score 1-5 how well the garment in image 2 matches image 1 in colour, cut and pattern. 5 = identical."
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=QA, temperature=0)
    r = with_backoff(lambda: client().models.generate_content(model=config.VISION_MODEL, contents=parts + [prompt], config=cfg))
    return r.parsed or QA.model_validate_json(r.text)


def preview(c, look: dict, provider: TryOnProvider, qa=qa_score) -> dict:
    """Try-on for the CHOSEN look only. Returns mode 'tryon' or 'collage' with the reason for any fallback."""
    t0 = time.time()
    fallback = {"mode": "collage", "path": look["collage_path"], "qa": None}
    ok, why = privacy.person_photos_allowed(c)
    if not ok:
        return {**fallback, "reason": why}
    data = privacy.load_user_photo(c)
    if data is None:
        return {**fallback, "reason": "No photo uploaded."}
    tmp = config.USER_DIR / "_person.png"
    tmp.write_bytes(data)
    anchor = next(g for g in look["garments"] if g["kind"] in ("dress", "ethnic_wear", "top"))
    try:
        res = provider.run(tmp, Path(anchor["cutout_path"]), look["look_id"])
        score = qa(res, Path(anchor["cutout_path"]))
    except ProviderUnavailable as e:
        return {**fallback, "reason": str(e)}
    except Exception as e:  # noqa: BLE001
        return {**fallback, "reason": f"QA failed: {e}"}
    finally:
        tmp.unlink(missing_ok=True)
    out = {"mode": "tryon", "path": str(res), "qa": score.score, "seconds": time.time() - t0, "reason": score.reason}
    if score.score < config.TRYON_QA_THRESHOLD:
        return {**fallback, "reason": f"Try-on rejected by QA ({score.score}/5): {score.reason}. Showing collage.", "qa": score.score}
    return out


def overlay_jewellery(person_png: bytes, earring: Path | None, necklace: Path | None) -> Image.Image:
    """Level 3: MediaPipe face landmarks place earrings and a necklace. It is an overlay, and looks like one."""
    try:
        import mediapipe as mp
        import numpy as np
    except ImportError as e:
        raise ProviderUnavailable("mediapipe not installed (pip install -r requirements-extra.txt)") from e
    img = Image.open(io.BytesIO(person_png)).convert("RGBA")
    arr = np.array(img.convert("RGB"))
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as fm:
        res = fm.process(arr)
    if not res.multi_face_landmarks:
        raise ProviderUnavailable("No face found in the photo.")
    lm = res.multi_face_landmarks[0].landmark
    P = lambda i: (lm[i].x * img.width, lm[i].y * img.height)  # noqa: E731
    (lx, ly), (rx, ry), (cx, cy) = P(234), P(454), P(152)
    fw = ((rx - lx) ** 2 + (ry - ly) ** 2) ** 0.5

    def paste(path, cxy, width):
        j = Image.open(path).convert("RGBA")
        j = j.resize((int(width), int(width * j.height / j.width)))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", j.size, (0, 0, 0, 255)), (int(cxy[0] - j.width / 2 + 4), int(cxy[1] + 5)), j.split()[3].point(lambda v: int(v * .3)))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
        img.alpha_composite(j, (int(cxy[0] - j.width / 2), int(cxy[1])))

    if earring:
        for ex, ey in ((lx, ly), (rx, ry)):
            paste(earring, (ex, ey + 0.05 * fw), 0.16 * fw)
    if necklace:
        paste(necklace, (cx, cy + 0.35 * fw), 1.0 * fw)
    return img.convert("RGB")
