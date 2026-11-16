from pydantic import BaseModel


class ProviderInfo(BaseModel):
    id: str
    display_name: str
