import json
import re

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.db.vector_store import get_vector_store
from app.schemas.intent import QueryIntent
from app.services.tax_calculator import (
    calculate_salaried_tax,
    calculate_aop_tax,
    calculate_property_rental_tax,
)

# Initialize the Careful Reader (Cross-Encoder)
reranker = CrossEncoder('BAAI/bge-reranker-base')

TAX_FUNCTION_MAP = {
    "salaried": calculate_salaried_tax,
    "aop": calculate_aop_tax,
    "property_rental": calculate_property_rental_tax,
}

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Pakistani tax assistant.
Given a user's question (and optional recent conversation history), determine:
1. intent_type: MUST be exactly "calculation" (needs tax math), "conceptual" (rules, explanations, greetings, or general chat), or "both". NEVER return null.
2. annual_income: Convert the user's income to an annual PKR amount. 
   - CRITICAL DEFAULT RULE: If the user provides a number (e.g., "2500000") without explicitly stating "monthly" or "per month", you MUST assume it is already their ANNUAL income. Do not multiply it.
   - Only multiply by 12 if they explicitly say "monthly", "per month", or "a month".
3. person_type: "salaried" if they mention salary/employer, "aop" if self-employed/business, "property_rental" if about rental income. null if unclear or not applicable.

Respond ONLY with valid JSON matching this exact shape, no other text:
{"intent_type": "...", "annual_income": <number or null>, "person_type": "..." or null, "reasoning": "..."}
"""

FINAL_ANSWER_SYSTEM_PROMPT = """You are a highly accurate Pakistani Tax Advisor specializing in the Tax Year 2027.

You will be provided with retrieved context from official sources. Each source has an index number (e.g., [1], [2]).

CRITICAL INSTRUCTIONS:
- You MUST append an inline citation immediately after stating a fact or rule derived from the context.
- Format the citation EXACTLY as a Markdown link pointing to "#", using the source number as the link text, and the source name as the title hover text.
- Example: "The advance tax rate for filers is 1.5% [1](# "Salient Features Budget 2026-27")."

CONFLICT RESOLUTION & HIERARCHY:
1. HIGHEST PRIORITY: "Tax Rate Card TY2027" and "Salient Features Budget 2026-27".
2. LOWEST PRIORITY: "Income Tax Ordinance 2001". 
- If the Salient Features document updates or contradicts the Ordinance, IGNORE the Ordinance and use the Salient Features.

CALCULATOR RULES (STRICTLY ENFORCED):
- If the prompt includes a "Calculated result" dictionary, you MUST use those EXACT numbers in your textual explanation. DO NOT perform your own arithmetic.
- Simply report the `fixed_tax_amount`, `marginal_rate`, `marginal_tax_amount`, and `total_tax_payable` exactly as they appear in the provided data.

HANDLING AMBIGUITY (NEW):
- If you receive a note stating "The user's income or taxpayer type could not be determined," DO NOT say "I don't know". 
- Instead, politely ask the user to clarify if their income is from Salary, Business (AOP), or Property Rental so you can perform the calculation.

Base your answers strictly on the provided context and the current Tax Year 2027 rules. If a rule is genuinely missing from the context, say you don't know.
"""

# In-memory session store (MVP). Swap with Redis or DB in production.
chat_histories: dict[str, list[tuple[str, str]]] = {}


def get_chat_history(session_id: str) -> list[tuple[str, str]]:
    """Retrieves the history for a given session, or creates a new one."""
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    return chat_histories[session_id]


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )


def detect_intent(query: str, history: list[tuple[str, str]] | None = None) -> QueryIntent:
    messages = [("system", INTENT_SYSTEM_PROMPT)]

    # Add conversation context if available to resolve follow-up queries
    if history:
        for past_q, past_a in history[-2:]:
            messages.append(("human", past_q))
            messages.append(("ai", past_a))

    messages.append(("human", query))

    response = get_llm().invoke(messages)
    raw = response.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    
    try:
        return QueryIntent(**json.loads(raw))
    except Exception as e:
        print(f"Intent validation failed: {e}. Falling back to default chat.")
        # Safe fallback for greetings or misformatted LLM responses
        return QueryIntent(
            intent_type="conceptual", 
            annual_income=None, 
            person_type=None, 
            reasoning="Fallback due to parsing error"
        )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def hybrid_search(query: str, k: int = 5, candidate_pool: int = 20) -> list[Document]:
    """
    Search in two ways and combine the results:
      1) meaning-based search (embeddings)   - finds related ideas
      2) keyword search (BM25)               - finds exact words like "surcharge"
    Combines results using Reciprocal Rank Fusion (RRF).
    """
    store = get_vector_store()

    semantic_docs = store.similarity_search(query, k=candidate_pool)

    stored = store.get()
    all_texts, all_metas = stored["documents"], stored["metadatas"]
    if not all_texts:
        return []

    bm25 = BM25Okapi([_tokenize(text) for text in all_texts])
    scores = bm25.get_scores(_tokenize(query))
    best_indexes = sorted(
        range(len(scores)), key=lambda i: scores[i], reverse=True
    )[:candidate_pool]
    keyword_docs = [
        Document(page_content=all_texts[i], metadata=all_metas[i])
        for i in best_indexes
    ]

    combined = {}
    for ranked_list in (semantic_docs, keyword_docs):
        for rank, doc in enumerate(ranked_list):
            entry = combined.setdefault(doc.page_content, {"doc": doc, "score": 0.0})
            entry["score"] += 1.0 / (60 + rank)

    best = sorted(combined.values(), key=lambda entry: entry["score"], reverse=True)[:k]
    return [entry["doc"] for entry in best]

def retrieve_and_rerank(query: str, top_k: int = 5) -> list:
    """
    Pulls a wider net of documents, then scores them precisely against the query.
    """
    # 1. The Fast Sorter: Pull 15 broad candidates instead of just 5
    broad_candidates = hybrid_search(query, k=15)
    
    if not broad_candidates:
        return []

    # 2. Prepare pairs for the Careful Reader: [["Query", "Doc Text 1"], ["Query", "Doc Text 2"]]
    pairs = [[query, chunk.page_content] for chunk in broad_candidates]
    
    # 3. Score the pairs using the Cross-Encoder
    scores = reranker.predict(pairs)
    
    # 4. Attach scores to the original chunks and sort them highest to lowest
    scored_chunks = list(zip(broad_candidates, scores))
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    
    # 5. Extract just the documents for the top_k winners
    best_chunks = [chunk for chunk, score in scored_chunks[:top_k]]
    
    return best_chunks


def process_query(query: str, session_id: str = "default") -> dict:
    history = get_chat_history(session_id)
    intent = detect_intent(query, history=history)

    # 1) Exact calculation (deterministic math)
    calculation_result = None
    missing_info = False
    if intent.intent_type in ("calculation", "both"):
        if intent.person_type and intent.annual_income:
            calculation_result = TAX_FUNCTION_MAP[intent.person_type](intent.annual_income)
        else:
            missing_info = True

    # 2) Retrieve explanations from documents
    retrieved_chunks = []
    if intent.intent_type in ("conceptual", "both"):
        retrieved_chunks = retrieve_and_rerank(query, top_k=5)

    # 3) Format retrieved context with numbered citation anchors
    context_blocks = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        # Extract the source filename or metadata
        src = chunk.metadata.get("source", "Unknown Document")
        src_lower = src.lower()
        
        # Dynamically assign the legal priority based on the document name
        if "salient" in src_lower or "budget" in src_lower:
            priority_tag = "HIGHEST PRIORITY (Newest Amendment - Overrides Base Law)"
        elif "rate" in src_lower or "card" in src_lower:
            priority_tag = "HIGHEST PRIORITY (Current TY2027 Rates)"
        elif "ordinance" in src_lower:
            priority_tag = "LOWEST PRIORITY (Base Law - Disregard if Salient Features contradict this)"
        else:
            priority_tag = "STANDARD PRIORITY"

        # Construct a highly structured, impossible-to-miss context block for the LLM
        block = (
            f"--- START OF SOURCE [{idx}] ---\n"
            f"Document Name: {src}\n"
            f"Legal Authority: {priority_tag}\n"
            f"Text:\n{chunk.page_content}\n"
            f"--- END OF SOURCE [{idx}] ---"
        )
        context_blocks.append(block)
        
    context_str = "\n\n".join(context_blocks)

    # 4) Construct message list with system prompt and history
    messages = [("system", FINAL_ANSWER_SYSTEM_PROMPT)]

    for past_q, past_a in history:
        messages.append(("human", past_q))
        messages.append(("ai", past_a))

    current_parts = [f"User question: {query}"]
    if calculation_result:
        current_parts.append(f"Calculated result: {calculation_result}")
    if missing_info:
        current_parts.append("Note: The user's income or taxpayer type could not be determined.")
    if context_str:
        current_parts.append(f"Context from official documents:\n{context_str}")

    messages.append(("human", "\n\n".join(current_parts)))

    # 5) Generate answer
    response = get_llm().invoke(messages)
    answer_text = response.content

    # 6) Update session history (retaining the last 5 conversation turns)
    history.append((query, answer_text))
    if len(history) > 5:
        history.pop(0)

    return {
        "answer": answer_text,
        "calculation": calculation_result,
        "sources": [
            {
                "index": idx,
                "content": chunk.page_content[:300],
                "source": chunk.metadata.get("source", "unknown"),
            }
            for idx, chunk in enumerate(retrieved_chunks, start=1)
        ],
    }

def stream_query(query: str, session_id: str = "default"):
    history = get_chat_history(session_id)
    intent = detect_intent(query, history=history)

    # 1) Exact calculation
    calculation_result = None
    missing_info = False
    if intent.intent_type in ("calculation", "both"):
        if intent.person_type and intent.annual_income:
            calculation_result = TAX_FUNCTION_MAP[intent.person_type](intent.annual_income)
        else:
            missing_info = True

    # 2) Retrieve context
    retrieved_chunks = []
    if intent.intent_type in ("conceptual", "both"):
        retrieved_chunks = retrieve_and_rerank(query, top_k=5)

    context_blocks = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        src = chunk.metadata.get("source", "unknown")
        context_blocks.append(f"[{idx}] Source: {src}\n{chunk.page_content}")
    context_str = "\n\n---\n\n".join(context_blocks)

    # 3) Build Prompt
    messages = [("system", FINAL_ANSWER_SYSTEM_PROMPT)]
    for past_q, past_a in history:
        messages.append(("human", past_q))
        messages.append(("ai", past_a))

    current_parts = [f"User question: {query}"]
    if calculation_result:
        current_parts.append(f"Calculated result: {calculation_result}")
    if missing_info:
        current_parts.append("Note: The user's income or taxpayer type could not be determined.")
    if context_str:
        current_parts.append(f"Context from official documents:\n{context_str}")

    messages.append(("human", "\n\n".join(current_parts)))

    # 4) Yield Metadata (Calculation & Sources) FIRST
    sources_data = [
        {"index": idx, "content": chunk.page_content[:300], "source": chunk.metadata.get("source", "unknown")}
        for idx, chunk in enumerate(retrieved_chunks, start=1)
    ]
    
    metadata = {
        "type": "metadata",
        "calculation": calculation_result,
        "sources": sources_data
    }
    yield f"data: {json.dumps(metadata)}\n\n"

    # 5) Stream LLM Text Tokens
    full_answer = ""
    for chunk in get_llm().stream(messages):
        if chunk.content:
            full_answer += chunk.content
            # Yield each text fragment
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.content})}\n\n"

    # 6) Save final assembled answer to history
    history.append((query, full_answer))
    if len(history) > 5:
        history.pop(0)