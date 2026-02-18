import logging
import json
from typing import Dict, Any, Type, Union, TypeVar

from openai import AsyncOpenAI
import instructor
from pydantic import BaseModel

from config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class OllamaClient:
    """
    Async wrapper for Ollama API interaction using Instructor for structured output.
    """
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout: int = OLLAMA_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Initialize Instructor-patched OpenAI client
        # Ollama provides an OpenAI-compatible API at /v1
        self.client = instructor.patch(
            AsyncOpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama",  # Required but ignored by Ollama
                timeout=self.timeout
            ),
            mode=instructor.Mode.JSON
        )

    async def generate(self, prompt: str, model: str, response_model: Type[T]) -> T:
        """
        Generate a structured response from the LLM matching the Pydantic model.
        """
        try:
            return await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_model=response_model,
                max_retries=3
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise e
