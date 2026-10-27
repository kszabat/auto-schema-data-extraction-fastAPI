import re

from pathlib import Path

_KEY_RE = re.compile(r"[0-9a-f]{32}")


class FileStorage:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        if not _KEY_RE.fullmatch(key):
            raise ValueError("Invalid storage key.")
        return self.root / key

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()
    
