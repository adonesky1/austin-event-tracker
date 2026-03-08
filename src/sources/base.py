from abc import ABC, abstractmethod

from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent


class SourceAdapter(ABC):
    name: str
    source_type: SourceType

    @abstractmethod
    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]: ...

    def is_enabled(self) -> bool:
        return True

    def rate_limit_delay(self) -> float:
        return 1.0
