import json
from typing import List, Dict, Any
from domain.contracts import ParsedNode
from core.logger import get_logger

logger = get_logger("JsonGenerator")

class JsonFragmentGenerator:
    def __init__(self):
        pass

    def _extract_fragments_recursive(self, node: ParsedNode, fragments: List[Dict[str, Any]]):
        """Recursively extracts fragments from the ParsedNode AST."""
        if not node:
            return
            
        # Compile all text and code from this specific node (not children)
        content_parts = []
        for text_block in node.text_blocks:
            content_parts.append(text_block.text_content)
            
        for code_block in node.code_blocks:
            content_parts.append(f"```{code_block.language}\n{code_block.text_content}\n```")
            
        combined_text = "\n".join(content_parts).strip()
        
        # Only save a fragment if it actually contains text to avoid empty chunk pollution
        if combined_text:
            fragment = {
                "id": node.metadata.id,
                "title": node.metadata.title,
                "path": node.metadata.path,
                "source_type": node.metadata.source_type,
                "text": combined_text
            }
            fragments.append(fragment)
            
        # Recurse for children
        for child in node.children:
            self._extract_fragments_recursive(child, fragments)

    def generate(self, root_node: ParsedNode) -> List[Dict[str, Any]]:
        """Generates a list of dictionaries representing knowledge fragments."""
        logger.info("Extracting JSON fragments from AST...")
        fragments = []
        self._extract_fragments_recursive(root_node, fragments)
        return fragments

    def export_to_file(self, fragments: List[Dict[str, Any]], filename: str = "workspace_fragments.json"):
        """Exports the fragments list to a JSON file."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(fragments, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully exported {len(fragments)} fragments to {filename}")
        except Exception as e:
            logger.error(f"Failed to export JSON fragments: {e}")
