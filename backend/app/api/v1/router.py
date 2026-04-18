from fastapi import APIRouter

from app.api.v1 import (
    admin,
    alerts,
    audit,
    auth,
    exams,
    health,
    messages,
    orgs,
    placeholders,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(orgs.router)
api_router.include_router(exams.router)
api_router.include_router(audit.router)
api_router.include_router(admin.router)
api_router.include_router(messages.router)
api_router.include_router(alerts.system_router)
api_router.include_router(alerts.org_alert_router)
api_router.include_router(alerts.ack_router)
api_router.include_router(placeholders.router)
