import json
import re

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.db.vector_store import get_vector_store
from app.schemas.intent import QueryIntent
from app.services.tax_calculator import (
    calculate_salaried_tax,
    calculate_aop_tax,
    calculate_property_rental_tax,
)

TAX_FUNCTION_MAP = {
    "salaried": calculate_salaried_tax,
    "aop": calculate_aop_tax,
    "property_rental": calculate_property_rental_tax,
}

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Pakistani tax assistant.
Given a user's question, determine:
1. intent_type: "calculation" (needs exact tax math), "conceptual" (needs explanation of rules), or "both"
2. If income is mentioned, convert it to annual_income in PKR (e.g. "250,000 a month" = 3000000 annual, "2.5 million" = 2500000)
3. person_type: "salaried" if they mention salary/employer, "aop" if self-employed/business, "property_rental" if about rental income. null if unclear or not applicable.

Respond ONLY with valid JSON matching this exact shape, no other text:
{"intent_type": "...", "annual_income": <number or null>, "person_type": "..." or null, "reasoning": "..."}
"""

FINAL_ANSWER_SYSTEM_PROMPT = """You are TaxMate, a highly accurate assistant that explains Pakistani tax \
law in clear, structured language for people who are not tax experts. You are given the user's question, \
and possibly a calculated tax result and/or text retrieved from official documents.

Rules:
- Use ONLY the calculated result and the provided context. Never use outside knowledge, \
  especially for rates, thresholds, or who a rule applies to.
- Each piece of context starts with a source filename. The sources are the Income Tax \
  Ordinance 2001, the Income Tax Rules 2002, the Budget 2026-27 Salient Features, and a Tax Year 2027 Rate Card.
- CONFLICT RESOLUTION: The Budget 2026-27 Salient Features and the Tax Year 2027 Rate Card represent \
  the newest, legally binding amendments. They OVERRIDE older figures in the Ordinance or Rules. \
  State the newest rule and mention it is the updated 2026-27 rule. Ignore historical amendment text \
  (e.g., "omitted by Finance Act").
- COMPREHENSIVENESS & STRUCTURE: If a query involves violations, late filings, or fines, you MUST explicitly \
  distinguish between different legal concepts (e.g., "Penalties" vs "ATL Surcharges" vs "Default Surcharges"). \
  Break your answer down using bold headers, bullet points, statutory minimums/maximums, and exceptions.
- CITATIONS: You must cite the specific Section numbers and append bracketed citations (e.g., [1], [2]) \
  at the end of sentences to show which retrieved chunk provided the information.
- If a calculation result is provided, state the exact tax amount and explain how it was derived.
- If the context does not contain the complete information needed, provide what you have and clearly add: \
  "I couldn't find the remaining details in the official documents I have."
- End with one short sentence saying this is general information, not professional tax advice.
"""

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=settings.openai_api_key)


def detect_intent(query: str) -> QueryIntent:
    response = get_llm().invoke([("system", INTENT_SYSTEM_PROMPT), ("human", query)])
    raw = response.content.strip()
    # The model sometimes wraps its JSON in ```json ... ``` - remove that if present
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return QueryIntent(**json.loads(raw))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def hybrid_search(query: str, k: int = 5, candidate_pool: int = 20) -> list[Document]:
    """
    Search in two ways and combine the results:
      1) meaning-based search (embeddings)   - finds related ideas
      2) keyword search (BM25)               - finds exact words like "surcharge"
    A chunk that ranks well in BOTH lists wins (this is called Reciprocal Rank Fusion).
    """
    store = get_vector_store()

    semantic_docs = store.similarity_search(query, k=candidate_pool)

    stored = store.get()
    all_texts, all_metas = stored["documents"], stored["metadatas"]
    if not all_texts:
        return []
    bm25 = BM25Okapi([_tokenize(text) for text in all_texts])
    scores = bm25.get_scores(_tokenize(query))
    best_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:candidate_pool]
    keyword_docs = [Document(page_content=all_texts[i], metadata=all_metas[i]) for i in best_indexes]

    combined = {}
    for ranked_list in (semantic_docs, keyword_docs):
        for rank, doc in enumerate(ranked_list):
            entry = combined.setdefault(doc.page_content, {"doc": doc, "score": 0.0})
            entry["score"] += 1.0 / (60 + rank)  # higher rank -> bigger score

    best = sorted(combined.values(), key=lambda entry: entry["score"], reverse=True)[:k]
    return [entry["doc"] for entry in best]


def process_query(query: str) -> dict:
    intent = detect_intent(query)

    # 1) exact calculation (no AI involved in the maths)
    calculation_result = None
    missing_info = False
    if intent.intent_type in ("calculation", "both"):
        if intent.person_type and intent.annual_income:
            calculation_result = TAX_FUNCTION_MAP[intent.person_type](intent.annual_income)
        else:
            missing_info = True

    # 2) retrieve explanations from the documents
    retrieved_chunks = []
    if intent.intent_type in ("conceptual", "both"):
        retrieved_chunks = hybrid_search(query, k=5)

    # 3) build one prompt from whatever we have
    parts = [f"User question: {query}"]
    if calculation_result:
        parts.append(f"Calculated result: {calculation_result}")
    if missing_info:
        parts.append("Note: the user's income or taxpayer type could not be determined.")
    if retrieved_chunks:
        context = "\n\n---\n\n".join(chunk.page_content for chunk in retrieved_chunks)
        parts.append(f"Context from official documents:\n{context}")

    response = get_llm().invoke([("system", FINAL_ANSWER_SYSTEM_PROMPT), ("human", "\n\n".join(parts))])

    return {
        "answer": response.content,
        "calculation": calculation_result,
        "sources": [
            {"content": chunk.page_content[:300], "source": chunk.metadata.get("source", "unknown")}
            for chunk in retrieved_chunks
        ],
    }