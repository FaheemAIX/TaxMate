import hashlib
import logging
import threading
from pathlib import Path

import pymupdf4llm
from langchain_text_splitters import MarkdownTextSplitter
from app.db.vector_store import get_indexed_state, delete_source, add_chunks

logger = logging.getLogger(__name__)

RAW_PDF_DIR = Path("app/data/raw_pdfs")
_sync_lock = threading.Lock()
PIPELINE_VERSION = "1"  

def process_markdown_pdf(pdf_path: Path, source_name: str):
    """Converts a PDF to Markdown and chunks it by header structure."""
    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    
    splitter = MarkdownTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = splitter.create_documents([md_text])
    return chunks

def _fingerprint(path: Path) -> str:
    """Generates a unique hash based on file contents."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{digest[:16]}:v{PIPELINE_VERSION}"

def sync_documents() -> dict:
    """Synchronizes ChromaDB with the raw_pdfs folder."""
    with _sync_lock:
        report = {"added": [], "updated": [], "removed": [], "unchanged": []}
        files = {p.name: p for p in RAW_PDF_DIR.glob("*.pdf")}
        indexed = get_indexed_state()
        
        # 1. Remove documents no longer in the folder
        for source in list(indexed.keys()):
            if source not in files:
                delete_source(source)
                report["removed"].append(source)
                
        # 2. Add or update documents
        for name, path in files.items():
            fingerprint = _fingerprint(path)
            entry = indexed.get(name)
            
            # Skip if file is identical and fully ingested
            if entry and entry["fingerprints"] == {fingerprint} and entry["count"] == entry["total"]:
                report["unchanged"].append(name)
                continue
                
            # Delete old chunks if updating or fixing a broken ingestion
            if entry:
                delete_source(name)
                
            logger.info(f"Processing {name}...")
            chunks = process_markdown_pdf(path, name)
            
            if not chunks:
                continue
                
            # Stamp metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "source": name, 
                    "fingerprint": fingerprint, 
                    "chunk_total": len(chunks)
                })
                
            add_chunks(chunks, name)
            report["updated" if entry else "added"].append(name)
            
        return report