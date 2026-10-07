'''
main.py is like the Resturant's Front Door Manager: It turns on the lights, opens the app, and directs incoming traffic to the right section.
'''

from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.routers import chat, calculator

app = FastAPI(title=settings.app_name)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(calculator.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": f"{settings.app_name} API is running"}