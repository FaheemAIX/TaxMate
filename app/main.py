'''
main.py is like the Resturant's Front Door Manager: It turns on the lights, opens the app, and directs incoming traffic to the right section.
'''

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from app.core.config import settings
from app.api.v1.routers import chat, calculator, admin
from app.services.ingestion_service import sync_documents

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run the sync process once on server startup
    print("Starting document sync...")
    report = await asyncio.to_thread(sync_documents)
    print("Document sync complete:", report)
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(calculator.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": f"{settings.app_name} API is running"}