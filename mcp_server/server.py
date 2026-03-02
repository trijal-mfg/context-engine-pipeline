import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Must come before any local imports — adds project root to sys.path so that
# packages like `chunking`, `retrieval`, `embedding`, etc. are resolvable
# regardless of the working directory when this script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from chunking.chunker import Chunk
from confluence.config import setup_logging
from embedding.embedder import OllamaEmbedder
from embedding.qdrant_vector_store import QdrantVectorStore
from retrieval import OllamaReranker, RetrievalResult, Retriever

setup_logging()
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "confluence-retriever",
    instructions=(
        "Search the Confluence knowledge base for relevant documentation. "
        "Use search_confluence to retrieve semantically similar passages given a natural language query. "
        "Each result includes the matched chunk, a relevance score, and surrounding context chunks."
    ),
)

# Singletons — initialized once at server startup
_embedder = OllamaEmbedder()
_vector_store = QdrantVectorStore()
_reranker = OllamaReranker()
_retriever = Retriever(
    embedder=_embedder,
    vector_store=_vector_store,
    reranker=_reranker,
)


def _serialize_chunk(c: Chunk) -> dict:
    return {
        "id": c.id,
        "doc_id": c.doc_id,
        "chunk_index": c.chunk_index,
        "text": c.text,
        "metadata": c.metadata,
    }


def _serialize_result(result: RetrievalResult) -> dict:
    return {
        "query": result.query,
        "results": [
            {
                "score": rc.score,
                "chunk": _serialize_chunk(rc.chunk),
                "context": [_serialize_chunk(c) for c in rc.context],
            }
            for rc in result.results
        ],
    }


@mcp.tool()
async def search_confluence(
    query: str,
    top_k: int = 5,
    space_key: Optional[str] = None,
    rerank: bool = False,
) -> str:
    """Search the Confluence knowledge base for passages relevant to a query.

    Args:
        query: Natural language search query.
        top_k: Number of results to return (default 5).
        space_key: Optional Confluence space key to restrict search (e.g. "ENG", "OPS").
        rerank: Whether to rerank results using Qwen3-Reranker for higher accuracy (slower).

    Returns:
        JSON string with ranked results. Each result contains:
        - score: relevance score (1.0 = relevant, 0.0 = not relevant when reranking)
        - chunk: the matched passage with id, doc_id, chunk_index, text, and metadata
        - context: adjacent chunks from the same document for surrounding context
    """
    logger.info(f"search_confluence called: query={query!r} top_k={top_k} space_key={space_key} rerank={rerank}")
    result = await _retriever.retrieve(query, rerank=rerank, top_k=top_k, space_key=space_key)
    return json.dumps(_serialize_result(result), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
