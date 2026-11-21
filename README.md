# Fashion Assistant
Catalogue your own wardrobe from photos, tell it the occasion, get three deliberately different looks (A your taste, B on trend, C exploration),
see them as collages, optionally preview on a photo, and it learns from what you pick.

## Setup (Windows, Python 3.11+)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-extra.txt     # optional: ADK chat, jewellery overlay, HF try-on
copy .env.example .env                    # optional for demo; add GEMINI_API_KEY from AI Studio for tagging/critic/trends
pytest -q                                 # 23 tests, no key needed
streamlit run app/app.py
```
In the app: **Wardrobe -> "Load 41-item demo wardrobe"** then **Style me**. That works with no key and no photos.
For your real wardrobe: add GEMINI_API_KEY, upload clothing/jewellery photos in the Wardrobe tab (or `python scripts/ingest_folder.py <folder>`), review tags.
First rembg run downloads its model. API: `uvicorn fashion.api:app --port 8000` (docs at /docs).

## Evaluation (writes to eval/reports/)
| Measure | Command |
|---|---|
| Tagging accuracy (60+ items) | `python eval/measure_tagging.py --from-reviewed` or `--labels labels.csv` |
| Learning curve, simulated persona, 200 sessions | `python eval/simulate_persona.py` |
| Diversity %, latency p50/p95, try-on pass rate, look ratings | `python eval/report.py summary` (`export-ratings` first for the 30-look rating sheet) |
| Rules, selection, privacy, learning | `pytest -q` |
Report real numbers with date and model. Do not claim more than you measured.

## Privacy rules
Free Gemini tier may train on inputs: only clothing/jewellery or stock photos. Your own face/body photo only after a paid no-training setup,
`ALLOW_PERSON_PHOTOS=true` and consent in the Privacy tab (encrypted at rest, one-click delete-everything). A public HF Space is a third party.
Trends: Google Search grounding, paraphrased notes with links. No Pinterest scraping. Schedule `scripts/refresh_trends.py` weekly (Task Scheduler).

## Limitations (and what I would change in production)
Rules are heuristic; 2D try-on is unreliable on draped/ethnic garments (QA step falls back to the collage); jewellery overlay looks like an overlay;
Gemini free-tier limits apply; SQLite/Qdrant are local (production: Firestore, Vertex Vector Search, Vertex Virtual Try-On, paid no-training config).
See docs/ for architecture, contracts and dated decisions.
