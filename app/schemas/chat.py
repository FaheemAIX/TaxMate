'''
schemas/chat.py is like the Resturant's Menu: It defines exactly what the customer is allowed to order (the query) and exactly what they will get back (the answer and sources).
'''

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, description="User's tax-related question in plain language")

class SourceChunk(BaseModel):
    content: str
    source: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk] = []