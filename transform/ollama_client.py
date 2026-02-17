import aiohttp
import logging
from typing import Dict, Any, Optional
import json

from config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

class OllamaClient:
    """
    Async wrapper for Ollama API interaction.
    """
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout: int = OLLAMA_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def generate(self, prompt: str, model: str, format: str = "json") -> Dict[str, Any]:
        """
        Generate a response from the LLM. 
        Forces JSON format by default to ensure structured output.
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": format,
            "options": {
                "temperature": 0.0, # Deterministic output
                "num_predict": 4096  # Allow long context for transformations
            }
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "response" not in result:
                        raise ValueError(f"Invalid response from Ollama: {result}")
                        
                    try:
                        return json.loads(result["response"])
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode JSON from Ollama response: {result['response']}")
                        raise ValueError(f"LLM did not return valid JSON: {e}")

        except aiohttp.ClientError as e:
            logger.error(f"Ollama API request failed: {e}")
            raise ConnectionError(f"Failed to communicate with Ollama at {self.base_url}: {e}")
