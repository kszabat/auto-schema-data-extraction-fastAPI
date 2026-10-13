from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from schema_extractor.api.deps import CurrentUser, DbSession
from schema_extractor.api.payloads import TokenOut, UserCreate, UserOut
from schema_extractor.security import create_access_token
from schema_extractor.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: DbSession):
    return auth_service.register_user(db, email=data.email, password=data.password)


@router.post("/login", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = auth_service.authenticate(db, email=form.username, password=form.password)
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
