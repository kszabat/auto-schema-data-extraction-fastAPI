from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from schema_extractor.db import repositories
from schema_extractor.db.models import User
from schema_extractor.errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from schema_extractor.security import DUMMY_HASH, hash_password, verify_password


def _normalize(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, *, email: str, password: str) -> User:
    email = _normalize(email)
    if repositories.get_user_by_email(db, email=email) is not None:
        raise EmailAlreadyRegisteredError
    try:
        user = repositories.create_user(
            db, email=email, hashed_password=hash_password(password)
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError from None
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = repositories.get_user_by_email(db, email=_normalize(email))
    is_valid = verify_password(password, user.hashed_password if user else DUMMY_HASH)
    if user is None or not is_valid:
        raise InvalidCredentialsError
    return user
