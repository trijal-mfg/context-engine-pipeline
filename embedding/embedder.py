from abc import ABC, abstractmethod
from typing import List

class Embedder(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


import httpx
from confluence.config import OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL

class OpenAIEmbedder(Embedder):
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.model = model
        # self.client = OpenAI(api_key=api_key) # Placeholder for actual client
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Placeholder implementation
        print(f"Embedding {len(texts)} texts using {self.model}")
        return [[0.1] * 1536 for _ in texts]

    @property
    def dimension(self) -> int:
        return 1536

class OllamaEmbedder(Embedder):
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_EMBEDDING_MODEL):
        self.base_url = base_url
        self.model = model
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            embeddings.append(embedding)
        return embeddings

    @property
    def dimension(self) -> int:
        # Check model dimension? For nomic-embed-text it's 768.
        #TODO implent properly
        return 768 

