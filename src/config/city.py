from pathlib import Path

import yaml
from pydantic import BaseModel


class CityConfig(BaseModel):
    name: str
    display_name: str
    state: str
    timezone: str
    latitude: float
    longitude: float
    radius_miles: int
    neighborhoods: list[str]
    default_sources: list[str]


def load_city_config(city_slug: str) -> CityConfig:
    path = Path(__file__).parent / "cities" / f"{city_slug}.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return CityConfig(**data)
