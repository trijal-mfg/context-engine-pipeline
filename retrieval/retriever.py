import asyncio
import logging
from typing import List, Optional

from chunking.chunker import Chunk
from embedding.embedder import Embedder
from embedding.qdrant_vector_store import QdrantVectorStore
from retrieval.models import RankedChunk, RetrievalResult
from retrieval.reranker import OllamaReranker

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: QdrantVectorStore,
        reranker: OllamaReranker,
        initial_candidates: int = 20,
        top_k: int = 5,
        context_window: int = 2,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker
        self.initial_candidates = initial_candidates
        self.top_k = top_k
        self.context_window = context_window

    async def retrieve(
        self,
        query: str,
        rerank: bool = False,
        top_k: Optional[int] = None,
        space_key: Optional[str] = None,
    ) -> RetrievalResult:
        k = top_k if top_k is not None else self.top_k

        # 1. Embed query (embedder is sync, run in thread pool)
        embeddings = await asyncio.to_thread(self.embedder.embed_texts, [query])
        query_embedding = embeddings[0]

        # 2. Fetch initial candidates from vector store
        candidates: List[Chunk] = await self.vector_store.search(
            query_embedding, limit=self.initial_candidates, space_key=space_key
        )
        logger.info(f"Retrieved {len(candidates)} candidates for reranking")

        if not candidates:
            return RetrievalResult(query=query, results=[])

        if rerank:
            # 3. Rerank candidates using Ollama LLM
            scores: List[float] = await self.reranker.score_batch(query, candidates)
        else:
            # If not reranking, assign a default score (e.g., 1.0) to all candidates
            scores = [1.0] * len(candidates)

        # 4. Sort by score descending, take top_k
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:k]

        # 5. Fetch adjacent context chunks for each top result (in parallel)
        context_tasks = [
            self.vector_store.get_adjacent_chunks(chunk.doc_id, chunk.chunk_index, self.context_window)
            for chunk, _ in ranked
        ]
        contexts: List[List[Chunk]] = await asyncio.gather(*context_tasks)

        # 6. Build result
        results = [
            RankedChunk(chunk=chunk, score=score, context=context)
            for (chunk, score), context in zip(ranked, contexts)
        ]

        logger.info(f"Returning {len(results)} ranked results")
        return RetrievalResult(query=query, results=results)
