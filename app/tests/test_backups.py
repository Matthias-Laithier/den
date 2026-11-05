from den import backups, links


def test_replaced_files_are_counted_then_cleaned(files_root, fake_home):
    packages = files_root / "home"
    (packages / "zsh").mkdir(parents=True)
    (packages / "zsh" / ".zshrc").write_text("repo")
    (fake_home / ".zshrc").write_text("mine")
    links.apply_all(links.plan("zsh"))
    assert backups.summary() == (1, len("mine"))
    backups.clean()
    assert backups.summary() == (0, 0)
