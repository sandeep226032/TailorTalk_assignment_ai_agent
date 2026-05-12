# This file ONLY does:
# 1. Receive HTTP request
# 2. Validate it (Pydantic does this automatically)
# 3. Call the service
# 4. Return HTTP response
# NOTHING else — no business logic here

from fastapi import APIRouter, HTTPException
from models.request import ChatRequest, ClearRequest
from models.response import ChatResponse
from services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()

@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    # Controller just calls service and returns
    response = await chat_service.process_message(
        session_id=request.session_id,
        message=request.message
    )
    return response

@router.post("/clear")
async def clear_chat(request: ClearRequest):
    await chat_service.clear_session(request.session_id)
    return {"status": "cleared"}