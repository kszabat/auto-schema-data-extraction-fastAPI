from pydantic_ai import BinaryContent

from schema_extractor.documents.exceptions import (
    DocumentTooLargeError,
    UnsupportedFileTypeError,
)

SUPPORTED_MEDIA_TYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
)


def detect_media_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def load_binary_content(data: bytes, *, max_bytes: int | None = None) -> BinaryContent:
    if max_bytes is not None and len(data) > max_bytes:
        raise DocumentTooLargeError(len(data), max_bytes)

    media_type = detect_media_type(data)
    if media_type is None:
        raise UnsupportedFileTypeError(SUPPORTED_MEDIA_TYPES)

    return BinaryContent(data=data, media_type=media_type)
