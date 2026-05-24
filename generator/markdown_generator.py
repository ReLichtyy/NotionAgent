import os
from domain.contracts import ParsedNode
from core.logger import get_logger

logger = get_logger("MarkdownGenerator")

class MarkdownGenerator:
    def __init__(self):
        pass

    def _get_heading_prefix(self, depth: int) -> str:
        """
        Maps the tree depth to a Markdown heading level.
        Markdown officially supports up to h6 (######).
        """
        level = depth + 1
        if level > 6:
            level = 6
        return "#" * level

    def _build_markdown_recursive(self, node: ParsedNode) -> str:
        """
        Recursively builds the markdown string for a node and its children.
        """
        content_parts = []

        # 1. Title as Heading
        heading = self._get_heading_prefix(node.metadata.depth)
        
        # Determine icon based on source_type
        icon = "📄"
        if node.metadata.source_type == "database":
            icon = "🗄️"
        elif node.metadata.source_type == "row":
            icon = "📝"
            
        content_parts.append(f"{heading} {icon} {node.metadata.title}")
        
        # 2. Metadata Context
        # Using blockquote so the LLM easily identifies it as context/metadata
        content_parts.append(f"> **Path:** `{node.metadata.path}`")
        content_parts.append(f"> **ID:** `{node.metadata.id}`")
        content_parts.append("") # Empty line

        # 3. Text Blocks
        for block in node.text_blocks:
            # We can format based on block type if needed, but for now we just append text
            # since the parser already added things like [x] for to-do
            if block.block_type in ["heading_1", "heading_2", "heading_3"]:
                content_parts.append(f"**{block.text_content}**\n")
            elif block.block_type == "quote":
                content_parts.append(f"> {block.text_content}\n")
            elif block.block_type in ["bulleted_list_item", "numbered_list_item"]:
                content_parts.append(f"- {block.text_content}")
            else:
                content_parts.append(f"{block.text_content}\n")

        if node.text_blocks:
            content_parts.append("") # Empty line separator

        # 4. Code Blocks
        for code_block in node.code_blocks:
            lang = code_block.language if code_block.language != "plaintext" else ""
            content_parts.append(f"```{lang}\n{code_block.text_content}\n```\n")

        # 5. Recursion for children
        for child in node.children:
            content_parts.append(self._build_markdown_recursive(child))

        return "\n".join(content_parts)

    def generate(self, root_node: ParsedNode) -> str:
        """
        Generates the full markdown document from the AST.
        """
        logger.info("Generating markdown document from AST...")
        return self._build_markdown_recursive(root_node)

    def export_to_file(self, content: str, filename: str = "workspace_context.md"):
        """
        Exports the generated markdown to a physical file.
        Also calculates basic statistics.
        """
        char_count = len(content)
        word_count = len(content.split())
        # Very rough estimation of tokens for OpenAI (1 token ~ 4 chars for english/code, can be more for spanish)
        est_tokens = char_count // 4

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"Markdown successfully exported to {filename}")
            logger.info("--- Document Statistics ---")
            logger.info(f"Characters: {char_count:,}")
            logger.info(f"Words:      {word_count:,}")
            logger.info(f"Est Tokens: ~{est_tokens:,}")
            
            if est_tokens > 100000:
                logger.warning("⚠️ High token count! Document might exceed 128K context window.")
                
        except Exception as e:
            logger.error(f"Failed to write markdown file: {e}")
