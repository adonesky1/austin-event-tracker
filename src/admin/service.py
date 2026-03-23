from sqlalchemy import select

from src.curation.profile import build_default_profile
from src.models.base import BudgetLevel, CrowdSensitivity, TrackedItemKind
from src.models.prompt_config import PromptConfig
from src.models.tracked_item import TrackedItem
from src.models.user import UserProfile
from src.schemas.admin import (
    PromptConfigResponse,
    TrackedItemCreate,
    TrackedItemResponse,
    TrackedItemUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)


def serialize_profile(profile: UserProfile) -> UserProfileResponse:
    return UserProfileResponse(
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
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def get_or_create_profile(session, settings) -> UserProfile:
    result = await session.execute(select(UserProfile).order_by(UserProfile.created_at.asc()).limit(1))
    profile = result.scalar_one_or_none()
    if profile is not None:
        return profile

    seeded = build_default_profile(settings)
    profile = UserProfile(
        email=seeded.email,
        city=seeded.city,
        adults=seeded.adults,
        children=seeded.children,
        preferred_neighborhoods=seeded.preferred_neighborhoods,
        max_distance_miles=seeded.max_distance_miles,
        preferred_days=seeded.preferred_days,
        preferred_times=seeded.preferred_times,
        budget=seeded.budget,
        interests=seeded.interests,
        dislikes=seeded.dislikes,
        max_events_per_digest=seeded.max_events_per_digest,
        crowd_sensitivity=seeded.crowd_sensitivity,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def update_profile(session, settings, payload: UserProfileUpdate) -> UserProfile:
    profile = await get_or_create_profile(session, settings)
    updates = payload.model_dump(exclude_unset=True)
    if "budget" in updates and updates["budget"] is not None:
        updates["budget"] = BudgetLevel(updates["budget"])
    if "crowd_sensitivity" in updates and updates["crowd_sensitivity"] is not None:
        updates["crowd_sensitivity"] = CrowdSensitivity(updates["crowd_sensitivity"])
    for field, value in updates.items():
        setattr(profile, field, value)
    await session.commit()
    await session.refresh(profile)
    return profile


def serialize_prompt_config(
    prompt: PromptConfig | None,
    *,
    key: str,
    system_prompt: str,
    user_prompt_template: str,
) -> PromptConfigResponse:
    return PromptConfigResponse(
        key=key,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        is_default=prompt is None,
        updated_at=prompt.updated_at if prompt else None,
    )


async def get_prompt_config(session, key: str) -> PromptConfig | None:
    result = await session.execute(select(PromptConfig).where(PromptConfig.key == key))
    return result.scalar_one_or_none()


async def update_prompt_config(session, key: str, system_prompt: str, user_prompt_template: str):
    prompt = await get_prompt_config(session, key)
    if prompt is None:
        prompt = PromptConfig(
            key=key,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )
        session.add(prompt)
    else:
        prompt.system_prompt = system_prompt
        prompt.user_prompt_template = user_prompt_template
    await session.commit()
    await session.refresh(prompt)
    return prompt


async def reset_prompt_config(session, key: str):
    prompt = await get_prompt_config(session, key)
    if prompt is not None:
        await session.delete(prompt)
        await session.commit()


def serialize_tracked_item(item: TrackedItem) -> TrackedItemResponse:
    return TrackedItemResponse(
        id=item.id,
        label=item.label,
        kind=item.kind.value if hasattr(item.kind, "value") else str(item.kind),
        enabled=item.enabled,
        boost_weight=item.boost_weight,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def list_tracked_items(session) -> list[TrackedItem]:
    result = await session.execute(select(TrackedItem).order_by(TrackedItem.created_at.asc()))
    return list(result.scalars().all())


async def create_tracked_item(session, payload: TrackedItemCreate) -> TrackedItem:
    item = TrackedItem(
        label=payload.label,
        kind=payload.kind,
        enabled=payload.enabled,
        boost_weight=payload.boost_weight,
        notes=payload.notes,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_tracked_item(session, item_id, payload: TrackedItemUpdate) -> TrackedItem | None:
    item = await session.get(TrackedItem, item_id)
    if item is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_tracked_item(session, item_id) -> bool:
    item = await session.get(TrackedItem, item_id)
    if item is None:
        return False
    await session.delete(item)
    await session.commit()
    return True
