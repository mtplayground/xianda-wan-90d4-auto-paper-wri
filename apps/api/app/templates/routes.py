import logging
import uuid
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.db.session import get_session
from app.storage.client import (
    ObjectStorageClient,
    ObjectStorageError,
    get_storage_client,
)
from app.templates.schemas import TemplateResponse
from app.templates.service import create_template_for_owner, list_templates_for_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates", tags=["templates"])

MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
ALLOWED_TEMPLATE_EXTENSIONS = {".tex", ".cls", ".sty", ".bib"}


def _normalize_template_name(name: str | None, filename: str) -> str:
    candidate = (name or PurePath(filename).stem).strip()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template name must not be blank",
        )
    return candidate[:255]


def _validate_filename(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template file name is required",
        )
    clean_name = PurePath(filename).name
    suffix = PurePath(clean_name).suffix.lower()
    if suffix not in ALLOWED_TEMPLATE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_TEMPLATE_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Template file must use one of these extensions: {allowed}",
        )
    return clean_name, suffix


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> list[TemplateResponse]:
    try:
        templates = list_templates_for_user(session, current_user.user.id)
    except SQLAlchemyError as exc:
        logger.exception("Template listing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list templates",
        ) from exc
    return [TemplateResponse.model_validate(template) for template in templates]


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_template(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorageClient, Depends(get_storage_client)],
    file: Annotated[UploadFile, File()],
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
) -> TemplateResponse:
    clean_filename, suffix = _validate_filename(file.filename)
    template_name = _normalize_template_name(name, clean_filename)
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template file must not be empty",
        )
    if len(data) > MAX_TEMPLATE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Template file is too large",
        )

    relative_key = f"templates/{current_user.user.id}/{uuid.uuid4()}{suffix}"
    try:
        stored_object = storage.upload_bytes(
            relative_key,
            data,
            content_type=file.content_type or "application/octet-stream",
        )
    except ObjectStorageError as exc:
        logger.exception("Template object upload failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not upload template",
        ) from exc

    try:
        template = create_template_for_owner(
            session,
            current_user.user.id,
            name=template_name,
            description=description.strip() if description else None,
            storage_key=stored_object.relative_key,
            metadata={
                "content_type": file.content_type,
                "extension": suffix,
                "original_filename": clean_filename,
                "size": stored_object.size,
            },
        )
        session.commit()
        session.refresh(template)
    except IntegrityError as exc:
        session.rollback()
        try:
            storage.delete_object(stored_object.relative_key)
        except ObjectStorageError:
            logger.exception("Uploaded template cleanup failed after duplicate name")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with that name already exists",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        try:
            storage.delete_object(stored_object.relative_key)
        except ObjectStorageError:
            logger.exception("Uploaded template cleanup failed after database error")
        logger.exception("Template record creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save template",
        ) from exc

    return TemplateResponse.model_validate(template)
