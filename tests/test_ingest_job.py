from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_run_ingestion_persists_and_returns_warning_summary(monkeypatch):
    from src.jobs import ingest_job

    calls: dict[str, object] = {}
    session = object()

    class FakeEngine:
        async def dispose(self):
            calls["disposed"] = True

    class FakeSessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakePipeline:
        def __init__(self, registry, db_session):
            calls["registry"] = registry
            calls["db_session"] = db_session
            self.last_results = {
                "eventbrite": {"status": "success", "count": 3},
                "do512": {"status": "error", "error": "Timed out"},
            }

        async def ingest(self, city_config, persist: bool = True):
            calls["city"] = city_config.name
            calls["persist"] = persist
            return ["event-1", "event-2", "event-3"]

    monkeypatch.setattr(
        ingest_job,
        "Settings",
        lambda: SimpleNamespace(default_city="austin"),
    )
    monkeypatch.setattr(
        ingest_job,
        "load_city_config",
        lambda city: SimpleNamespace(name=city),
    )
    monkeypatch.setattr(ingest_job, "build_registry", lambda settings: "registry")
    monkeypatch.setattr(ingest_job, "create_engine", lambda settings: FakeEngine())
    monkeypatch.setattr(
        ingest_job,
        "create_session_factory",
        lambda engine: (lambda: FakeSessionContext()),
    )
    monkeypatch.setattr(ingest_job, "IngestionPipeline", FakePipeline)

    result = await ingest_job.run_ingestion()

    assert calls["db_session"] is session
    assert calls["persist"] is True
    assert calls["city"] == "austin"
    assert calls["disposed"] is True

    assert result["status"] == "warning"
    assert result["total_events"] == 3
    assert "source error" in result["summary"].lower()
    assert result["source_results"]["do512"]["error"] == "Timed out"
