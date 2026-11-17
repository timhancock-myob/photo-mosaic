from fastapi import APIRouter

from source_gateway.schemas import ProviderInfo

router = APIRouter(prefix="/sources", tags=["sources"])

PROVIDERS = [ProviderInfo(id="local_folder", display_name="Local folder")]


@router.get("/providers")
def list_providers() -> list[ProviderInfo]:
    return PROVIDERS
