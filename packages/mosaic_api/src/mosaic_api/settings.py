from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MOSAIC_", env_file=".env", extra="ignore")

    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]
    data_dir: str = "data"
