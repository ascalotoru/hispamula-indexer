from bs4 import BeautifulSoup

from app.hispamula import _parse_group


def test_serie_groups(read_fixture):
    soup = BeautifulSoup(read_fixture("detail_serie.html"), "html.parser")
    groups = []
    for table in soup.select("table.T2"):
        gid, label, rows = _parse_group(table)
        groups.append((gid, label, len(rows)))
    assert (10181, "HDTV-TDT: avi (XviD-mp3)", 9) in groups
    assert (10641, "DVD-DVB: avi (XviD-mp3)", 9) in groups
