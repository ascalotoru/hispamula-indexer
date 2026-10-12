import time

from app import main
from app.cache import TTLCache

from tests.conftest import FakeSession


def test_cache_devuelve_valor_dentro_del_ttl():
    cache = TTLCache(ttl=60)
    cache.set("a", {"n": 1})
    assert cache.get("a") == {"n": 1}


def test_cache_devuelve_none_si_no_existe():
    cache = TTLCache(ttl=60)
    assert cache.get("inexistente") is None


def test_cache_expira_pasado_el_ttl():
    cache = TTLCache(ttl=0.01)
    cache.set("a", 1)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_cache_clear_vacia():
    cache = TTLCache(ttl=60)
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None


def test_do_search_cachea_evitando_re_raspado(read_fixture, monkeypatch):
    """La segunda búsqueda idéntica no debe volver a tocar la red."""
    session = FakeSession(page=read_fixture("search.html"))
    monkeypatch.setattr(main, "get_session", lambda: session)
    main._search_cache.clear()
    main._detail_cache.clear()

    main._do_search("terminator", "all")
    calls_first = len(session.calls)
    assert calls_first > 1  # búsqueda + al menos un detalle

    main._do_search("terminator", "all")
    assert len(session.calls) == calls_first
