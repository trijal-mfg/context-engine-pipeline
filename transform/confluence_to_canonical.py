import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from transform.canonical_models import CanonicalDocument, Section, Block, BlockType
from transform.cleaner import clean_text

logger = logging.getLogger(__name__)

class AdfToCanonicalConverter:
    def __init__(self):
        self.sections: List[Section] = []
        self.current_section: Optional[Section] = None
        # Default section for content before the first heading
        self.current_section = Section(heading="Introduction", level=0, blocks=[])
        self.sections.append(self.current_section)

    def convert(self, metadata: Dict[str, Any], adf_json: Dict[str, Any]) -> CanonicalDocument:
        self._reset()
        
        # Traverse ADF
        self._process_node(adf_json)
        
        # Filter empty sections? Maybe not, strict preservation. 
        # But we might want to drop the "Introduction" if it's empty and there are other sections.
        if len(self.sections) > 1 and not self.sections[0].blocks and not self.sections[0].full_text:
             self.sections.pop(0)

        # Populate full_text for sections
        for section in self.sections:
            texts = [b.content for b in section.blocks]
            section.full_text = "\n".join(texts)
            
        return CanonicalDocument(
            id=metadata.get("page_id") or metadata.get("_id"), # Handle both raw responses and stored Mongo docs
            title=metadata.get("title", "Untitled"),
            url=self._construct_url(metadata), 
            version=metadata.get("version", 1),
            sections=self.sections,
            metadata=metadata
        )

    def _reset(self):
        self.sections = []
        self.current_section = Section(heading="Introduction", level=0, blocks=[])
        self.sections.append(self.current_section)

    def _construct_url(self, metadata: Dict[str, Any]) -> str:
        # This is a bit hacky without base URL, but we can store it or pass it. 
        # For now, placeholder or use links if available in metadata.
        base = metadata.get("_links", {}).get("base", "")
        webui = metadata.get("_links", {}).get("webui", "")
        if base and webui:
            return base + webui
        return ""

    def _process_node(self, node: Dict[str, Any]):
        node_type = node.get("type")
        content = node.get("content", [])

        if node_type == "doc":
            for child in content:
                self._process_node(child)
        
        elif node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            text = self._extract_text(node)
            cleaned_heading = clean_text(text)
            
            # Start new section
            new_section = Section(heading=cleaned_heading, level=level, blocks=[])
            self.sections.append(new_section)
            self.current_section = new_section
            
        elif node_type == "paragraph":
            text = self._extract_text(node)
            cleaned_text = clean_text(text)
            if cleaned_text:
                self.current_section.blocks.append(Block(
                    content=cleaned_text,
                    type=BlockType.PARAGRAPH
                ))
                
        elif node_type == "codeBlock":
            text = self._extract_text(node) 
            # Code blocks often want to preserve structure, so maybe less aggressive cleaning?
            # But clean_text mostly does whitespace collapsing which might harm code indentation.
            # Let's just strip ends for code.
            language = node.get("attrs", {}).get("language", "text")
            if text and text.strip():
                 self.current_section.blocks.append(Block(
                    content=text, # Preserve internal whitespace for code
                    type=BlockType.CODE,
                    metadata={"language": language}
                ))

        elif node_type == "bulletList" or node_type == "orderedList":
             # Flatten lists for now or handle them as block items
             for child in content:
                 self._process_node(child)

        elif node_type == "listItem":
            # List items usually contain paragraphs. 
            # We want to extract content but maybe mark it as list item.
            # Simple approach: flatten to text.
            text = self._extract_text(node)
            cleaned = clean_text(text)
            if cleaned:
                 self.current_section.blocks.append(Block(
                    content=f"- {cleaned}",
                    type=BlockType.LIST_ITEM
                ))
        
        elif node_type == "table":
            # Tables are complex. Simple extraction: row by row text.
            # Better: Markdown representation?
            # For this MVP, let's extract text row by row.
            table_text = self._extract_table_text(node)
            if table_text:
                self.current_section.blocks.append(Block(
                    content=table_text,
                    type=BlockType.TABLE
                ))
        
        else:
            # Fallback for other types (blockquote, panel, etc): extract text
             text = self._extract_text(node)
             cleaned = clean_text(text)
             # Avoid empty blocks
             if cleaned:
                 self.current_section.blocks.append(Block(
                     content=cleaned,
                     type=BlockType.UNKNOWN
                 ))

    def _extract_text(self, node: Dict[str, Any]) -> str:
        """Recursively extract text from a node."""
        node_type = node.get("type")
        
        if node_type == "text":
            return node.get("text", "")
        
        content = node.get("content", [])
        texts = [self._extract_text(child) for child in content]
        return "".join(texts)

    def _extract_table_text(self, table_node: Dict[str, Any]) -> str:
        rows = []
        content = table_node.get("content", [])
        for row_node in content:
            if row_node.get("type") == "tableRow":
                cells = []
                for cell_node in row_node.get("content", []):
                    # cell content is usually paragraph, so extract text
                    cell_text = self._extract_text(cell_node)
                    cells.append(clean_text(cell_text))
                rows.append(" | ".join(cells))
        return "\n".join(rows)

