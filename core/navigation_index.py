import json
import os
from typing import Dict, List, Optional
from domain.contracts import NavNode, RawNode
from core.logger import get_logger

logger = get_logger("NavigationIndex")

class NavigationIndex:
    """
    Adapter that maintains an O(1) dictionary tree for rapid Notion path resolution and hierarchy querying.
    """
    def __init__(self, storage_path: str = "workspace_tree.json"):
        self.storage_path = storage_path
        self.tree: Dict[str, NavNode] = {}
        
    def load(self):
        """Loads the tree from the JSON file."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.tree[k] = NavNode(**v)
                logger.info(f"Loaded {len(self.tree)} nodes from navigation index.")
            except Exception as e:
                logger.error(f"Failed to load navigation index: {e}")
                self.tree = {}

    def save(self):
        """Persists the tree to JSON."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                raw_dict = {k: v.model_dump() for k, v in self.tree.items()}
                json.dump(raw_dict, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.tree)} nodes to navigation index.")
        except Exception as e:
            logger.error(f"Failed to save navigation index: {e}")

    def _traverse_and_build(self, node: RawNode, parent_id: Optional[str] = None, depth: int = 0):
        # Normalizar ID
        node_id = node.node_id
        
        # Calcular path y breadcrumb
        breadcrumb = node.title or "Untitled"
        path = breadcrumb.lower().strip()
        
        if parent_id and parent_id in self.tree:
            parent_nav = self.tree[parent_id]
            breadcrumb = f"{parent_nav.breadcrumb} > {breadcrumb}"
            path = f"{parent_nav.path}/{path}"
        else:
            path = f"/{path}"

        # Register self
        nav_node = NavNode(
            id=node_id,
            title=node.title or "Untitled",
            type=node.node_type,
            parent_id=parent_id,
            children_ids=[child.node_id for child in node.children],
            depth=depth,
            breadcrumb=breadcrumb,
            path=path,
            icon=node.icon,
            accessible=(node.status == "active"),
            status=node.status
        )
        
        self.tree[node_id] = nav_node
        
        # Recurse
        for child in node.children:
            self._traverse_and_build(child, parent_id=node_id, depth=depth + 1)

    def build_from_rawnodes(self, root_node: RawNode):
        """Constructs the navigation dictionary from a RawNode AST."""
        self.tree.clear()
        self._traverse_and_build(root_node)
        self.save()

    def list_children(self, parent_id: str) -> List[NavNode]:
        """Returns the direct children of a given node."""
        parent = self.tree.get(parent_id)
        if not parent:
            return []
        
        children = []
        for cid in parent.children_ids:
            if cid in self.tree:
                children.append(self.tree[cid])
        return children

    def resolve_path(self, breadcrumb_str: str) -> Optional[NavNode]:
        """Finds a node by exact path or exact breadcrumb match."""
        # Convert path to standard format just in case
        clean_query = breadcrumb_str.strip().lower()
        if not clean_query.startswith("/"):
            # Attempt to treat as "Lab > IA" format and clean to "/lab/ia"
            search_path = "/" + "/".join([p.strip() for p in clean_query.split(">")])
        else:
            search_path = clean_query
            
        # O(N) search on dict, extremely fast for <10k items
        for node in self.tree.values():
            if node.path.lower() == search_path or node.breadcrumb.lower() == clean_query:
                return node
                
        return None

    def find_by_title(self, title_query: str) -> List[NavNode]:
        """Fuzzy search for nodes by title."""
        query = title_query.lower().strip()
        results = []
        for node in self.tree.values():
            if query in node.title.lower():
                results.append(node)
        return results

    def get_descendants(self, root_id: str) -> List[NavNode]:
        """Recursively fetches all descendants of a given node."""
        if root_id not in self.tree:
            return []
            
        descendants = []
        for cid in self.tree[root_id].children_ids:
            if cid in self.tree:
                descendants.append(self.tree[cid])
                descendants.extend(self.get_descendants(cid))
        return descendants
