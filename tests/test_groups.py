from bs4 import BeautifulSoup

from app.hispamula import _parse_group


def test_serie_groups(read_fixture):
    soup = BeautifulSoup(read_fixture("detail_serie.html"), "lxml")
    groups = []
    for table in soup.select("table.T2"):
        label, rows = _parse_group(table)
        groups.append((label, len(rows)))
    assert ("HDTV-TDT: avi (XviD-mp3)", 9) in groups
    assert ("DVD-DVB: avi (XviD-mp3)", 9) in groups


def test_legacy_group_parse(read_fixture):
    """Los grupos antiguos listan cada fichero con Download(gid, code) en vez
    de checkboxes elink_; también deben parsearse."""
    soup = BeautifulSoup(read_fixture("detail_legacy.html"), "lxml")
    label, rows = _parse_group(soup.select_one("table.T2"))
    assert label == "DVD-Rip: avi (XviD-mp3)"
    assert len(rows) == 1
    row = rows[0]
    assert row.filename == "Heroes Del Cielo.avi"
    assert row.downloads == 5457
    assert row.group_id == 5730
    assert row.code == "1"


def test_modern_rows_keep_no_code(read_fixture):
    """Las filas modernas (checkbox) no guardan code: se descargan en lote."""
    soup = BeautifulSoup(read_fixture("detail_mixed.html"), "lxml")
    label, rows = _parse_group(soup.select("table.T2")[0])
    assert label == "BRrip: avi (XviD-AC3)"
    assert len(rows) == 2
    assert all(row.group_id == 20893 for row in rows)
    assert all(row.code is None for row in rows)