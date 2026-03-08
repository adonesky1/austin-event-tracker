import pytest


@pytest.fixture
def austin_config():
    from src.config.city import load_city_config

    return load_city_config("austin")


@pytest.fixture
def settings():
    from src.config.settings import Settings

    return Settings(
        database_url="sqlite+aiosqlite:///test.db",
        anthropic_api_key="test-key",
        resend_api_key="test-key",
    )
