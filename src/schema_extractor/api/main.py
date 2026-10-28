import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from schema_extractor.api.deps import get_storage
from schema_extractor.api.routers import auth, extractions, schemas
from schema_extractor.db.session import get_session_factory
from schema_extractor.documents.exceptions import (
    DocumentLoadError,
    DocumentTooLargeError,
    UnsupportedFileTypeError,
)
from schema_extractor.errors import (
    DomainError,
    EmailAlreadyRegisteredError,
    ExtractionNotFoundError,
    InvalidCredentialsError,
    SchemaGenerationError,
    SchemaNotFoundError,
    TooManyActiveExtractionsError,
    VersionConflictError,
    VersionNotFoundError,
)
from schema_extractor.services import extraction_service

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    SchemaNotFoundError: 404,
    VersionNotFoundError: 404,
    ExtractionNotFoundError: 404,
    VersionConflictError: 409,
    EmailAlreadyRegisteredError: 409,
    InvalidCredentialsError: 401,
    TooManyActiveExtractionsError: 429,
    SchemaGenerationError: 502,
}

_STATUS_BY_DOCUMENT_ERROR: dict[type[DocumentLoadError], int] = {
    DocumentTooLargeError: 413,
    UnsupportedFileTypeError: 415,
}


def _status_for(exc: DomainError) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return status
    return 400


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status = _status_for(exc)
        if isinstance(exc, SchemaGenerationError):
            logger.warning("Schema generation failed: %s", exc)
            detail = "The model could not produce a valid schema. Try rephrasing the request."
        else:
            detail = str(exc)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status, content={"detail": detail}, headers=headers
        )

    @app.exception_handler(DocumentLoadError)
    async def handle_document_error(
        request: Request, exc: DocumentLoadError
    ) -> JSONResponse:
        status = _STATUS_BY_DOCUMENT_ERROR.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_session_factory()() as db:
        recovered = extraction_service.recover_interrupted(db, storage=get_storage())
    if recovered:
        logger.warning("Marked %d interrupted extraction(s) as failed.", recovered)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Schema Extractor", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(schemas.router)
    app.include_router(extractions.router)
    return app


app = create_app()
