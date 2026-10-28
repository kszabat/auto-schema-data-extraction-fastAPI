import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import PurePath

from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.models import Model
from sqlalchemy.orm import Session

from schema_extractor.db import repositories
from schema_extractor.db.models import Extraction, ExtractionStatus, SchemaVersion
from schema_extractor.documents.exceptions import DocumentLoadError
from schema_extractor.documents.multimodal import load_binary_content
from schema_extractor.errors import (
    ExtractionNotFoundError,
    SchemaNotFoundError,
    TooManyActiveExtractionsError,
    VersionNotFoundError,
)
from schema_extractor.extraction.pipeline import run_extraction
from schema_extractor.schema.meta_models import TemplateSpec
from schema_extractor.storage import FileStorage

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractContextManager[Session]]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _display_name(filename: str | None) -> str:
    name = PurePath(filename or "").name[:255]
    return name or "document"


def create_extraction(
    db: Session,
    *,
    user_id: uuid.UUID,
    schema_id: uuid.UUID,
    version_number: int | None,
    filename: str | None,
    data: bytes,
    storage: FileStorage,
    max_bytes: int,
    max_active: int,
) -> Extraction:
    load_binary_content(data, max_bytes=max_bytes)

    schema = repositories.get_schema(db, user_id=user_id, schema_id=schema_id)
    if schema is None:
        raise SchemaNotFoundError(schema_id)

    if version_number is None:
        version = repositories.get_latest_version(db, schema_id=schema_id)
    else:
        version = repositories.get_version(
            db, schema_id=schema_id, version_number=version_number
        )

    if version is None:
        raise VersionNotFoundError(schema_id, version_number or 1)

    if repositories.count_active_extractions(db, user_id=user_id) >= max_active:
        raise TooManyActiveExtractionsError(max_active)

    key = uuid.uuid4().hex
    storage.save(key, data)
    try:
        extraction = repositories.create_extraction(
            db,
            user_id=user_id,
            schema_version_id=version.id,
            filename=_display_name(filename),
            storage_key=key,
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete()
        raise
    return extraction


def process_extraction(
    session_factory: SessionFactory,
    extraction_id: uuid.UUID,
    *,
    model: Model,
    storage: FileStorage,
    max_bytes: int,
    timeout_seconds: float,
) -> None:
    with session_factory() as db:
        extraction = db.get(Extraction, extraction_id)
        if extraction is None or extraction.status != ExtractionStatus.PENDING:
            return

        version = db.get(SchemaVersion, extraction.schema_version_id)
        spec = TemplateSpec.model_validate(version.definition)
        storage_key = extraction.storage_key

        extraction.status = ExtractionStatus.RUNNING
        extraction.started_at = _utcnow()
        db.commit()

        result: dict | None = None
        error: str | None = None

        try:
            data = storage.read(storage_key)
            output = asyncio.run(
                asyncio.wait_for(
                    run_extraction(data, spec, model=model, max_bytes=max_bytes),
                    timeout=timeout_seconds,
                )
            )
            result = output.model_dump(mode="json")
        except TimeoutError:
            error = "The extraction timed out."
        except UnexpectedModelBehavior:
            logger.warning("Extraction %s: invalid model output", extraction_id)
            error = "The model returned data that does not match the schema."
        except DocumentLoadError as e:
            error = str(e)
        except Exception:
            logger.exception("Extraction %s failed", extraction_id)
            error = "The extraction failed because of a model or server error."

        storage.delete(storage_key)
        extraction.status = (
            ExtractionStatus.DONE if error is None else ExtractionStatus.FAILED
        )
        extraction.result = result
        extraction.error = error
        extraction.finished_at = _utcnow()
        db.commit()


def recover_interrupted(db: Session, *, storage: FileStorage) -> int:
    interrupted = repositories.list_active_extractions(db)
    for extraction in interrupted:
        storage.delete(extraction.storage_key)
        extraction.status = ExtractionStatus.FAILED
        extraction.error = "Interrupted by a server restart. Upload the document again."
        extraction.finished_at = _utcnow()
    db.commit()
    return len(interrupted)


def get_user_extraction(
    db: Session, *, user_id: uuid.UUID, extraction_id: uuid.UUID
) -> Extraction:
    extraction = repositories.get_extraction(
        db, user_id=user_id, extraction_id=extraction_id
    )
    if extraction is None:
        raise ExtractionNotFoundError(extraction_id)
    return extraction


def list_user_extractions(db: Session, user_id: uuid.UUID) -> list[Extraction]:
    repositories.list_extractions(db, user_id=user_id)
