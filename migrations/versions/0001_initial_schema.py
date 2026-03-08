"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    eventcategory = postgresql.ENUM(
        "music", "arts", "festivals", "theatre", "kids", "outdoor", "seasonal", "community",
        name="eventcategory",
    )
    sourcetype = postgresql.ENUM("api", "feed", "scraper", name="sourcetype")
    budgetlevel = postgresql.ENUM("free", "low", "moderate", "any", name="budgetlevel")
    crowdsensitivity = postgresql.ENUM("low", "medium", "high", name="crowdsensitivity")
    feedbacktype = postgresql.ENUM(
        "thumbs_up", "thumbs_down", "more_like_this", "less_like_this",
        "too_far", "too_expensive", "wrong_age", "already_knew",
        name="feedbacktype",
    )
    digeststatus = postgresql.ENUM("draft", "sent", "failed", name="digeststatus")
    sourcehealthstatus = postgresql.ENUM(
        "healthy", "degraded", "failing", "disabled", name="sourcehealthstatus"
    )

    for enum in [eventcategory, sourcetype, budgetlevel, crowdsensitivity,
                 feedbacktype, digeststatus, sourcehealthstatus]:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.Enum("music", "arts", "festivals", "theatre", "kids",
                                      "outdoor", "seasonal", "community",
                                      name="eventcategory"), nullable=False),
        sa.Column("subcategory", sa.String(100)),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(50), default="America/Chicago"),
        sa.Column("venue_name", sa.String(255)),
        sa.Column("address", sa.Text),
        sa.Column("neighborhood", sa.String(100)),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("price_min", sa.Numeric(10, 2)),
        sa.Column("price_max", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(3), default="USD"),
        sa.Column("age_suitability", sa.String(50)),
        sa.Column("family_score", sa.Float),
        sa.Column("image_url", sa.Text),
        sa.Column("tags", sa.ARRAY(sa.String)),
        sa.Column("confidence", sa.Float, default=0.5),
        sa.Column("dedupe_group_id", postgresql.UUID(as_uuid=True)),
        sa.Column("canonical_event_url", sa.Text),
        sa.Column("editorial_summary", sa.Text),
        sa.Column("relevance_explanation", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "event_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("events.id")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.Enum("api", "feed", "scraper", name="sourcetype")),
        sa.Column("source_url", sa.Text),
        sa.Column("raw_payload", postgresql.JSONB),
        sa.Column("title", sa.Text),
        sa.Column("start_datetime", sa.DateTime(timezone=True)),
        sa.Column("venue_name", sa.String(255)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), default="austin"),
        sa.Column("adults", postgresql.JSONB),
        sa.Column("children", postgresql.JSONB),
        sa.Column("preferred_neighborhoods", sa.ARRAY(sa.String)),
        sa.Column("max_distance_miles", sa.Integer, default=30),
        sa.Column("preferred_days", sa.ARRAY(sa.String)),
        sa.Column("preferred_times", sa.ARRAY(sa.String)),
        sa.Column("budget", sa.Enum("free", "low", "moderate", "any", name="budgetlevel"),
                  default="moderate"),
        sa.Column("interests", sa.ARRAY(sa.String)),
        sa.Column("dislikes", sa.ARRAY(sa.String)),
        sa.Column("max_events_per_digest", sa.Integer, default=15),
        sa.Column("crowd_sensitivity",
                  sa.Enum("low", "medium", "high", name="crowdsensitivity"),
                  default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("user_profiles.id")),
        sa.Column("subject", sa.Text),
        sa.Column("html_content", sa.Text),
        sa.Column("plaintext_content", sa.Text),
        sa.Column("event_ids", sa.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Enum("draft", "sent", "failed", name="digeststatus"),
                  default="draft"),
        sa.Column("window_start", sa.Date),
        sa.Column("window_end", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("user_profiles.id")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("events.id")),
        sa.Column("feedback_type", sa.Enum(
            "thumbs_up", "thumbs_down", "more_like_this", "less_like_this",
            "too_far", "too_expensive", "wrong_age", "already_knew",
            name="feedbacktype",
        ), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "source_health",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("events_found", sa.Integer, default=0),
        sa.Column("errors", sa.Text),
        sa.Column("status",
                  sa.Enum("healthy", "degraded", "failing", "disabled",
                          name="sourcehealthstatus"),
                  default="healthy"),
    )


def downgrade() -> None:
    op.drop_table("source_health")
    op.drop_table("feedback")
    op.drop_table("digests")
    op.drop_table("user_profiles")
    op.drop_table("event_sources")
    op.drop_table("events")

    for name in ["sourcehealthstatus", "digeststatus", "feedbacktype",
                 "crowdsensitivity", "budgetlevel", "sourcetype", "eventcategory"]:
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
