import pytest

from den import secrets, skills
from den.machine.paths import ROOT
from den.machine.system import System
from den.manifest import loader
from den.mcp import catalog

EXAMPLE = ROOT / "example"


@pytest.mark.parametrize("os", ["macos", "arch", "debian"])
def test_the_example_files_repository_loads_on_every_os(os, monkeypatch):
    monkeypatch.setenv("DEN_FILES", str(EXAMPLE))

    manifest = loader.load(System(os, os, "arm64"), ["work"])

    assert manifest.packages and manifest.tasks and manifest.agents and manifest.link_packages
    assert [server.name for server in catalog.load_servers()] == ["notion", "github", "playwright"]
    assert [skill.name for skill in skills.installed()] == ["commit-message"]
    assert secrets.names() == ["GITHUB_TOKEN"]
