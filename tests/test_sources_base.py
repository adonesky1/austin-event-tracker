import pytest

from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter
from src.sources.registry import SourceRegistry


def test_source_adapter_interface():
    with pytest.raises(TypeError):
        SourceAdapter()


def test_source_registry():
    class FakeSource(SourceAdapter):
        name = "fake"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            return []

    registry = SourceRegistry()
    registry.register(FakeSource())
    assert "fake" in registry.list_sources()
    assert registry.get("fake").name == "fake"


def test_registry_get_enabled():
    class EnabledSource(SourceAdapter):
        name = "enabled"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            return []

    class DisabledSource(SourceAdapter):
        name = "disabled"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            return []

        def is_enabled(self):
            return False

    registry = SourceRegistry()
    registry.register(EnabledSource())
    registry.register(DisabledSource())
    enabled = registry.get_enabled()
    assert len(enabled) == 1
    assert enabled[0].name == "enabled"
