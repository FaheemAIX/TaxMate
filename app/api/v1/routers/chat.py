'''
api/routers/chat.py is like a Resturant's Waiter: It takes the customer's question, checks it against the Menu (schema), and hands the request to the kitchen. Waiters do not cook. Your router should never contain AI logic or math.
'''

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import process_query

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    result = process_query(request.query)
    return ChatResponse(**result)