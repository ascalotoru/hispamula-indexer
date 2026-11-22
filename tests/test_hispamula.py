from app.hispamula import novedades

from tests.conftest import FakeSession


def test_novedades_extrae_title_ids(read_fixture):
    session = FakeSession(page=read_fixture("atom.xml"))
    assert novedades(session) == [40645, 40899, 40896, 41511, 5444]
