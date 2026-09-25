from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def _fallback_vector(text: str, dimensions: int = 384) -> list[float]:
    """Deterministic local fallback when the transformer weights are unavailable."""
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            self.model = _load_model(model_name)
            self.backend = "sentence-transformers"
        except Exception:
            self.model = None
            self.backend = "deterministic-fallback"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            return [_fallback_vector(text) for text in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if self.model is None:
            return _fallback_vector(text)
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
