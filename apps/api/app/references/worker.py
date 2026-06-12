import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session_factory
from app.references.embeddings import EMBEDDING_MODEL_NAME, get_reference_embedder
from app.references.models import EMBEDDING_DIMENSIONS
from app.references.service import (
    apply_chunk_embedding,
    get_reference_with_chunks,
    list_chunks_without_embeddings,
    mark_reference_embedding_completed,
    mark_reference_embedding_failed,
    mark_reference_embedding_running,
)

logger = logging.getLogger(__name__)


def run_reference_embedding_job(reference_id: UUID) -> None:
    try:
        _run_reference_embedding_job(reference_id)
    except Exception as exc:
        logger.exception(
            "Unhandled reference embedding failure",
            extra={"reference_id": str(reference_id)},
        )
        _mark_failed(reference_id, str(exc) or "Unexpected embedding failure")


def _run_reference_embedding_job(reference_id: UUID) -> None:
    embedder = get_reference_embedder()

    with get_session_factory()() as session:
        reference = get_reference_with_chunks(session, reference_id)
        if reference is None:
            logger.warning(
                "Reference not found for embedding",
                extra={"reference_id": str(reference_id)},
            )
            return

        pending_chunks = list_chunks_without_embeddings(reference)
        if not pending_chunks:
            mark_reference_embedding_completed(
                reference,
                model=EMBEDDING_MODEL_NAME,
                dimensions=EMBEDDING_DIMENSIONS,
                embedded_chunk_count=len(reference.chunks),
            )
            session.commit()
            return

        mark_reference_embedding_running(
            reference,
            model=EMBEDDING_MODEL_NAME,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        session.commit()

    embedded_count = 0
    try:
        with get_session_factory()() as session:
            reference = get_reference_with_chunks(session, reference_id)
            if reference is None:
                return
            pending_chunks = list_chunks_without_embeddings(reference)
            for chunk in pending_chunks:
                embedding = embedder.embed(chunk.content)
                apply_chunk_embedding(
                    chunk,
                    model=embedding.model,
                    dimensions=embedding.dimensions,
                    vector=embedding.vector,
                )
                embedded_count += 1

            mark_reference_embedding_completed(
                reference,
                model=EMBEDDING_MODEL_NAME,
                dimensions=EMBEDDING_DIMENSIONS,
                embedded_chunk_count=embedded_count,
            )
            session.commit()
    except SQLAlchemyError as exc:
        logger.exception(
            "Reference embedding persistence failed",
            extra={"reference_id": str(reference_id)},
        )
        _mark_failed(reference_id, str(exc))


def _mark_failed(reference_id: UUID, error_message: str) -> None:
    try:
        with get_session_factory()() as session:
            reference = get_reference_with_chunks(session, reference_id)
            if reference is None:
                return
            mark_reference_embedding_failed(reference, error_message)
            session.commit()
    except SQLAlchemyError:
        logger.exception("Failed to persist reference embedding failure")
