# City Family Events Curator - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-credible MVP that ingests Austin events from 4 real sources, deduplicates them, ranks with AI, and sends polished email digests twice per week.

**Architecture:** Pipeline-oriented FastAPI monolith with APScheduler, Postgres, Claude Haiku LLM, Resend email. Two Docker containers (app + db).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, APScheduler, Playwright, httpx, BeautifulSoup4, Anthropic SDK, Resend SDK, Pydantic v2, Jinja2, Docker.

**Design doc:** `docs/plans/2026-03-07-city-family-events-curator-design.md`

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/main.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/config/__init__.py`
- Create: `src/config/settings.py`
- Create: `src/config/cities/austin.yaml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "austin-event-tracker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.28.0",
    "beautifulsoup4>=4.12.0",
    "playwright>=1.49.0",
    "anthropic>=0.42.0",
    "resend>=2.0.0",
    "apscheduler>=3.11.0",
    "jinja2>=3.1.0",
    "python-Levenshtein>=0.26.0",
    "pyyaml>=6.0",
    "structlog>=24.4.0",
    "itsdangerous>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "factory-boy>=3.3.0",
    "aiosqlite>=0.21.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

**Step 2: Create .env.example**

```env
DATABASE_URL=postgresql+asyncpg://events:events@localhost:5432/events
ANTHROPIC_API_KEY=sk-ant-...
RESEND_API_KEY=re_...
EVENTBRITE_API_KEY=...
BANDSINTOWN_APP_ID=...
ADMIN_API_KEY=changeme
DEFAULT_CITY=austin
DIGEST_SCHEDULE_DAYS=tue,fri
DIGEST_HOUR=8
FROM_EMAIL=events@yourdomain.com
BASE_URL=http://localhost:8000
FEEDBACK_SECRET=changeme-to-random-string
LOG_LEVEL=INFO
```

**Step 3: Create .gitignore**

Standard Python gitignore + `.env`, `__pycache__`, `.venv`, `*.pyc`, `.ruff_cache`.

**Step 4: Create config/settings.py with Pydantic Settings**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    resend_api_key: str
    eventbrite_api_key: str = ""
    bandsintown_app_id: str = ""
    admin_api_key: str = "changeme"
    default_city: str = "austin"
    digest_schedule_days: str = "tue,fri"
    digest_hour: int = 8
    from_email: str = "events@localhost"
    base_url: str = "http://localhost:8000"
    feedback_secret: str = "changeme"
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}
```

**Step 5: Create city config loader + austin.yaml**

`src/config/city.py`:
```python
from pydantic import BaseModel
import yaml
from pathlib import Path

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
```

`src/config/cities/austin.yaml`:
```yaml
name: austin
display_name: "Austin, TX"
state: TX
timezone: America/Chicago
latitude: 30.2672
longitude: -97.7431
radius_miles: 30
neighborhoods:
  - Downtown
  - South Austin
  - East Austin
  - North Austin
  - West Austin
  - South Congress
  - Zilker
  - Mueller
  - Domain
  - Cedar Park
  - Round Rock
  - Pflugerville
  - Bee Cave
  - Lakeway
default_sources:
  - eventbrite
  - bandsintown
  - do512
  - austin_chronicle
```

**Step 6: Create minimal FastAPI app in src/main.py**

```python
from fastapi import FastAPI
from src.config.settings import Settings

settings = Settings()
app = FastAPI(title="City Family Events Curator")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 7: Create all __init__.py files for package structure**

Create empty `__init__.py` in: `src/`, `src/config/`, `src/sources/`, `src/ingestion/`, `src/models/`, `src/schemas/`, `src/dedupe/`, `src/ranking/`, `src/llm/`, `src/digest/`, `src/notifications/`, `src/api/`, `src/jobs/`, `tests/`.

**Step 8: Create tests/conftest.py with basic fixtures**

```python
import pytest
from pathlib import Path

@pytest.fixture
def austin_config():
    from src.config.city import load_city_config
    return load_city_config("austin")

@pytest.fixture
def settings():
    from src.config.settings import Settings
    return Settings(
        database_url="sqlite+aiosqlite:///test.db",
        anthropic_api_key="test-key",
        resend_api_key="test-key",
    )
```

**Step 9: Write test for city config loading**

`tests/test_config.py`:
```python
def test_load_austin_config(austin_config):
    assert austin_config.name == "austin"
    assert austin_config.timezone == "America/Chicago"
    assert "Downtown" in austin_config.neighborhoods
    assert "eventbrite" in austin_config.default_sources
```

**Step 10: Run test, verify pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with config, settings, and city loader"
```

---

## Task 2: Database Models + Migrations

**Files:**
- Create: `src/models/base.py`
- Create: `src/models/event.py`
- Create: `src/models/user.py`
- Create: `src/models/digest.py`
- Create: `src/models/feedback.py`
- Create: `src/models/source_health.py`
- Create: `src/models/database.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Test: `tests/test_models.py`

**Step 1: Write test for model imports and table names**

`tests/test_models.py`:
```python
def test_event_model_has_required_columns():
    from src.models.event import Event
    cols = {c.name for c in Event.__table__.columns}
    required = {"id", "title", "start_datetime", "city", "category", "canonical_event_url"}
    assert required.issubset(cols)

def test_event_source_model():
    from src.models.event import EventSource
    cols = {c.name for c in EventSource.__table__.columns}
    assert "raw_payload" in cols
    assert "source_name" in cols

def test_user_profile_model():
    from src.models.user import UserProfile
    cols = {c.name for c in UserProfile.__table__.columns}
    assert "email" in cols
    assert "interests" in cols

def test_digest_model():
    from src.models.digest import Digest
    cols = {c.name for c in Digest.__table__.columns}
    assert "html_content" in cols
    assert "status" in cols

def test_feedback_model():
    from src.models.feedback import Feedback
    cols = {c.name for c in Feedback.__table__.columns}
    assert "feedback_type" in cols

def test_source_health_model():
    from src.models.source_health import SourceHealth
    cols = {c.name for c in SourceHealth.__table__.columns}
    assert "source_name" in cols
    assert "status" in cols
```

**Step 2: Run tests, verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL (modules don't exist yet)

**Step 3: Create src/models/base.py with SQLAlchemy base + enums**

```python
import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class EventCategory(str, enum.Enum):
    MUSIC = "music"
    ARTS = "arts"
    FESTIVALS = "festivals"
    THEATRE = "theatre"
    KIDS = "kids"
    OUTDOOR = "outdoor"
    SEASONAL = "seasonal"
    COMMUNITY = "community"

class SourceType(str, enum.Enum):
    API = "api"
    FEED = "feed"
    SCRAPER = "scraper"

class BudgetLevel(str, enum.Enum):
    FREE = "free"
    LOW = "low"
    MODERATE = "moderate"
    ANY = "any"

class CrowdSensitivity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class FeedbackType(str, enum.Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    MORE_LIKE_THIS = "more_like_this"
    LESS_LIKE_THIS = "less_like_this"
    TOO_FAR = "too_far"
    TOO_EXPENSIVE = "too_expensive"
    WRONG_AGE = "wrong_age"
    ALREADY_KNEW = "already_knew"

class DigestStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"

class SourceHealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"
```

**Step 4: Create src/models/event.py**

```python
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Float, Numeric, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin, EventCategory, SourceType

class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[EventCategory] = mapped_column(Enum(EventCategory), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100))
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(50), default="America/Chicago")
    venue_name: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    age_suitability: Mapped[str | None] = mapped_column(String(50))
    family_score: Mapped[float | None] = mapped_column(Float)
    image_url: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    dedupe_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    canonical_event_url: Mapped[str | None] = mapped_column(Text)
    editorial_summary: Mapped[str | None] = mapped_column(Text)
    relevance_explanation: Mapped[str | None] = mapped_column(Text)

    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")

class EventSource(Base):
    __tablename__ = "event_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"))
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    title: Mapped[str | None] = mapped_column(Text)
    start_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue_name: Mapped[str | None] = mapped_column(String(255))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped[Event | None] = relationship(back_populates="sources")
```

Note: import `func` from sqlalchemy at top: `from sqlalchemy import ..., func` and add `DateTime` import to the `from sqlalchemy` line as well.

**Step 5: Create src/models/user.py**

```python
import uuid
from sqlalchemy import String, Text, Integer, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, TimestampMixin, BudgetLevel, CrowdSensitivity

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="austin")
    adults: Mapped[dict | None] = mapped_column(JSONB)
    children: Mapped[dict | None] = mapped_column(JSONB)
    preferred_neighborhoods: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_distance_miles: Mapped[int] = mapped_column(Integer, default=30)
    preferred_days: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    preferred_times: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    budget: Mapped[BudgetLevel] = mapped_column(Enum(BudgetLevel), default=BudgetLevel.MODERATE)
    interests: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    dislikes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_events_per_digest: Mapped[int] = mapped_column(Integer, default=15)
    crowd_sensitivity: Mapped[CrowdSensitivity] = mapped_column(
        Enum(CrowdSensitivity), default=CrowdSensitivity.MEDIUM
    )
```

**Step 6: Create src/models/digest.py**

```python
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Date, Enum, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, DigestStatus, DateTime
from sqlalchemy import DateTime as SADateTime, func

class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    subject: Mapped[str] = mapped_column(Text)
    html_content: Mapped[str] = mapped_column(Text)
    plaintext_content: Mapped[str] = mapped_column(Text)
    event_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    sent_at: Mapped[datetime | None] = mapped_column(SADateTime(timezone=True))
    status: Mapped[DigestStatus] = mapped_column(Enum(DigestStatus), default=DigestStatus.DRAFT)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(SADateTime(timezone=True), server_default=func.now())
```

**Step 7: Create src/models/feedback.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Enum, ForeignKey, func
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, FeedbackType

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"))
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(SADateTime(timezone=True), server_default=func.now())
```

**Step 8: Create src/models/source_health.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Enum, func
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, SourceHealthStatus

class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_run_at: Mapped[datetime] = mapped_column(SADateTime(timezone=True), server_default=func.now())
    last_success_at: Mapped[datetime | None] = mapped_column(SADateTime(timezone=True))
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SourceHealthStatus] = mapped_column(
        Enum(SourceHealthStatus), default=SourceHealthStatus.HEALTHY
    )
```

**Step 9: Create src/models/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config.settings import Settings

def create_engine(settings: Settings):
    return create_async_engine(settings.database_url, echo=False)

def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

**Step 10: Create src/models/__init__.py exporting all models**

```python
from src.models.base import Base
from src.models.event import Event, EventSource
from src.models.user import UserProfile
from src.models.digest import Digest
from src.models.feedback import Feedback
from src.models.source_health import SourceHealth

__all__ = ["Base", "Event", "EventSource", "UserProfile", "Digest", "Feedback", "SourceHealth"]
```

**Step 11: Run tests, verify pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 12: Set up Alembic**

Run: `alembic init migrations`

Then edit `alembic.ini` to set `sqlalchemy.url` placeholder, and edit `migrations/env.py` to import the models and read DATABASE_URL from settings. Use the synchronous version of the URL for Alembic (replace `asyncpg` with `psycopg2` or use `postgresql://`).

The `migrations/env.py` must import `from src.models import Base` and set `target_metadata = Base.metadata`.

**Step 13: Commit**

```bash
git add -A
git commit -m "feat: database models for events, users, digests, feedback, source health"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `src/schemas/event.py`
- Create: `src/schemas/user.py`
- Create: `src/schemas/source.py`
- Test: `tests/test_schemas.py`

**Step 1: Write test for RawEvent schema**

`tests/test_schemas.py`:
```python
from datetime import datetime, timezone

def test_raw_event_schema():
    from src.schemas.event import RawEvent
    raw = RawEvent(
        source_name="eventbrite",
        source_type="api",
        source_url="https://example.com/event/1",
        title="Test Event",
        start_datetime=datetime.now(timezone.utc),
        venue_name="Test Venue",
        city="austin",
    )
    assert raw.title == "Test Event"
    assert raw.source_name == "eventbrite"

def test_normalized_event_schema():
    from src.schemas.event import NormalizedEvent
    event = NormalizedEvent(
        title="Test Event",
        category="music",
        start_datetime=datetime.now(timezone.utc),
        city="austin",
    )
    assert event.category == "music"

def test_user_profile_schema():
    from src.schemas.user import UserProfileSchema
    profile = UserProfileSchema(
        email="test@example.com",
        city="austin",
        interests=["music", "outdoor"],
    )
    assert profile.email == "test@example.com"
```

**Step 2: Run tests, verify fail**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL

**Step 3: Create src/schemas/event.py**

```python
import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class RawEvent(BaseModel):
    source_name: str
    source_type: str
    source_url: str | None = None
    title: str
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    venue_name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    city: str
    latitude: float | None = None
    longitude: float | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str = "USD"
    age_suitability: str | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    canonical_event_url: str | None = None
    raw_payload: dict | None = None

class NormalizedEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    description: str | None = None
    category: str
    subcategory: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    timezone: str = "America/Chicago"
    venue_name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    city: str
    latitude: float | None = None
    longitude: float | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str = "USD"
    age_suitability: str | None = None
    family_score: float | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    canonical_event_url: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
```

**Step 4: Create src/schemas/user.py**

```python
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
```

**Step 5: Create src/schemas/source.py**

```python
from pydantic import BaseModel

class SourceHealthSchema(BaseModel):
    source_name: str
    status: str
    events_found: int = 0
    errors: str | None = None
```

**Step 6: Run tests, verify pass**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: pydantic schemas for events, users, and sources"
```

---

## Task 4: Source Adapter Interface + Registry

**Files:**
- Create: `src/sources/base.py`
- Create: `src/sources/registry.py`
- Test: `tests/test_sources_base.py`

**Step 1: Write test for adapter interface and registry**

`tests/test_sources_base.py`:
```python
from datetime import datetime, timezone
from src.schemas.event import RawEvent

def test_source_adapter_interface():
    from src.sources.base import SourceAdapter, SourceType
    # Verify abstract class can't be instantiated
    import pytest
    with pytest.raises(TypeError):
        SourceAdapter()

def test_source_registry():
    from src.sources.registry import SourceRegistry
    from src.sources.base import SourceAdapter, SourceType
    from src.config.city import CityConfig

    class FakeSource(SourceAdapter):
        name = "fake"
        source_type = SourceType.API
        async def fetch_events(self, city_config):
            return []

    registry = SourceRegistry()
    registry.register(FakeSource())
    assert "fake" in registry.list_sources()
    assert registry.get("fake").name == "fake"
```

**Step 2: Run test, verify fail**

Run: `pytest tests/test_sources_base.py -v`
Expected: FAIL

**Step 3: Create src/sources/base.py**

```python
from abc import ABC, abstractmethod
from src.models.base import SourceType
from src.schemas.event import RawEvent

class SourceAdapter(ABC):
    name: str
    source_type: SourceType

    @abstractmethod
    async def fetch_events(self, city_config) -> list[RawEvent]:
        ...

    def is_enabled(self) -> bool:
        return True

    def rate_limit_delay(self) -> float:
        return 1.0
```

**Step 4: Create src/sources/registry.py**

```python
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
```

**Step 5: Run tests, verify pass**

Run: `pytest tests/test_sources_base.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: source adapter interface and registry"
```

---

## Task 5: Eventbrite Adapter

**Files:**
- Create: `src/sources/eventbrite.py`
- Test: `tests/test_source_eventbrite.py`

**Step 1: Write test with mocked HTTP response**

`tests/test_source_eventbrite.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from src.sources.eventbrite import EventbriteAdapter

SAMPLE_RESPONSE = {
    "events": [
        {
            "id": "123",
            "name": {"text": "Austin Music Festival"},
            "description": {"text": "A great music festival"},
            "start": {"utc": "2026-03-15T15:00:00Z", "timezone": "America/Chicago"},
            "end": {"utc": "2026-03-15T22:00:00Z", "timezone": "America/Chicago"},
            "venue": {
                "name": "Zilker Park",
                "address": {"localized_address_display": "2100 Barton Springs Rd, Austin, TX"},
                "latitude": "30.2669",
                "longitude": "-97.7725",
            },
            "url": "https://www.eventbrite.com/e/123",
            "logo": {"url": "https://img.example.com/logo.jpg"},
            "is_free": False,
            "ticket_availability": {
                "minimum_ticket_price": {"major_value": "25.00"},
                "maximum_ticket_price": {"major_value": "75.00"},
            },
            "category_id": "103",
            "subcategory_id": None,
        }
    ],
    "pagination": {"has_more_items": False},
}

@pytest.fixture
def adapter():
    return EventbriteAdapter(api_key="test-key")

@pytest.fixture
def austin_config():
    from src.config.city import load_city_config
    return load_city_config("austin")

@pytest.mark.asyncio
async def test_eventbrite_parses_events(adapter, austin_config):
    mock_response = AsyncMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    assert len(events) == 1
    assert events[0].title == "Austin Music Festival"
    assert events[0].venue_name == "Zilker Park"
    assert events[0].source_name == "eventbrite"
    assert events[0].price_min == 25.00
    assert events[0].canonical_event_url == "https://www.eventbrite.com/e/123"
```

**Step 2: Run test, verify fail**

Run: `pytest tests/test_source_eventbrite.py -v`
Expected: FAIL

**Step 3: Implement src/sources/eventbrite.py**

Build the adapter that:
- Uses httpx to call Eventbrite's `/v3/events/search/` endpoint with Austin location params
- Parses the response into `RawEvent` list
- Handles pagination (follow `has_more_items`)
- Maps Eventbrite category IDs to our EventCategory enum
- Extracts price from ticket_availability
- Sets `source_name = "eventbrite"`, `source_type = SourceType.API`
- Stores full response in `raw_payload`

Key Eventbrite category ID mapping (partial):
- 103 = Music
- 105 = Performing & Visual Arts
- 110 = Food & Drink
- 113 = Community & Culture
- 115 = Family & Education

**Step 4: Run test, verify pass**

Run: `pytest tests/test_source_eventbrite.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: eventbrite source adapter with API parsing"
```

---

## Task 6: Bandsintown Adapter

**Files:**
- Create: `src/sources/bandsintown.py`
- Test: `tests/test_source_bandsintown.py`

**Step 1: Write test with mocked HTTP response**

`tests/test_source_bandsintown.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from src.sources.bandsintown import BandsintownAdapter

SAMPLE_RESPONSE = [
    {
        "id": "456",
        "artist": {"name": "Khruangbin"},
        "venue": {
            "name": "ACL Live at The Moody Theater",
            "city": "Austin",
            "region": "TX",
            "country": "United States",
            "latitude": "30.2651",
            "longitude": "-97.7467",
            "location": "Austin, TX",
        },
        "datetime": "2026-03-20T20:00:00",
        "url": "https://www.bandsintown.com/e/456",
        "offers": [{"url": "https://tickets.example.com", "status": "available"}],
        "title": "Khruangbin at ACL Live",
        "description": "Live concert",
    }
]

@pytest.fixture
def adapter():
    return BandsintownAdapter(app_id="test-app")

@pytest.fixture
def austin_config():
    from src.config.city import load_city_config
    return load_city_config("austin")

@pytest.mark.asyncio
async def test_bandsintown_parses_events(adapter, austin_config):
    mock_response = AsyncMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    assert len(events) == 1
    assert events[0].title == "Khruangbin at ACL Live"
    assert events[0].venue_name == "ACL Live at The Moody Theater"
    assert events[0].source_name == "bandsintown"
    assert events[0].city == "austin"
```

**Step 2: Run test, verify fail**

**Step 3: Implement src/sources/bandsintown.py**

Bandsintown API: query `/v3/events/search` or use location-based endpoint with Austin coordinates. All events from Bandsintown are `category = "music"`. Parse artist name, venue, datetime, URL, offers.

**Step 4: Run test, verify pass**

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: bandsintown source adapter for music events"
```

---

## Task 7: Austin Chronicle Scraper

**Files:**
- Create: `src/sources/austin_chronicle.py`
- Test: `tests/test_source_chronicle.py`
- Create: `tests/fixtures/chronicle_sample.html`

**Step 1: Create a sample HTML fixture**

Save a representative snippet of an Austin Chronicle events listing page to `tests/fixtures/chronicle_sample.html`. This should contain 2-3 sample event listings with title, date, venue, description, URL in the structure the real page uses.

**Step 2: Write test that parses the fixture**

`tests/test_source_chronicle.py`:
```python
import pytest
from pathlib import Path
from src.sources.austin_chronicle import AustinChronicleAdapter

@pytest.fixture
def sample_html():
    return (Path(__file__).parent / "fixtures" / "chronicle_sample.html").read_text()

@pytest.fixture
def adapter():
    return AustinChronicleAdapter()

def test_chronicle_parses_html(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert len(events) >= 1
    assert events[0].title
    assert events[0].source_name == "austin_chronicle"
    assert events[0].source_type == "scraper"
```

**Step 3: Run test, verify fail**

**Step 4: Implement src/sources/austin_chronicle.py**

Uses httpx + BeautifulSoup to:
- Fetch the Austin Chronicle events calendar page
- Parse event listings from HTML
- Extract title, date/time, venue, description, URL, category
- Return as `RawEvent` list
- Separate `parse_listings(html)` method for testability
- Check robots.txt compliance
- Set appropriate rate limiting (2s delay)

**Step 5: Run test, verify pass**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: austin chronicle scraper adapter"
```

---

## Task 8: Do512 Scraper

**Files:**
- Create: `src/sources/do512.py`
- Test: `tests/test_source_do512.py`
- Create: `tests/fixtures/do512_sample.html`

**Step 1: Create sample HTML fixture of Do512 event listings**

**Step 2: Write test**

`tests/test_source_do512.py`:
```python
import pytest
from pathlib import Path
from src.sources.do512 import Do512Adapter

@pytest.fixture
def sample_html():
    return (Path(__file__).parent / "fixtures" / "do512_sample.html").read_text()

@pytest.fixture
def adapter():
    return Do512Adapter()

def test_do512_parses_html(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert len(events) >= 1
    assert events[0].title
    assert events[0].source_name == "do512"
```

**Step 3: Run test, verify fail**

**Step 4: Implement src/sources/do512.py**

Uses Playwright for JS-rendered content:
- Launch headless browser
- Navigate to Do512 events page
- Wait for event listings to render
- Extract event data from DOM
- Separate `parse_listings(html)` for unit testing against fixture
- For the actual `fetch_events`, use Playwright to get rendered HTML, then call `parse_listings`
- Set rate limiting (3s delay, respectful of the site)

**Step 5: Run test, verify pass**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: do512 scraper adapter with playwright"
```

---

## Task 9: Instagram Stub

**Files:**
- Create: `src/sources/instagram.py`
- Test: `tests/test_source_instagram.py`

**Step 1: Write test**

```python
from src.sources.instagram import InstagramAdapter

def test_instagram_is_stub():
    adapter = InstagramAdapter()
    assert adapter.name == "instagram"
    assert adapter.is_enabled() is False
```

**Step 2: Implement stub**

```python
from src.sources.base import SourceAdapter, SourceType
from src.schemas.event import RawEvent

class InstagramAdapter(SourceAdapter):
    name = "instagram"
    source_type = SourceType.SCRAPER

    async def fetch_events(self, city_config) -> list[RawEvent]:
        # TODO: Instagram API is locked down. Options:
        # 1. Use Apify or similar third-party scraping service
        # 2. Monitor specific venue/promoter accounts via Graph API (requires business account)
        # 3. Use unofficial API (compliance risk)
        raise NotImplementedError("Instagram adapter not yet implemented")

    def is_enabled(self) -> bool:
        return False
```

**Step 3: Run test, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: instagram source adapter stub"
```

---

## Task 10: Ingestion Pipeline

**Files:**
- Create: `src/ingestion/pipeline.py`
- Create: `src/ingestion/normalizer.py`
- Test: `tests/test_ingestion.py`

**Step 1: Write test for normalizer**

`tests/test_ingestion.py`:
```python
import pytest
from datetime import datetime, timezone
from src.schemas.event import RawEvent
from src.ingestion.normalizer import normalize_raw_event

def test_normalize_raw_event():
    raw = RawEvent(
        source_name="eventbrite",
        source_type="api",
        title="  Test Event  ",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        venue_name="zilker park",
        city="Austin",
        canonical_event_url="https://example.com/event/1",
        tags=["music", "outdoor"],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.title == "Test Event"  # trimmed
    assert normalized.city == "austin"  # lowercased
    assert normalized.venue_name == "Zilker Park"  # title-cased
    assert normalized.source_name == "eventbrite"
```

**Step 2: Write test for pipeline orchestration**

```python
@pytest.mark.asyncio
async def test_ingestion_pipeline_runs_enabled_sources():
    from src.sources.registry import SourceRegistry
    from src.sources.base import SourceAdapter, SourceType
    from src.ingestion.pipeline import IngestionPipeline

    class FakeSource(SourceAdapter):
        name = "fake"
        source_type = SourceType.API
        async def fetch_events(self, city_config):
            return [RawEvent(
                source_name="fake",
                source_type="api",
                title="Fake Event",
                start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
                city="austin",
            )]

    registry = SourceRegistry()
    registry.register(FakeSource())

    from src.config.city import load_city_config
    city_config = load_city_config("austin")
    pipeline = IngestionPipeline(registry=registry, db_session=None)
    results = await pipeline.ingest(city_config, persist=False)
    assert len(results) == 1
    assert results[0].title == "Fake Event"
```

**Step 3: Run tests, verify fail**

**Step 4: Implement src/ingestion/normalizer.py**

Normalizes: strip whitespace from title, lowercase city, title-case venue name, carry forward all fields, assign default category if missing.

**Step 5: Implement src/ingestion/pipeline.py**

```python
class IngestionPipeline:
    def __init__(self, registry, db_session):
        self.registry = registry
        self.db_session = db_session

    async def ingest(self, city_config, persist=True) -> list[NormalizedEvent]:
        all_events = []
        for source in self.registry.get_enabled():
            try:
                raw_events = await source.fetch_events(city_config)
                normalized = [normalize_raw_event(e) for e in raw_events]
                all_events.extend(normalized)
                # Update source health: success
            except Exception as e:
                # Log error, update source health: failing
                structlog.get_logger().error("source_failed", source=source.name, error=str(e))
        if persist and self.db_session:
            await self._persist_events(all_events)
        return all_events
```

**Step 6: Run tests, verify pass**

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: ingestion pipeline with normalizer"
```

---

## Task 11: Deduplication Engine

**Files:**
- Create: `src/dedupe/engine.py`
- Create: `src/dedupe/similarity.py`
- Test: `tests/test_dedupe.py`

**Step 1: Write test for exact match dedup**

`tests/test_dedupe.py`:
```python
import pytest
from datetime import datetime, timezone
from src.schemas.event import NormalizedEvent
from src.dedupe.engine import DedupeEngine

def make_event(**kwargs):
    defaults = dict(
        title="Test Event",
        category="music",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        venue_name="Zilker Park",
        canonical_event_url="https://example.com/event/1",
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)

def test_exact_url_dedup():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(canonical_event_url="https://example.com/e/1", source_name="eventbrite"),
        make_event(canonical_event_url="https://example.com/e/1", source_name="do512"),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1

def test_exact_title_venue_date_dedup():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(title="SXSW 2026", venue_name="Convention Center",
                   start_datetime=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
                   canonical_event_url="https://a.com/1"),
        make_event(title="SXSW 2026", venue_name="Convention Center",
                   start_datetime=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
                   canonical_event_url="https://b.com/2"),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1

def test_different_events_not_deduped():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(title="Jazz Night", venue_name="Continental Club",
                   canonical_event_url="https://a.com/1"),
        make_event(title="Rock Show", venue_name="Mohawk",
                   canonical_event_url="https://b.com/2"),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 2
```

**Step 2: Write test for fuzzy match**

```python
def test_fuzzy_title_dedup():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(title="Austin City Limits Music Festival 2026",
                   venue_name="Zilker Park",
                   canonical_event_url="https://a.com/1"),
        make_event(title="ACL Music Festival 2026",
                   venue_name="Zilker Park",
                   canonical_event_url="https://b.com/2"),
    ]
    # These should be caught by fuzzy matching (same venue, same date, similar title)
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1
```

**Step 3: Run tests, verify fail**

**Step 4: Implement src/dedupe/similarity.py**

```python
from Levenshtein import ratio as levenshtein_ratio

def title_similarity(a: str, b: str) -> float:
    return levenshtein_ratio(a.lower().strip(), b.lower().strip())

def venue_similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return levenshtein_ratio(a.lower().strip(), b.lower().strip())

def datetime_proximity(a, b) -> float:
    diff_hours = abs((a - b).total_seconds()) / 3600
    if diff_hours <= 2:
        return 1.0
    elif diff_hours <= 6:
        return 0.5
    return 0.0

def combined_similarity(event_a, event_b) -> float:
    title_sim = title_similarity(event_a.title, event_b.title)
    venue_sim = venue_similarity(event_a.venue_name, event_b.venue_name)
    time_sim = datetime_proximity(event_a.start_datetime, event_b.start_datetime)
    return 0.5 * title_sim + 0.3 * venue_sim + 0.2 * time_sim
```

**Step 5: Implement src/dedupe/engine.py**

Three-pass strategy:
1. Exact match on URL, then on (normalized title + venue + date)
2. Fuzzy match: for remaining, compute `combined_similarity`. Merge if > 0.8.
3. LLM tiebreaker for 0.6-0.8 range (if llm_client provided, else skip)

On merge: keep the event with more populated fields, assign shared `dedupe_group_id`.

**Step 6: Run tests, verify pass**

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: deduplication engine with exact, fuzzy, and LLM tiebreaker"
```

---

## Task 12: LLM Abstraction Layer

**Files:**
- Create: `src/llm/base.py`
- Create: `src/llm/anthropic.py`
- Test: `tests/test_llm.py`

**Step 1: Write test for LLM interface and Anthropic implementation**

`tests/test_llm.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

def test_llm_interface():
    from src.llm.base import LLMClient
    with pytest.raises(TypeError):
        LLMClient()

@pytest.mark.asyncio
async def test_anthropic_client_calls_api():
    from src.llm.anthropic import AnthropicLLMClient

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"category": "music", "family_score": 0.8}')]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    client = AnthropicLLMClient(api_key="test-key")
    client._client = mock_client

    result = await client.complete("Classify this event", system="You are a classifier")
    assert "music" in result
```

**Step 2: Run tests, verify fail**

**Step 3: Implement src/llm/base.py**

```python
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        ...

    @abstractmethod
    async def complete_json(self, prompt: str, system: str | None = None) -> dict:
        ...
```

**Step 4: Implement src/llm/anthropic.py**

```python
import json
import anthropic
from src.llm.base import LLMClient

class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        kwargs = {"model": self.model, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        response = await self._client.messages.create(**kwargs)
        return response.content[0].text

    async def complete_json(self, prompt: str, system: str | None = None) -> dict:
        text = await self.complete(prompt, system=system, json_mode=True)
        return json.loads(text)
```

**Step 5: Run tests, verify pass**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: LLM abstraction with anthropic implementation"
```

---

## Task 13: Ranking Engine

**Files:**
- Create: `src/ranking/rules.py`
- Create: `src/ranking/feedback.py`
- Create: `src/ranking/engine.py`
- Test: `tests/test_ranking.py`

**Step 1: Write test for rule-based scoring**

`tests/test_ranking.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema
from src.ranking.rules import compute_rule_score

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
        title="Test Event", category="music",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)

def test_matching_interest_scores_high(user_profile):
    event = make_event(category="music", neighborhood="Zilker")
    score = compute_rule_score(event, user_profile)
    assert score > 0.6

def test_disliked_category_scores_low(user_profile):
    event = make_event(category="theatre")
    score = compute_rule_score(event, user_profile)
    assert score < 0.4

def test_free_event_scores_well_for_budget_user(user_profile):
    event = make_event(price_min=0, price_max=0)
    score = compute_rule_score(event, user_profile)
    assert score > 0.5
```

**Step 2: Write test for feedback adjustment**

```python
from src.ranking.feedback import adjust_score_for_feedback
from src.models.base import FeedbackType

def test_thumbs_up_boosts_similar():
    feedback_history = [
        {"event_category": "music", "event_neighborhood": "Zilker", "feedback_type": FeedbackType.THUMBS_UP},
    ]
    event = make_event(category="music", neighborhood="Zilker")
    adjusted = adjust_score_for_feedback(0.5, event, feedback_history)
    assert adjusted > 0.5

def test_too_far_penalizes_distant():
    feedback_history = [
        {"event_category": "music", "event_neighborhood": "Cedar Park", "feedback_type": FeedbackType.TOO_FAR},
    ]
    event = make_event(category="music", neighborhood="Cedar Park")
    adjusted = adjust_score_for_feedback(0.5, event, feedback_history)
    assert adjusted < 0.5
```

**Step 3: Run tests, verify fail**

**Step 4: Implement src/ranking/rules.py**

Scoring sub-components (each 0-1, weighted and combined):
- `category_score`: 1.0 if in interests, 0.0 if in dislikes, 0.5 otherwise
- `day_score`: 1.0 if event day matches preferred_days, 0.3 otherwise
- `time_score`: 1.0 if event time matches preferred_times, 0.3 otherwise
- `neighborhood_score`: 1.0 if in preferred_neighborhoods, 0.5 otherwise
- `budget_score`: based on price vs budget level
- `recency_score`: events sooner get mild boost (1.0 for this week, 0.7 for next, 0.5 for 2+ weeks)

`compute_rule_score` = weighted average of all sub-scores.

**Step 5: Implement src/ranking/feedback.py**

Simple lookup: for each past feedback item, if category/neighborhood/venue matches the current event, apply a boost or penalty. Recent feedback weighted 2x compared to older (> 30 days).

**Step 6: Implement src/ranking/engine.py**

```python
class RankingEngine:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def rank_events(self, events, user_profile, feedback_history=None) -> list[tuple[NormalizedEvent, float]]:
        scored = []
        for event in events:
            rule_score = compute_rule_score(event, user_profile)
            fb_score = adjust_score_for_feedback(rule_score, event, feedback_history or [])
            llm_score = event.family_score or 0.5
            final = 0.5 * rule_score + 0.2 * fb_score + 0.3 * llm_score
            scored.append((event, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
```

**Step 7: Run tests, verify pass**

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: ranking engine with rule-based scoring and feedback adjustment"
```

---

## Task 14: LLM Synthesis Module

**Files:**
- Create: `src/llm/synthesis.py`
- Test: `tests/test_synthesis.py`

**Step 1: Write test for event synthesis**

`tests/test_synthesis.py`:
```python
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema
from src.llm.synthesis import EventSynthesizer

def make_event(**kwargs):
    defaults = dict(
        title="Test Event", category="music",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin", venue_name="Zilker Park",
        description="A fun outdoor music festival for all ages",
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)

@pytest.mark.asyncio
async def test_synthesizer_enriches_events():
    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "events": [
            {
                "index": 0,
                "family_score": 0.9,
                "editorial_summary": "A wonderful outdoor music festival perfect for families.",
                "relevance_explanation": "Great for your kids aged 5 and 8, free admission, in your favorite neighborhood.",
                "age_suitability": "all ages",
            }
        ]
    }

    profile = UserProfileSchema(email="test@example.com", interests=["music", "outdoor"])
    synthesizer = EventSynthesizer(llm_client=mock_llm)
    events = [make_event()]
    enriched = await synthesizer.enrich_events(events, profile)

    assert enriched[0].family_score == 0.9
    assert "wonderful" in enriched[0].editorial_summary
    assert enriched[0].age_suitability == "all ages"
```

**Step 2: Run test, verify fail**

**Step 3: Implement src/llm/synthesis.py**

```python
class EventSynthesizer:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def enrich_events(self, events, user_profile):
        # Build prompt with user profile + event batch
        # Ask LLM to return JSON array with family_score, editorial_summary,
        # relevance_explanation, age_suitability for each event
        # Parse response and merge into event objects
        # Cache results (set on the event objects directly)
```

System prompt instructs the LLM:
- You are scoring events for family relevance
- Never invent dates, venues, or prices
- Base all assessments on the provided data
- Return structured JSON matching the schema

User prompt includes:
- Family profile (ages, interests, neighborhoods, budget)
- Batch of events (title, description, venue, date, price, category)
- Request for family_score, editorial_summary, relevance_explanation, age_suitability

**Step 4: Run test, verify pass**

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: LLM synthesis module for event enrichment"
```

---

## Task 15: Digest Generator + Email Templates

**Files:**
- Create: `src/digest/generator.py`
- Create: `src/digest/sections.py`
- Create: `src/templates/email/digest.html`
- Create: `src/templates/email/digest.txt`
- Test: `tests/test_digest.py`

**Step 1: Write test for section grouping**

`tests/test_digest.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from src.schemas.event import NormalizedEvent
from src.digest.sections import group_events_into_sections

def make_event(title, category="music", family_score=0.7, price_max=None,
               days_from_now=3, **kwargs):
    return NormalizedEvent(
        title=title, category=category,
        start_datetime=datetime.now(timezone.utc) + timedelta(days=days_from_now),
        city="austin", family_score=family_score,
        price_max=price_max,
        **kwargs,
    )

def test_group_events_creates_sections():
    events_with_scores = [
        (make_event("Top Event", family_score=0.95), 0.95),
        (make_event("Kids Fest", category="kids", family_score=0.9), 0.9),
        (make_event("Jazz Night", category="music", family_score=0.3), 0.8),
        (make_event("Free Concert", price_max=0, family_score=0.6), 0.7),
        (make_event("Future Fest", days_from_now=14, family_score=0.8), 0.75),
    ]
    sections = group_events_into_sections(events_with_scores)
    assert "top_picks" in sections
    assert "kids_family" in sections
    assert "date_night" in sections
    assert len(sections["top_picks"]) <= 4
```

**Step 2: Write test for HTML rendering**

```python
def test_digest_renders_html():
    from src.digest.generator import DigestGenerator
    from jinja2 import Environment, FileSystemLoader

    events_with_scores = [
        (make_event("Test Event", venue_name="Zilker Park",
                    editorial_summary="A great event",
                    relevance_explanation="Perfect for your family"), 0.9),
    ]
    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test")
    html = generator.render_html(events_with_scores, window_start="Mar 8", window_end="Mar 22")
    assert "Test Event" in html
    assert "Zilker Park" in html
    assert "<html" in html.lower()
```

**Step 3: Run tests, verify fail**

**Step 4: Implement src/digest/sections.py**

Group events into sections based on score, family_score, price, and date proximity:
- `top_picks`: top 3-4 by final score
- `kids_family`: family_score > 0.7, sorted by score
- `date_night`: family_score < 0.5 OR category in (music, theatre, community), sorted by score
- `this_weekend`: start_datetime within 4 days
- `plan_ahead`: start_datetime > 7 days out, high score
- `free_cheap`: price_max <= 10 or price_max is None (free)

Deduplicate across sections (event appears in at most 2).

**Step 5: Create src/templates/email/digest.html**

Jinja2 HTML email template. Clean, mobile-first design:
- System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Muted color palette: warm grays, subtle accent color (#2563eb for links)
- Max-width 600px table layout (email compatible)
- Hero header with city name + date range
- Section headers
- Event cards: title, date, venue, neighborhood, price badge, editorial summary, "why for you" italic line, feedback thumbs up/down links, details link
- Footer with web view link

Feedback links format: `{{base_url}}/api/feedback/{{event.id}}?type=thumbs_up&token={{token}}`

**Step 6: Create src/templates/email/digest.txt**

Plaintext version with same content, clean formatting.

**Step 7: Implement src/digest/generator.py**

```python
class DigestGenerator:
    def __init__(self, base_url, feedback_secret):
        self.base_url = base_url
        self.feedback_secret = feedback_secret
        self.env = Environment(loader=FileSystemLoader("src/templates/email"))

    def render_html(self, events_with_scores, window_start, window_end) -> str:
        sections = group_events_into_sections(events_with_scores)
        template = self.env.get_template("digest.html")
        return template.render(sections=sections, window_start=window_start, window_end=window_end, ...)

    def render_plaintext(self, events_with_scores, window_start, window_end) -> str:
        ...

    def _generate_feedback_token(self, event_id, feedback_type) -> str:
        # Use itsdangerous to sign tokens for email feedback links
        ...
```

**Step 8: Run tests, verify pass**

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: digest generator with HTML/plaintext email templates"
```

---

## Task 16: Notification Delivery (Resend)

**Files:**
- Create: `src/notifications/base.py`
- Create: `src/notifications/email.py`
- Test: `tests/test_notifications.py`

**Step 1: Write test**

`tests/test_notifications.py`:
```python
import pytest
from unittest.mock import patch, MagicMock

def test_notification_channel_interface():
    from src.notifications.base import NotificationChannel
    with pytest.raises(TypeError):
        NotificationChannel()

@pytest.mark.asyncio
async def test_email_channel_sends():
    from src.notifications.email import EmailChannel

    channel = EmailChannel(api_key="test-key", from_email="test@example.com")
    with patch("resend.Emails.send", return_value={"id": "123"}) as mock_send:
        result = await channel.send(
            to="user@example.com",
            subject="Your Austin Events",
            html="<h1>Events</h1>",
            text="Events",
        )
    mock_send.assert_called_once()
    assert result == {"id": "123"}
```

**Step 2: Run test, verify fail**

**Step 3: Implement src/notifications/base.py**

```python
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, html: str, text: str) -> dict:
        ...

class PushChannel(NotificationChannel):
    """TODO: Implement push notifications.
    Interface ready for: FCM, APNs, or web push.
    Needs: device token registration, quiet hours config, urgency levels.
    """
    async def send(self, to, subject, html, text):
        raise NotImplementedError("Push notifications not yet implemented")
```

**Step 4: Implement src/notifications/email.py**

```python
import resend
from src.notifications.base import NotificationChannel

class EmailChannel(NotificationChannel):
    def __init__(self, api_key: str, from_email: str):
        resend.api_key = api_key
        self.from_email = from_email

    async def send(self, to, subject, html, text):
        return resend.Emails.send({
            "from": self.from_email,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        })
```

**Step 5: Run tests, verify pass**

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: notification channels with resend email implementation"
```

---

## Task 17: API Routes (Admin + Feedback + Web View)

**Files:**
- Create: `src/api/admin.py`
- Create: `src/api/feedback.py`
- Create: `src/api/digests.py`
- Create: `src/api/deps.py`
- Create: `src/templates/web/digest_view.html`
- Modify: `src/main.py`
- Test: `tests/test_api.py`

**Step 1: Write test for feedback endpoint**

`tests/test_api.py`:
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from src.main import app
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

def test_feedback_endpoint_validates_token(client):
    response = client.get("/api/feedback/some-event-id?type=thumbs_up&token=invalid")
    assert response.status_code in (400, 403)

def test_admin_requires_api_key(client):
    response = client.get("/admin/sources")
    assert response.status_code in (401, 403)

def test_admin_with_api_key(client):
    response = client.get("/admin/sources", headers={"X-API-Key": "changeme"})
    assert response.status_code == 200
```

**Step 2: Run tests, verify fail**

**Step 3: Implement src/api/deps.py**

```python
from fastapi import Header, HTTPException, Depends
from src.config.settings import Settings

def get_settings():
    return Settings()

def verify_admin_key(x_api_key: str = Header(...), settings: Settings = Depends(get_settings)):
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

**Step 4: Implement src/api/feedback.py**

```python
from fastapi import APIRouter, Query
from itsdangerous import URLSafeSerializer

router = APIRouter(prefix="/api/feedback")

@router.get("/{event_id}")
async def record_feedback(event_id: str, type: str = Query(...), token: str = Query(...)):
    # Validate token using itsdangerous
    # Record feedback to database
    # Return a simple "thank you" HTML page
```

**Step 5: Implement src/api/admin.py**

```python
from fastapi import APIRouter, Depends
from src.api.deps import verify_admin_key

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_admin_key)])

@router.get("/sources")
async def list_sources(): ...

@router.post("/sources/{name}/toggle")
async def toggle_source(name: str): ...

@router.post("/ingest")
async def trigger_ingest(): ...

@router.post("/digest/preview")
async def preview_digest(): ...

@router.post("/digest/send")
async def send_digest(): ...

@router.post("/digest/{digest_id}/resend")
async def resend_digest(digest_id: str): ...

@router.get("/events")
async def list_events(category: str | None = None, limit: int = 50): ...
```

**Step 6: Implement src/api/digests.py**

```python
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/digests/{digest_id}", response_class=HTMLResponse)
async def view_digest(digest_id: str):
    # Load digest from DB, return html_content
```

**Step 7: Create src/templates/web/digest_view.html**

Simple wrapper around the digest HTML content for web viewing.

**Step 8: Wire routers into src/main.py**

Import and include all routers. Set up database session middleware. Configure structlog.

**Step 9: Run tests, verify pass**

**Step 10: Commit**

```bash
git add -A
git commit -m "feat: API routes for admin, feedback, and digest web view"
```

---

## Task 18: Scheduler / Jobs

**Files:**
- Create: `src/jobs/scheduler.py`
- Create: `src/jobs/ingest_job.py`
- Create: `src/jobs/digest_job.py`
- Modify: `src/main.py`
- Test: `tests/test_jobs.py`

**Step 1: Write test for job definitions**

`tests/test_jobs.py`:
```python
def test_scheduler_registers_jobs():
    from src.jobs.scheduler import create_scheduler
    scheduler = create_scheduler(start=False)
    job_ids = [j.id for j in scheduler.get_jobs()]
    assert "ingest_all_sources" in job_ids
    assert "generate_and_send_digest" in job_ids
    assert "cleanup_old_events" in job_ids
```

**Step 2: Run test, verify fail**

**Step 3: Implement src/jobs/scheduler.py**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.jobs.ingest_job import run_ingestion
from src.jobs.digest_job import run_digest

def create_scheduler(start=True) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Chicago")
    scheduler.add_job(run_ingestion, CronTrigger(hour=6), id="ingest_all_sources")
    scheduler.add_job(run_digest, CronTrigger(day_of_week="tue,fri", hour=8), id="generate_and_send_digest")
    scheduler.add_job(cleanup_old_events, CronTrigger(day_of_week="sun", hour=3), id="cleanup_old_events")
    if start:
        scheduler.start()
    return scheduler
```

**Step 4: Implement src/jobs/ingest_job.py**

```python
async def run_ingestion():
    # Load city config
    # Create source registry with all enabled adapters
    # Create ingestion pipeline
    # Run pipeline
    # Run deduplication on new events
    # Update source health
    # Log results
```

**Step 5: Implement src/jobs/digest_job.py**

```python
async def run_digest():
    # Load user profile(s)
    # Query events in next 2-3 weeks
    # Run ranking engine
    # Run LLM synthesis on top candidates
    # Generate digest HTML + plaintext
    # Save digest record
    # Send via email channel
    # Mark as sent
```

**Step 6: Wire scheduler startup into src/main.py**

Start scheduler on FastAPI startup event. Shut down on shutdown event.

**Step 7: Run tests, verify pass**

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: APScheduler jobs for ingestion and digest generation"
```

---

## Task 19: Docker + Deployment

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `scripts/seed.py`
- Modify: `src/main.py` (add Alembic migration on startup)

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .
RUN playwright install chromium --with-deps

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create docker-compose.yml**

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: events
      POSTGRES_PASSWORD: events
      POSTGRES_DB: events
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U events"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**Step 3: Create scripts/seed.py**

Seeds the default Austin user profile:
```python
# Insert default user profile:
# - email from FROM_EMAIL env
# - Austin city
# - 2 adults (~35), 2 children (5, 8)
# - interests: music, outdoor, festivals, kids, arts, seasonal
# - preferred neighborhoods: South Austin, Zilker, East Austin, Downtown
# - preferred days: saturday, sunday
# - budget: moderate
# - max_distance: 30 miles
```

**Step 4: Add startup migration to src/main.py**

On startup: run `alembic upgrade head`, then run seed if no users exist.

**Step 5: Create Alembic initial migration**

Generate migration from models: `alembic revision --autogenerate -m "initial schema"`

**Step 6: Test Docker build**

```bash
docker compose build
docker compose up -d
docker compose logs app
# Verify: app is running, health endpoint responds
curl http://localhost:8000/health
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: docker deployment with postgres, seed data, and migrations"
```

---

## Task 20: Integration Stubs + Calendar Interface

**Files:**
- Create: `src/integrations/__init__.py`
- Create: `src/integrations/calendar.py`

**Step 1: Create calendar integration stub**

```python
from abc import ABC, abstractmethod

class CalendarIntegration(ABC):
    """Interface for calendar integrations (Google Calendar, Apple Calendar, etc.)"""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool: ...

    @abstractmethod
    async def create_event(self, event_data: dict) -> str: ...

    @abstractmethod
    async def update_event(self, event_id: str, event_data: dict) -> bool: ...

    @abstractmethod
    async def check_duplicate(self, event_data: dict) -> str | None: ...


class GoogleCalendarIntegration(CalendarIntegration):
    """TODO: Implement Google Calendar integration.

    Needs:
    - OAuth 2.0 flow for user authorization
    - Google Calendar API v3 client
    - Event creation with proper timezone handling
    - Duplicate detection by title + datetime
    - Token refresh handling

    Setup: Use Google Cloud Console to create OAuth credentials.
    API: https://developers.google.com/calendar/api/v3/reference
    """
    async def authenticate(self, credentials): raise NotImplementedError
    async def create_event(self, event_data): raise NotImplementedError
    async def update_event(self, event_id, event_data): raise NotImplementedError
    async def check_duplicate(self, event_data): raise NotImplementedError
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: calendar integration interface stub for future google calendar support"
```

---

## Task 21: End-to-End Smoke Test

**Files:**
- Create: `tests/test_e2e.py`

**Step 1: Write end-to-end test**

`tests/test_e2e.py`:
```python
"""
End-to-end smoke test: runs the full pipeline with mock sources and mock LLM.
Verifies: ingest -> normalize -> dedupe -> rank -> synthesize -> generate digest.
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.schemas.event import RawEvent
from src.schemas.user import UserProfileSchema
from src.sources.registry import SourceRegistry
from src.sources.base import SourceAdapter, SourceType
from src.ingestion.pipeline import IngestionPipeline
from src.dedupe.engine import DedupeEngine
from src.ranking.engine import RankingEngine
from src.digest.generator import DigestGenerator
from unittest.mock import AsyncMock

class MockSource(SourceAdapter):
    name = "mock"
    source_type = SourceType.API
    async def fetch_events(self, city_config):
        return [
            RawEvent(source_name="mock", source_type="api", title="Austin Music Fest",
                     start_datetime=datetime.now(timezone.utc) + timedelta(days=3),
                     city="austin", venue_name="Zilker Park", price_min=0, price_max=0,
                     tags=["music", "outdoor"], canonical_event_url="https://example.com/1"),
            RawEvent(source_name="mock", source_type="api", title="Kids Art Workshop",
                     start_datetime=datetime.now(timezone.utc) + timedelta(days=5),
                     city="austin", venue_name="Blanton Museum", tags=["kids", "arts"],
                     canonical_event_url="https://example.com/2"),
        ]

@pytest.mark.asyncio
async def test_full_pipeline():
    # 1. Ingest
    registry = SourceRegistry()
    registry.register(MockSource())
    from src.config.city import load_city_config
    city = load_city_config("austin")
    pipeline = IngestionPipeline(registry=registry, db_session=None)
    events = await pipeline.ingest(city, persist=False)
    assert len(events) == 2

    # 2. Dedupe (no dupes expected)
    engine = DedupeEngine(llm_client=None)
    deduped = engine.deduplicate(events)
    assert len(deduped) == 2

    # 3. Rank
    profile = UserProfileSchema(
        email="test@example.com", interests=["music", "outdoor", "kids"],
        children=[{"age": 5}],
    )
    ranker = RankingEngine()
    ranked = await ranker.rank_events(deduped, profile)
    assert len(ranked) == 2
    assert ranked[0][1] >= ranked[1][1]  # sorted by score

    # 4. Generate digest
    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test")
    html = generator.render_html(ranked, window_start="Mar 8", window_end="Mar 22")
    assert "Austin Music Fest" in html
    assert "Kids Art Workshop" in html
```

**Step 2: Run test**

Run: `pytest tests/test_e2e.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add -A
git commit -m "test: end-to-end smoke test for full pipeline"
```

---

## Task Summary

| # | Task | Key Deliverable |
|---|---|---|
| 1 | Project scaffolding | pyproject.toml, config, FastAPI app, city loader |
| 2 | Database models | All 6 tables, Alembic setup |
| 3 | Pydantic schemas | RawEvent, NormalizedEvent, UserProfileSchema |
| 4 | Source adapter interface | ABC + registry |
| 5 | Eventbrite adapter | Real API adapter |
| 6 | Bandsintown adapter | Real API adapter |
| 7 | Austin Chronicle scraper | httpx + BS4 adapter |
| 8 | Do512 scraper | Playwright adapter |
| 9 | Instagram stub | Interface only |
| 10 | Ingestion pipeline | Orchestration + normalizer |
| 11 | Deduplication engine | 3-pass dedupe |
| 12 | LLM abstraction | Provider-agnostic interface + Anthropic impl |
| 13 | Ranking engine | Rule-based + feedback scoring |
| 14 | LLM synthesis | Event enrichment with editorial summaries |
| 15 | Digest generator | Section grouping + HTML/plaintext email templates |
| 16 | Notifications | Resend email channel + push stub |
| 17 | API routes | Admin, feedback, digest web view |
| 18 | Scheduler | APScheduler cron jobs |
| 19 | Docker deployment | Dockerfile, compose, seed, migrations |
| 20 | Calendar stub | Google Calendar interface |
| 21 | E2E smoke test | Full pipeline verification |
