import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from schema_extractor.api.deps import (
    CurrentUser,
    DbSession,
    ExtractionModelDep,
    SettingsDep,
    StorageDep,
    TaskSessionFactoryDep,
)
from schema_extractor.api.payloads import ExtractionOut
from schema_extractor.services import extraction_service

router = APIRouter(prefix="/extractions", tags=["extractions"])


@router.post("", response_model=ExtractionOut, status_code=202)
def create_extraction(
    user: CurrentUser,
    db: DbSession,
    settings: SettingsDep,
    background_tasks: BackgroundTasks,
    storage: StorageDep,
    model: ExtractionModelDep,
    session_factory: TaskSessionFactoryDep,
    file: Annotated[UploadFile, File()],
    schema_id: Annotated[uuid.UUID, Form()],
    version: Annotated[int | None, Form(ge=1)] = None,
):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)

    extraction = extraction_service.create_extraction(
        db,
        user_id=user.id,
        schema_id=schema_id,
        version_number=version,
        filename=file.filename,
        data=data,
        storage=storage,
        max_bytes=max_bytes,
        max_active=settings.max_active_extractions_per_user,
    )
    background_tasks.add_task(
        extraction_service.process_extraction,
        session_factory,
        extraction.id,
        model=model,
        storage=storage,
        max_bytes=max_bytes,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return extraction


@router.get("", response_model=list[ExtractionOut])
def list_extractions(db: DbSession, user: CurrentUser):
    return extraction_service.list_user_extractions(db, user_id=user.id)


@router.get("/{extraction_id}", response_model=ExtractionOut)
def get_extraction(extraction_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return extraction_service.get_user_extraction(
        db, user_id=user.id, extraction_id=extraction_id
    )
