from typing import List, Tuple, Dict, Any
import logging
import json

from ollama_client import OllamaClient
from config import OLLAMA_MODEL_CLASSIFIER

logger = logging.getLogger(__name__)

class Classifier:
    """
    Classifies documents into the most appropriate schema.
    """
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    async def classify(self, canonical_doc: Dict[str, Any], available_schemas: List[str]) -> Tuple[str, float]:
        """
        Determines the schema_id for a given document.
        Returns (schema_id, confidence).
        """
        
        # doc = {
        #     "title": canonical_doc.get("title"),
        #     "source": canonical_doc.get("source"),
        #     "content_snippet": self._get_content_snippet(canonical_doc)
        # }
        doc=canonical_doc
        prompt = f"""
        You are a document classifier for a technical documentation system.
        Your task is to classify the following document into EXACTLY ONE of the provided schema IDs.

        Available Schemas:
        {json.dumps(available_schemas, indent=2)}

        Document to Classify:
        {json.dumps(canonical_doc, indent=2)}

        Instructions:
        1. Analyze the document content and structure.
        2. Select the schema_id that best fits the document.
        3. If no specific schema fits well, select 'general_doc_v1'.
        4. Return a JSON object with "schema_id" and "confidence" (0.0 to 1.0).

        Example Output:
        {{
            "schema_id": "runbook_v1",
            "confidence": 0.95
        }}
        """

        try:
            response = await self.ollama.generate(prompt, OLLAMA_MODEL_CLASSIFIER)
            
            schema_id = response.get("schema_id")
            confidence = response.get("confidence", 0.0)

            if schema_id not in available_schemas:
                logger.warning(f"LLM returned invalid schema_id: {schema_id}. Fallback to general_doc_v1.")
                return "general_doc_v1", 0.0

            return schema_id, confidence

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Fallback on failure
            return "general_doc_v1", 0.0

    def _get_content_snippet(self, doc: Dict[str, Any], max_chars: int = 2000) -> str:
        """Helper to extract a text snippet from content blocks."""
        blocks = doc.get("content_blocks", [])
        text_parts = []
        current_len = 0
        
        for block in blocks:
            text = block.get("text", "")
            if text:
                text_parts.append(text)
                current_len += len(text)
                if current_len >= max_chars:
                    break
        
        return "\n".join(text_parts)[:max_chars]
