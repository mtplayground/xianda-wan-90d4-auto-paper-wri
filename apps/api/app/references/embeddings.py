import hashlib
import math
import re
from dataclasses import dataclass

from app.references.models import EMBEDDING_DIMENSIONS

EMBEDDING_MODEL_NAME = "hashing-lexical-v1"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class ReferenceEmbedding:
    model: str
    dimensions: int
    vector: list[float]


class ReferenceEmbedder:
    def embed(self, text: str) -> ReferenceEmbedding:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return ReferenceEmbedding(
                model=EMBEDDING_MODEL_NAME,
                dimensions=EMBEDDING_DIMENSIONS,
                vector=vector,
            )

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign * (1.0 + math.log1p(len(token)))

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return ReferenceEmbedding(
                model=EMBEDDING_MODEL_NAME,
                dimensions=EMBEDDING_DIMENSIONS,
                vector=vector,
            )
        return ReferenceEmbedding(
            model=EMBEDDING_MODEL_NAME,
            dimensions=EMBEDDING_DIMENSIONS,
            vector=[value / norm for value in vector],
        )


def get_reference_embedder() -> ReferenceEmbedder:
    return ReferenceEmbedder()
