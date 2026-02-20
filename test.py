import asyncio
from embedding.qdrant_vector_store import QdrantVectorStore
from embedding.embedder import OllamaEmbedder

async def main():
    # Initialize components
    vector_store = QdrantVectorStore()
    embedder = OllamaEmbedder()
    
    query = "confluence"
    print(f"Querying for: '{query}'")

    # Generate embedding
    embeddings = embedder.embed_texts([query])
    query_embedding = embeddings[0]
    
    # Test 1: Search without filter
    print("\n--- Search Results (No Filter) ---")
    results = await vector_store.search(query_embedding, limit=5)
    for chunk in results:
        print(f"ID: {chunk.id} | Space: {chunk.metadata.get('space_key')} | Score: {chunk.metadata.get('score', 'N/A')}")
        print(f"Text snippet: {chunk.text[:100]}...\n")

    # Test 2: Search with space_key filter (if you have data)
    # print("\n--- Search Results (Filter space_key='ENG') ---")
    # results_eng = await vector_store.search(query_embedding, limit=5, space_key="ENG")
    # for chunk in results_eng:
    #     print(f"ID: {chunk.id} | Space: {chunk.metadata.get('space_key')}")

if __name__ == "__main__":
    asyncio.run(main())