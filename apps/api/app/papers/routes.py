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
    PaperCitationSuggestionRequest,
    PaperCreate,
    PaperReferenceSearchRequest,
    PaperReferenceSearchResponse,
    PaperReferenceSearchResult,
    PaperResponse,
    PaperUpdate,
)
from app.papers.service import (
    apply_paper_update,
    create_paper_for_owner,
    get_paper_for_owner,
    list_papers_for_owner,
)
from app.references.retrieval import (
    DEFAULT_REFERENCE_CONTEXT,
    ReferenceSearchResult,
    build_reference_context,
    search_reference_chunks,
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


def _to_reference_search_result(
    result: ReferenceSearchResult,
) -> PaperReferenceSearchResult:
    return PaperReferenceSearchResult(
        reference_id=result.reference.id,
        reference_title=result.reference.title,
        chunk_id=result.chunk.id,
        chunk_index=result.chunk.chunk_index,
        content=result.chunk.content,
        score=result.score,
        distance=result.distance,
        metadata=result.chunk.metadata_json,
    )


def _search_reference_context(
    session: Session,
    *,
    owner_id: UUID,
    paper_id: UUID,
    query: str,
    limit: int,
    max_chars: int = 12_000,
) -> tuple[str, list[PaperReferenceSearchResult]]:
    if limit < 1:
        return DEFAULT_REFERENCE_CONTEXT, []
    results = search_reference_chunks(
        session,
        owner_id=owner_id,
        paper_id=paper_id,
        query=query,
        limit=limit,
    )
    context = build_reference_context(results, max_chars=max_chars)
    return context, [_to_reference_search_result(result) for result in results]


def _complete_ai_prompt(
    prompt: RenderedPrompt,
    *,
    reference_context: str,
    references: list[PaperReferenceSearchResult],
) -> PaperAiResponse:
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
        reference_context=reference_context,
        references=references,
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
    reference_query = payload.reference_query or payload.selected_text
    try:
        reference_context, references = _search_reference_context(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
            query=reference_query,
            limit=payload.reference_limit,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference retrieval for AI polish failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve reference context",
        ) from exc
    try:
        prompt = render_prompt(
            "polish_selection",
            paper_title=paper.title,
            operation=payload.operation,
            instruction=payload.instruction,
            surrounding_context=payload.surrounding_context
            or paper.latex_source[:20_000],
            reference_context=reference_context,
            selected_text=payload.selected_text,
        )
    except PromptRenderError as exc:
        logger.exception("AI polish prompt rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare AI editing prompt",
        ) from exc
    return _complete_ai_prompt(
        prompt,
        reference_context=reference_context,
        references=references,
    )


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
    reference_query = payload.reference_query or payload.draft_context[-20_000:]
    try:
        reference_context, references = _search_reference_context(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
            query=reference_query,
            limit=payload.reference_limit,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference retrieval for AI continuation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve reference context",
        ) from exc
    try:
        prompt = render_prompt(
            "continue_draft",
            paper_title=paper.title,
            draft_context=payload.draft_context,
            instruction=payload.instruction,
            reference_context=reference_context,
            target_length=payload.target_length,
        )
    except PromptRenderError as exc:
        logger.exception("AI continuation prompt rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare AI continuation prompt",
        ) from exc
    return _complete_ai_prompt(
        prompt,
        reference_context=reference_context,
        references=references,
    )


@router.post(
    "/{paper_id}/references/search",
    response_model=PaperReferenceSearchResponse,
)
def search_paper_references(
    paper_id: UUID,
    payload: PaperReferenceSearchRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperReferenceSearchResponse:
    paper = _load_paper(
        session,
        owner_id=current_user.user.id,
        paper_id=paper_id,
    )
    try:
        context, results = _search_reference_context(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
            query=payload.query,
            limit=payload.limit,
            max_chars=payload.context_max_chars,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference semantic search failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not search references",
        ) from exc
    return PaperReferenceSearchResponse(
        query=payload.query,
        context=context,
        results=results,
    )


@router.post(
    "/{paper_id}/references/suggestions",
    response_model=PaperAiResponse,
)
def suggest_paper_citations(
    paper_id: UUID,
    payload: PaperCitationSuggestionRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PaperAiResponse:
    paper = _load_paper(
        session,
        owner_id=current_user.user.id,
        paper_id=paper_id,
    )
    reference_query = payload.reference_query or payload.passage
    try:
        reference_context, references = _search_reference_context(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
            query=reference_query,
            limit=payload.reference_limit,
            max_chars=payload.context_max_chars,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference retrieval for citation suggestions failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve reference context",
        ) from exc
    try:
        prompt = render_prompt(
            "suggest_citations",
            passage=payload.passage,
            reference_summaries=reference_context,
            instruction=payload.instruction,
        )
    except PromptRenderError as exc:
        logger.exception("Citation suggestion prompt rendering failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not prepare citation suggestion prompt",
        ) from exc
    return _complete_ai_prompt(
        prompt,
        reference_context=reference_context,
        references=references,
    )


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
