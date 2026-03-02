import asyncio
from confluence.config import setup_logging
from embedding.embedder import OllamaEmbedder
from embedding.qdrant_vector_store import QdrantVectorStore
from retrieval import OllamaReranker, Retriever


async def main():
    setup_logging()

    embedder = OllamaEmbedder()
    vector_store = QdrantVectorStore()
    reranker = OllamaReranker()

    retriever = Retriever(
        embedder=embedder,
        vector_store=vector_store,
        reranker=reranker,
        initial_candidates=20,
        top_k=5,
        context_window=2,
    )

    query = "redis crash"
    print(f"\nQuery: '{query}'\n{'='*60}")

    result = await retriever.retrieve(query, top_k=5)
    print(result)
    # for i, ranked in enumerate(result.results, 1):
    #     print(f"\n[{i}] Score: {ranked.score:.3f}")
    #     print(f"    Chunk ID:  {ranked.chunk.id}")
    #     print(f"    Doc ID:    {ranked.chunk.doc_id}")
    #     print(f"    Section:   {ranked.chunk.metadata.get('section_heading')}")
    #     print(f"    Text:      {ranked.chunk.text[:120]}...")
    #     if ranked.context:
    #         print(f"    Context chunks ({len(ranked.context)}):")
    #         for ctx in ranked.context:
    #             print(f"      [idx={ctx.chunk_index}] {ctx.text[:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
