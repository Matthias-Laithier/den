from den.machine.paths import expand, home_packages, instructions_file, manifest_dir, secrets_dir, skills_dir


def test_expand_uses_the_shell_default_when_the_variable_is_unset(monkeypatch, fake_home):
    monkeypatch.delenv("KIMI_CODE_HOME", raising=False)
    assert expand("${KIMI_CODE_HOME:-~/.kimi-code}/skills") == fake_home / ".kimi-code" / "skills"


def test_expand_prefers_the_variable_when_it_is_set(monkeypatch, tmp_path):
    monkeypatch.setenv("KIMI_CODE_HOME", str(tmp_path))
    assert expand("${KIMI_CODE_HOME:-~/.kimi-code}/skills") == tmp_path / "skills"


def test_config_paths_follow_den_files(files_root):
    assert home_packages() == files_root / "home"
    assert skills_dir() == files_root / "skills"
    assert instructions_file() == files_root / "instructions" / "AGENTS.md"
    assert manifest_dir() == files_root / "manifest"
    assert secrets_dir() == files_root / "secrets"
