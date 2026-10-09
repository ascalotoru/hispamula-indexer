"""Scraping de hispamula.org: búsqueda, detalle y enlaces ed2k."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .session import HispamulaSession

TITLE_ID_RE = re.compile(r"title=(\d+)")
YEAR_RE = re.compile(r"\b(\d{4})\b")
ED2K_RE = re.compile(r"ed2k://\|file\|([^|]*)\|(\d+)\|([0-9A-Fa-f]{32})\|/")

MOVIE_TYPES = {"Película", "Documental"}
TV_TYPES = {"Serie", "Docuserie"}


@dataclass
class SearchResult:
    title_id: int
    title: str
    year: int | None
    type: str
    synopsis: str = ""
    cover: str = ""


@dataclass
class Ed2kFile:
    url: str
    name: str
    size: int
    hash: str
    group_id: int
    group_label: str
    downloads: int = 0


@dataclass
class TitleDetail:
    title_id: int
    title: str
    year: int | None
    type: str
    files: list[Ed2kFile] = field(default_factory=list)


def _extract_year(title_text: str) -> int | None:
    matches = YEAR_RE.findall(title_text)
    if not matches:
        return None
    return int(matches[-1])


def search(session: HispamulaSession, query: str) -> list[SearchResult]:
    response = session.get("/", params={"view": "search", "q": query})
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[SearchResult] = []
    for tr in soup.select("tr.T1"):
        anchor = tr.select_one("h1 a")
        if anchor is None:
            continue
        match = TITLE_ID_RE.search(anchor.get("href", ""))
        if match is None:
            continue
        title_id = int(match.group(1))
        title = anchor.get_text(" ", strip=True)
        synopsis = ""
        text_p = tr.select_one("p.TEXT")
        if text_p is not None:
            synopsis = text_p.get_text(" ", strip=True)
        typ = ""
        info = tr.select_one("p.INFO")
        if info is not None:
            m = re.match(r"Género:\s*([^>]+)", info.get_text(" ", strip=True))
            if m:
                typ = m.group(1).strip()
        cover = ""
        img = tr.select_one("img.COVER_SMALL")
        if img is not None:
            cover = img.get("src", "")
        results.append(
            SearchResult(
                title_id=title_id,
                title=title,
                year=_extract_year(title),
                type=typ,
                synopsis=synopsis,
                cover=cover,
            )
        )
    return results


def _parse_group(table) -> tuple[int, str, list[tuple[str, int]]]:
    """Devuelve (group_id, label, [(filename, downloads), ...]) de una tabla T2."""
    rows: list[tuple[str, int]] = []
    group_id: int | None = None
    for tr in table.select("tr"):
        icon = tr.select_one("td.ICON input[id^='elink_']")
        if icon is None:
            continue
        input_id = icon.get("id", "")
        m = re.match(r"elink_(\d+)_(\d+)", input_id)
        if m is None:
            continue
        group_id = int(m.group(1))
        anchor = tr.select_one("td a")
        filename = anchor.get_text(" ", strip=True) if anchor else ""
        sizes = tr.select("td.SIZE")
        downloads = 0
        if len(sizes) >= 2:
            downloads = int(re.sub(r"\D", "", sizes[1].get_text()) or 0)
        rows.append((filename, downloads))
    label = ""
    heading = table.find_previous("h2")
    if heading is not None:
        label = heading.get_text(" ", strip=True)
    return group_id or 0, label, rows


def _download_links(session: HispamulaSession, group_id: int, count: int) -> list[Ed2kFile]:
    code = "1" * count
    response = session.get("/ajax/download.php", params={"id": group_id, "code": code})
    soup = BeautifulSoup(response.text, "html.parser")
    textarea = soup.find(id="ELINKSLIST")
    if textarea is None:
        return []
    text = textarea.get_text()
    files: list[Ed2kFile] = []
    for line in text.splitlines():
        line = line.strip()
        m = ED2K_RE.search(line)
        if m is None:
            continue
        files.append(
            Ed2kFile(
                url=line,
                name=m.group(1),
                size=int(m.group(2)),
                hash=m.group(3).upper(),
                group_id=group_id,
                group_label="",
            )
        )
    return files


def detail(session: HispamulaSession, title_id: int) -> TitleDetail:
    response = session.get("/", params={"title": title_id})
    soup = BeautifulSoup(response.text, "html.parser")

    title = ""
    h1 = soup.select_one("h1")
    if h1 is not None:
        title = h1.get_text(" ", strip=True)

    typ = ""
    info = soup.select_one("p.INFO")
    if info is not None:
        m = re.match(r"Género:\s*([^>]+)", info.get_text(" ", strip=True))
        if m:
            typ = m.group(1).strip()

    files: list[Ed2kFile] = []
    for table in soup.select("table.T2"):
        group_id, label, rows = _parse_group(table)
        if group_id == 0 or not rows:
            continue
        ed2k = _download_links(session, group_id, len(rows))
        for (filename, downloads), f in zip(rows, ed2k):
            if filename:
                f.name = filename
            f.group_label = label
            f.downloads = downloads
            files.append(f)

    return TitleDetail(
        title_id=title_id,
        title=title,
        year=_extract_year(title),
        type=typ,
        files=files,
    )


def torznab_category(typ: str) -> int:
    if typ in MOVIE_TYPES:
        return 2000
    if typ in TV_TYPES:
        return 5000
    return 0
