from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

PERSIST_DIR = "app/data/chroma_db"

SYSTEM_PROMPT = """You are TaxMate, a helpful assistant that explains Pakistani tax law \
in simple, plain language for ordinary people who are not tax experts.

Rules:
- Only use the information in the provided context to answer.
- If the context does not contain enough information to answer, say so clearly \
  instead of guessing.
- Explain in simple everyday language, avoiding legal jargon where possible.
- Do not invent tax rates, exemptions, or numbers that are not in the context.
"""

def get_vector_store():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )
    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )

def answer_query(query: str, k: int = 4):
    vector_store = get_vector_store()
    relevant_chunks = vector_store.similarity_search(query, k=k)

    context_text = "\n\n---\n\n".join(chunk.page_content for chunk in relevant_chunks)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key
    )

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"Context:\n{context_text}\n\nQuestion: {query}")
    ]

    response = llm.invoke(messages)

    return response.content, relevant_chunks