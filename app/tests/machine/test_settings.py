from pathlib import Path

from den.machine.settings import Settings


def test_settings_round_trip_files_with_profiles(fake_home, tmp_path):
    files = tmp_path / "den-files"
    Settings(profiles=["work", "personal"], files=files).save()
    assert Settings.load() == Settings(profiles=["work", "personal"], files=files)


def test_settings_load_expands_files_home_path(fake_home):
    Settings(files=Path("~/repos/den-files")).save()
    assert Settings.load().files == fake_home / "repos" / "den-files"
