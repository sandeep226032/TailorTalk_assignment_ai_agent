"""
memory_service.py
─────────────────
Responsible for ONE thing only:
Managing conversation memory — adding, retrieving, trimming history.

It does NOT know about:
- HTTP requests
- The LLM or agent
- HOW history is stored (delegates to SessionStore)

It only knows:
- WHAT conversation history looks like
- WHEN to trim it
- HOW to convert between formats

Why does this exist separately from session_store.py?

session_store.py  = the drawer (storage mechanism — RAM, Redis, DB)
memory_service.py = the filing system (rules for what goes in the drawer)

If you switch from RAM to Redis, only session_store.py changes.
If you change memory rules (trim at 30 instead of 20), only this changes.
They never need to change for the same reason.
"""

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from repository.session_store import SessionStore
from core.config import settings


class MemoryService:
    """
    Manages conversation history for all active sessions.
    
    In Node.js terms, this is like a service that wraps a repository
    and adds business rules on top of raw data access.
    
    SessionStore says: "store this, retrieve that"
    MemoryService says: "but only keep 20 messages, and always
                         store in HumanMessage/AIMessage format"
    """

    def __init__(self):
        # MemoryService OWNS a SessionStore
        # It doesn't receive one from outside (not injected)
        # Why? Because MemoryService always needs exactly one store.
        # If you needed to swap stores, you'd do it in config, not here.
        self._store = SessionStore()

    # ── Public methods — called by ChatService ────────────────────

    def get_history(self, session_id: str) -> list[BaseMessage]:
        """
        Retrieves conversation history for a session.
        
        Returns a list of LangChain message objects:
        [
            HumanMessage(content="find all PDFs"),
            AIMessage(content="I found 3 PDFs: ..."),
            HumanMessage(content="which ones from 2024?"),
            AIMessage(content="2 of those are from 2024: ..."),
        ]
        
        Why LangChain message objects and not plain dicts?
        LangChain's agent expects BaseMessage objects specifically.
        If you passed plain dicts {"role": "user", "content": "..."},
        the agent would crash.
        
        Why not store them as dicts and convert here?
        Storage and retrieval should be symmetric — store what you
        retrieve. Converting back and forth adds complexity with no benefit.
        So we store LangChain objects directly.
        
        Returns empty list (not None) if no history exists.
        Empty list = valid first conversation.
        None = error. Always return a valid type.
        """
        return self._store.get(session_id)

    def update_history(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """
        Adds a new exchange (user + assistant) to history.
        
        Why add BOTH messages together in one method?
        A conversation exchange is atomic — a question without
        an answer (or vice versa) makes no sense in history.
        By accepting both together, we guarantee history always
        has matched pairs.
        
        Wrong history (unpaired):
        [HumanMessage("find PDFs")]   ← no response paired with it
        
        Correct history (paired):
        [HumanMessage("find PDFs"), AIMessage("Found 3...")]
        
        After adding, automatically trims to max length.
        The trimming rule lives HERE (business rule),
        not in SessionStore (storage rule).
        
        Why trim from the FRONT not the BACK?
        Most recent messages are most relevant.
        Oldest messages are least relevant.
        Remove oldest first: history[-20:] keeps last 20.
        
        Conversation example with trim at 4:
        Before: [H1, A1, H2, A2, H3, A3]  (6 messages)
        Add H4, A4:
        Raw:    [H1, A1, H2, A2, H3, A3, H4, A4]  (8 messages)
        Trim:   [H2, A2, H3, A3, H4, A4]  (last 4 kept — always pairs)
        
        Why trim at even numbers?
        Messages come in pairs (Human + AI).
        Trimming at odd numbers would split a pair, leaving
        an AI response without its question — confusing for the LLM.
        settings.max_history_length should always be even.
        """
        current_history = self._store.get(session_id)

        # Add the new exchange
        current_history.append(HumanMessage(content=user_message))
        current_history.append(AIMessage(content=assistant_response))

        # Trim if over limit
        # Always trim in pairs (keep even number) to avoid orphaned messages
        max_length = settings.max_history_length
        if len(current_history) > max_length:
            # Trim from front, keep most recent messages
            # Make sure we keep an even number (full pairs only)
            trimmed = current_history[-max_length:]
            # If somehow odd, remove first element to make even
            if len(trimmed) % 2 != 0:
                trimmed = trimmed[1:]
            current_history = trimmed

        self._store.set(session_id, current_history)

    def clear(self, session_id: str) -> None:
        """
        Clears all history for a session.
        Called when user clicks "New Conversation".
        
        Why not just set to empty list?
        self._store.set(session_id, []) would work but leaves
        the key in the store with an empty value — wasted memory.
        Deleting the key entirely is cleaner.
        """
        self._store.delete(session_id)

    def get_message_count(self, session_id: str) -> int:
        """
        Returns number of messages in a session.
        
        Why does this exist?
        Useful for:
        - Debugging ("how long is this conversation?")
        - Analytics ("average conversation length")
        - Future feature: warn user when approaching memory limit
        
        Returns 0 if session doesn't exist (not an error).
        """
        return len(self._store.get(session_id))

    def session_exists(self, session_id: str) -> bool:
        """
        Checks if a session has any history.
        
        Useful for:
        - Deciding whether to show "continue conversation" UI
        - Validating session IDs in routes
        - Avoiding unnecessary store lookups
        """
        return self._store.exists(session_id)

    # ── Private helper ────────────────────────────────────────────

    def _format_history_for_display(
        self,
        session_id: str
    ) -> list[dict]:
        """
        Converts LangChain message objects to plain dicts.
        
        Why does this exist?
        AgentService needs LangChain objects (get_history returns those).
        But if you ever need to:
        - Send history over HTTP (API response)
        - Store in a database (serialize to JSON)
        - Display in logs
        
        You need plain dicts, not LangChain objects.
        
        LangChain objects → plain dicts:
        HumanMessage(content="find PDFs") 
            → {"role": "user", "content": "find PDFs"}
        AIMessage(content="Found 3 files...")
            → {"role": "assistant", "content": "Found 3 files..."}
        
        This is a private method because it's a utility —
        external callers get the right format automatically
        from the public methods.
        """
        history = self._store.get(session_id)
        formatted = []

        for message in history:
            if isinstance(message, HumanMessage):
                formatted.append({
                    "role": "user",
                    "content": message.content,
                })
            elif isinstance(message, AIMessage):
                formatted.append({
                    "role": "assistant",
                    "content": message.content,
                })

        return formatted