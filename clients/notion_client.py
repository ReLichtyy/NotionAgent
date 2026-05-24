import time
from typing import Any, Dict, List
from notion_client import Client
from notion_client.errors import APIResponseError
from core.config import get_settings
from core.exceptions import NotionConnectionError
from core.logger import get_logger

logger = get_logger("NotionClient")

class NotionAppClient:
    def __init__(self):
        settings = get_settings()
        # The official notion_client automatically retries on 429 Rate Limit responses by default.
        self.client = Client(auth=settings.NOTION_API_KEY)
        
    def test_connection(self) -> bool:
        """
        Tests the connection by attempting to do an empty search.
        Returns True if successful, raises NotionConnectionError otherwise.
        """
        try:
            results = self.client.search(query="")
            logger.info(f"Successfully connected to Notion. Found {len(results.get('results', []))} top-level objects.")
            return True
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            raise NotionConnectionError(f"Failed to connect to Notion: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when connecting to Notion: {e}")
            raise NotionConnectionError(f"Unexpected error: {e}")

    def search_all_accessible_objects(self) -> List[Dict[str, Any]]:
        """
        Retrieves all pages and databases shared with this integration.
        """
        results = []
        try:
            # We fetch all pages and databases
            query = self.client.search(query="")
            for item in query.get("results", []):
                results.append(item)
            return results
        except Exception as e:
            logger.error(f"Failed to search workspace: {e}")
            return []

    def get_page_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all children blocks for a given block/page ID, handling pagination.
        """
        blocks = []
        has_more = True
        next_cursor = None
        
        while has_more:
            try:
                # Si next_cursor es None, el SDK lo ignora o da error, mejor condicional
                kwargs = {"block_id": block_id}
                if next_cursor:
                    kwargs["start_cursor"] = next_cursor
                    
                response = self.client.blocks.children.list(**kwargs)
                blocks.extend(response.get("results", []))
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
            except Exception as e:
                logger.error(f"Failed to get blocks for {block_id}: {e}")
                break
                
        return blocks

    def get_database_pages(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Queries a database to get all pages inside it, handling pagination.
        """
        pages = []
        has_more = True
        next_cursor = None
        
        while has_more:
            try:
                kwargs = {"database_id": database_id}
                if next_cursor:
                    kwargs["start_cursor"] = next_cursor
                    
                response = self.client.databases.query(**kwargs)
                pages.extend(response.get("results", []))
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
            except Exception as e:
                logger.error(f"Failed to query database {database_id}: {e}")
                break
                
        return pages

    def get_page_details(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieves the page object details (like properties, title).
        """
        try:
            return self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            logger.error(f"Failed to retrieve page {page_id}: {e}")
            return {}

    def append_toggle_to_page(self, page_id: str, title: str, text_content: str) -> bool:
        """
        Appends a toggle block to the given page ID.
        """
        try:
            # We can split text_content by newlines into multiple paragraphs if needed,
            # but for simplicity, we add it as one large text chunk in a paragraph, 
            # limited to 2000 chars per text object by Notion API.
            # Notion restricts rich_text content to 2000 chars. We must chunk it.
            chunks = [text_content[i:i+2000] for i in range(0, len(text_content), 2000)]
            rich_text_array = [{"type": "text", "text": {"content": chunk}} for chunk in chunks]
            
            self.client.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [{"type": "text", "text": {"content": title[:2000]}}],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": rich_text_array
                                    }
                                }
                            ]
                        }
                    }
                ]
            )
            logger.info(f"Successfully appended toggle '{title}' to page {page_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to append toggle to page {page_id}: {e}")
            return False
