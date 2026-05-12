from pydantic import BaseModel, Field
class ChatResponse(BaseModel):
    session_id: str
    response: str
    sources_found: int = 0      # Extra metadata

class HealthResponse(BaseModel):
    status: str
    version: str