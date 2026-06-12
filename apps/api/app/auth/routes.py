import logging
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.session import verify_mctai_session_cookie
from app.config import get_settings
from app.db.session import get_session
from app.users.models import User
from app.users.service import (
    OAUTH_IDENTITY_PROVIDERS,
    UserUpsertResult,
    link_oauth_identity_from_mctai_claims,
    upsert_user_from_mctai_claims,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    email_verified: bool
    display_name: str | None
    picture_url: str | None
    created: bool


def _frontend_base_url(request: Request) -> str:
    settings = get_settings()
    if settings.self_url:
        return settings.self_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _safe_return_path(return_to: str | None) -> str:
    if not return_to:
        return "/"
    if not return_to.startswith("/") or return_to.startswith("/api"):
        return "/"
    return return_to


def _frontend_url(request: Request, return_to: str | None = None) -> str:
    return f"{_frontend_base_url(request)}{_safe_return_path(return_to)}"


def _frontend_url_with_query(
    request: Request,
    return_to: str | None,
    query_params: dict[str, str],
) -> str:
    frontend_url = _frontend_url(request, return_to)
    separator = "&" if "?" in frontend_url else "?"
    return f"{frontend_url}{separator}{urlencode(query_params)}"


def _validate_oauth_provider(provider: str) -> str:
    provider_name = provider.strip().lower()
    if provider_name not in OAUTH_IDENTITY_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unsupported OAuth provider",
        )
    return provider_name


def build_mctai_login_url(request: Request, return_to: str | None = None) -> str:
    auth_config = get_settings().require_mctai_auth()
    frontend_url = _frontend_url(request, return_to)
    query = urlencode(
        {
            "app_token": auth_config.app_token,
            "return_to": frontend_url,
        }
    )
    return f"{auth_config.url.rstrip('/')}/login?{query}"


def _redirect_to_mctai_login(
    request: Request,
    return_to: str | None,
    status_code: int,
) -> RedirectResponse:
    return RedirectResponse(
        build_mctai_login_url(request, return_to),
        status_code=status_code,
    )


@router.get("/login", include_in_schema=False)
def login(request: Request, return_to: str | None = None) -> RedirectResponse:
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/login", include_in_schema=False)
def login_post(request: Request, return_to: str | None = None) -> RedirectResponse:
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_303_SEE_OTHER,
    )


@router.get("/register", include_in_schema=False)
def register(request: Request, return_to: str | None = None) -> RedirectResponse:
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/register", include_in_schema=False)
def register_post(request: Request, return_to: str | None = None) -> RedirectResponse:
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_303_SEE_OTHER,
    )


@router.get("/oauth/{provider}/redirect", include_in_schema=False)
def oauth_redirect(
    provider: str,
    request: Request,
    return_to: str | None = None,
) -> RedirectResponse:
    _validate_oauth_provider(provider)
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/oauth/{provider}/redirect", include_in_schema=False)
def oauth_redirect_post(
    provider: str,
    request: Request,
    return_to: str | None = None,
) -> RedirectResponse:
    _validate_oauth_provider(provider)
    return _redirect_to_mctai_login(
        request,
        return_to,
        status.HTTP_303_SEE_OTHER,
    )


@router.get("/oauth/{provider}/callback", include_in_schema=False)
def oauth_callback(
    provider: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    return_to: str | None = None,
) -> RedirectResponse:
    provider_name = _validate_oauth_provider(provider)
    claims = verify_mctai_session_cookie(request.cookies)
    if claims is None:
        return _redirect_to_mctai_login(
            request,
            return_to,
            status.HTTP_307_TEMPORARY_REDIRECT,
        )
    try:
        link_oauth_identity_from_mctai_claims(session, claims, provider_name)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("OAuth identity link failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not link OAuth identity",
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return RedirectResponse(
        _frontend_url_with_query(
            request,
            return_to,
            {"auth": "linked", "provider": provider_name},
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _to_response(result: UserUpsertResult) -> AuthenticatedUserResponse:
    user: User = result.user
    return AuthenticatedUserResponse(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified,
        display_name=user.display_name,
        picture_url=user.picture_url,
        created=result.created,
    )


@router.get("/me", response_model=AuthenticatedUserResponse)
def current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> AuthenticatedUserResponse:
    claims = verify_mctai_session_cookie(request.cookies)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in"
        )
    try:
        result = upsert_user_from_mctai_claims(session, claims)
        session.commit()
        session.refresh(result.user)
    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Authenticated user upsert failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not persist authenticated user",
        ) from exc
    return _to_response(result)
