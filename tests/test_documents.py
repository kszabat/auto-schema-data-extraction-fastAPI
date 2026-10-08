import pytest

from schema_extractor.documents.exceptions import (
    DocumentTooLargeError,
    UnsupportedFileTypeError,
)
from schema_extractor.documents.multimodal import (
    detect_media_type,
    load_binary_content,
)

PDF = b"%PDF-1.7\n%fake"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 8
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 8
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (PDF, "application/pdf"),
        (PNG, "image/png"),
        (JPEG, "image/jpeg"),
        (WEBP, "image/webp"),
        (b"hello world", None),
        (b"", None),
    ],
)
def test_detect_media_type(data, expected):
    assert detect_media_type(data) == expected


def test_load_binary_content_keeps_data_and_type():
    content = load_binary_content(PDF)
    assert content.media_type == "application/pdf"
    assert content.data == PDF


def test_unsupported_content_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        load_binary_content(b"MZ\x90\x00 random binary data")


def test_too_large_document_is_rejected():
    with pytest.raises(DocumentTooLargeError):
        load_binary_content(PDF, max_bytes=5)
