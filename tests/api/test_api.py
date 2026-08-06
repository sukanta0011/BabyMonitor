from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api.app import app


def test_app_starts_with_no_cameras():
    with patch("src.api.app.start_streaming", return_value=[]):
        with TestClient(app) as client:
            response = client.get("/frame_info")
            assert response.status_code == 200
