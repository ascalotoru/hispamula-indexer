from app.hispamula import search

from tests.conftest import FakeSession


def test_search_parse(read_fixture):
    session = FakeSession(page=read_fixture("search.html"))
    results = search(session, "terminator")
    assert results
    ids = {r.title_id for r in results}
    assert 372 in ids
    terminator = next(r for r in results if r.title_id == 372)
    assert terminator.type == "Película"
    assert terminator.year == 1984
    assert "Terminator" in terminator.title
