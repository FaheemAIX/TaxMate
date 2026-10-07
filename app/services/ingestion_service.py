import re
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

RAW_PDF_DIR = Path("app/data/raw_pdfs")
PERSIST_DIR = "app/data/chroma_db"

ORDINANCE_BODY_END_PAGE = 521  # pages beyond this are Schedules (ordinance-specific)

RUNNING_HEADER_PATTERN = re.compile(
    r"(Chapter [IVXL]+|First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|"
    r"Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth) "
    r"[\w\s–\-]*?_{5,}\s*\d+"
)

SECTION_SPLIT_PATTERN = re.compile(
    r"(?=(?:^|\n)\s*(?:\d+\[)?\d{1,3}[A-Z]{0,2}\.\s+[A-Z][a-zA-Z \-]+\.\s*[—\-])"
)

SCHEDULE_DIVISION_PATTERN = re.compile(
    r"(?=(?:^|\n)\s*(?:\d+\[)?\s*(?:PART[- ]|Division\s)[IVXLC]+[A-Z]{0,2}\b)"
)


def load_documents():
    documents = []
    for pdf_path in RAW_PDF_DIR.glob("*.pdf"):
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        documents.extend(pages)
    return documents


def clean_page_text(raw_text: str) -> str:
    return RUNNING_HEADER_PATTERN.sub("", raw_text).strip()


def _chunks_to_documents(raw_chunks, source_name):
    return [
        Document(page_content=chunk, metadata={"source": source_name})
        for chunk in raw_chunks
    ]


def process_ordinance_pdf(documents, source_name):
    """Ordinance-specific: split into body (by legal section) + schedules (by division)."""
    body_pages = [d for d in documents if d.metadata.get("page", 0) <= ORDINANCE_BODY_END_PAGE]
    schedule_pages = [d for d in documents if d.metadata.get("page", 0) > ORDINANCE_BODY_END_PAGE]

    body_text = "\n".join(clean_page_text(d.page_content) for d in body_pages)
    schedule_text = "\n".join(clean_page_text(d.page_content) for d in schedule_pages)

    body_chunks = [s.strip() for s in SECTION_SPLIT_PATTERN.split(body_text) if len(s.strip()) >= 30]
    schedule_chunks = [s.strip() for s in SCHEDULE_DIVISION_PATTERN.split(schedule_text) if len(s.strip()) >= 50]

    return _chunks_to_documents(body_chunks, source_name) + _chunks_to_documents(schedule_chunks, source_name)


def process_generic_table_pdf(documents, source_name):
    """For documents like the rate card: one table-heading pattern throughout."""
    TABLE_HEADER_PATTERN = re.compile(
        r"(?=(?:Rate[s]? (?:of|for)|Tax Rate[s]? (?:of|for)).{0,120}?\(Section)"
    )
    full_text = "\n".join(clean_page_text(d.page_content) for d in documents)
    chunks = [s.strip() for s in TABLE_HEADER_PATTERN.split(full_text) if len(s.strip()) >= 20]
    return _chunks_to_documents(chunks, source_name)


DOCUMENT_PROCESSOR_MAP = {
    "2026724177725705IncomeTaxOrdinanace2001_2026_latest.pdf": process_ordinance_pdf,
    "Tax_Rate_Card_for_Tax_Year_2025_26.pdf": process_generic_table_pdf,
}

def build_vector_store():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )

    all_documents = []

    for pdf_path in RAW_PDF_DIR.glob("*.pdf"):
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        source_name = pdf_path.name

        processor = DOCUMENT_PROCESSOR_MAP.get(pdf_path.name, process_generic_table_pdf)
        all_documents.extend(processor(pages, source_name))

    vector_store = Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    print(f"Stored {len(all_documents)} chunks from {len(list(RAW_PDF_DIR.glob('*.pdf')))} PDF(s)")
    return vector_store