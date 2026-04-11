from src.config.settings import Settings
from src.models.user import UserProfile
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


def user_profile_to_schema(profile: UserProfile) -> UserProfileSchema:
    return UserProfileSchema(
        id=profile.id,
        email=profile.email,
        city=profile.city,
        adults=profile.adults or [],
        children=profile.children or [],
        preferred_neighborhoods=profile.preferred_neighborhoods or [],
        max_distance_miles=profile.max_distance_miles,
        preferred_days=profile.preferred_days or [],
        preferred_times=profile.preferred_times or [],
        budget=profile.budget.value if hasattr(profile.budget, "value") else str(profile.budget),
        interests=profile.interests or [],
        dislikes=profile.dislikes or [],
        max_events_per_digest=profile.max_events_per_digest,
        crowd_sensitivity=(
            profile.crowd_sensitivity.value
            if hasattr(profile.crowd_sensitivity, "value")
            else str(profile.crowd_sensitivity)
        ),
    )
