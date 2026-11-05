import os
import tempfile
from pathlib import Path


class ChangedConcurrently(Exception):
    pass


def read_bytes_if_exists(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def write_atomically(path: Path, content: str | bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content.encode() if isinstance(content, str) else content)
    if mode is not None:
        os.chmod(temporary, mode)
    elif path.exists():
        os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)


def replace_if_unchanged(path: Path, content: str, read_as: bytes | None) -> None:
    if read_bytes_if_exists(path) != read_as:
        raise ChangedConcurrently(f"{path} changed while den was editing it, try again")
    write_atomically(path, content)
