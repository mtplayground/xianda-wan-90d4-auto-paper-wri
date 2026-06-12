from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.references.models import Reference, ReferenceChunk


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
        metadata_json=metadata,
    )
    reference.chunks = [
        ReferenceChunk(
            owner_id=owner_id,
            chunk_index=index,
            content=chunk,
            token_count=len(chunk.split()),
            metadata_json={"source": "pdf"},
        )
        for index, chunk in enumerate(text_chunks)
    ]
    session.add(reference)
    return reference
