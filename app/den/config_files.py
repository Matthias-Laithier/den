import json
import shutil
from pathlib import Path
from typing import Protocol

import tomlkit
import yaml

from den import backups
from den.machine.files import read_bytes_if_exists, replace_if_unchanged
from den.machine.paths import home

JSON_INDENT = 2
_FORMATS: dict[str, type] = {}


class DocumentFormat(Protocol):
    def load(self, text: str): ...

    def dump(self, document) -> str: ...

    def table_array(self, tables: list[dict]): ...


def handles(*suffixes: str):
    def register(document_format: type) -> type:
        for suffix in suffixes:
            if suffix in _FORMATS:
                raise ValueError(f"duplicate settings file suffix: {suffix}")
            _FORMATS[suffix] = document_format
        return document_format

    return register


@handles(".json", ".jsonc")
class JsonFormat:
    def load(self, text: str):
        return json.loads(text) if text.strip() else {}

    def dump(self, document) -> str:
        return json.dumps(document, indent=JSON_INDENT, ensure_ascii=False) + "\n"

    def table_array(self, tables: list[dict]):
        return tables


@handles(".toml")
class TomlFormat:
    def load(self, text: str):
        return tomlkit.parse(text)

    def dump(self, document) -> str:
        return tomlkit.dumps(document)

    def table_array(self, tables: list[dict]):
        array = tomlkit.aot()
        for table in tables:
            array.append(tomlkit.item(table))
        return array


@handles(".yaml")
class YamlFormat:
    def load(self, text: str):
        return yaml.safe_load(text) or {}

    def dump(self, document) -> str:
        return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)

    def table_array(self, tables: list[dict]):
        return tables


def format_for(path: Path) -> DocumentFormat:
    if path.suffix not in _FORMATS:
        raise ValueError(f"unsupported settings file: {path}")
    return _FORMATS[path.suffix]()


def load(path: Path, document_format: DocumentFormat) -> tuple[object, bytes | None]:
    raw = read_bytes_if_exists(path)
    return document_format.load(raw.decode() if raw else ""), raw


def save(path: Path, document, document_format: DocumentFormat, read_as: bytes | None, backup_group: str) -> None:
    if path.exists():
        destination = backups.new_folder() / backup_group / path.relative_to(home())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    replace_if_unchanged(path, document_format.dump(document), read_as)
