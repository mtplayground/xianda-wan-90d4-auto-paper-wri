from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compilations.models import CompilationJob, CompilationJobStatus
from app.papers.models import Paper


def create_compilation_job(
    session: Session,
    *,
    owner_id: UUID,
    paper_id: UUID,
) -> CompilationJob:
    job = CompilationJob(
        owner_id=owner_id,
        paper_id=paper_id,
        status=CompilationJobStatus.PENDING.value,
    )
    session.add(job)
    return job


def get_compilation_job_for_owner(
    session: Session,
    *,
    owner_id: UUID,
    job_id: UUID,
) -> CompilationJob | None:
    statement = select(CompilationJob).where(
        CompilationJob.id == job_id,
        CompilationJob.owner_id == owner_id,
    )
    return session.scalar(statement)


def list_compilation_jobs_for_paper(
    session: Session,
    *,
    owner_id: UUID,
    paper_id: UUID,
) -> list[CompilationJob]:
    statement = (
        select(CompilationJob)
        .where(
            CompilationJob.owner_id == owner_id,
            CompilationJob.paper_id == paper_id,
        )
        .order_by(CompilationJob.created_at.desc())
    )
    return list(session.scalars(statement))


def get_job_with_paper(
    session: Session, job_id: UUID
) -> tuple[CompilationJob, Paper] | None:
    statement = (
        select(CompilationJob, Paper)
        .join(Paper, Paper.id == CompilationJob.paper_id)
        .where(CompilationJob.id == job_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        return None
    return row[0], row[1]


def mark_job_running(job: CompilationJob) -> None:
    job.status = CompilationJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    job.finished_at = None
    job.error_message = None
    job.log_text = None
    job.pdf_storage_key = None


def mark_job_succeeded(
    job: CompilationJob,
    *,
    pdf_storage_key: str,
    log_text: str,
) -> None:
    job.status = CompilationJobStatus.SUCCEEDED.value
    job.pdf_storage_key = pdf_storage_key
    job.log_text = log_text
    job.error_message = None
    job.finished_at = datetime.now(UTC)


def mark_job_failed(
    job: CompilationJob,
    *,
    error_message: str,
    log_text: str | None = None,
) -> None:
    job.status = CompilationJobStatus.FAILED.value
    job.error_message = error_message
    job.log_text = log_text
    job.finished_at = datetime.now(UTC)
