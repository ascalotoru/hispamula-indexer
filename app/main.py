"""Servicio Torznab de hispamula.org."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response

from . import config
from .hispamula import (
    Ed2kFile,
    MOVIE_TYPES,
    TV_TYPES,
    HispamulaSession,
    detail,
    search,
    torznab_category,
)
from .torznab import capabilities, feed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hispamula-indexer")

app = FastAPI(title="hispamula-indexer")

_session: HispamulaSession | None = None


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


def _do_search(query: str, mode: str) -> list[tuple[Ed2kFile, int]]:
    session = get_session()
    results = search(session, query)
    files: list[tuple[Ed2kFile, int]] = []
    for result in results[: config.MAX_RESULTS]:
        if not _filter_type(result.type, mode):
            continue
        try:
            det = detail(session, result.title_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("error detalle %s: %s", result.title_id, exc)
            continue
        category = torznab_category(det.type)
        for f in det.files:
            files.append((f, category))
    return files


@app.get("/api")
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
