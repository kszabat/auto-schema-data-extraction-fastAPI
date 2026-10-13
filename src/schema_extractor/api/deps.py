from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from schema_extractor.agents.schema_agent import build_schema_agent
from schema_extractor.config import get_settings
from schema_extractor.db.models import User
from schema_extractor.db.session import get_db
from schema_extractor.llm.factory import build_llm
from schema_extractor.security import decode_access_token
from schema_extractor.services.schema_service import SchemaAgent


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise credentials_error from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user

def get_schema_agent() -> SchemaAgent:
    return build_schema_agent(build_llm(get_settings().schema_model))

current_user = Annotated[User, Depends(get_current_user)]
SchemaAgentDep = Annotated[SchemaAgent, Depends(get_schema_agent)]
