"""
for normalizing documents from diffrent sources to a common format, only temproraty here TODO move this to indiviual confluence, slack, jira modules later
"""

from typing import Dict, Any, List
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CanonicalBuilder:
    """
    Converts source-specific documents (e.g., Confluence ADF) into a Canonical Raw Document format.
    """
    
    def build_canonical(self, source_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Determines source type and delegates.
        Currently only supports 'confluence'.
        """
        # In a real system, we'd detect source from metadata or passed args.
        # For now, we assume Confluence structure if certain keys are present.
        
        # TODO: Better source detection logic
        return self._build_from_confluence(source_doc)

    def _build_from_confluence(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps Confluence ADF/Storage format to Canonical Raw Document.
        """
        content_blocks = self._extract_content_blocks(doc.get("content", ""))
        
        return {
            "source": "confluence",
            "source_id": doc.get("_id"), # Assuming page_id is the _id
            "page_version": doc.get("version", 1),
            "title": doc.get("title"),
            "author": doc.get("author"), # Might need adjustment based on upstream data
            "created_at": doc.get("created_at", datetime.now(timezone.utc).isoformat()), 
            "content_blocks": content_blocks
        }

    def _extract_content_blocks(self, content: Any) -> List[Dict[str, str]]:
        """
        Parses the content to extract meaningful blocks (paragraphs, headings, etc.).
        
        NOTE: This is a simplified extraction. 
        If 'content' is already processed text, we wrap it.
        If it's raw ADF JSON, we would need a proper recursive parser here.
        Assuming 'content' here is the text representation stored by previous stages or raw string.
        """
        
        # If content is a string, split by newlines for a basic block structure
        if isinstance(content, str):
            blocks = []
            for line in content.split('\n'):
                if line.strip():
                    # Basic heuristic for type
                    b_type = "paragraph"
                    if line.startswith("#"):
                        b_type = "heading"
                    elif line.startswith("- ") or line.startswith("* "):
                        b_type = "list"
                        
                    blocks.append({
                        "type": b_type,
                        "text": line.strip()
                    })
            return blocks
        
        # If content is dict (ADF), implementation would be more complex
        # For this stage, we assume we might be getting text or need to implement ADF parsing
        # validation.
        
        logger.warning(f"Unsupported content type: {type(content)}. returning empty blocks.")
        return []
