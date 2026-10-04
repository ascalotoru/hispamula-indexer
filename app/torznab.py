"""Generación de XML Torznab/Newznab."""

from __future__ import annotations

import time
from email.utils import formatdate
from xml.sax.saxutils import escape, quoteattr

from .hispamula import Ed2kFile


def capabilities() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<caps>\n'
        "  <server appversion=\"0.1\" version=\"0.1\" title=\"Hispamula\" "
        "strapline=\"eMule links indexer\" email=\"\" url=\"https://www.hispamula.org\"/>\n"
        "  <limits max=\"100\" default=\"100\"/>\n"
        "  <categories>\n"
        '    <category id="2000" name="Movies">\n'
        '      <subcat id="2000" name="Movies"/>\n'
        "    </category>\n"
        '    <category id="5000" name="TV">\n'
        '      <subcat id="5000" name="TV"/>\n'
        "    </category>\n"
        "  </categories>\n"
        "  <searching>\n"
        '    <search available="yes" supportedParams="q"/>\n'
        '    <movie-search available="yes" supportedParams="q"/>\n'
        '    <tv-search available="yes" supportedParams="q,season,ep"/>\n'
        "  </searching>\n"
        "</caps>\n"
    )


def _item_xml(f: Ed2kFile, category: int, pubdate: str) -> str:
    guid = f.hash
    title = escape(f.name)
    url = quoteattr(f.url)
    seeders = max(f.downloads, 0)
    return (
        "<item>\n"
        f"  <title>{title}</title>\n"
        f'  <guid isPermaLink="false">{guid}</guid>\n'
        f"  <pubDate>{pubdate}</pubDate>\n"
        f"  <category>{category}</category>\n"
        f"  <size>{f.size}</size>\n"
        f'  <torznab:attr name="seeders" value="{seeders}"/>\n'
        f'  <torznab:attr name="peers" value="{seeders}"/>\n'
        f"  <enclosure url={url} length=\"{f.size}\" type=\"application/x-ed2k\"/>\n"
        "</item>\n"
    )


def feed(files: list[tuple[Ed2kFile, int]], query: str = "") -> str:
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
