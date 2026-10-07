from app.services.ingestion_service import build_vector_store

vector_store = build_vector_store()

results = vector_store.similarity_search("tax on sale of immovable property", k=3)
for r in results:
    print("---")
    print(r.metadata)
    print(r.page_content[:300])