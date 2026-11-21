"""Run weekly (Windows Task Scheduler). Needs GEMINI_API_KEY. Uses Google Search grounding; stores paraphrased notes + links only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import db, trends  # noqa: E402

print("added", trends.refresh(db.conn()), "trend notes")
