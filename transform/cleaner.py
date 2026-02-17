import re

def clean_text(text: str) -> str:
    """
    Deterministic whitespace cleaning.
    - Replaces multiple spaces with single space.
    - Trims leading/trailing whitespace.
    - Preserves newlines? The requirement says "deterministic normalization only".
      Usually for embedding chunks, we might want to keep some structure, but strictly cleaning 
      spurious whitespace is good.
    """
    if not text:
        return ""
    
    # Replace non-breaking spaces
    text = text.replace('\xa0', ' ')
    
    # Collapse multiple spaces (but keep newlines for now, or collapse them too?)
    # If we want to preserve block integrity, we typically handle newlines at block level.
    # Inside a text block (like paragraph), newlines might be semantic or soft wraps.
    # Let's collapse runs of spaces/tabs to single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Strip
    return text.strip()

def normalize_markdown(text: str) -> str:
    """
    Normalizes some markdown-like artifacts if any.
    For now, just a placeholder or simple pass-through as ADF usually gives structured text.
    """
    return text
