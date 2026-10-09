from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_caps_all_paths():
    for path in ("/", "/api", "/api/api"):
        response = client.get(path, params={"t": "caps"})
        assert response.status_code == 200
        assert "<caps>" in response.text
