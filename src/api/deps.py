from functools import lru_cache

from fastapi import Header, HTTPException, Depends

from src.config.settings import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


def verify_admin_key(
    x_api_key: str = Header(..., description="Admin API key"),
    settings: Settings = Depends(get_settings),
):
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
