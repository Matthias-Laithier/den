from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from den import config_files
from den.config_files import DocumentFormat

BACKUP_GROUP = "mcp"


class Section(Protocol):
    def entries(self, document) -> dict[str, dict]: ...

    def store(self, document, entries: dict[str, dict], document_format: DocumentFormat) -> None: ...


@dataclass(frozen=True)
class KeyedSection:
    key: str

    def entries(self, document) -> dict[str, dict]:
        return {name: dict(entry) for name, entry in document.get(self.key, {}).items()}

    def store(self, document, entries: dict[str, dict], document_format: DocumentFormat) -> None:
        document[self.key] = entries


@dataclass(frozen=True)
class NamedTableArray:
    key: str

    def entries(self, document) -> dict[str, dict]:
        return {entry["name"]: dict(entry) for entry in document.get(self.key, [])}

    def store(self, document, entries: dict[str, dict], document_format: DocumentFormat) -> None:
        tables = [{"name": name, **{k: v for k, v in entry.items() if k != "name"}} for name, entry in entries.items()]
        document[self.key] = document_format.table_array(tables)


@dataclass(frozen=True)
class ConfigFile:
    path: Path
    document_format: DocumentFormat
    section: Section

    def read(self) -> dict[str, dict]:
        document, _ = config_files.load(self.path, self.document_format)
        return self.section.entries(document)

    def write(self, entries: dict[str, dict]) -> None:
        document, raw = config_files.load(self.path, self.document_format)
        self.section.store(document, entries, self.document_format)
        config_files.save(self.path, document, self.document_format, raw, BACKUP_GROUP)
