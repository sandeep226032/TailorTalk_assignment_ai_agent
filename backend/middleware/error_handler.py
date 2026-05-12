"""
error_handler.py
────────────────
Catches ALL unhandled exceptions across the entire app.

Without this:
- FastAPI returns raw Python tracebacks to the user
- User sees: "Internal Server Error" with no useful info
- You see nothing in logs

With this:
- Every error is caught in one place
- User gets a clean JSON error response
- You get a full log with what went wrong

Node.js equivalent: your global error middleware
app.use((err, req, res, next) => { res.status(500).json({error: err.message}) })
"""

import time
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.exceptions import (
    DriveConnectionError,
    AgentError,
    SessionNotFoundError,
)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except DriveConnectionError as e:
            # Known error — Drive credentials/connection failed
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "drive_connection_error",
                    "message": str(e),
                    "status_code": 503,
                },
            )

        except AgentError as e:
            # Known error — LangChain agent failed
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "agent_error",
                    "message": str(e),
                    "status_code": 500,
                },
            )

        except SessionNotFoundError as e:
            # Known error — invalid session ID
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "session_not_found",
                    "message": str(e),
                    "status_code": 404,
                },
            )

        except Exception as e:
            # Unknown error — log full traceback, return generic message
            # Why generic message to user?
            # Never expose internal error details to users —
            # stack traces can reveal file paths, library versions,
            # and code structure useful to attackers
            print(f"[ErrorHandler] Unhandled exception: {traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "internal_server_error",
                    "message": "Something went wrong. Please try again.",
                    "status_code": 500,
                },
            )