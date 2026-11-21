"""Gemini vision tagging with a JSON response schema."""
import io
from PIL import Image
from google.genai import types

from . import config
from .llm_client import client, with_backoff
from .schema import ItemTags

PROMPT_VERSION = "tagging_v1"


def load_prompt() -> str:
    text = (config.PROMPT_DIR / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    return text.replace("{occasions}", ", ".join(config.OCCASIONS))


def _flatten_to_jpeg(cutout_path) -> bytes:
    img = Image.open(cutout_path).convert("RGBA")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    bg.thumbnail((768, 768))
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def tag_image(cutout_path) -> ItemTags:
    part = types.Part.from_bytes(data=_flatten_to_jpeg(cutout_path), mime_type="image/jpeg")
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json", response_schema=ItemTags, temperature=0.1
    )
    resp = with_backoff(
        lambda: client().models.generate_content(
            model=config.VISION_MODEL, contents=[part, load_prompt()], config=cfg
        )
    )
    if resp.parsed is not None:
        return resp.parsed
    return ItemTags.model_validate_json(resp.text)
