# Architecture
```
photos -> rembg cutout -> Gemini vision (JSON schema) -> review UI -> SQLite item (auto_tags immutable) + Qdrant
occasion form / ADK stylist chat
   -> context (Open-Meteo)  -> looks.build_candidates (anchor + layer + jewellery, hard filters)
   -> rules.rule_score (colour HSV, pattern, formality, jewellery, season, occasion)
   + learner preference + trend_score (decaying notes) + novelty - recency
   -> select_three: A taste (argmax), B trend (argmax), C explore (Thompson sample); differ() + rule gate
   -> critic (Gemini checklist, deterministic fallback) -> rationale -> render.compose collage
   -> user picks -> learner.update (2 pairs per rejected look) + wear counts + choice_event log
chosen look -> tryon.preview (privacy gate -> provider -> Gemini QA >=3 else collage fallback)
jewellery overlay: MediaPipe face landmarks (optional)
```
Modules: config, schema, db, llm_client, tagger, imaging, vectors, pipeline, rules, features, learner, looks, trends, critic,
render, tryon, privacy, service, stylist (ADK), api (FastAPI), demo. Prompts versioned in prompts/.
Every tool-like function returns {ok, data, error}. Free-tier swaps: Qdrant->Vertex Vector Search, SQLite->Firestore, HF Space->Vertex Virtual Try-On.
