"""Seed default Austin user profile if none exists."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


async def seed():
    from sqlalchemy import select
    from src.models.database import create_engine, create_session_factory
    from src.models.user import UserProfile
    from src.config.settings import Settings

    settings = Settings()
    engine = create_engine(settings)
    Session = create_session_factory(engine)

    async with Session() as session:
        result = await session.execute(select(UserProfile).limit(1))
        if result.scalar_one_or_none() is not None:
            print("Users already exist, skipping seed.")
            return

        user = UserProfile(
            email=settings.from_email,
            city="austin",
            adults=[{"age": 35}, {"age": 35}],
            children=[{"age": 5}, {"age": 8}],
            interests=["music", "outdoor", "festivals", "kids", "arts", "seasonal"],
            preferred_neighborhoods=["South Austin", "Zilker", "East Austin", "Downtown"],
            preferred_days=["saturday", "sunday"],
            budget="moderate",
            max_distance_miles=30,
        )
        session.add(user)
        await session.commit()
        print(f"Seeded default user: {user.email}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
