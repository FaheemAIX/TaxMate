'''
schemas/chat.py is like the Resturant's Menu: It defines exactly what the customer is allowed to order (the query) and exactly what they will get back (the answer and sources).
'''

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for the conversation session")
    query: str = Field(..., min_length=3, description="User question about FBR tax laws")

class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)