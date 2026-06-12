import logging
import uuid
from pathlib import PurePath
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.db.session import get_session
from app.papers.service import get_paper_for_owner
from app.references.models import Reference
from app.references.pdf import (
    ReferencePdfParseError,
    chunk_reference_text,
    extract_pdf_text,
)
from app.references.schemas import (
    ReferenceChunkResponse,
    ReferenceResponse,
    ReferenceUploadResponse,
)
from app.references.service import (
    create_reference_from_pdf,
    get_reference_for_owner,
    list_references_for_owner,
    list_references_for_paper,
)
from app.references.worker import run_reference_embedding_job
from app.storage.client import (
    ObjectStorageClient,
    ObjectStorageError,
    get_storage_client,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/references", tags=["references"])

MAX_REFERENCE_PDF_BYTES = 30 * 1024 * 1024


def _reference_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Reference not found",
    )


def _paper_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Paper not found",
    )


def _validate_pdf_upload(file: UploadFile, data: bytes) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF file name is required",
        )
    clean_filename = PurePath(file.filename).name
    if PurePath(clean_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reference upload must be a PDF file",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF file must not be empty",
        )
    if len(data) > MAX_REFERENCE_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF file is too large",
        )
    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file does not look like a PDF",
        )
    return clean_filename


def _normalize_title(title: str | None, filename: str) -> str:
    value = (title or PurePath(filename).stem).strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reference title must not be blank",
        )
    return value[:512]


def _to_response(
    reference: Reference,
    storage: ObjectStorageClient,
) -> ReferenceResponse:
    response = ReferenceResponse.model_validate(reference)
    if reference.source_identifier:
        try:
            response.source_url = storage.presigned_get_url(reference.source_identifier)
        except ObjectStorageError:
            logger.exception("Reference PDF signed URL creation failed")
    return response


@router.get("", response_model=list[ReferenceResponse])
def list_references(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> list[ReferenceResponse]:
    try:
        references = list_references_for_owner(session, current_user.user.id)
    except SQLAlchemyError as exc:
        logger.exception("Reference listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list references",
        ) from exc
    return [_to_response(reference, storage) for reference in references]


@router.get("/by-paper/{paper_id}", response_model=list[ReferenceResponse])
def list_paper_references(
    paper_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> list[ReferenceResponse]:
    try:
        paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        if paper is None:
            raise _paper_not_found()
        references = list_references_for_paper(
            session,
            owner_id=current_user.user.id,
            paper_id=paper.id,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Paper reference listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list paper references",
        ) from exc
    return [_to_response(reference, storage) for reference in references]


@router.get("/{reference_id}", response_model=ReferenceResponse)
def get_reference(
    reference_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> ReferenceResponse:
    try:
        reference = get_reference_for_owner(
            session,
            owner_id=current_user.user.id,
            reference_id=reference_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load reference",
        ) from exc
    if reference is None:
        raise _reference_not_found()
    return _to_response(reference, storage)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    reference_id: UUID,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
) -> None:
    try:
        reference = get_reference_for_owner(
            session,
            owner_id=current_user.user.id,
            reference_id=reference_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Reference delete lookup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load reference",
        ) from exc
    if reference is None:
        raise _reference_not_found()

    storage_key = reference.source_identifier
    try:
        session.delete(reference)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Reference deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete reference",
        ) from exc

    if storage_key:
        try:
            storage.delete_object(storage_key)
        except ObjectStorageError:
            logger.exception("Reference PDF object deletion failed")


@router.post(
    "/uploads/pdf",
    response_model=ReferenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference_pdf(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    paper_id: Annotated[UUID | None, Form()] = None,
) -> ReferenceUploadResponse:
    data = await file.read()
    clean_filename = _validate_pdf_upload(file, data)
    reference_title = _normalize_title(title, clean_filename)

    if paper_id is not None:
        try:
            paper = get_paper_for_owner(session, current_user.user.id, paper_id)
        except SQLAlchemyError as exc:
            logger.exception("Reference paper lookup failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not load paper",
            ) from exc
        if paper is None:
            raise _paper_not_found()

    try:
        extracted = extract_pdf_text(data)
    except ReferencePdfParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    chunks = chunk_reference_text(extracted.text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF does not contain extractable text",
        )

    relative_key = f"references/{current_user.user.id}/{uuid.uuid4()}.pdf"
    try:
        stored_object = storage.upload_bytes(
            relative_key,
            data,
            content_type=file.content_type or "application/pdf",
            metadata={"original_filename": clean_filename},
        )
    except ObjectStorageError as exc:
        logger.exception("Reference PDF object upload failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not upload reference PDF",
        ) from exc

    try:
        reference = create_reference_from_pdf(
            session,
            current_user.user.id,
            title=reference_title,
            paper_id=paper_id,
            storage_key=stored_object.relative_key,
            text_chunks=chunks,
            metadata={
                "content_type": file.content_type,
                "original_filename": clean_filename,
                "page_count": extracted.page_count,
                "size": stored_object.size,
                "text_char_count": len(extracted.text),
            },
        )
        session.commit()
        session.refresh(reference)
        background_tasks.add_task(run_reference_embedding_job, reference.id)
    except SQLAlchemyError as exc:
        session.rollback()
        try:
            storage.delete_object(stored_object.relative_key)
        except ObjectStorageError:
            logger.exception("Uploaded reference PDF cleanup failed")
        logger.exception("Reference PDF record creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save reference",
        ) from exc

    return ReferenceUploadResponse(
        reference=_to_response(reference, storage),
        chunks=[
            ReferenceChunkResponse.model_validate(chunk) for chunk in reference.chunks
        ],
        extracted_text_chars=len(extracted.text),
    )
