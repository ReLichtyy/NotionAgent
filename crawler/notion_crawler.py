import time
from typing import Optional, Dict, Any
from clients.notion_client import NotionAppClient
from domain.contracts import RawNode
from core.logger import get_logger

logger = get_logger("NotionCrawler")

class NotionCrawler:
    def __init__(self, max_depth: int = 3):
        self.client = NotionAppClient()
        self.max_depth = max_depth

    def _extract_title(self, page_obj: Dict[str, Any]) -> str:
        """Helper to extract a title from a page object properties."""
        try:
            properties = page_obj.get("properties", {})
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_array = prop_data.get("title", [])
                    if title_array:
                        return "".join([t.get("plain_text", "") for t in title_array])
            return "Untitled"
        except Exception:
            return "Untitled"
    def _extract_icon(self, page_obj: Dict[str, Any]) -> Optional[str]:
        """Helper to extract an emoji icon from a page object if available."""
        try:
            icon_obj = page_obj.get("icon")
            if icon_obj and icon_obj.get("type") == "emoji":
                return icon_obj.get("emoji")
        except Exception:
            pass
        return None
    def crawl_page(self, page_id: str, current_depth: int = 0) -> Optional[RawNode]:
        """Crawls a single page and its children recursively up to max_depth."""
        if current_depth > self.max_depth:
            logger.info(f"Max depth {self.max_depth} reached at page {page_id}.")
            return None

        logger.info(f"Crawling page: {page_id} (Depth: {current_depth})")
        
        # Get page details for title and icon
        page_obj = self.client.get_page_details(page_id)
        title = self._extract_title(page_obj)
        icon = self._extract_icon(page_obj)

        # Get all blocks
        blocks, status = self.client.get_page_blocks(page_id)
        
        node = RawNode(
            node_id=page_id,
            node_type="page",
            title=title,
            icon=icon,
            status=status,
            raw_blocks=blocks,
            children=[]
        )

        # Recursively crawl children if they are pages or databases
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "child_page":
                child_id = block.get("id")
                child_node = self.crawl_page(child_id, current_depth + 1)
                if child_node:
                    node.children.append(child_node)
                    
            elif block_type == "child_database":
                child_id = block.get("id")
                child_node = self.crawl_database(child_id, current_depth + 1)
                if child_node:
                    node.children.append(child_node)

        return node

    def crawl_database(self, database_id: str, current_depth: int = 0) -> Optional[RawNode]:
        """Crawls a database by getting all its pages and crawling them."""
        if current_depth > self.max_depth:
            logger.info(f"Max depth {self.max_depth} reached at database {database_id}.")
            return None

        logger.info(f"Crawling database: {database_id} (Depth: {current_depth})")
        
        pages, status = self.client.get_database_pages(database_id)
        
        node = RawNode(
            node_id=database_id,
            node_type="database",
            title=f"Database {database_id}",
            status=status,
            raw_blocks=[],
            children=[]
        )

        for page in pages:
            page_id = page.get("id")
            # Pages inside DB are children of the DB
            child_node = self.crawl_page(page_id, current_depth + 1)
            if child_node:
                node.children.append(child_node)

        return node

    def crawl_all_workspace(self) -> Optional[RawNode]:
        """Entry point for the crawler. Searches all accessible objects and crawls them."""
        logger.info(f"Starting FULL workspace crawl with max depth {self.max_depth}")
        
        # We create a virtual root node to hold everything
        root_node = RawNode(
            node_id="workspace_root",
            node_type="workspace",
            title="Workspace Root",
            raw_blocks=[],
            children=[]
        )
        
        items = self.client.search_all_accessible_objects()
        logger.info(f"Found {len(items)} top-level objects in workspace search.")
        
        for item in items:
            item_type = item.get("object")
            item_id = item.get("id")
            
            if item_type == "page":
                child_node = self.crawl_page(item_id, current_depth=1)
                if child_node:
                    root_node.children.append(child_node)
            elif item_type == "database":
                child_node = self.crawl_database(item_id, current_depth=1)
                if child_node:
                    root_node.children.append(child_node)
                    
        return root_node
