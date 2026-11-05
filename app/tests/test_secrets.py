import stat

import pytest

from den import secrets


def test_saved_secrets_decrypt_and_load_into_a_private_shell_file(files_root, fake_home):
    secrets.save({"API_KEY": "it's secret"}, "correct horse")
    assert secrets.decrypt("correct horse") == {"API_KEY": "it's secret"}
    assert secrets.names() == ["API_KEY"]
    assert secrets.local_names() == {"API_KEY"}
    assert stat.S_IMODE(secrets.local_file().stat().st_mode) == 0o600
    assert not secrets.is_outdated()


def test_wrong_passphrase_is_rejected(files_root, fake_home):
    secrets.save({"API_KEY": "value"}, "correct horse")
    with pytest.raises(secrets.WrongPassphrase):
        secrets.decrypt("battery staple")
