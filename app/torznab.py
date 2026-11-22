"""Generación de XML Torznab/Newznab."""

from __future__ import annotations

import base64
import re
import time
from email.utils import formatdate
from os.path import splitext
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

from . import __version__
from .config import BASE_URL
from .hispamula import Ed2kFile

AMULERR_TRACKER = "http://amulerr"

# Radarr no puede parsear un release sin año. Sólo se añade a ficheros de
# vídeo: en un .srt con el mismo nombre haría que Radarr lo aprobase.
VIDEO_EXTS = {
    ".3gp", ".avi", ".divx", ".iso", ".m2ts", ".m4v", ".mkv", ".mov",
    ".mp4", ".mpeg", ".mpg", ".ogm", ".ts", ".vob", ".webm", ".wmv",
}


def to_btih(ed2k_hash: str) -> str:
    """Hash ed2k (32 hex) → btih base32 que espera aMulerr.

    aMulerr codifica los 16 bytes del hash ed2k en un buffer de 20 bytes
    (los 4 últimos a cero) y lo pasa a base32 en mayúsculas.
    """
    raw = bytes.fromhex(ed2k_hash) + b"\x00" * 4
    return base64.b32encode(raw).decode("ascii")


def to_magnet(ed2k_hash: str, name: str, size: int) -> str:
    """Magnet que el shim qBittorrent de aMulerr convierte de vuelta a ed2k.

    Radarr exige un enclosure ``application/x-bittorrent`` y aMulerr sólo
    acepta este formato; el ``ed2k://`` crudo no le sirve.
    """
    return (
        f"magnet:?xt=urn:btih:{to_btih(ed2k_hash)}"
        f"&dn={quote(name, safe='')}&xl={size}&tr={AMULERR_TRACKER}"
    )


def capabilities() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<caps>\n'
        f"  <server appversion=\"{__version__}\" version=\"{__version__}\" title=\"Hispamula\" "
        "strapline=\"eMule links indexer\" email=\"\" url=\"https://www.hispamula.org\"/>\n"
        "  <limits max=\"100\" default=\"100\"/>\n"
        "  <categories>\n"
        '    <category id="2000" name="Movies">\n'
        '      <subcat id="2010" name="Foreign"/>\n'
        '      <subcat id="2020" name="Other"/>\n'
        '      <subcat id="2030" name="SD"/>\n'
        '      <subcat id="2040" name="HD"/>\n'
        '      <subcat id="2045" name="UHD"/>\n'
        '      <subcat id="2050" name="BluRay"/>\n'
        '      <subcat id="2060" name="3D"/>\n'
        '      <subcat id="2070" name="DVD"/>\n'
        '      <subcat id="2080" name="WEB-DL"/>\n'
        '      <subcat id="2090" name="x265"/>\n'
        "    </category>\n"
        '    <category id="5000" name="TV">\n'
        '      <subcat id="5010" name="WEB-DL"/>\n'
        '      <subcat id="5020" name="Foreign"/>\n'
        '      <subcat id="5030" name="SD"/>\n'
        '      <subcat id="5040" name="HD"/>\n'
        '      <subcat id="5045" name="UHD"/>\n'
        '      <subcat id="5050" name="Other"/>\n'
        '      <subcat id="5060" name="Sport"/>\n'
        '      <subcat id="5070" name="Anime"/>\n'
        '      <subcat id="5080" name="Documentary"/>\n'
        '      <subcat id="5090" name="x265"/>\n'
        "    </category>\n"
        "  </categories>\n"
        "  <searching>\n"
        '    <search available="yes" supportedParams="q"/>\n'
        '    <movie-search available="yes" supportedParams="q"/>\n'
        '    <tv-search available="yes" supportedParams="q,season,ep"/>\n'
        "  </searching>\n"
        "</caps>\n"
    )


def _release_name(f: Ed2kFile, categories: list[int]) -> str:
    """Añade el año de la ficha al nombre del fichero si no lo lleva.

    ``Nombre (2020) [BDrip 1080p: ...]``: Radarr descarta con "Unable to parse
    release" todo release sin año. El nombre viaja también en el ``dn`` del
    magnet, que aMulerr usa como nombre del fichero en aMule; así el import
    automático empareja el fichero descargado ("Movie title mismatch" si no).
    """
    stem, ext = splitext(f.name)
    if (
        f.year
        and ext.lower() in VIDEO_EXTS
        and 2000 in categories
        and not re.search(rf"\b{f.year}\b", f.name)
    ):
        return f"{stem} ({f.year}){ext}"
    return f.name


def _item_xml(f: Ed2kFile, categories: list[int], pubdate: str) -> str:
    guid = f.hash
    label = f" [{f.group_label}]" if f.group_label else ""
    release = _release_name(f, categories)
    title = escape(f"{release}{label}")
    magnet = quoteattr(to_magnet(f.hash, release, f.size))
    seeders = max(f.downloads, 0)
    cat_tags = "".join(f"  <category>{c}</category>\n" for c in categories)
    cat_attrs = "".join(
        f'  <torznab:attr name="category" value="{c}"/>\n' for c in categories
    )
    page_url = escape(f"{BASE_URL}/?title={f.title_id}")
    return (
        "<item>\n"
        f"  <title>{title}</title>\n"
        f'  <guid isPermaLink="false">{guid}</guid>\n'
        f"  <comments>{page_url}</comments>\n"
        f"  <pubDate>{pubdate}</pubDate>\n"
        f"{cat_tags}"
        f"  <size>{f.size}</size>\n"
        f'  <torznab:attr name="size" value="{f.size}"/>\n'
        f"{cat_attrs}"
        f'  <torznab:attr name="seeders" value="{seeders}"/>\n'
        f'  <torznab:attr name="peers" value="{seeders}"/>\n'
        f"  <enclosure url={magnet} length=\"{f.size}\" type=\"application/x-bittorrent\"/>\n"
        "</item>\n"
    )


def feed(files: list[tuple[Ed2kFile, list[int]]], query: str = "") -> str:
    pubdate = formatdate(time.time(), usegmt=True)
    items = "".join(_item_xml(f, cat, pubdate) for f, cat in files)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:torznab="http://torznab.com/schemas/2015/feed">\n'
        "<channel>\n"
        "  <title>Hispamula</title>\n"
        f"  <link>https://www.hispamula.org/</link>\n"
        "  <description>eMule links indexer</description>\n"
        f"  <pubDate>{pubdate}</pubDate>\n"
        f"  <lastBuildDate>{pubdate}</lastBuildDate>\n"
        f"  <item_count>{len(files)}</item_count>\n"
        f"{items}"
        "</channel>\n"
        "</rss>\n"
    )
