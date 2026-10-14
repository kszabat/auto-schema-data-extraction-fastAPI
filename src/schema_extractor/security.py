import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from schema_extractor.config import get_settings

ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()

DUMMY_HASH = _password_hash.hash("dummy-password")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def create_access_token(
    user_id: uuid.UUID, expires_delta: datetime | None = None
) -> str:
    settings = get_settings()
    delta = expires_delta or timedelta(settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": datetime.now(UTC) + delta}
    return jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[ALGORITHM],
        options={"require": ["sub", "exp"]},
    )

    try:
        return uuid.UUID(payload["sub"])
    except jwt.InvalidKeyError as e:
        raise jwt.InvalidTokenError("Invalid subject") from e


if __name__ == "__main__":
    raise jwt.InvalidTokenError("Invalid subject")