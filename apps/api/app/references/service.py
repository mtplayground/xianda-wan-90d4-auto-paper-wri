from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.references.models import Reference, ReferenceChunk

EMBEDDING_STATUS_QUEUED = "queued"
EMBEDDING_STATUS_RUNNING = "running"
EMBEDDING_STATUS_COMPLETED = "completed"
EMBEDDING_STATUS_FAILED = "failed"


def list_references_for_owner(session: Session, owner_id: UUID) -> list[Reference]:
    statement = (
        select(Reference)
        .where(Reference.owner_id == owner_id)
        .order_by(Reference.updated_at.desc(), Reference.created_at.desc())
    )
    return list(session.scalars(statement))


def get_reference_for_owner(
    session: Session,
    owner_id: UUID,
    reference_id: UUID,
) -> Reference | None:
    statement = select(Reference).where(
        Reference.id == reference_id,
        Reference.owner_id == owner_id,
    )
    return session.scalar(statement)


def get_reference_with_chunks(
    session: Session,
    reference_id: UUID,
) -> Reference | None:
    statement = (
        select(Reference)
        .options(selectinload(Reference.chunks))
        .where(Reference.id == reference_id)
    )
    return session.scalar(statement)


def list_chunks_without_embeddings(
    reference: Reference,
) -> list[ReferenceChunk]:
    return sorted(
        (chunk for chunk in reference.chunks if chunk.embedding is None),
        key=lambda chunk: chunk.chunk_index,
    )


def create_reference_from_pdf(
    session: Session,
    owner_id: UUID,
    *,
    title: str,
    paper_id: UUID | None,
    storage_key: str,
    text_chunks: list[str],
    metadata: dict[str, Any],
) -> Reference:
    reference = Reference(
        owner_id=owner_id,
        paper_id=paper_id,
        title=title,
        source_type="pdf",
        source_identifier=storage_key,
        metadata_json={
            **metadata,
            "embedding_status": EMBEDDING_STATUS_QUEUED,
        },
    )
    reference.chunks = [
        ReferenceChunk(
            owner_id=owner_id,
            chunk_index=index,
            content=chunk,
            token_count=len(chunk.split()),
            metadata_json={
                "source": "pdf",
                "embedding_status": EMBEDDING_STATUS_QUEUED,
            },
        )
        for index, chunk in enumerate(text_chunks)
    ]
    session.add(reference)
    return reference


def mark_reference_embedding_running(
    reference: Reference,
    *,
    model: str,
    dimensions: int,
) -> None:
    reference.metadata_json = {
        **reference.metadata_json,
        "embedding_status": EMBEDDING_STATUS_RUNNING,
        "embedding_model": model,
        "embedding_dimensions": dimensions,
    }


def mark_reference_embedding_completed(
    reference: Reference,
    *,
    model: str,
    dimensions: int,
    embedded_chunk_count: int,
) -> None:
    reference.metadata_json = {
        **reference.metadata_json,
        "embedding_status": EMBEDDING_STATUS_COMPLETED,
        "embedding_model": model,
        "embedding_dimensions": dimensions,
        "embedded_chunk_count": embedded_chunk_count,
    }


def mark_reference_embedding_failed(reference: Reference, error_message: str) -> None:
    reference.metadata_json = {
        **reference.metadata_json,
        "embedding_status": EMBEDDING_STATUS_FAILED,
        "embedding_error": error_message,
    }


def apply_chunk_embedding(
    chunk: ReferenceChunk,
    *,
    model: str,
    dimensions: int,
    vector: list[float],
) -> None:
    chunk.embedding = vector
    chunk.metadata_json = {
        **chunk.metadata_json,
        "embedding_status": EMBEDDING_STATUS_COMPLETED,
        "embedding_model": model,
        "embedding_dimensions": dimensions,
    }
