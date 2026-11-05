import subprocess

from den.services.git import Repo


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        check=True,
        capture_output=True,
    )


def test_renamed_and_new_files_are_reported_once_each(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "old.txt").write_text("content")
    git(tmp_path, "add", "old.txt")
    git(tmp_path, "commit", "-q", "-m", "initial")
    git(tmp_path, "mv", "old.txt", "new.txt")
    (tmp_path / "added.txt").write_text("other")
    changes = Repo(tmp_path).state().changes
    assert sorted((change.path, change.label) for change in changes) == [("added.txt", "new"), ("new.txt", "renamed")]
