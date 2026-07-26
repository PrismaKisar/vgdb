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


def test_a_grid_page_is_resolved_through_the_api(monkeypatch):
    """A grid page is HTML, so its id has to become an image URL first."""
    monkeypatch.setattr(sgdb, "get", lambda path, key: {"data": {"url": "cdn/art.png"}})
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("https://www.steamgriddb.com/grid/801236", "k") == b"downloaded cdn/art.png"


def test_a_bare_grid_id_is_resolved_too(monkeypatch):
    monkeypatch.setattr(sgdb, "get", lambda path, key: {"data": {"url": "cdn/art.png"}})
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("801236", "k") == b"downloaded cdn/art.png"


def test_a_plain_image_url_is_downloaded_as_is(monkeypatch):
    monkeypatch.setattr(sgdb, "fetch", lambda url, key=None: f"downloaded {url}".encode())

    assert sgdb.artwork_from("https://example.com/a.png", "k") == b"downloaded https://example.com/a.png"
