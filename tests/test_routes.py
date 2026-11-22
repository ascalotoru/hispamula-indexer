from fastapi.testclient import TestClient

from app import main
from app.hispamula import Ed2kFile, SearchResult, TitleDetail
from app.main import app

from tests.conftest import FakeSession

client = TestClient(app)


def test_caps_all_paths():
    for path in ("/", "/api", "/api/api"):
        response = client.get(path, params={"t": "caps"})
        assert response.status_code == 200
        assert "<caps>" in response.text


def test_status_cache_fria(read_fixture, monkeypatch):
    session = FakeSession(page=read_fixture("atom.xml"))
    monkeypatch.setattr(main, "get_session", lambda: session)
    main._search_cache.clear()
    main._detail_cache.clear()

    body = client.get("/status").json()

    assert body["novedades_total"] == 5
    assert body["novedades_en_cache"] == 0
    assert body["detail_cache"] == 0
    assert body["caliente"] is False


def test_status_cache_caliente(read_fixture, monkeypatch):
    session = FakeSession(page=read_fixture("atom.xml"))
    monkeypatch.setattr(main, "get_session", lambda: session)
    main._search_cache.clear()
    main._detail_cache.clear()
    for tid in (40645, 40899, 40896, 41511, 5444):
        main._detail_cache.set(tid, object())

    body = client.get("/status").json()

    assert body["novedades_en_cache"] == 5
    assert body["detail_cache"] == 5
    assert body["caliente"] is True


def test_do_search_propaga_anio(monkeypatch):
    f = Ed2kFile(
        url="ed2k://|file|a|10|0123456789ABCDEF0123456789ABCDEF|/",
        name="El Robo Del Siglo.mkv",
        size=10,
        hash="0123456789ABCDEF0123456789ABCDEF",
        group_id=1,
        group_label="HD 1080p",
    )
    det = TitleDetail(
        title_id=34262,
        title="El robo del siglo (2020)",
        year=2020,
        type="Película",
        files=[f],
    )
    monkeypatch.setattr(main, "get_session", lambda: FakeSession())
    monkeypatch.setattr(
        main,
        "search",
        lambda session, query: [
            SearchResult(title_id=34262, title="El robo del siglo", year=2020, type="Película")
        ],
    )
    monkeypatch.setattr(main, "detail", lambda session, tid: det)
    main._search_cache.clear()
    main._detail_cache.clear()

    files = main._do_search("El robo del siglo", "movie")

    assert files
    assert files[0][0].year == 2020
