from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

PERSIST_DIR = "app/data/chroma_db"
BATCH_SIZE = 64

def get_vector_store() -> Chroma:
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )
    return Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)

def get_indexed_state() -> dict:
    """Reads metadata to see what files and chunks are currently in the DB."""
    data = get_vector_store().get(include=["metadatas"])
    state = {}
    for meta in data["metadatas"]:
        entry = state.setdefault(
            meta["source"], {"fingerprints": set(), "count": 0, "total": 0}
        )
        entry["fingerprints"].add(meta.get("fingerprint", ""))
        entry["count"] += 1
        entry["total"] = max(entry["total"], meta.get("chunk_total", 0))
    return state

def delete_source(source: str) -> int:
    """Deletes all chunks belonging to a specific PDF."""
    store = get_vector_store()
    ids = store.get(where={"source": source})["ids"]
    for start in range(0, len(ids), 1000):
        store.delete(ids=ids[start:start + 1000])
    return len(ids)

def add_chunks(chunks: list[Document], source: str) -> None:
    """Embeds and saves new chunks in small batches."""
    store = get_vector_store()
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        ids = [f"{source}::{start + i}" for i in range(len(batch))]
        store.add_documents(batch, ids=ids)