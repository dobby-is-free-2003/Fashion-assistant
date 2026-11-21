"""vector_store interface (upsert/search/delete) with a Qdrant implementation.
Local embedded mode needs no Docker. Swap for Vertex AI Vector Search in production."""
import uuid
from abc import ABC, abstractmethod

from . import config
from .llm_client import client, with_backoff

DIM = 768


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, item_id: str, vector: list[float], payload: dict) -> None: ...
    @abstractmethod
    def search(self, vector: list[float], k: int = 5, kind: str | None = None) -> list[dict]: ...
    @abstractmethod
    def delete(self, item_id: str) -> None: ...


def _pid(item_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, item_id))


class QdrantStore(VectorStore):
    def __init__(self, path=None, collection="wardrobe"):
        from qdrant_client import QdrantClient, models
        self.m, self.col = models, collection
        self.q = QdrantClient(path=str(path or config.QDRANT_PATH))
        if not self.q.collection_exists(collection):
            self.q.create_collection(collection, vectors_config=models.VectorParams(
                size=DIM, distance=models.Distance.COSINE))

    def upsert(self, item_id, vector, payload):
        self.q.upsert(self.col, [self.m.PointStruct(
            id=_pid(item_id), vector=vector, payload={**payload, "item_id": item_id})])

    def search(self, vector, k=5, kind=None):
        flt = None
        if kind:
            flt = self.m.Filter(must=[self.m.FieldCondition(key="kind", match=self.m.MatchValue(value=kind))])
        hits = self.q.query_points(self.col, query=vector, limit=k, query_filter=flt).points
        return [{"item_id": h.payload["item_id"], "score": h.score} for h in hits]

    def delete(self, item_id):
        self.q.delete(self.col, points_selector=self.m.PointIdsList(points=[_pid(item_id)]))


class VertexVectorStub(VectorStore):
    """Production swap point. Not implemented on purpose (not free tier)."""
    def upsert(self, *a, **k): raise NotImplementedError
    def search(self, *a, **k): raise NotImplementedError
    def delete(self, *a, **k): raise NotImplementedError


def tags_to_text(tags: dict) -> str:
    keys = ["kind", "subtype", "pattern", "fabric_guess", "neckline", "sleeve", "fit", "metal_tone"]
    parts = [f"{k}: {tags[k]}" for k in keys if tags.get(k)]
    parts.append(f"formality {tags['formality']}, colour {tags['primary_color_hex']}")
    parts += tags.get("style_tags", []) + tags.get("occasions", [])
    return "; ".join(parts)


def embed_text(text: str) -> list[float]:
    from google.genai import types
    r = with_backoff(lambda: client().models.embed_content(
        model=config.EMBED_MODEL, contents=text,
        config=types.EmbedContentConfig(output_dimensionality=DIM)))
    return list(r.embeddings[0].values)
