from typing import Dict, Any, List, Type, Union
from pydantic import BaseModel
import logging
import json
import hashlib

from ollama_client import OllamaClient
from config import OLLAMA_MODEL_TRANSFORMER

logger = logging.getLogger(__name__)

class Transformer:
    """
    Transforms a Canonical Raw Document using single-pass extraction into specific types.
    """
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    async def transform(self, canonical_doc: Dict[str, Any], available_models: List[Type[BaseModel]]) -> Any:
        """
        Executes the LLM transformation using dynamically loaded Pydantic models.
        """
        if not available_models:
             raise ValueError("No schema models available for transformation")

        # Dynamically create the Union type
        # In Python 3.10+ we could use X | Y | Z, but simpler here is Union[tuple(models)]
        # However, Instructor/Pydantic works best if we pass the Union directly or Iterable
        
        # Construct the Union type
        DynamicUnion = Union[tuple(available_models)] # type: ignore
        
        prompt = self._construct_prompt(canonical_doc)
        
        try:
            # Single-pass extraction using Dynamic Union
            response = await self.ollama.generate(
                prompt=prompt, 
                model=OLLAMA_MODEL_TRANSFORMER,
                response_model=DynamicUnion
            )
            return response
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise e
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise e

    def _construct_prompt(self, doc: Dict[str, Any]) -> str:
        """
        Builds the transformation prompt.
        """
        # We don't need to pass the schema JSON anymore because Instructor handles it.
        # We just need to present the document clearly.
        
        # Strip potentially massive usage of token space if needed, 
        # but for now we assume it fits or is chunked elsewhere.
        
        return f"""
        You are an expert data extraction engine.
        Analyze the following document and extract the relevant information into the correct structure.
        
        Determine if the document is a 'Runbook', 'Incident Ticket', or just a 'General Document'.
        Extract all fields accurately.
        
        Document Context:
        Title: {doc.get('title', 'Unknown')}
        Source ID: {doc.get('source_id', 'Unknown')}
        
        Document Content:
        {json.dumps(doc, indent=2)}
        """

    def compute_hash(self, doc: Dict[str, Any], model: str) -> str:
        """
        Computes a hash of the inputs to the transformation.
        """
        content_str = json.dumps(doc, sort_keys=True)
        # Schema ID is no longer an input variable since we infer it, 
        # but the code logic might still want to track what it became.
        # For the input hash, we just care about the doc and the model version.
        data = f"{content_str}|{model}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
