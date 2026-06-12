from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.config import MctaiAuthConfig, get_settings

MCTAI_SESSION_COOKIE = "mctai_session"


class MctaiSessionError(RuntimeError):
    pass


@dataclass(frozen=True)
class MctaiSessionClaims:
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None
    raw: Mapping[str, Any]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MctaiSessionClaims":
        sub = payload.get("sub")
        email = payload.get("email")
        if not isinstance(sub, str) or not sub:
            raise MctaiSessionError("mctai_session is missing sub")
        if not isinstance(email, str) or not email:
            raise MctaiSessionError("mctai_session is missing email")
        name = payload.get("name")
        picture = payload.get("picture")
        return cls(
            sub=sub,
            email=email,
            email_verified=bool(payload.get("email_verified", False)),
            name=name if isinstance(name, str) else None,
            picture=picture if isinstance(picture, str) else None,
            raw=payload,
        )


@lru_cache
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def verify_mctai_session_token(
    token: str,
    *,
    auth_config: MctaiAuthConfig | None = None,
) -> MctaiSessionClaims:
    if not token:
        raise MctaiSessionError("mctai_session token is required")
    config = auth_config or get_settings().require_mctai_auth()
    try:
        signing_key = get_jwks_client(config.jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config.app_token,
            issuer=config.url,
        )
    except InvalidTokenError as exc:
        raise MctaiSessionError("Invalid mctai_session token") from exc
    return MctaiSessionClaims.from_payload(payload)


def verify_mctai_session_cookie(
    cookies: Mapping[str, str],
    *,
    auth_config: MctaiAuthConfig | None = None,
) -> MctaiSessionClaims | None:
    token = cookies.get(MCTAI_SESSION_COOKIE)
    if not token:
        return None
    try:
        return verify_mctai_session_token(token, auth_config=auth_config)
    except MctaiSessionError:
        return None
