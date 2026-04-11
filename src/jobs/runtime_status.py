from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any


ACTIVE_JOB_STATUSES = {"queued", "running"}


@dataclass
class JobRuntimeState:
    job_id: str
    name: str
    status: str = "idle"
    trigger: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
    error: str | None = None
    traceback: str | None = None
    details: dict[str, Any] | None = None


_runtime_by_job_id: dict[str, JobRuntimeState] = {}


def register_job(job_id: str, name: str) -> JobRuntimeState:
    state = _runtime_by_job_id.get(job_id)
    if state is None:
        state = JobRuntimeState(job_id=job_id, name=name)
        _runtime_by_job_id[job_id] = state
    else:
        state.name = name
    return state


def is_job_active(job_id: str) -> bool:
    state = _runtime_by_job_id.get(job_id)
    return state is not None and state.status in ACTIVE_JOB_STATUSES


def mark_job_queued(job_id: str, name: str, trigger: str) -> JobRuntimeState:
    state = register_job(job_id, name)
    state.status = "queued"
    state.trigger = trigger
    state.started_at = None
    state.completed_at = None
    state.summary = f"{trigger.title()} run queued."
    state.error = None
    state.traceback = None
    state.details = None
    return state


def mark_job_running(job_id: str, name: str, trigger: str) -> JobRuntimeState:
    state = register_job(job_id, name)
    state.status = "running"
    state.trigger = trigger
    state.started_at = datetime.now(timezone.utc)
    state.completed_at = None
    state.summary = f"{trigger.title()} run in progress."
    state.error = None
    state.traceback = None
    state.details = None
    return state


def mark_job_complete(
    job_id: str,
    name: str,
    trigger: str,
    result: Any,
) -> JobRuntimeState:
    state = register_job(job_id, name)
    state.status = _result_status(result)
    state.trigger = trigger
    state.completed_at = datetime.now(timezone.utc)
    if state.started_at is None:
        state.started_at = state.completed_at
    state.summary = _result_summary(result)
    state.error = _result_error(result)
    state.traceback = None
    state.details = _compact_result(result)
    return state


def mark_job_failed(
    job_id: str,
    name: str,
    trigger: str,
    exc: Exception,
    traceback_text: str | None = None,
) -> JobRuntimeState:
    state = register_job(job_id, name)
    state.status = "failed"
    state.trigger = trigger
    state.completed_at = datetime.now(timezone.utc)
    if state.started_at is None:
        state.started_at = state.completed_at
    state.summary = "Run failed."
    state.error = f"{type(exc).__name__}: {exc}"
    state.traceback = traceback_text
    state.details = None
    return state


def get_job_runtime_snapshot(job_id: str, name: str) -> dict[str, Any]:
    state = register_job(job_id, name)
    return {
        "status": state.status,
        "trigger": state.trigger,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        "summary": state.summary,
        "error": state.error,
        "traceback": state.traceback,
        "details": state.details,
    }


def _result_status(result: Any) -> str:
    if isinstance(result, dict):
        status = result.get("status")
        if isinstance(status, str) and status:
            return status
    return "success"


def _result_summary(result: Any) -> str:
    if isinstance(result, dict):
        summary = result.get("summary")
        if isinstance(summary, str) and summary:
            return summary
        status = result.get("status")
        if isinstance(status, str) and status:
            return f"Run {status}."
    return "Run completed."


def _result_error(result: Any) -> str | None:
    if isinstance(result, dict):
        error = result.get("error")
        if error:
            return str(error)
    return None


def _compact_result(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    return _make_json_safe(result)


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    return str(value)
