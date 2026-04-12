"""Structured placeholders for features planned in later implementation phases."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["roadmap"])


@router.get("/grading-queue")
async def grading_queue_placeholder() -> dict[str, object]:
    return {"items": [], "phase": 6}


@router.get("/analytics/summary")
async def analytics_summary_placeholder() -> dict[str, object]:
    return {"metrics": {}, "phase": 7}


@router.get("/notifications")
async def notifications_placeholder() -> dict[str, object]:
    return {"items": [], "phase": 8}


@router.get("/audit-log")
async def audit_log_placeholder() -> dict[str, object]:
    return {"entries": [], "phase": 8}


@router.get("/certificates/status")
async def certificates_status_placeholder() -> dict[str, object]:
    return {"enabled": False, "phase": 8}


@router.get("/import-export/status")
async def import_export_status_placeholder() -> dict[str, object]:
    return {"formats": ["json", "toml", "yaml"], "phase": 8}


@router.get("/media/config")
async def media_config_placeholder() -> dict[str, object]:
    return {"backend": "local", "phase": 8}


@router.get("/questions/overview")
async def questions_overview_placeholder() -> dict[str, object]:
    return {"types": ["mc", "open", "fib", "order", "match", "info"], "phase": 4}


@router.get("/attempts/overview")
async def attempts_overview_placeholder() -> dict[str, object]:
    return {"status": "not_implemented", "phase": 5}
