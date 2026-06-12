import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.compilations.models import CompilationJob
from app.compilations.schemas import CompilationJobResponse
from app.compilations.service import (
    create_compilation_job,
    get_compilation_job_for_owner,
    list_compilation_jobs_for_paper,
)
from app.compilations.worker import run_compilation_job
from app.db.session import get_session
from app.papers.service import get_paper_for_owner
from app.storage.client import (
    ObjectStorageClient,
    ObjectStorageError,
    get_storage_client,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["compilations"])


def _job_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Compilation job not found",
    )


def _paper_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Paper not found",
    )


def _to_response(
    job: CompilationJob,
    storage: ObjectStorageClient,
) -> CompilationJobResponse:
    response = CompilationJobResponse.model_validate(job)
    if job.pdf_storage_key:
        try:
            response.pdf_url = storage.presigned_get_url(job.pdf_storage_key)
        except ObjectStorageError:
            logger.exception("Compiled PDF signed URL creation failed")
    return response


@router.post(
    "/api/papers/{paper_id}/compilation-jobs",
    response_model=CompilationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_paper_compilation_job(
    paper_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> CompilationJobResponse:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        if paper is None:
            raise _paper_not_found()
        job = create_compilation_job(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
        )
        session.commit()
        session.refresh(job)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Compilation job creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create compilation job",
        ) from exc

    background_tasks.add_task(run_compilation_job, job.id)
    return _to_response(job, storage)


@router.get(
    "/api/papers/{paper_id}/compilation-jobs",
    response_model=list[CompilationJobResponse],
)
def list_paper_compilation_jobs(
    paper_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> list[CompilationJobResponse]:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        if paper is None:
            raise _paper_not_found()
        jobs = list_compilation_jobs_for_paper(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Compilation job listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list compilation jobs",
        ) from exc
    return [_to_response(job, storage) for job in jobs]


@router.get(
    "/api/compilation-jobs/{job_id}",
    response_model=CompilationJobResponse,
)
def get_compilation_job(
    job_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> CompilationJobResponse:
    try:
        job = get_compilation_job_for_owner(
            session,
            owner_id=current_user.user.id,
            job_id=job_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Compilation job lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load compilation job",
        ) from exc
    if job is None:
        raise _job_not_found()
    return _to_response(job, storage)
