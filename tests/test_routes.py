from fastapi.testclient import TestClient

from app import main
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
