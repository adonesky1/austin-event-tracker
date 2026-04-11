from src.jobs.runtime_status import (
    get_job_runtime_snapshot,
    mark_job_complete,
    mark_job_failed,
    mark_job_queued,
    mark_job_running,
)


def test_job_runtime_snapshot_tracks_completed_warning_result():
    job_id = "test_job_runtime_warning"
    job_name = "Test Job Runtime Warning"

    mark_job_queued(job_id, job_name, "manual")
    mark_job_running(job_id, job_name, "manual")
    mark_job_complete(
        job_id,
        job_name,
        "manual",
        {
            "status": "warning",
            "summary": "Ingested 12 events with 1 source error.",
            "source_results": {"do512": {"status": "error", "error": "Timed out"}},
        },
    )

    snapshot = get_job_runtime_snapshot(job_id, job_name)
    assert snapshot["status"] == "warning"
    assert snapshot["trigger"] == "manual"
    assert snapshot["summary"] == "Ingested 12 events with 1 source error."
    assert snapshot["details"]["source_results"]["do512"]["error"] == "Timed out"
    assert snapshot["started_at"] is not None
    assert snapshot["completed_at"] is not None


def test_job_runtime_snapshot_tracks_failure():
    job_id = "test_job_runtime_failure"
    job_name = "Test Job Runtime Failure"

    mark_job_running(job_id, job_name, "scheduler")
    mark_job_failed(
        job_id,
        job_name,
        "scheduler",
        RuntimeError("Boom"),
        traceback_text="Traceback line 1\nTraceback line 2",
    )

    snapshot = get_job_runtime_snapshot(job_id, job_name)
    assert snapshot["status"] == "failed"
    assert snapshot["error"] == "RuntimeError: Boom"
    assert snapshot["summary"] == "Run failed."
    assert "Traceback line 1" in snapshot["traceback"]
