from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class RawNode(BaseModel):
    """
    Represents a page or database and its recursively extracted content.
    Used by the Crawler to pass the full tree to the Parser.
    """
    node_id: str
    node_type: str  # "page" or "database"
    title: Optional[str] = None
    raw_blocks: List[Dict[str, Any]] = []
    children: List['RawNode'] = []

class MetadataContext(BaseModel):
    id: str
    parent_id: Optional[str] = None
    path: str
    depth: int
    source_type: str  # "page", "database", or "row"
    title: str

class BlockContext(BaseModel):
    block_type: str
    text_content: str

class CodeBlockContext(BlockContext):
    language: str

class ParsedNode(BaseModel):
    """
    Represents a clean, strictly typed node of knowledge parsed from a RawNode.
    """
    metadata: MetadataContext
    text_blocks: List[BlockContext] = []
    code_blocks: List[CodeBlockContext] = []
    children: List['ParsedNode'] = []
