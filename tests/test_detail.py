from app.hispamula import detail

from tests.conftest import FakeSession


def test_detail_collection(read_fixture):
    session = FakeSession(
        page=read_fixture("detail_collection.html"),
        downloads={"82289": read_fixture("download_82289.html")},
    )
    det = detail(session, 41554)
    assert det.title_id == 41554
    assert len(det.files) == 44
    first = det.files[0]
    assert first.hash == "B4DCEC7F52F1962638B441CA168575E3"
    assert first.size == 2784465463
    assert first.group_label == "BDrip 1080p: mkv (HEVC 10b-AC3)"
    assert first.url.startswith("ed2k://")
    assert first.name
