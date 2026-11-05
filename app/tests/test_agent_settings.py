import json
import tomllib

import yaml

from den import agent_settings
from den.manifest.models import SettingsFile


def test_applying_codex_settings_keeps_its_other_keys(fake_home):
    config = fake_home / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text('model = "gpt"\n\n[features]\nhooks = true\ncodex_git_commit = true\n')
    settings = SettingsFile("~/.codex/config.toml", {"features": {"codex_git_commit": False}})
    assert not agent_settings.is_applied(settings)
    agent_settings.apply(settings)
    assert tomllib.loads(config.read_text()) == {"model": "gpt", "features": {"hooks": True, "codex_git_commit": False}}
    assert agent_settings.is_applied(settings)


def test_applying_creates_a_missing_json_settings_file_with_nested_keys(fake_home):
    settings = SettingsFile("~/.qwen/settings.json", {"general": {"gitCoAuthor": {"commit": False, "pr": False}}})
    agent_settings.apply(settings)
    assert json.loads((fake_home / ".qwen" / "settings.json").read_text()) == {
        "general": {"gitCoAuthor": {"commit": False, "pr": False}}
    }


def test_home_paths_in_keys_and_values_point_into_this_machines_home(fake_home):
    settings = SettingsFile(
        "~/.codex/config.toml",
        {"catalog": "~/.codex/catalog.json", "projects": {"~/repos": {"trust_level": "trusted"}}, "tilde": "~x"},
    )
    agent_settings.apply(settings)
    assert tomllib.loads((fake_home / ".codex" / "config.toml").read_text()) == {
        "catalog": f"{fake_home}/.codex/catalog.json",
        "projects": {f"{fake_home}/repos": {"trust_level": "trusted"}},
        "tilde": "~x",
    }
    assert agent_settings.is_applied(settings)


def test_applying_yaml_settings_keeps_its_other_keys(fake_home):
    config = fake_home / ".hermes" / "config.yaml"
    config.parent.mkdir()
    config.write_text("telemetry:\n  enabled: false\nmodel:\n  default: old\n")
    settings = SettingsFile("~/.hermes/config.yaml", {"model": {"provider": "gateway", "default": "opus"}})
    assert not agent_settings.is_applied(settings)
    agent_settings.apply(settings)
    assert yaml.safe_load(config.read_text()) == {
        "telemetry": {"enabled": False},
        "model": {"default": "opus", "provider": "gateway"},
    }
    assert agent_settings.is_applied(settings)
