from pathlib import Path

from vgdb import config


def test_the_archive_defaults_outside_the_code_repository(monkeypatch):
    monkeypatch.delenv("VGDB_FILE", raising=False)

    assert config.archive_path() == Path.home() / ".vgdb" / "games.json"


def test_the_archive_path_is_always_absolute(tmp_path, monkeypatch):
    """vgdb is installed globally and runs from any directory."""
    monkeypatch.setenv("VGDB_FILE", "games.json")
    monkeypatch.chdir(tmp_path)

    assert config.archive_path().is_absolute()


def test_a_home_relative_archive_path_is_expanded(monkeypatch):
    monkeypatch.setenv("VGDB_FILE", "~/elsewhere/games.json")

    assert config.archive_path() == Path.home() / "elsewhere" / "games.json"


def test_the_key_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("VGDB_SGDB_KEY", "from-the-environment")

    assert config.steamgriddb_key() == "from-the-environment"


def test_the_key_falls_back_to_the_untracked_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("VGDB_SGDB_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('VGDB_SGDB_KEY="from-the-file"\n')

    assert config.steamgriddb_key() == "from-the-file"


def test_the_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("VGDB_SGDB_KEY", "from-the-environment")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("VGDB_SGDB_KEY=from-the-file\n")

    assert config.steamgriddb_key() == "from-the-environment"


def test_other_names_in_the_env_file_are_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("VGDB_SGDB_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SOMETHING_ELSE=nope\n")

    assert config.steamgriddb_key() is None


def test_no_key_anywhere_is_not_an_error(tmp_path, monkeypatch):
    """Without a key the cover scripts fall back to Steam rather than stopping."""
    monkeypatch.delenv("VGDB_SGDB_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    assert config.steamgriddb_key() is None
