from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import mosaic_core
import source_gateway
from mosaic_api.settings import Settings


class Health(BaseModel):
    status: str
    core_version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Photo Mosaic API", version="0.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> Health:
        return Health(status="ok", core_version=mosaic_core.__version__)

    app.include_router(source_gateway.router)
    return app


app = create_app()
