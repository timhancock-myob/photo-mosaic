from pydantic import BaseModel

import mosaic_core


class Health(BaseModel):
    status: str
    core_version: str


def get_health() -> Health:
    return Health(status="ok", core_version=mosaic_core.__version__)
