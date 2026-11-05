from den import links


def make_package(files_root):
    packages = files_root / "home"
    (packages / "zsh" / ".config" / "zsh").mkdir(parents=True)
    (packages / "zsh" / ".zshrc").write_text("repo")
    (packages / "zsh" / ".config" / "zsh" / "aliases.zsh").write_text("repo")
    return packages


def states(planned):
    return {link.relative: link.state for link in planned}


def test_plan_folds_missing_directories_and_reports_conflicts(files_root, fake_home):
    make_package(files_root)
    (fake_home / ".config").mkdir()
    (fake_home / ".zshrc").write_text("mine")
    assert states(links.plan("zsh")) == {".config/zsh": "missing", ".zshrc": "conflict"}


def test_plan_marks_links_into_another_dotfiles_copy_as_stale(files_root, fake_home):
    make_package(files_root)
    old_copy = files_root / "old" / ".config" / "zsh"
    old_copy.mkdir(parents=True)
    (fake_home / ".config").mkdir()
    (fake_home / ".config" / "zsh").symlink_to(old_copy)
    assert states(links.plan("zsh"))[".config/zsh"] == "stale"


def test_apply_all_links_everything_and_backs_up_replaced_files(files_root, fake_home):
    packages = make_package(files_root)
    (fake_home / ".zshrc").write_text("mine")
    backup = links.apply_all(links.plan("zsh"))
    assert backup is not None
    assert (fake_home / ".zshrc").resolve() == packages / "zsh" / ".zshrc"
    assert (backup / ".zshrc").read_text() == "mine"
    assert set(states(links.plan("zsh")).values()) == {"linked"}


def test_adopt_moves_the_file_on_disk_into_the_repo(files_root, fake_home):
    packages = make_package(files_root)
    (fake_home / ".zshrc").write_text("mine")
    conflict = next(link for link in links.plan("zsh") if link.state == "conflict")
    links.adopt(conflict)
    assert (packages / "zsh" / ".zshrc").read_text() == "mine"
    assert (fake_home / ".zshrc").is_symlink()


def test_directories_shared_by_several_packages_are_created_instead_of_linked(files_root, fake_home):
    packages = make_package(files_root)
    (packages / "ghostty" / ".config" / "ghostty").mkdir(parents=True)
    (packages / "ghostty" / ".config" / "ghostty" / "config").write_text("repo")
    planned = links.plan_all(["ghostty", "zsh"])
    assert states(planned) == {".config/ghostty": "missing", ".config/zsh": "missing", ".zshrc": "missing"}
    links.apply_all(planned)
    assert not (fake_home / ".config").is_symlink()
