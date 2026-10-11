"""Generación de XML Torznab/Newznab."""

from __future__ import annotations

import time
from email.utils import formatdate
from xml.sax.saxutils import escape, quoteattr

from . import __version__
from .config import BASE_URL
from .hispamula import Ed2kFile


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


def _item_xml(f: Ed2kFile, categories: list[int], pubdate: str) -> str:
    guid = f.hash
    label = f" [{f.group_label}]" if f.group_label else ""
    title = escape(f"{f.name}{label}")
    url = quoteattr(f.url)
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
        f"  <enclosure url={url} length=\"{f.size}\" type=\"application/x-ed2k\"/>\n"
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
