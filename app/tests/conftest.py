import subprocess

import pytest

GIT_TEST_CONFIG = ("-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false")


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *GIT_TEST_CONFIG, *args], check=True, capture_output=True)


@pytest.fixture
def git():
    return _git


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
