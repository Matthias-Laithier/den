import pytest

from den.machine.system import System
from den.manifest import loader

ARCH = System("arch", "Arch Linux", "x86_64")
DEBIAN = System("debian", "Debian", "x86_64")


@pytest.fixture
def manifest_dir(files_root):
    return files_root / "manifest"


def test_each_os_installs_a_package_with_its_first_available_method(manifest_dir):
    manifest_dir.mkdir()
    (manifest_dir / "packages.toml").write_text(
        '[fd]\nbrew = "fd"\napt = "fd-find"\nuv_tool = "fd"\n\n[kitty]\ncask = "kitty"\n'
    )
    assert [(p.name, p.method, p.targets) for p in loader.load(DEBIAN, []).packages] == [("fd", "apt", ("fd-find",))]
    assert [(p.name, p.method) for p in loader.load(ARCH, []).packages] == [("fd", "uv_tool")]


def test_entries_are_filtered_by_os_and_profile(manifest_dir):
    manifest_dir.mkdir()
    (manifest_dir / "tasks.toml").write_text(
        '[work-only]\nprofiles = ["work"]\nrun = "true"\n\n[mac-only]\nos = ["macos"]\nrun = "true"\n'
    )
    assert [task.name for task in loader.load(ARCH, []).tasks] == []
    assert [task.name for task in loader.load(ARCH, ["work"]).tasks] == ["work-only"]


def test_agent_with_a_skills_path_that_is_not_a_path_is_rejected(manifest_dir):
    manifest_dir.mkdir()
    (manifest_dir / "agents.toml").write_text('[claude]\nhome = "~/.claude"\nskills = 1\n')
    with pytest.raises(loader.InvalidManifest):
        loader.load(ARCH, [])


def test_settings_for_an_agent_missing_from_agents_toml_are_rejected(manifest_dir):
    manifest_dir.mkdir()
    (manifest_dir / "agents.toml").write_text('[claude]\nhome = "~/.claude"\nskills = "~/.claude/skills"\n')
    (manifest_dir / "agent-settings.toml").write_text('[cladue."~/.claude/settings.json"]\nmodel = "opus"\n')
    with pytest.raises(loader.InvalidManifest):
        loader.load(ARCH, [])
