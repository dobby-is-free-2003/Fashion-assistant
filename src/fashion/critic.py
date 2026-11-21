"""Critic + rationale. Gemini checklist prompt when a key is set; deterministic fallback otherwise."""
import logging

from pydantic import BaseModel

from . import config
from .llm_client import client, with_backoff

log = logging.getLogger("fashion.critic")


class Verdict(BaseModel):
    coherent: bool
    issues: list[str] = []
    rationale: str


def describe(c) -> str:
    return "\n".join(f"- {g['subtype']} ({g['kind']}, colour {g['primary_color_hex']}, {g['pattern']}, formality {g['formality']}, "
                     f"neckline {g.get('neckline')}, metal {g.get('metal_tone')}, embellishment {g['embellishment_level']})"
                     for g in c["garments"] + c["jewels"])


def fallback(c, session) -> Verdict:
    top = [r for r in c["reasons"] if r][:2]
    text = f"This works for a {session['occasion'].replace('_', ' ')}: {top[0]}. " + (f"Also, {top[1]}." if len(top) > 1 else "")
    return Verdict(coherent=c["rule"] >= 0.55, issues=[], rationale=text)


def review(c, session, weather=None) -> Verdict:
    if not config.llm_enabled():
        return fallback(c, session)
    from google.genai import types
    prompt = (config.PROMPT_DIR / "critic_v1.md").read_text(encoding="utf-8").format(
        occasion=session["occasion"], formality=session["formality"], weather=weather or {}, items=describe(c),
        reasons="; ".join(c["reasons"]))
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=Verdict, temperature=0.3)
    try:
        r = with_backoff(lambda: client().models.generate_content(model=config.VISION_MODEL, contents=prompt, config=cfg))
        return r.parsed or Verdict.model_validate_json(r.text)
    except Exception as e:  # noqa: BLE001
        log.warning("critic LLM failed, using fallback: %s", e)
        return fallback(c, session)
