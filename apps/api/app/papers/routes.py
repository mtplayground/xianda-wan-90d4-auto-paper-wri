import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.claude import ClaudeClientError, PromptRenderError, get_claude_client
from app.claude.prompts import RenderedPrompt, render_prompt
from app.db.session import get_session
from app.papers.models import Paper
from app.papers.schemas import (
    PaperAiContinueRequest,
    PaperAiPolishRequest,
    PaperAiResponse,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
)
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


def _load_paper(
    session: Session,
    *,
    owner_id: UUID,
    paper_id: UUID,
) -> Paper:
    try:
        paper = get_paper_for_owner(session, owner_id, paper_id)
    except SQLAlchemyError as exc:
        logger.exception("Paper lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load paper",
        ) from exc
    if paper is None:
        raise _not_found()
    return paper


def _complete_ai_prompt(prompt: RenderedPrompt) -> PaperAiResponse:
    try:
        message = get_claude_client().complete_prompt(prompt)
    except ClaudeClientError as exc:
        logger.exception("Claude completion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI editing request failed",
        ) from exc
    except RuntimeError as exc:
        logger.exception("Claude client is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI editing is not configured",
        ) from exc
    return PaperAiResponse(
        text=message.text,
        model=message.model,
        stop_reason=message.stop_reason,
        input_tokens=message.input_tokens,
        output_tokens=message.output_tokens,
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
    paper = _load_paper(
        session,
        owner_id=current_user.user.id,
        paper_id=paper_id,
    )
    return PaperResponse.model_validate(paper)


@router.post("/{paper_id}/ai/polish", response_model=PaperAiResponse)
def polish_paper_text(
    paper_id: UUID,
    payload: PaperAiPolishRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperAiResponse:
    paper = _load_paper(
        session,
        owner_id=current_user.user.id,
        paper_id=paper_id,
    )
    try:
        prompt = render_prompt(
            "polish_selection",
            paper_title=paper.title,
            operation=payload.operation,
            instruction=payload.instruction,
            surrounding_context=payload.surrounding_context
            or paper.latex_source[:20_000],
            selected_text=payload.selected_text,
        )
    except PromptRenderError as exc:
        logger.exception("AI polish prompt rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare AI editing prompt",
        ) from exc
    return _complete_ai_prompt(prompt)


@router.post("/{paper_id}/ai/continue", response_model=PaperAiResponse)
def continue_paper_text(
    paper_id: UUID,
    payload: PaperAiContinueRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperAiResponse:
    paper = _load_paper(
        session,
        owner_id=current_user.user.id,
        paper_id=paper_id,
    )
    try:
        prompt = render_prompt(
            "continue_draft",
            paper_title=paper.title,
            draft_context=payload.draft_context,
            instruction=payload.instruction,
            target_length=payload.target_length,
        )
    except PromptRenderError as exc:
        logger.exception("AI continuation prompt rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare AI continuation prompt",
        ) from exc
    return _complete_ai_prompt(prompt)


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
