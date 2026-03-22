from src.config.settings import Settings
from src.schemas.user import UserProfileSchema


def build_default_profile(settings: Settings) -> UserProfileSchema:
    return UserProfileSchema(
        email=settings.from_email,
        city=settings.default_city,
        adults=[{"age": 35}, {"age": 35}],
        children=[{"age": 5}, {"age": 8}],
        preferred_neighborhoods=["South Austin", "Zilker", "East Austin", "Downtown"],
        max_distance_miles=30,
        preferred_days=["saturday", "sunday", "friday"],
        preferred_times=["morning", "afternoon", "evening"],
        budget="moderate",
        interests=["music", "outdoor", "festivals", "kids", "arts", "seasonal", "community"],
        dislikes=[],
        max_events_per_digest=15,
        crowd_sensitivity="medium",
    )
