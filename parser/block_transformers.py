from typing import Any, Dict, List, Optional, Tuple

def extract_rich_text(rich_text_array: List[Dict[str, Any]]) -> str:
    """
    Consolidates a Notion rich_text array into a single plain text string.
    We could extract Markdown links here if needed, but for now we focus on plain_text
    to keep it clean and robust. If we want bold/italic, we can inject markdown here.
    """
    if not rich_text_array:
        return ""
    
    text_parts = []
    for rt in rich_text_array:
        # We can extract plain_text directly
        plain = rt.get("plain_text", "")
        
        # Optional: Add simple markdown wrapper for annotations if needed in the future
        # annotations = rt.get("annotations", {})
        # if annotations.get("bold"): plain = f"**{plain}**"
        # ...
        
        text_parts.append(plain)
        
    return "".join(text_parts)

def parse_standard_block(block: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Parses standard text blocks (paragraphs, headings, lists, quotes, callouts).
    Returns a tuple of (block_type, text_content) or None if unsupported/empty.
    """
    block_type = block.get("type")
    if not block_type:
        return None
        
    # The actual content object is keyed by the block type
    content_obj = block.get(block_type, {})
    
    # We support these standard types which all have a "rich_text" array inside their content object
    supported_text_types = {
        "paragraph", "heading_1", "heading_2", "heading_3", 
        "bulleted_list_item", "numbered_list_item", "to_do", 
        "toggle", "quote", "callout"
    }
    
    if block_type in supported_text_types:
        rich_text = content_obj.get("rich_text", [])
        text = extract_rich_text(rich_text)
        
        # For to_do blocks, maybe append a checkmark representation
        if block_type == "to_do":
            checked = content_obj.get("checked", False)
            box = "[x]" if checked else "[ ]"
            text = f"{box} {text}"
            
        if text.strip() or block_type == "paragraph": 
            # We keep empty paragraphs as spacing, but can filter empty others
            return (block_type, text)
            
    return None

def parse_code_block(block: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    """
    Parses a code block.
    Returns (block_type, language, code_content)
    """
    block_type = block.get("type")
    if block_type != "code":
        return None
        
    content_obj = block.get("code", {})
    language = content_obj.get("language", "plaintext")
    rich_text = content_obj.get("rich_text", [])
    code_content = extract_rich_text(rich_text)
    
    return ("code", language, code_content)
