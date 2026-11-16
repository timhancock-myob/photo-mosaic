from fastapi.testclient import TestClient

from mosaic_api import create_app


def test_health() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_gateway_router_is_mounted() -> None:
    response = TestClient(create_app()).get("/sources/providers")
    assert response.status_code == 200
