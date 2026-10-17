'''
api/routers/chat.py is like a Resturant's Waiter: It takes the customer's question, checks it against the Menu (schema), and hands the request to the kitchen. Waiters do not cook. Your router should never contain AI logic or math.
'''

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import process_query, stream_query
import logging

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    try:
        # Pass both the query and the session_id to your service
        result = process_query(request.query, request.session_id)
        
        formatted_sources = [
            f"{s['source']} (Content: {s['content'][:100]}...)" 
            for s in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=formatted_sources
        )
    except Exception as e:
        logging.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred.")

# Add this new streaming route:
@router.post("/stream")
def ask_question_stream(request: ChatRequest):
    try:
        # media_type="text/event-stream" tells the browser to keep the connection open
        return StreamingResponse(
            stream_query(request.query, request.session_id), 
            media_type="text/event-stream"
        )
    except Exception as e:
        logging.error(f"Error processing streaming query: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred.")