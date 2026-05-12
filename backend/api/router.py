"""
router.py
─────────
Central place that combines all route groups.
main.py imports ONLY this — not individual route files.

Why?
Adding a new route group = add one line here.
main.py never needs to change.
"""

from fastapi import APIRouter
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router

api_router = APIRouter()

api_router.include_router(chat_router)
api_router.include_router(health_router)

# Final routes after main.py adds /api/v1 prefix:
# /api/v1/chat
# /api/v1/chat/clear
# /api/v1/health
# /api/v1/health/deep