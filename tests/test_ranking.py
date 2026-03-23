import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema
from src.ranking.rules import compute_rule_score
from src.ranking.feedback import adjust_score_for_feedback
from src.models.base import FeedbackType


@pytest.fixture
def user_profile():
    return UserProfileSchema(
        email="test@example.com",
        city="austin",
        interests=["music", "outdoor", "festivals"],
        dislikes=["theatre"],
        preferred_days=["saturday", "sunday"],
        preferred_times=["morning", "afternoon"],
        preferred_neighborhoods=["South Austin", "Zilker"],
        budget="moderate",
        children=[{"age": 5}, {"age": 8}],
    )


def make_event(**kwargs):
    defaults = dict(
        title="Test Event",
        category="music",
        start_datetime=datetime.now(timezone.utc) + timedelta(days=3),
        city="austin",
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)


def test_matching_interest_scores_high(user_profile):
    event = make_event(category="music", neighborhood="Zilker")
    score = compute_rule_score(event, user_profile)
    assert score > 0.6


def test_disliked_category_scores_lower_than_liked(user_profile):
    liked = make_event(category="music")
    disliked = make_event(category="theatre")
    liked_score = compute_rule_score(liked, user_profile)
    disliked_score = compute_rule_score(disliked, user_profile)
    assert disliked_score < liked_score
    assert disliked_score < 0.5  # disliked events stay below neutral


def test_free_event_scores_well(user_profile):
    from decimal import Decimal
    event = make_event(category="music", price_min=Decimal("0"), price_max=Decimal("0"))
    score = compute_rule_score(event, user_profile)
    assert score > 0.5


def test_expensive_event_scores_lower(user_profile):
    from decimal import Decimal
    cheap = make_event(category="music", price_max=Decimal("15"))
    expensive = make_event(category="music", price_max=Decimal("150"))
    cheap_score = compute_rule_score(cheap, user_profile)
    expensive_score = compute_rule_score(expensive, user_profile)
    assert cheap_score > expensive_score


def test_preferred_neighborhood_boosts_score(user_profile):
    zilker = make_event(category="music", neighborhood="Zilker")
    remote = make_event(category="music", neighborhood="Round Rock")
    zilker_score = compute_rule_score(zilker, user_profile)
    remote_score = compute_rule_score(remote, user_profile)
    assert zilker_score > remote_score


def test_tracked_item_boost_applies_best_match(user_profile):
    event = make_event(
        title="ACL Festival Aftershow",
        description="One-night celebration with local bands",
        tags=["music", "festival"],
    )
    base_score = compute_rule_score(event, user_profile, tracked_items=[])
    boosted_score = compute_rule_score(
        event,
        user_profile,
        tracked_items=[
            SimpleNamespace(label="ACL", enabled=True, boost_weight=0.12),
            SimpleNamespace(label="festival", enabled=True, boost_weight=0.2),
        ],
    )

    assert boosted_score > base_score
    assert round(boosted_score - base_score, 2) >= 0.12


def test_thumbs_up_boosts_similar():
    feedback_history = [
        {
            "event_category": "music",
            "event_neighborhood": "Zilker",
            "feedback_type": FeedbackType.THUMBS_UP,
            "created_at": datetime.now(timezone.utc),
        }
    ]
    event = make_event(category="music", neighborhood="Zilker")
    adjusted = adjust_score_for_feedback(0.5, event, feedback_history)
    assert adjusted > 0.5


def test_too_far_penalizes():
    feedback_history = [
        {
            "event_category": "music",
            "event_neighborhood": "Cedar Park",
            "feedback_type": FeedbackType.TOO_FAR,
            "created_at": datetime.now(timezone.utc),
        }
    ]
    event = make_event(category="music", neighborhood="Cedar Park")
    adjusted = adjust_score_for_feedback(0.5, event, feedback_history)
    assert adjusted < 0.5


@pytest.mark.asyncio
async def test_ranking_engine_sorts_by_score():
    from src.ranking.engine import RankingEngine
    profile = UserProfileSchema(
        email="test@example.com",
        interests=["music"],
    )
    events = [
        make_event(title="Low Score", category="seasonal"),
        make_event(title="High Score", category="music"),
    ]
    engine = RankingEngine()
    ranked = await engine.rank_events(events, profile)
    assert ranked[0][0].title == "High Score"
    assert ranked[0][1] >= ranked[1][1]
