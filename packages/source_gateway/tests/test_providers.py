from fastapi import FastAPI
from fastapi.testclient import TestClient

from source_gateway import router


def test_lists_local_folder_provider() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/sources/providers")
    assert response.status_code == 200
    assert {"id": "local_folder", "display_name": "Local folder"} in response.json()
