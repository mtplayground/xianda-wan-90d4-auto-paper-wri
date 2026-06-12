from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    return get_password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return get_password_hasher().verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    if not password_hash:
        return True
    try:
        return get_password_hasher().check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
