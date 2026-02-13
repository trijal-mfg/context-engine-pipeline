from lxml import etree
from typing import Any, Dict, List
import json

def get_clean_tag(element: etree._Element) -> str:
    """
    Safely extract tag name with namespace prefix if present.
    """
    if not isinstance(element.tag, str):
        # Comment, processing instruction, etc.
        return "__special__"

    if element.tag.startswith("{"):
        uri, local = element.tag[1:].split("}")
        for prefix, ns in element.nsmap.items():
            if ns == uri:
                return f"{prefix}:{local}" if prefix else local
        return local

    return element.tag


def element_to_dict(element: etree._Element) -> Dict[str, Any]:
    """
    Safe recursive conversion.
    Handles:
      - normal elements
      - comments
      - special nodes
    """

    # Handle comments
    if isinstance(element, etree._Comment):
        return {
            "tag": "__comment__",
            "text": element.text
        }

    # Handle processing instructions
    if isinstance(element, etree._ProcessingInstruction):
        return {
            "tag": "__processing_instruction__",
            "text": element.text
        }

    # Handle weird internal nodes safely
    if not isinstance(element.tag, str):
        return {
            "tag": "__unknown__"
        }

    node: Dict[str, Any] = {
        "tag": get_clean_tag(element)
    }

    # Attributes
    if element.attrib:
        node["attributes"] = dict(element.attrib)

    # Text
    if element.text and element.text.strip():
        node["text"] = element.text.strip()

    # Children
    children: List[Dict[str, Any]] = []

    for child in element.iterchildren():
        children.append(element_to_dict(child))

        # Preserve tail
        if child.tail and child.tail.strip():
            children.append({
                "tag": "__tail__",
                "text": child.tail.strip()
            })

    if children:
        node["children"] = children

    return node


if __name__ == "__main__":
    input_path = "/Users/trijal.shinde/workspace/context-engine-ingestion-pipeline/data/confluence/raw/TPG/779485312/version_6.xml"
    output_path = "op.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    root = etree.fromstring(content.encode("utf-8"))
    result = element_to_dict(root)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    