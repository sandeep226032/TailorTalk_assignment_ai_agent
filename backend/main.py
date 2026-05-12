"""
main.py
────────
The application entry point — starts the FastAPI app.

This file should be as THIN as possible.
Its only jobs are:
1. Create the FastAPI app instance
2. Register middleware
3. Register routers
4. Start the server

Nothing else. No business logic. No route handlers. No database calls.

Why so thin?
In production, main.py is imported by:
- uvicorn (to start the server)
- pytest (to create a test client)
- gunicorn (alternative production server)

If main.py has business logic, all those importers get that logic
whether they want it or not. Thin main.py = clean separation.

Node.js equivalent:
This is your app.js or server.js — the file that does
app.use(middleware) and app.use('/api', routes) and app.listen(3000)
Nothing more.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.router import api_router
from middleware.logger import LoggerMiddleware
from middleware.error_handler import ErrorHandlerMiddleware
from core.config import settings


# ── Lifespan — startup and shutdown logic ─────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs code BEFORE the server starts accepting requests (startup)
    and AFTER it stops (shutdown).

    Why lifespan instead of @app.on_event("startup")?
    @app.on_event is deprecated in newer FastAPI versions.
    Lifespan is the modern replacement — it uses a context manager
    which is cleaner and more Pythonic.

    Startup (before yield):
    - Validate that all required env vars exist
    - Test Google Drive connection
    - Pre-warm the LLM client
    - Connect to Redis (if using it)
    Any error here = server refuses to start = you catch config
    problems immediately, not when the first user hits the API.

    Shutdown (after yield):
    - Close database connections
    - Flush logs
    - Release file handles
    Without this, connections leak and resources aren't freed cleanly.

    Node.js equivalent:
    This is like your server.js doing:
    mongoose.connect() before app.listen()
    process.on('SIGTERM', () => server.close()) for shutdown
    """
    # ── Startup ──────────────────────────────────────────────────
    print(f"[Startup] Starting {settings.app_name} v{settings.app_version}")
    print(f"[Startup] Environment: {settings.environment}")
    print(f"[Startup] Debug mode: {settings.debug_mode}")

    # Validate critical environment variables exist
    # Fail fast — better to crash at startup than mid-conversation
    _validate_config()

    # Optionally test Drive connection at startup
    # Uncomment in production to catch credential issues early
    # await _test_drive_connection()

    print("[Startup] All checks passed. Server ready.")

    yield  # ← Server runs here, handling requests

    # ── Shutdown ──────────────────────────────────────────────────
    print("[Shutdown] Server shutting down. Cleaning up...")
    # Add cleanup here: close DB connections, flush logs, etc.
    print("[Shutdown] Cleanup complete.")


# ── App factory ───────────────────────────────────────────────────
def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Why a factory function instead of just app = FastAPI()?

    1. TESTING:
       In tests, you call create_app() to get a fresh app instance.
       If you just did app = FastAPI() at module level, tests
       would share the same app instance — causing interference
       between tests.

       # In tests:
       from main import create_app
       app = create_app()
       client = TestClient(app)

    2. MULTIPLE INSTANCES:
       Some deployment setups need multiple app instances.
       Factory function makes that trivial.

    3. CLARITY:
       All configuration is in one function — easy to read
       exactly how the app is set up.

    Node.js equivalent:
    This is the pattern where you export a function that
    creates and returns your Express app:
    module.exports = createApp()
    instead of module.exports = app
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Conversational AI agent for Google Drive file discovery",

        # Disable docs in production — don't expose API structure publicly
        # In development, docs available at /docs and /redoc
        docs_url="/docs" if settings.debug_mode else None,
        redoc_url="/redoc" if settings.debug_mode else None,

        lifespan=lifespan,
    )

    # Register everything on the app
    _register_middleware(app)
    _register_routers(app)

    return app


# ── Middleware registration ───────────────────────────────────────
def _register_middleware(app: FastAPI) -> None:
    """
    Registers all middleware in the correct ORDER.

    Why does order matter?
    Middleware wraps requests like layers of an onion.
    Request goes IN through layers top to bottom.
    Response comes OUT through layers bottom to top.

    Request flow:
    CORS → ErrorHandler → Logger → Your route handler
    Response flow:
    Your route handler → Logger → ErrorHandler → CORS

    CORS must be OUTERMOST (added last in FastAPI, runs first):
    Because CORS headers must be on EVERY response, including
    error responses. If ErrorHandler is outside CORS, error
    responses won't have CORS headers and browser will block them.

    Logger should be INSIDE ErrorHandler:
    So you log the actual error, not the wrapped error response.

    Node.js equivalent:
    app.use(cors())
    app.use(errorHandler)
    app.use(logger)
    (same ordering concern applies in Express)
    """

    # Custom middleware (added first = innermost = runs last)
    app.add_middleware(LoggerMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)

    # CORS (added last = outermost = runs first)
    # Why CORS?
    # Browser security blocks requests from one origin to another.
    # Your Streamlit app is at streamlit.io, API is at render.com.
    # Without CORS headers, browser refuses to send the request.
    # CORS tells the browser "yes, this cross-origin request is allowed"
    
    origins = settings.allowed_origins
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",")]

    app.add_middleware(
        CORSMiddleware,

        # In production, replace * with your actual Streamlit URL:
        # allow_origins=["https://your-app.streamlit.app"]
        # Using * in production is a security risk — any website
        # could make requests to your API on behalf of users
        allow_origins=origins,

        allow_credentials=True,
        allow_methods=["GET", "POST"],   # Only methods your API uses
        allow_headers=["Content-Type"],  # Only headers your API needs
    )


# ── Router registration ───────────────────────────────────────────
def _register_routers(app: FastAPI) -> None:
    """
    Registers all route groups under the API prefix.

    Why a prefix like /api/v1?

    Versioning (/v1):
    When you make breaking changes to your API, you release /v2.
    Old Streamlit frontend keeps using /v1.
    New Streamlit frontend uses /v2.
    Both work simultaneously — no forced migration.

    Without versioning:
    You change POST /chat to return a different shape.
    Every client immediately breaks. No gradual migration possible.

    /api prefix:
    Separates API routes from non-API routes.
    If you ever add a web interface to the same server,
    /api/... vs /... makes routing unambiguous.

    api_router is imported from app/api/router.py which
    combines all sub-routers (chat, health) into one.
    This keeps main.py from knowing about individual routes.
    """
    app.include_router(
        api_router,
        prefix="/api/v1",
    )


# ── Startup validation ────────────────────────────────────────────
def _validate_config() -> None:
    """
    Validates all required configuration exists at startup.

    Why validate at startup?
    Without this, the server starts fine but crashes when
    the first user sends a message and the code tries to
    use a missing env var. That's a terrible user experience.

    With this, the server refuses to start if config is wrong.
    You catch the problem in deployment, not in production traffic.

    This is called "fail fast" — detect problems as early
    as possible, not when they cause user-visible failures.

    Node.js equivalent:
    if (!process.env.GROQ_API_KEY) {
      throw new Error('GROQ_API_KEY is required')
      process.exit(1)
    }
    """
    required = {
        "GROQ_API_KEY": settings.groq_api_key,
        "DRIVE_FOLDER_ID": settings.drive_folder_id,
        "GOOGLE_CREDENTIALS_PATH": settings.google_credentials_path,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            f"[Config Error] Missing required environment variables: "
            f"{', '.join(missing)}\n"
            f"Check your .env file."
        )

    print("[Config] All required environment variables present.")


# ── App instance ──────────────────────────────────────────────────
# Created at module level so uvicorn can import it:
# uvicorn main:app --host 0.0.0.0 --port 8000
#          ↑    ↑
#          file  variable name
app = create_app()


# ── Local development runner ──────────────────────────────────────
if __name__ == "__main__":
    """
    Only runs when you execute: python main.py
    Does NOT run when uvicorn imports the module.

    Why uvicorn.run() instead of just uvicorn main:app in terminal?
    For local development, python main.py is simpler.
    For production, uvicorn main:app is used directly.
    Both work identically — this is just convenience.

    reload=True:
    Watches for file changes and restarts automatically.
    Like nodemon in Node.js.
    NEVER use reload=True in production — it's slow and
    creates security issues.
    """
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug_mode,  # Auto-reload only in development
    )