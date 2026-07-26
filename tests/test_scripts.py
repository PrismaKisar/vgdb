import sgdb


def test_the_key_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("VGDB_SGDB_KEY", "from-the-environment")

    assert sgdb.api_key() == "from-the-environment"


def test_the_key_falls_back_to_the_untracked_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("VGDB_SGDB_KEY", raising=False)
    monkeypatch.setattr(sgdb, "PROJECT", tmp_path)
    (tmp_path / ".env").write_text('VGDB_SGDB_KEY="from-the-file"\n')

    assert sgdb.api_key() == "from-the-file"


def test_no_key_anywhere_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.delenv("VGDB_SGDB_KEY", raising=False)
    monkeypatch.setattr(sgdb, "PROJECT", tmp_path)

    assert sgdb.api_key() is None
