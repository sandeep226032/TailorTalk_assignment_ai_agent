# Like a service in Node — knows HOW to do things
# Doesn't know about HTTP at all

from services.agent_service import AgentService
from services.memory_service import MemoryService
from models.response import ChatResponse

class ChatService:
    def __init__(self):
        self.agent_service = AgentService()
        self.memory_service = MemoryService()

    async def process_message(self, session_id: str, message: str) -> ChatResponse:
        history = self.memory_service.get_history(session_id)
        
        raw_response = await self.agent_service.run(
            message=message,
            history=history
        )
        
        self.memory_service.update_history(session_id, message, raw_response)
        
        return ChatResponse(
            session_id=session_id,
            response=raw_response,
        )

    async def clear_session(self, session_id: str):
        self.memory_service.clear(session_id)