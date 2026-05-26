from typing import Optional, List
from domain.contracts import RawNode, ParsedNode, MetadataContext, BlockContext, CodeBlockContext
from parser.block_transformers import parse_standard_block, parse_code_block
from core.logger import get_logger

logger = get_logger("NotionParser")

class NotionParser:
    def __init__(self):
        pass

    def parse_node(self, raw_node: RawNode, current_path: str = "", depth: int = 0, is_db_row: bool = False) -> Optional[ParsedNode]:
        """
        Recursively converts a RawNode tree into a strictly typed ParsedNode tree.
        """
        if not raw_node:
            return None
            
        title = raw_node.title or "Untitled"
        
        # Determine source type
        if raw_node.node_type == "database":
            source_type = "database"
        else:
            source_type = "row" if is_db_row else "page"
            
        # Build path string
        separator = " / " if current_path else ""
        new_path = f"{current_path}{separator}{title}"
        
        metadata = MetadataContext(
            id=raw_node.node_id,
            parent_id=None, # In a flat struct we'd inject parent_id here, but we keep hierarchy
            path=new_path,
            depth=depth,
            source_type=source_type,
            title=title,
            status=raw_node.status
        )
        
        text_blocks: List[BlockContext] = []
        code_blocks: List[CodeBlockContext] = []
        parsed_children: List[ParsedNode] = []
        
        # Process Blocks
        for raw_block in raw_node.raw_blocks:
            block_type = raw_block.get("type")
            
            # Try to parse as code block
            code_res = parse_code_block(raw_block)
            if code_res:
                _, lang, code_content = code_res
                code_blocks.append(CodeBlockContext(
                    block_type="code",
                    text_content=code_content,
                    language=lang
                ))
                continue
                
            # Try to parse as standard text block
            text_res = parse_standard_block(raw_block)
            if text_res:
                b_type, content = text_res
                text_blocks.append(BlockContext(
                    block_type=b_type,
                    text_content=content
                ))
                continue
                
            # If not supported, we just ignore it silently to avoid log spam, 
            # or we could log it at debug level.
            # logger.debug(f"Unsupported block type ignored: {block_type}")
            
        # Process Children
        for child_raw_node in raw_node.children:
            # If current node is a database, all its direct children are rows
            child_is_row = (source_type == "database")
            
            parsed_child = self.parse_node(
                raw_node=child_raw_node,
                current_path=new_path,
                depth=depth + 1,
                is_db_row=child_is_row
            )
            
            if parsed_child:
                # Set parent relationship
                parsed_child.metadata.parent_id = metadata.id
                parsed_children.append(parsed_child)
                
        return ParsedNode(
            metadata=metadata,
            text_blocks=text_blocks,
            code_blocks=code_blocks,
            children=parsed_children
        )
