"""Scraping de hispamula.org: búsqueda, detalle y enlaces ed2k."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .session import HispamulaSession

TITLE_ID_RE = re.compile(r"title=(\d+)")
YEAR_RE = re.compile(r"\b(\d{4})\b")
QUERY_YEAR_RE = re.compile(r"\s+\d{4}\s*$")
ED2K_RE = re.compile(r"ed2k://\|file\|([^|]*)\|(\d+)\|([0-9A-Fa-f]{32})\|/")
DOWNLOAD_JS_RE = re.compile(r"Download\((\d+),'([01]+)'\)")

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
    title_id: int = 0


@dataclass
class TitleDetail:
    title_id: int
    title: str
    year: int | None
    type: str
    files: list[Ed2kFile] = field(default_factory=list)


@dataclass
class GroupRow:
    """Una fila descargable de una tabla T2.

    Las publicaciones modernas enumeran las filas con checkboxes
    ``elink_<gid>_<i>`` y se descargan en lote (``code`` None); las antiguas
    llevan un enlace ``Download(<gid>, '<code>')`` por fila (``code`` = la
    máscara exacta que selecciona esa fila).
    """

    filename: str
    downloads: int
    group_id: int
    code: str | None = None


def _extract_year(title_text: str) -> int | None:
    matches = YEAR_RE.findall(title_text)
    if not matches:
        return None
    return int(matches[-1])


def _extract_type(root) -> str:
    """Devuelve el tipo ('Serie', 'Película', ...) desde el p.INFO de Género."""
    for info in root.select("p.INFO"):
        m = re.match(r"Género:\s*([^>]+)", info.get_text(" ", strip=True))
        if m:
            return m.group(1).strip()
    return ""


def normalize_query(query: str) -> str:
    """Quita el año final que añaden los *arr al título.

    hispamula busca por título o título original (substring); un año
    pegado ("Les Chevaliers du ciel 2005") no aparece en ninguno de los
    dos y la búsqueda devuelve 0 resultados.
    """
    return QUERY_YEAR_RE.sub("", query).strip()


def search(session: HispamulaSession, query: str) -> list[SearchResult]:
    query = normalize_query(query)
    response = session.get("/", params={"view": "search", "q": query})
    soup = BeautifulSoup(response.text, "lxml")
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
        typ = _extract_type(tr)
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


def _parse_group(table) -> tuple[str, list[GroupRow]]:
    """Devuelve (label, filas descargables) de una tabla T2.

    Admite filas modernas (checkbox ``elink_<gid>_<i>``, se descargan en
    lote) y filas legacy (enlace ``Download(<gid>,'<code>')``, cada una con
    su propia máscara de bits).
    """
    rows: list[GroupRow] = []
    for tr in table.select("tr"):
        cells = tr.select("td")
        if len(cells) < 2:
            continue
        icon = tr.select_one("td.ICON input[id^='elink_']")
        if icon is not None:
            m = re.match(r"elink_(\d+)_\d+", icon.get("id", ""))
            if m is None:
                continue
            group_id = int(m.group(1))
            code: str | None = None
        else:
            dl = tr.select_one('a[href^="javascript:Download"]')
            if dl is None:
                continue
            m = DOWNLOAD_JS_RE.search(dl.get("href", ""))
            if m is None:
                continue
            group_id, code = int(m.group(1)), m.group(2)
        anchor = cells[1].select_one("a")
        filename = (
            anchor.get_text(" ", strip=True)
            if anchor is not None
            else cells[1].get_text(" ", strip=True)
        )
        sizes = tr.select("td.SIZE")
        downloads = 0
        if len(sizes) >= 2:
            downloads = int(re.sub(r"\D", "", sizes[1].get_text()) or 0)
        rows.append(GroupRow(filename, downloads, group_id, code))
    label = ""
    heading = table.find_previous("h2")
    if heading is not None:
        label = heading.get_text(" ", strip=True)
    return label, rows


def _download_links(session: HispamulaSession, group_id: int, code: str) -> list[Ed2kFile]:
    """Descarga las ed2k del grupo con la máscara ``code`` ('1'*n selecciona
    todas las filas de un grupo moderno; una máscara con un único bit o '1'
    devuelve la fila concreta de un grupo legacy)."""
    response = session.get("/ajax/download.php", params={"id": group_id, "code": code})
    soup = BeautifulSoup(response.text, "lxml")
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


def _attach_files(files: list[Ed2kFile], rows: list[GroupRow], label: str, title_id: int) -> list[Ed2kFile]:
    """Empareja por índice fila <-> ed2k y rellena el metadato del fichero."""
    out: list[Ed2kFile] = []
    for row, f in zip(rows, files):
        if row.filename:
            f.name = row.filename
        f.group_label = label
        f.downloads = row.downloads
        f.title_id = title_id
        out.append(f)
    return out


def detail(session: HispamulaSession, title_id: int) -> TitleDetail:
    response = session.get("/", params={"title": title_id})
    soup = BeautifulSoup(response.text, "lxml")

    title = ""
    h1 = soup.select_one("h1")
    if h1 is not None:
        title = h1.get_text(" ", strip=True)

    typ = _extract_type(soup)

    files: list[Ed2kFile] = []
    for table in soup.select("table.T2"):
        label, rows = _parse_group(table)
        if not rows:
            continue
        # Grupos modernos: un lote por grupo (una petición con '1'*n);
        # legacy: una petición por fila con su propia máscara.
        modern = [r for r in rows if r.code is None]
        legacy = [r for r in rows if r.code is not None]
        if modern:
            gid = modern[0].group_id
            files += _attach_files(
                _download_links(session, gid, "1" * len(modern)), modern, label, title_id
            )
        for row in legacy:
            files += _attach_files(
                _download_links(session, row.group_id, row.code), [row], label, title_id
            )

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


_UHD_RE = re.compile(r"\b(2160p|4k|uhd)\b", re.I)
_HD_RE = re.compile(r"\b(1080p|720p)\b", re.I)
_SD_RE = re.compile(r"\b(480p|576p|360p|xvid|dvdrip|dvd-rip)\b", re.I)
_WEB_DL_RE = re.compile(r"\bweb-?dl\b", re.I)
_BLURAY_RE = re.compile(r"\b(blu-?ray|bd-?rip|brrip|bdrip)\b", re.I)
_X265_RE = re.compile(r"\b(hevc|x265|h\.?265)\b", re.I)


def torznab_subcategories(typ: str, label: str) -> list[int]:
    """Subcategorías Newznab para un archivo según su calidad (resolución,
    formato y codec). Devuelve la categoría padre + subcategorías."""
    parent = torznab_category(typ)
    if not parent:
        return []
    is_tv = parent == 5000
    text = label.lower()
    cats: list[int] = [parent]
    if _UHD_RE.search(text):
        cats.append(5045 if is_tv else 2045)
    elif _HD_RE.search(text):
        cats.append(5040 if is_tv else 2040)
    elif _SD_RE.search(text):
        cats.append(5030 if is_tv else 2030)
    if _WEB_DL_RE.search(text):
        cats.append(5010 if is_tv else 2080)
    elif _BLURAY_RE.search(text):
        cats.append(2050)  # Movies/BluRay
    if _X265_RE.search(text):
        cats.append(5090 if is_tv else 2090)
    return cats
