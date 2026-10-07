from app.services.rag_service import answer_query

questions = [
    "How much income tax do I pay on a monthly salary of 100,000 PKR?",
    "What tax do I pay if I sell a property I've owned for 3 years?",
]

for q in questions:
    answer, chunks = answer_query(q)
    print(f"Q: {q}")
    print(f"A: {answer}")
    print(f"Sources: {[c.metadata for c in chunks]}")
    print("---")