"""
health.py
─────────
Health check endpoint — GET /api/v1/health

Why does a health check endpoint exist?

When you deploy on Render, Railway, or any cloud platform:
1. The platform sends GET /health every 30 seconds
2. If it gets 200 OK → "app is healthy, keep running"
3. If it gets 500 or timeout → "app is broken, restart it"

Without a health endpoint:
- Platform has no way to know if your app is actually working
- A crashed app sits dead forever — no automatic recovery
- You find out when a user complains, not from monitoring

With a health endpoint:
- Platform detects crash within 30 seconds
- Automatically restarts your app
- You can also check it manually to verify deployment worked:
  curl https://your-app.onrender.com/api/v1/health

Levels of health checks:

LEVEL 1 — Basic (are you alive?):
    Just return 200 OK.
    "Yes, the server is running."
    Catches: server crashed, port not listening

LEVEL 2 — Shallow (can you respond?):
    Return version, uptime, environment info.
    "Yes, running, here's some info about me."
    Catches: app started but is misconfigured

LEVEL 3 — Deep (can you do your job?):
    Actually test Drive connection, test LLM connection.
    "Yes, and all my dependencies work."
    Catches: credentials expired, Drive API down, Groq API down

We implement Level 2 always + Level 3 optionally.
Level 3 makes the health check slow (network calls) so
it's behind a separate /health/deep endpoint.

Node.js equivalent:
app.get('/health', (req, res) => res.json({ status: 'ok' }))
Same concept, just more structured here.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone
import time

from core.config import settings
from core.constants import SuccessMessages

router = APIRouter(prefix="/health", tags=["health"])

# Track when the server started
# Used to calculate uptime
_start_time = time.time()


# ── Response models ───────────────────────────────────────────────
class HealthResponse(BaseModel):
    """
    Structured health response.

    Why a Pydantic model instead of plain dict?
    - Automatic JSON serialization
    - Type validation
    - Self-documenting (shows in /docs)
    - Consistent shape — callers know exactly what to expect

    status: "healthy" | "degraded" | "unhealthy"
    - healthy: everything works
    - degraded: running but some non-critical feature is down
    - unhealthy: critical failure (return 503, not 200)
    """
    status: str
    app_name: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: str


class DeepHealthResponse(HealthResponse):
    """
    Extended health response with dependency checks.
    Inherits all fields from HealthResponse and adds:
    """
    drive_connected: bool
    drive_error: str | None
    llm_connected: bool
    llm_error: str | None


# ── Level 2: Shallow health check ────────────────────────────────
@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check — just confirms server is running.

    Returns 200 OK with server info.
    Fast — no network calls, no external dependencies.
    This is what Render/Railway polls every 30 seconds.

    Why return app info (version, environment)?
    After deploying, you can verify:
    - "Is the right version running?" (version field)
    - "Did it deploy to production or staging?" (environment field)
    - "Has it been running long enough?" (uptime field)
      A fresh restart (low uptime) after a deploy = deployment worked.
      Repeated low uptimes = app keeps crashing = bug.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _start_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ── Level 3: Deep health check ────────────────────────────────────
@router.get("/deep", response_model=DeepHealthResponse)
async def deep_health_check() -> DeepHealthResponse:
    """
    Deep health check — tests all external dependencies.

    Returns 200 if everything works.
    Returns 503 if any critical dependency is down.

    Why a separate endpoint?
    - Shallow check (/health): fast, polled every 30s by platform
    - Deep check (/health/deep): slow, called manually or every 5min

    If you made the platform poll the deep check every 30s:
    - 2 HTTP calls to external APIs every 30s
    - Costs money (API calls aren't free at scale)
    - Slows down the health check response
    - More chances for false positives (Drive API has brief blips)

    What does "testing Drive connection" mean?
    We call Drive API with a minimal query — not to get real results,
    but just to verify credentials work and the API responds.
    If it throws an exception → credentials expired or Drive API down.

    What does "testing LLM connection" mean?
    We send a tiny message to Groq and check we get a response.
    If it throws → API key invalid or Groq is down.
    """
    drive_ok, drive_error = await _check_drive_connection()
    llm_ok, llm_error = await _check_llm_connection()

    # Determine overall status
    if drive_ok and llm_ok:
        overall_status = "healthy"
        http_status = 200
    elif not drive_ok and not llm_ok:
        overall_status = "unhealthy"
        http_status = 503
    else:
        # One works, one doesn't = degraded
        overall_status = "degraded"
        http_status = 200  # Still return 200 — partially working

    response = DeepHealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _start_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
        drive_connected=drive_ok,
        drive_error=drive_error,
        llm_connected=llm_ok,
        llm_error=llm_error,
    )

    # FastAPI can return custom status codes using Response
    # But for simplicity here we return the model directly
    # In a real app: from fastapi import Response
    # return Response(content=response.json(), status_code=http_status)
    return response


# ── Dependency check helpers ──────────────────────────────────────
async def _check_drive_connection() -> tuple[bool, str | None]:
    """
    Tests Google Drive API connection.

    Returns (True, None) if connected.
    Returns (False, "error message") if not.

    Why list files with pageSize=1?
    - Smallest possible valid API call
    - Proves: credentials valid, API enabled, folder accessible
    - Costs minimal API quota
    - Fast response

    Why catch ALL exceptions?
    Drive connection can fail for many reasons:
    - FileNotFoundError: credentials.json missing
    - google.auth.exceptions.TransportError: network issue
    - googleapiclient.errors.HttpError: API quota exceeded
    - json.JSONDecodeError: credentials.json malformed
    We want to catch all of them and report clearly.
    """
    try:
        from app.tools.drive_client import get_drive_client
        service = get_drive_client()
        service.files().list(pageSize=1, fields="files(id)").execute()
        return True, None
    except Exception as e:
        return False, str(e)


async def _check_llm_connection() -> tuple[bool, str | None]:
    """
    Tests Groq LLM API connection.

    Sends a minimal message — just to verify the API key works
    and Groq responds. Not a real query, just a ping.

    Why max_tokens=5?
    We don't need a real response — just proof the API works.
    5 tokens = minimal cost, minimal wait time.

    Why catch ALL exceptions?
    LLM connection can fail for:
    - groq.AuthenticationError: invalid API key
    - groq.RateLimitError: quota exceeded
    - httpx.ConnectError: network issue
    - Exception: anything unexpected
    """
    try:
        from langchain_groq import ChatGroq
        from app.core.config import settings

        llm = ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            max_tokens=5,   # Minimal response — just testing connectivity
        )
        await llm.ainvoke("ping")
        return True, None
    except Exception as e:
        return False, str(e)