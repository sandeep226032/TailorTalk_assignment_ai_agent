"""
exceptions.py
─────────────
Custom exception classes for the app.

Why custom exceptions instead of just raising Exception("message")?

1. You can catch them SPECIFICALLY:
   except DriveConnectionError  ← only catches Drive errors
   except Exception             ← catches everything (too broad)

2. error_handler.py maps each exception type to an HTTP status code:
   DriveConnectionError → 503
   SessionNotFoundError → 404
   AgentError           → 500

3. Self-documenting — when you see raise DriveConnectionError()
   you immediately know what failed without reading the message
"""


class DriveConnectionError(Exception):
    """Raised when Google Drive API connection fails."""
    def __init__(self, message: str = "Could not connect to Google Drive."):
        super().__init__(message)


class AgentError(Exception):
    """Raised when the LangChain agent fails to run."""
    def __init__(self, message: str = "Agent encountered an error."):
        super().__init__(message)


class SessionNotFoundError(Exception):
    """Raised when a session ID doesn't exist in the store."""
    def __init__(self, session_id: str):
        super().__init__(f"Session '{session_id}' not found.")


class ConfigurationError(Exception):
    """Raised at startup when required config is missing."""
    def __init__(self, missing_keys: list[str]):
        super().__init__(
            f"Missing required environment variables: {', '.join(missing_keys)}"
        )