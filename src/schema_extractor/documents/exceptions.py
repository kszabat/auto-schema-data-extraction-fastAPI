from collections.abc import Iterable


class DocumentLoadError(Exception):
    """Base class for document loading errors."""


class UnsupportedFileTypeError(DocumentLoadError):
    def __init__(self, supported: Iterable[str]) -> None:
        self.supported = tuple(supported)
        super().__init__(
            f"Unsupported file type. Supported types: {', '.join(self.supported)}."
        )


class DocumentTooLargeError(DocumentLoadError):
    def __init__(self, size: int, max_bytes: int) -> None:
        self.size = size
        self.max_bytes = max_bytes
        super().__init__(f"Document is too large: {size} bytes (max {max_bytes}).")
