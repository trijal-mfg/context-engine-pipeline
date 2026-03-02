import asyncio
import logging
from typing import List

import httpx

from chunking.chunker import Chunk
from confluence.config import OLLAMA_BASE_URL, OLLAMA_RERANK_MODEL

logger = logging.getLogger(__name__)

# Qwen3-Reranker uses a yes/no format it was trained on.
# "yes" → 1.0, "no" → 0.0. The model outputs after a <think> block.
_SYSTEM_PROMPT = (
    "Judge whether the Document meets the requirements based on the Query and the Instruct "
    "provided by user. Note that the answer can only be \"yes\" or \"no\"."
)

_PROMPT_TEMPLATE = """\
<|im_start|>system
{system}<|im_end|>
<|im_start|>user
<Instruct>: Given a search query, retrieve relevant passages that answer the query
<Query>: {query}
<Document>: {passage}<|im_end|>
<|im_start|>assistant
<think></think>
"""


class OllamaReranker:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_RERANK_MODEL):
        self.base_url = base_url
        self.model = model

    async def score_batch(self, query: str, chunks: List[Chunk]) -> List[float]:
        """Score all (query, chunk) pairs concurrently. Returns scores in the same order as chunks."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = [self._score_one(client, query, chunk) for chunk in chunks]
            return await asyncio.gather(*tasks)

    async def _score_one(self, client: httpx.AsyncClient, query: str, chunk: Chunk) -> float:
        prompt = _PROMPT_TEMPLATE.format(
            system=_SYSTEM_PROMPT, query=query, passage=chunk.text
        )
        try:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            raw = response.json()["response"].strip().lower()
            # Model outputs "yes" or "no" after its <think> block
            if "yes" in raw:
                return 1.0
            elif "no" in raw:
                return 0.0
            # Fallback: try parsing a float in case model deviated
            return float(raw)
        except (ValueError, KeyError, httpx.HTTPError) as e:
            logger.warning(f"Reranker scoring failed for chunk {chunk.id}: {e}")
            return 0.0
