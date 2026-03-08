from src.sources.base import SourceAdapter


class SourceRegistry:
    def __init__(self):
        self._sources: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter):
        self._sources[adapter.name] = adapter

    def get(self, name: str) -> SourceAdapter:
        return self._sources[name]

    def list_sources(self) -> list[str]:
        return list(self._sources.keys())

    def get_enabled(self) -> list[SourceAdapter]:
        return [s for s in self._sources.values() if s.is_enabled()]
