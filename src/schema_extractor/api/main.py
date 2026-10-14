import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from schema_extractor.api.routers import auth, schemas
from schema_extractor.errors import (
    DomainError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    SchemaGenerationError,
    SchemaNotFoundError,
    VersionConflictError,
    VersionNotFoundError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    SchemaNotFoundError: 404,
    VersionNotFoundError: 404,
    VersionConflictError: 409,
    EmailAlreadyRegisteredError: 409,
    InvalidCredentialsError: 401,
    SchemaGenerationError: 502,
}


def _status_for(e: DomainError) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(e, error_type):
            return status
    return 400


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, e: DomainError) -> JSONResponse:
        status = _status_for(e)
        if isinstance(e, SchemaGenerationError):
            logger.warning("Schema generation failed: %s", e)
            detail = "The model could not produce a valid schema. Try rephrasing the request."
        else:
            detail = str(e)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status, content={"detail": detail}, headers=headers
        )


def create_app() -> FastAPI:
    app = FastAPI(title="Schema Extractor")
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(schemas.router)
    return app


app = create_app()
