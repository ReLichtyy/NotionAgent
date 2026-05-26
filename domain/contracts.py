from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from enum import Enum

class NodeStatus(str, Enum):
    ACTIVE = "active"
    INACCESSIBLE = "inaccessible"
    MISSING = "missing"
    UNVERIFIED = "unverified"

class NavNode(BaseModel):
    """
    Representación ligera y estructural de una página o base de datos en el Workspace Tree.
    Optimizado para navegación rápida O(1).
    """
    id: str
    title: str
    type: str  # "page", "database", "workspace_root"
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    depth: int = 0
    breadcrumb: str = ""
    path: str = ""
    icon: Optional[str] = None
    accessible: bool = True
    status: NodeStatus = NodeStatus.ACTIVE

class RawNode(BaseModel):
    """
    Represents a page or database and its recursively extracted content.
    Used by the Crawler to pass the full tree to the Parser.
    """
    node_id: str
    node_type: str  # "page" or "database"
    title: Optional[str] = None
    icon: Optional[str] = None
    status: NodeStatus = NodeStatus.ACTIVE
    raw_blocks: List[Dict[str, Any]] = []
    children: List['RawNode'] = []

class MetadataContext(BaseModel):
    id: str
    parent_id: Optional[str] = None
    path: str
    depth: int
    source_type: str  # "page", "database", or "row"
    title: str
    status: NodeStatus = NodeStatus.ACTIVE

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
