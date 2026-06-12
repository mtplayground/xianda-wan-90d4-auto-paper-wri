from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.references.embeddings import get_reference_embedder
from app.references.models import Reference, ReferenceChunk

DEFAULT_REFERENCE_CONTEXT = "No matching reference context was found."


@dataclass(frozen=True)
class ReferenceSearchResult:
    reference: Reference
    chunk: ReferenceChunk
    distance: float

    @property
    def score(self) -> float:
        return max(0.0, 1.0 - self.distance)


def search_reference_chunks(
    session: Session,
    *,
    owner_id: UUID,
    paper_id: UUID,
    query: str,
    limit: int,
) -> list[ReferenceSearchResult]:
    if limit < 1:
        return []

    embedding = get_reference_embedder().embed(query)
    if not any(value != 0 for value in embedding.vector):
        return []

    distance = ReferenceChunk.embedding.cosine_distance(embedding.vector)
    statement = (
        select(Reference, ReferenceChunk, distance.label("distance"))
        .join(ReferenceChunk, ReferenceChunk.reference_id == Reference.id)
        .where(
            Reference.owner_id == owner_id,
            Reference.paper_id == paper_id,
            ReferenceChunk.owner_id == owner_id,
            ReferenceChunk.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(limit)
    )

    results: list[ReferenceSearchResult] = []
    for reference, chunk, raw_distance in session.execute(statement):
        distance_value = float(raw_distance)
        results.append(
            ReferenceSearchResult(
                reference=reference,
                chunk=chunk,
                distance=distance_value,
            )
        )
    return results


def build_reference_context(
    results: list[ReferenceSearchResult],
    *,
    max_chars: int,
) -> str:
    if not results or max_chars < 1:
        return DEFAULT_REFERENCE_CONTEXT

    parts: list[str] = []
    used_chars = 0
    for index, result in enumerate(results, start=1):
        content = " ".join(result.chunk.content.split())
        if not content:
            continue
        title = result.reference.title.strip() or "Untitled reference"
        heading = (
            f"[R{index}] {title}; chunk {result.chunk.chunk_index}; "
            f"score {result.score:.3f}"
        )
        remaining = max_chars - used_chars - len(heading) - 2
        if remaining <= 0:
            break
        excerpt = content[:remaining]
        block = f"{heading}\n{excerpt}"
        parts.append(block)
        used_chars += len(block) + 2
        if used_chars >= max_chars:
            break

    if not parts:
        return DEFAULT_REFERENCE_CONTEXT
    return "\n\n".join(parts)
