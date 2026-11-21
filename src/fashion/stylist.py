"""Conversational stylist built on Google ADK (optional dependency: pip install -r requirements-extra.txt).
The core app does not need it; the form in the UI calls the same service."""
import asyncio

from . import config


def available() -> bool:
    try:
        import google.adk  # noqa: F401
        return config.llm_enabled()
    except ImportError:
        return False


class Stylist:
    APP = "fashion_stylist"

    def __init__(self, svc):
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        self.svc, self.created = svc, set()

        def plan_looks(occasion: str, formality: int = 0, colours_to_avoid: str = "", colours_to_wear: str = "") -> dict:
            """Build three outfit looks from the owner's wardrobe. formality 1 (casual) to 5 (very formal), 0 if unknown.
            colours_to_avoid / colours_to_wear: comma separated from neutral, red, orange, yellow, green, blue, purple, pink."""
            try:
                sp = lambda s: [x.strip() for x in s.split(",") if x.strip()]  # noqa: E731
                p = svc.plan_looks(occasion, formality or None, sp(colours_to_avoid), sp(colours_to_wear))
                return {"ok": True, "error": None, "data": [{"slot": l["slot"], "items": [g["subtype"] for g in l["garments"] + l["jewels"]],
                                                              "rationale": l["rationale"]} for l in p["looks"]]}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "data": None, "error": str(e)}

        def wardrobe_summary() -> dict:
            """Counts of wardrobe items by kind."""
            return {"ok": True, "data": svc.wardrobe_summary(), "error": None}

        agent = LlmAgent(name="stylist", model=config.VISION_MODEL, instruction=(config.PROMPT_DIR / "stylist_v1.md").read_text(encoding="utf-8"),
                         tools=[plan_looks, wardrobe_summary])
        self.ss = InMemorySessionService()
        self.runner = Runner(agent=agent, app_name=self.APP, session_service=self.ss)

    def turn(self, user_id: str, session_id: str, text: str) -> str:
        from google.genai import types

        async def go():
            if session_id not in self.created:
                await self.ss.create_session(app_name=self.APP, user_id=user_id, session_id=session_id)
                self.created.add(session_id)
            out = ""
            async for ev in self.runner.run_async(user_id=user_id, session_id=session_id,
                                                  new_message=types.Content(role="user", parts=[types.Part(text=text)])):
                if ev.is_final_response() and ev.content and ev.content.parts:
                    out = ev.content.parts[0].text or ""
            return out
        return asyncio.run(go())
