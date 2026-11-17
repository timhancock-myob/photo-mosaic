from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import source_gateway
from mosaic_api.services.meta import Health, get_health
from mosaic_api.settings import Settings


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
        return get_health()

    app.include_router(source_gateway.router)
    return app


app = create_app()
