import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.session import MctaiSessionClaims, verify_mctai_session_cookie
from app.db.session import get_session
from app.users.models import User
from app.users.service import upsert_user_from_mctai_claims

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CurrentUserContext:
    user: User
    claims: MctaiSessionClaims
    created: bool


def get_optional_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUserContext | None:
    claims = verify_mctai_session_cookie(request.cookies)
    if claims is None:
        request.state.current_user = None
        return None
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

    current_user = CurrentUserContext(
        user=result.user,
        claims=claims,
        created=result.created,
    )
    request.state.current_user = current_user
    return current_user


def require_current_user(
    current_user: Annotated[
        CurrentUserContext | None,
        Depends(get_optional_current_user),
    ],
) -> CurrentUserContext:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in",
        )
    return current_user


CurrentUser = Annotated[CurrentUserContext, Depends(require_current_user)]
