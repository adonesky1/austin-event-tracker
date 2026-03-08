def test_scheduler_registers_jobs():
    from src.jobs.scheduler import create_scheduler
    scheduler = create_scheduler(start=False)
    job_ids = [j.id for j in scheduler.get_jobs()]
    assert "ingest_all_sources" in job_ids
    assert "generate_and_send_digest" in job_ids
    assert "cleanup_old_events" in job_ids
