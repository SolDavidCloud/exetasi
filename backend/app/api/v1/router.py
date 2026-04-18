from fastapi import APIRouter

from app.api.v1 import admin, audit, auth, exams, health, orgs, placeholders, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(orgs.router)
api_router.include_router(exams.router)
api_router.include_router(audit.router)
api_router.include_router(admin.router)
api_router.include_router(placeholders.router)
