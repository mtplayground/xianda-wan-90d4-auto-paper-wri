import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.compilations.models import CompilationJobStatus
from app.compilations.service import (
    get_job_with_paper,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)
from app.db.session import get_session_factory
from app.latex import TexLiveRunner, TexLiveRunnerError
from app.storage.client import ObjectStorageError, get_storage_client

logger = logging.getLogger(__name__)
PDF_CONTENT_TYPE = "application/pdf"


def run_compilation_job(job_id: UUID) -> None:
    try:
        _run_compilation_job(job_id)
    except Exception as exc:
        logger.exception(
            "Unhandled compilation job failure", extra={"job_id": str(job_id)}
        )
        _mark_failed(job_id, str(exc) or "Unexpected compilation job failure")


def _run_compilation_job(job_id: UUID) -> None:
    with get_session_factory()() as session:
        job_and_paper = get_job_with_paper(session, job_id)
        if job_and_paper is None:
            logger.warning("Compilation job not found", extra={"job_id": str(job_id)})
            return
        job, paper = job_and_paper
        if job.status != CompilationJobStatus.PENDING.value:
            logger.info(
                "Skipping compilation job with non-pending status",
                extra={"job_id": str(job_id), "status": job.status},
            )
            return
        mark_job_running(job)
        session.commit()

    try:
        result = TexLiveRunner().compile(
            {"main.tex": paper.latex_source},
            main_file="main.tex",
        )
    except TexLiveRunnerError as exc:
        _mark_failed(job_id, str(exc))
        return

    if not result.success or result.pdf is None:
        message = result.errors[0] if result.errors else "TeX compilation failed"
        _mark_failed(job_id, message, result.log)
        return

    relative_key = f"compilations/{paper.owner_id}/{paper.id}/{job_id}.pdf"
    try:
        stored_object = get_storage_client().upload_bytes(
            relative_key,
            result.pdf,
            content_type=PDF_CONTENT_TYPE,
        )
    except ObjectStorageError as exc:
        logger.exception("Compiled PDF upload failed", extra={"job_id": str(job_id)})
        _mark_failed(job_id, str(exc), result.log)
        return

    with get_session_factory()() as session:
        job_and_paper = get_job_with_paper(session, job_id)
        if job_and_paper is None:
            return
        job, _paper = job_and_paper
        mark_job_succeeded(
            job,
            pdf_storage_key=stored_object.relative_key,
            log_text=result.log,
        )
        session.commit()


def _mark_failed(job_id: UUID, message: str, log_text: str | None = None) -> None:
    try:
        with get_session_factory()() as session:
            job_and_paper = get_job_with_paper(session, job_id)
            if job_and_paper is None:
                return
            job, _paper = job_and_paper
            mark_job_failed(job, error_message=message, log_text=log_text)
            session.commit()
    except SQLAlchemyError:
        logger.exception("Failed to persist compilation job failure")
