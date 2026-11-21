# Decisions (dated)
- 2026-11-11: Ethnic wear is a first-class kind. A saree/lehenga/kurta set is ONE item (anchor, no bottom added). OCCASIONS in config.py is a placeholder: edit to your top five.
- 2026-11-11: Qdrant embedded mode locally (no Docker). Vertex stub kept for production.
- 2026-11-11: auto_tags_json immutable so tagging accuracy is measured on model output, not on corrected tags.
- 2026-11-11: Preference model is numpy (logistic on pairwise differences, diagonal Laplace posterior for Thompson sampling) instead of scikit-learn: needs online updates and posterior variance. No pooled item-embedding feature in v1 (kept DIM small and explainable).
- 2026-11-11: W_PREF=4.0 chosen on the simulated persona (1.5 learned too slowly).
- 2026-11-11: Critic = Gemini checklist (text only, no images) with deterministic fallback when no key or on error.
- 2026-11-11: Try-on needs consent AND ALLOW_PERSON_PHOTOS=true. Public HF Space = third party. Space API signature may change: verify.
- 2026-11-11: Model names (gemini-2.5-flash, gemini-embedding-001) are defaults only. VERIFY on AI Studio. ADK API usage in stylist.py and the HF Space call were written from memory and not run: verify against current docs.
- Trend sources: Google Search grounding only; paraphrased notes + links. No Pinterest scraping. Seed notes are labelled placeholders.
