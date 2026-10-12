from app.hispamula import detail, torznab_category

from tests.conftest import FakeSession


def test_detail_collection(read_fixture):
    session = FakeSession(
        page=read_fixture("detail_collection.html"),
        downloads={"82289": read_fixture("download_82289.html")},
    )
    det = detail(session, 41554)
    assert det.title_id == 41554
    assert det.type == "Película"
    assert torznab_category(det.type) == 2000
    assert len(det.files) == 44
    first = det.files[0]
    assert first.hash == "B4DCEC7F52F1962638B441CA168575E3"
    assert first.size == 2784465463
    assert first.group_label == "BDrip 1080p: mkv (HEVC 10b-AC3)"
    assert first.url.startswith("ed2k://")
    assert first.name


def test_detail_sets_title_id(read_fixture):
    session = FakeSession(
        page=read_fixture("detail_collection.html"),
        downloads={"82289": read_fixture("download_82289.html")},
    )
    det = detail(session, 41554)
    assert det.files
    assert all(f.title_id == 41554 for f in det.files)


def test_detail_serie_type(read_fixture):
    session = FakeSession(
        page=read_fixture("detail_serie.html"),
        downloads={},
    )
    det = detail(session, 1)
    assert det.type == "Serie"
    assert torznab_category(det.type) == 5000


def test_detail_legacy_group(read_fixture):
    """Un grupo legacy (Download(gid, code) sin checkbox) también debe
    aportar su fichero al detalle."""
    session = FakeSession(
        page=read_fixture("detail_legacy.html"),
        downloads={"5730": read_fixture("download_5730.html")},
    )
    det = detail(session, 1927)
    assert det.title_id == 1927
    assert det.type == "Película"
    assert len(det.files) == 1
    f = det.files[0]
    assert f.title_id == 1927
    assert f.group_id == 5730
    assert f.group_label == "DVD-Rip: avi (XviD-mp3)"
    assert f.name == "Heroes Del Cielo.avi"
    assert f.size == 729917440
    assert f.hash == "AB22B51CCAF865BA7768F053467153BD"
    assert f.downloads == 5457
    assert f.url.startswith("ed2k://")


def test_detail_mixed_groups(read_fixture):
    """Título con grupo moderno (checkbox) y grupos legacy: salen todos los
    ficheros que lista la web (regresión de 'Héroes del cielo')."""
    session = FakeSession(
        page=read_fixture("detail_mixed.html"),
        downloads={
            "20893": read_fixture("download_20893.html"),
            "11518": read_fixture("download_11518.html"),
            "5730": read_fixture("download_5730.html"),
        },
    )
    det = detail(session, 1927)
    assert len(det.files) == 4
    assert {f.group_id for f in det.files} == {20893, 11518, 5730}
    labels = {f.group_label for f in det.files}
    assert labels == {"BRrip: avi (XviD-AC3)", "DVD-Rip: avi (XviD-AC3)",
                      "DVD-Rip: avi (XviD-mp3)"}
    names = {f.name for f in det.files}
    assert "Heroes Del Cielo.avi" in names
    assert "Herois del cel.avi" in names
    assert "Héroes del cielo.avi" in names