from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import asdict

from chunking.chunker import Chunk

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]):
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], limit: int = 5) -> List[Chunk]:
        pass

class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self.store = {} # id -> (chunk, embedding)

    def upsert(self, chunks: List[Chunk], embeddings: List[List[float]]):
        for chunk, embedding in zip(chunks, embeddings):
            self.store[chunk.id] = {
                "chunk": chunk,
                "embedding": embedding
            }
        print(f"Stored {len(chunks)} chunks in memory.")

    def search(self, query_embedding: List[float], limit: int = 5) -> List[Chunk]:
        # Dummy search
        return [data["chunk"] for data in list(self.store.values())[:limit]]
