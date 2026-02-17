import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def _estimate_tokens(text: str) -> int:
    """
    Simple token estimation: ~4 chars per token.
    """
    if not text:
        return 0
    return len(text) // 4

def _flatten_adf_node(node: Dict[str, Any]) -> str:
    """
    Recursively flatten an ADF node into plain text.
    Handles paragraphs, bulletLists, orderedLists, tables, codeBlocks, etc.
    """
    node_type = node.get("type")
    content = node.get("content", [])
    text = ""

    if node_type == "text":
        return node.get("text", "")

    elif node_type == "paragraph":
        # Process children and join
        child_texts = [_flatten_adf_node(child) for child in content]
        return "".join(child_texts) + "\n\n"

    elif node_type == "bulletList":
        for item in content:
            # Each item is a listItem
            text += "- " + _flatten_adf_node(item).strip() + "\n"
        return text + "\n"

    elif node_type == "orderedList":
        for i, item in enumerate(content, 1):
             text += f"{i}. " + _flatten_adf_node(item).strip() + "\n"
        return text + "\n"

    elif node_type == "listItem":
        # listItem content is usually a paragraph or nested list
        child_texts = [_flatten_adf_node(child) for child in content]
        # Join with space if multiple blocks in one list item, though usually just one
        return "".join(child_texts)

    elif node_type == "table":
        # Flatten row-wise
        rows = []
        for row in content:
            if row.get("type") == "tableRow":
                cells = []
                for cell in row.get("content", []):
                    if cell.get("type") in ("tableCell", "tableHeader"):
                         cell_text = _flatten_adf_node(cell).strip()
                         cells.append(cell_text)
                rows.append(" | ".join(cells))
        return "\n".join(rows) + "\n\n"
    
    elif node_type in ("tableCell", "tableHeader"):
         child_texts = [_flatten_adf_node(child) for child in content]
         return "".join(child_texts)

    elif node_type == "codeBlock":
        code_content = ""
        for child in content:
             code_content += _flatten_adf_node(child)
        return f"```\n{code_content}\n```\n\n"
    
    elif node_type == "media":
        return "[MEDIA]"
        
    elif node_type == "mediaGroup":
         child_texts = [_flatten_adf_node(child) for child in content]
         return "\n".join(child_texts) + "\n"

    elif node_type in ("doc", "layoutSection", "layoutColumn"):
        # Structural containers, just recurse
        for child in content:
            text += _flatten_adf_node(child)
        return text

    # Fallback for unknown types (e.g. rule, expansion, etc) - try to extract text from children
    for child in content:
        text += _flatten_adf_node(child)
    
    return text


def adf_to_sections(adf_json: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert ADF JSON into a list of logical sections based on headings.
    
    Args:
        adf_json: The 'value' of the 'body.atlas_doc_format' field.
        metadata: Confluence page metadata including id, version, title, ancestors.
        
    Returns:
        Dict containing page metadata and a list of sections.
    """
    page_id = metadata.get("id")
    # Handle version: might be int or dict depending on API response
    version_info = metadata.get("version", {})
    if isinstance(version_info, dict):
        version = version_info.get("number", 1)
    else:
        version = int(version_info)
        
    # Extract space key safely
    space_info = metadata.get("space", {})
    if isinstance(space_info, dict):
        space_key = space_info.get("key", "")
    else:
        space_key = str(space_info)

    title = metadata.get("title", "")
    ancestors = metadata.get("ancestors", [])

    sections = []
    
    # Initialize first section (preamble before any heading)
    current_section = {
        "heading": None,
        "level": None,
        "content": ""
    }
    
    content_nodes = adf_json.get("content", [])
    
    for node in content_nodes:
        node_type = node.get("type")
        
        if node_type == "heading":
            # Push current section if it has content
            if current_section["content"].strip():
                sections.append(current_section)
            
            # Start new section
            level = node.get("attrs", {}).get("level", 1)
            heading_text = ""
            for child in node.get("content", []):
                if child.get("type") == "text":
                    heading_text += child.get("text", "")
            
            current_section = {
                "heading": heading_text,
                "level": level,
                "content": ""  # Heading text itself usually isn't body content, but acts as label
            }
        else:
            # Append flattened content to current section
            text = _flatten_adf_node(node)
            current_section["content"] += text

    # Push final section
    if current_section["content"].strip():
        sections.append(current_section)
        
    # If explicit headings exist, the preamble might be empty or just meta info.
    # If NO headings exist, we should have one section with heading=None.
    if not sections and not current_section["content"].strip() and not content_nodes:
         # Empty doc
         pass
    elif not sections and current_section["content"].strip() == "":
         # Doc with only empty content?
         pass

    return {
        "page_id": page_id,
        "version": version,
        "space_key": space_key,
        "title": title,
        "ancestors": ancestors,
        "sections": sections
    }


def _split_text_on_tokens(text: str, max_tokens: int) -> List[str]:
    """
    Split text into chunks that fit within max_tokens.
    Splits by double newline (paragraph) first, then single newline.
    Does NOT split mid-word.
    """
    estimated = _estimate_tokens(text)
    if estimated <= max_tokens:
        return [text]
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    # Split by paragraphs
    paragraphs = text.split("\n\n")
    
    for para in paragraphs:
        para_tokens = _estimate_tokens(para)
        
        # If adding this paragraph exceeds max, push current chunk
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0
            
        # If single paragraph is HUGE, need to split it by lines or logic
        if para_tokens > max_tokens:
            # Recursive strategy: split by single newline if possible
            if "\n" in para and not para.strip().startswith("- "): # simplistic list check
                 lines = para.split("\n")
                 for line in lines:
                      line_tokens = _estimate_tokens(line)
                      if current_tokens + line_tokens > max_tokens and current_chunk:
                           chunks.append("\n\n".join(current_chunk))
                           current_chunk = []
                           current_tokens = 0
                      current_chunk.append(line)
                      current_tokens += line_tokens
            else:
                 # Fallback: split by words
                 words = para.split(" ")
                 sentence_chunk = []
                 sentence_tokens = 0
                 
                 for word in words:
                       # Re-add space for estimation except last
                       w_len = _estimate_tokens(word + " ")
                       if sentence_tokens + w_len > max_tokens and sentence_chunk:
                            chunks.append(" ".join(sentence_chunk))
                            sentence_chunk = []
                            sentence_tokens = 0
                       sentence_chunk.append(word)
                       sentence_tokens += w_len
                 
                 if sentence_chunk:
                      chunks.append(" ".join(sentence_chunk)) 
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def get_embedding_text(chunk: Dict[str, Any]) -> str:
    """
    Format chunk for embedding.
    Format:
    Title: {title}
    Section: {heading if exists}
    
    {content}
    """
    parts = [f"Title: {chunk['title']}"]
    if chunk.get("heading"):
        parts.append(f"Section: {chunk['heading']}")
    
    parts.append("") # Empty line
    parts.append(chunk["content"])
    
    return "\n".join(parts)


def chunk_sections(page_data: Dict[str, Any], max_tokens: int = 600) -> List[Dict[str, Any]]:
    """
    Chunk the sections from adf_to_sections into embedding-ready objects.
    
    Args:
        page_data: Output from adf_to_sections.
        max_tokens: Approximate max tokens per chunk.
        
    Returns:
        List of chunk objects.
    """
    page_id = page_data["page_id"]
    version = page_data["version"]
    space_key = page_data["space_key"]
    title = page_data["title"]
    ancestors = page_data.get("ancestors", [])
    
    ancestor_ids = [a.get("id") for a in ancestors if a.get("id")]
    parent_id = ancestor_ids[-1] if ancestor_ids else None
    
    all_chunks = []
    
    for s_idx, section in enumerate(page_data["sections"]):
        content = section["content"]
        heading = section["heading"]
        level = section["level"]
        
        # Determine depth from heading level, defaulting to 0 for no heading
        depth = level if level is not None else 0
        
        text_chunks = _split_text_on_tokens(content, max_tokens)
        
        for c_idx, chunk_text in enumerate(text_chunks):
            chunk_id = f"{page_id}_v{version}_s{s_idx}_c{c_idx}"
            
            chunk_obj = {
                "chunk_id": chunk_id,
                "page_id": page_id,
                "version": version,
                "space_key": space_key,
                "title": title,
                "heading": heading,
                "section_index": s_idx,
                "chunk_index": c_idx,
                "content": chunk_text.strip(),
                "ancestor_ids": ancestor_ids,
                "parent_id": parent_id,
                "depth": depth
            }
            # Attach embedding text helper? (Or simple function usage is preferred)
            # The user asked for "expose a method or field". We can compute it here or rely on the helper.
            # Let's add it as a field for convenience if they want to store it directly.
            chunk_obj["embedding_text"] = get_embedding_text(chunk_obj)
            
            all_chunks.append(chunk_obj)
            
    return all_chunks
