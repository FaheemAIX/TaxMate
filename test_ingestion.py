from app.services.ingestion_service import load_documents, split_documents, build_vector_store

docs = load_documents()
chunks = split_documents(docs)
vector_store = build_vector_store(chunks)

print(f"Stored {len(chunks)} chunks in vector DB")

# quick similarity search test
results = vector_store.similarity_search("income tax on salary", k=2)
for r in results:
    print("---")
    print(r.page_content[:200])
    print(r.metadata)