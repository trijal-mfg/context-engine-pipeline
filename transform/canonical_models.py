from dataclasses import dataclass, fields, field
from typing import List, Optional, Dict, Any
from enum import Enum

class BlockType(Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    CODE = "code"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"
    UNKNOWN = "unknown"

@dataclass
class Block:
    content: str
    type: BlockType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Section:
    heading: str
    level: int
    blocks: List[Block]
    full_text: str = ""  # Concatenated text of blocks, populated during processing

@dataclass
class CanonicalDocument:
    id: str
    title: str
    url: str
    version: int
    sections: List[Section]
    metadata: Dict[str, Any] = field(default_factory=dict)
