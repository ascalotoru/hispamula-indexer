"""Servicio Torznab de hispamula.org."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response

from . import config
from .cache import TTLCache
from .hispamula import (
    Ed2kFile,
    MOVIE_TYPES,
    TV_TYPES,
    HispamulaSession,
    detail,
    search,
    torznab_subcategories,
)
from .torznab import capabilities, feed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hispamula-indexer")

app = FastAPI(title="hispamula-indexer")

_session: HispamulaSession | None = None

# Caché de búsquedas y fichas para evitar el re-raspado N+1 (título +
# enlaces ed2k por cada resultado), que hacía que el RSS sync de los *arr
# superase su timeout.
_search_cache = TTLCache(config.CACHE_TTL)
_detail_cache = TTLCache(config.CACHE_TTL)


def get_session() -> HispamulaSession:
    global _session
    if _session is None:
        _session = HispamulaSession(
            base_url=config.BASE_URL,
            username=config.USERNAME,
            password=config.PASSWORD,
            request_delay=config.REQUEST_DELAY,
            timeout=config.TIMEOUT,
            user_agent=config.USER_AGENT,
        )
    return _session


def _filter_type(typ: str, mode: str) -> bool:
    if mode == "movie":
        return typ in MOVIE_TYPES
    if mode == "tv":
        return typ in TV_TYPES
    return True


def _do_search(query: str, mode: str) -> list[tuple[Ed2kFile, list[int]]]:
    session = get_session()
    results = _search_cache.get(query)
    if results is None:
        results = search(session, query)
        _search_cache.set(query, results)
    files: list[tuple[Ed2kFile, list[int]]] = []
    # El RSS sync de los *arr consulta sin `q`: se limita para no superar su
    # timeout raspando toda la portada en frío.
    limit = config.MAX_RESULTS if query.strip() else config.RSS_MAX_RESULTS
    for result in results[:limit]:
        if not _filter_type(result.type, mode):
            continue
        det = _detail_cache.get(result.title_id)
        if det is None:
            try:
                det = detail(session, result.title_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("error detalle %s: %s", result.title_id, exc)
                continue
            _detail_cache.set(result.title_id, det)
        for f in det.files:
            cats = torznab_subcategories(det.type, f"{f.name} {f.group_label}")
            files.append((f, cats))
    return files


@app.get("/")
@app.get("/api")
@app.get("/api/api")
def api(request: Request) -> Response:
    t = request.query_params.get("t", "search")
    if t == "caps":
        return PlainTextResponse(capabilities(), media_type="application/xml")
    query = request.query_params.get("q", "")
    if t in ("search", "movie", "tvsearch"):
        mode = "movie" if t == "movie" else ("tv" if t == "tvsearch" else "all")
        files = _do_search(query, mode)
        return PlainTextResponse(feed(files, query), media_type="application/xml")
    return PlainTextResponse(feed([], ""), media_type="application/xml")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
