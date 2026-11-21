# Contracts
- Item tags: fashion/schema.py ItemTags (also the Gemini response schema). Flat view: db.flat(item).
- Candidate dict: ids, garments, jewels, anchor_ids, anchor_family, rule, comps, reasons, trend, novelty, recency, want, x (features.DIM floats).
- StylistService.plan_looks(occasion, formality, avoid, wear, weather) -> {session_id, session, weather, looks[3]}; choose(session_id, look_id|None, reason).
- TryOnProvider.run(person_path, garment_path, job_id) -> result path; raises ProviderUnavailable.
- VectorStore: upsert / search / delete.
