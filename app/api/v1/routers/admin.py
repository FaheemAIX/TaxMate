from fastapi import APIRouter
from app.services.ingestion_service import sync_documents
from app.db.vector_store import get_indexed_state

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/sync")
def run_sync():
    """Manually trigger a sync of the raw_pdfs folder with ChromaDB."""
    return sync_documents()

@router.get("/documents")
def list_documents():
    """See exactly what is currently indexed in ChromaDB."""
    return {src: {"chunks": e["count"]} for src, e in get_indexed_state().items()}