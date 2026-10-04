import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeSession:
    """Sustituye HispamulaSession en tests (sin red)."""

    def __init__(self, page: str = "", downloads: dict[str, str] | None = None):
        self.page = page
        self.downloads = downloads or {}
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, path: str, params: dict | None = None):
        self.calls.append((path, params))
        if path == "/ajax/download.php":
            gid = str(params["id"])
            return FakeResponse(self.downloads.get(gid, ""))
        return FakeResponse(self.page)


@pytest.fixture
def read_fixture():
    def _read(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return _read
