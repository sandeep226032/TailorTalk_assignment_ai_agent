# Like repository/ in Node — only knows HOW to store/retrieve data
# Doesn't know what the data means or why it's being stored

from langchain_core.messages import HumanMessage, AIMessage
from core.config import settings

class SessionStore:
    """
    Currently in-memory. 
    To switch to Redis, only THIS file changes — nothing else.
    That's the whole point of the repository pattern.
    """
    def __init__(self):
        self._store: dict[str, list] = {}

    def get(self, session_id: str) -> list:
        return self._store.get(session_id, [])

    def set(self, session_id: str, history: list):
        # Trim to max length
        if len(history) > settings.max_history_length:
            history = history[-settings.max_history_length:]
        self._store[session_id] = history

    def delete(self, session_id: str):
        self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        return session_id in self._store