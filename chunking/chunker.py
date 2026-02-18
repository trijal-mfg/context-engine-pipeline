from typing import List, Dict, Any
from dataclasses import dataclass, field
import uuid
import tiktoken

from transform.canonical_models import CanonicalDocument, Section, Block

@dataclass
class Chunk:
    id: str
    doc_id: str
    chunk_index: int
    total_chunks: int 
    text: str
    metadata: Dict[str, Any]

class Chunker:
    def __init__(self, max_tokens: int = 512, model_name: str = "cl100k_base"):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding(model_name)

    def chunk_document(self, doc: CanonicalDocument) -> List[Chunk]:
        chunks = []
        
        for section in doc.sections:
            section_chunks = self._chunk_section(section, doc)
            chunks.extend(section_chunks)
            
        # Update total chunks info
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total
            
        return chunks

    def _chunk_section(self, section: Section, doc: CanonicalDocument) -> List[Chunk]:
        """
        Chunks a section while respecting block boundaries.
        """
        chunks = []
        current_chunk_blocks = []
        current_tokens = 0
        
        # Calculate heading tokens to add context if needed, 
        # but for now we only count them if we decide to prepend them.
        # User requirement: "Chunk by section first".
        
        for block in section.blocks:
            block_content = block.content
            if not block_content:
                continue
                
            block_tokens = len(self.tokenizer.encode(block_content))
            
            # If adding this block exceeds max_tokens...
            if current_chunk_blocks and (current_tokens + block_tokens > self.max_tokens):
                # Finalize current chunk
                chunks.append(self._create_chunk(current_chunk_blocks, section, doc))
                current_chunk_blocks = []
                current_tokens = 0
            
            current_chunk_blocks.append(block)
            current_tokens += block_tokens
            
        # Finalize last chunk
        if current_chunk_blocks:
            chunks.append(self._create_chunk(current_chunk_blocks, section, doc))
            
        return chunks

    def _create_chunk(self, blocks: List[Block], section: Section, doc: CanonicalDocument) -> Chunk:
        # Join block content
        content = "\n\n".join([b.content for b in blocks])
        
        # Generate stable ID if possible, or random
        chunk_id = str(uuid.uuid4())
        
        return Chunk(
            id=chunk_id,
            doc_id=doc.id,
            chunk_index=0, # Placeholder
            total_chunks=0, # Placeholder
            text=content,
            metadata={
                "title": doc.title,
                "url": doc.url,
                "version": doc.version,
                "section_heading": section.heading,
                "section_level": section.level,
                "block_types": [b.type.value for b in blocks],
                # Hierarchy metadata
                "parent_id": doc.metadata.get("parent_id"),
                "ancestor_ids": doc.metadata.get("ancestor_ids", []),
                "depth": doc.metadata.get("depth", 0)
            }
        )
