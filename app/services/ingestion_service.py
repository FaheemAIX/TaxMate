from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

RAW_PDF_DIR = Path("app/data/raw_pdfs")

def load_documents():
    documents = []
    pdf_files = list(RAW_PDF_DIR.glob("*.pdf"))

    for pdf_path in pdf_files:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        documents.extend(pages)

    return documents

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\nSection", "\nSECTION", "\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_documents(documents)
    return chunks

PERSIST_DIR = "app/data/chroma_db"

def get_embedding_model():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )

def build_vector_store(chunks):
    embeddings = get_embedding_model()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    return vector_store