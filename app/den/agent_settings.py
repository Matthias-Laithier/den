from collections.abc import MutableMapping

from den import config_files
from den.machine.paths import home
from den.manifest.models import SettingsFile

BACKUP_GROUP = "agent-settings"
HOME_PREFIX = "~/"


def _with_home(value):
    if isinstance(value, dict):
        return {_with_home(key): _with_home(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_with_home(item) for item in value]
    if isinstance(value, str) and value.startswith(HOME_PREFIX):
        return str(home() / value.removeprefix(HOME_PREFIX))
    return value


def _contains(document, values: dict) -> bool:
    for key, value in values.items():
        if isinstance(value, dict):
            if not isinstance(document.get(key), MutableMapping) or not _contains(document[key], value):
                return False
        elif document.get(key) != value:
            return False
    return True


def _merge(document, values: dict) -> None:
    for key, value in values.items():
        if isinstance(value, dict) and isinstance(document.get(key), MutableMapping):
            _merge(document[key], value)
        else:
            document[key] = value


def is_applied(settings: SettingsFile) -> bool:
    if not settings.path.exists():
        return False
    document, _ = config_files.load(settings.path, config_files.format_for(settings.path))
    return _contains(document, _with_home(settings.values))


def apply(settings: SettingsFile) -> None:
    document_format = config_files.format_for(settings.path)
    document, raw = config_files.load(settings.path, document_format)
    _merge(document, _with_home(settings.values))
    config_files.save(settings.path, document, document_format, raw, BACKUP_GROUP)
