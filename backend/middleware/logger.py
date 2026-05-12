"""
logger.py
─────────
Logs every incoming request and outgoing response.

Why log requests?
- See exactly what's happening in production
- Debug issues: "User got an error — what did they send?"
- Monitor performance: "This endpoint is taking 10 seconds"
- Track usage: "How many /chat requests per minute?"

What we log:
→ REQUEST:  method, path, client IP
← RESPONSE: status code, time taken

We do NOT log request bodies — they contain user messages
which may be sensitive. Log metadata, not content.

Node.js equivalent: morgan middleware
app.use(morgan('combined'))
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        print(
            f"[Request]  {request.method} {request.url.path} "
            f"| IP: {request.client.host}"
        )

        # Process the request
        response = await call_next(request)

        # Log response with time taken
        duration = round((time.time() - start_time) * 1000, 2)
        print(
            f"[Response] {request.method} {request.url.path} "
            f"| Status: {response.status_code} "
            f"| Duration: {duration}ms"
        )

        # Why add X-Process-Time header?
        # Frontend or monitoring tools can read this header
        # to track how long each request took without
        # parsing log files
        response.headers["X-Process-Time"] = f"{duration}ms"

        return response