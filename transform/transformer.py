from typing import Dict, Any
import logging
import json
import hashlib

from ollama_client import OllamaClient
from config import OLLAMA_MODEL_TRANSFORMER

logger = logging.getLogger(__name__)

class Transformer:
    """
    Transforms a Canonical Raw Document into the structure defined by a Target Schema.
    """
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    async def transform(self, canonical_doc: Dict[str, Any], target_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the LLM transformation.
        Returns the raw dictionary (unvalidated).
        """
        
        prompt = self._construct_prompt(canonical_doc, target_schema)
        
        try:
            response = await self.ollama.generate(prompt, OLLAMA_MODEL_TRANSFORMER)
            return response
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise e

    def _construct_prompt(self, doc: Dict[str, Any], schema: Dict[str, Any]) -> str:
        """
        Builds the transformation prompt.
        """
        schema_json = schema.get("json_schema", {})
        
        return f"""
        You are a data transformation engine.
        Your task is to extract information from the Source Document and structure it EXACTLY according to the Target Schema.

        Target Schema (JSON Schema):
        {json.dumps(schema_json, indent=2)}

        Source Document (Canonical Format):
        {json.dumps(doc, indent=2)}

        Instructions:
        1. Read the Source Document carefully.
        2. Extract relevant fields to populate the Target Schema.
        3. All fields in the schema are REQUIRED.
        4. If a field cannot be found, use null or an empty string as appropriate for the type, BUT prefer extracting over null.
        5. 'unmapped_content' should contain any significant text that didn't fit into other specific fields.
        6. Return ONLY the valid JSON object matching the schema.
        """

    def compute_hash(self, doc: Dict[str, Any], schema_id: str, model: str) -> str:
        """
        Computes a hash of the inputs to the transformation.
        Used for idempotency / change detection.
        """
        # We hash the canonical doc content, the schema ID, and the model name
        # If any of these change, we should re-queue.
        content_str = json.dumps(doc, sort_keys=True)
        data = f"{content_str}|{schema_id}|{model}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
