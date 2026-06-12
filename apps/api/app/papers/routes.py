import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.db.session import get_session
from app.papers.schemas import PaperCreate, PaperResponse, PaperUpdate
from app.papers.service import (
    apply_paper_update,
    create_paper_for_owner,
    get_paper_for_owner,
    list_papers_for_owner,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/papers", tags=["papers"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Paper not found",
    )


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper(
    payload: PaperCreate,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperResponse:
    try:
        paper = create_paper_for_owner(session, current_user.user.id, payload)
        session.commit()
        session.refresh(paper)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Paper creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create paper",
        ) from exc
    return PaperResponse.model_validate(paper)


@router.get("", response_model=list[PaperResponse])
def list_papers(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> list[PaperResponse]:
    try:
        papers = list_papers_for_owner(session, current_user.user.id)
    except SQLAlchemyError as exc:
        logger.exception("Paper listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list papers",
        ) from exc
    return [PaperResponse.model_validate(paper) for paper in papers]


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(
    paper_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperResponse:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
    except SQLAlchemyError as exc:
        logger.exception("Paper lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load paper",
        ) from exc
    if paper is None:
        raise _not_found()
    return PaperResponse.model_validate(paper)


@router.patch("/{paper_id}", response_model=PaperResponse)
def update_paper(
    paper_id: UUID,
    payload: PaperUpdate,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperResponse:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        if paper is None:
            raise _not_found()
        apply_paper_update(paper, payload)
        session.commit()
        session.refresh(paper)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Paper update failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update paper",
        ) from exc
    return PaperResponse.model_validate(paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        if paper is None:
            raise _not_found()
        session.delete(paper)
        session.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Paper deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete paper",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
