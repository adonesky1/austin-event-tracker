from pydantic import BaseModel, Field


class UserProfileSchema(BaseModel):
    email: str
    city: str = "austin"
    adults: list[dict] = Field(default_factory=lambda: [{"age": 35}])
    children: list[dict] = Field(default_factory=list)
    preferred_neighborhoods: list[str] = Field(default_factory=list)
    max_distance_miles: int = 30
    preferred_days: list[str] = Field(default_factory=lambda: ["saturday", "sunday"])
    preferred_times: list[str] = Field(default_factory=lambda: ["morning", "afternoon"])
    budget: str = "moderate"
    interests: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    max_events_per_digest: int = 15
    crowd_sensitivity: str = "medium"
