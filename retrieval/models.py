from dataclasses import dataclass, field
from typing import List

from chunking.chunker import Chunk


@dataclass
class RankedChunk:
    chunk: Chunk
    score: float
    context: List[Chunk] = field(default_factory=list)  # adjacent chunks, sorted by chunk_index, excludes self


@dataclass
class RetrievalResult:
    query: str
    results: List[RankedChunk]  # sorted by score descending
