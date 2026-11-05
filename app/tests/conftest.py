import pytest


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def files_root(tmp_path, monkeypatch):
    root = tmp_path / "den-files"
    root.mkdir()
    monkeypatch.setenv("DEN_FILES", str(root))
    return root
