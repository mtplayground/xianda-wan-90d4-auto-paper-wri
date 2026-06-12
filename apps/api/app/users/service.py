from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.session import MctaiSessionClaims
from app.users.models import User, UserIdentity

LOCAL_IDENTITY_PROVIDER = "local"
MCTAI_IDENTITY_PROVIDER = "mctai"


@dataclass(frozen=True)
class UserUpsertResult:
    user: User
    created: bool


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized:
        raise ValueError("Email must not be empty")
    return normalized


def upsert_user_from_mctai_claims(
    session: Session,
    claims: MctaiSessionClaims,
) -> UserUpsertResult:
    now = datetime.now(UTC)
    identity = session.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == MCTAI_IDENTITY_PROVIDER,
            UserIdentity.provider_subject == claims.sub,
        )
    )
    if identity:
        user = identity.user
        user.email = claims.email
        user.normalized_email = normalize_email(claims.email)
        user.email_verified = claims.email_verified
        user.display_name = claims.name
        user.picture_url = claims.picture
        user.last_seen_at = now
        identity.email = claims.email
        return UserUpsertResult(user=user, created=False)

    normalized_email = normalize_email(claims.email)
    user = session.scalar(select(User).where(User.normalized_email == normalized_email))
    created = user is None
    if user is None:
        user = User(
            email=claims.email,
            normalized_email=normalized_email,
            email_verified=claims.email_verified,
            display_name=claims.name,
            picture_url=claims.picture,
            last_seen_at=now,
        )
        session.add(user)
        session.flush()
    else:
        user.email = claims.email
        user.email_verified = claims.email_verified
        user.display_name = claims.name
        user.picture_url = claims.picture
        user.last_seen_at = now

    session.add(
        UserIdentity(
            user_id=user.id,
            provider=MCTAI_IDENTITY_PROVIDER,
            provider_subject=claims.sub,
            email=claims.email,
        )
    )
    return UserUpsertResult(user=user, created=created)
