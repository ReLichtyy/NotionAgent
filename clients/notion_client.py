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

    def append_toggle_to_page(self, page_id: str, title: str, text_content: str) -> tuple[bool, str]:
        """
        Appends a toggle block to the given page ID.
        Returns a tuple (success: bool, error_message: str).
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
            return True, "Éxito"
            
        except APIResponseError as e:
            if e.code == "restricted_resource":
                msg = ("Error 'RestrictedResource': La integración tiene las capabilities globales correctas, "
                       "pero falló al escribir. Causa probable: (1) La página/bloque específico es de solo lectura para esta integración, "
                       "o (2) El endpoint 'append' tiene restricciones estructurales sobre el recurso destino.")
            elif e.code == "object_not_found":
                msg = ("Error 'ObjectNotFound': El page_id/block_id usado es incorrecto, "
                       "o la página no ha sido compartida con la Integración.")
            else:
                msg = f"Error nativo de Notion API: {e.code} - {e.message}"
                
            logger.error(msg)
            return False, msg
            
        except Exception as e:
            msg = f"Error inesperado al comunicarse con Notion: {e}"
            logger.error(msg)
            return False, msg

    def create_page(self, parent_page_id: str, title: str) -> tuple[bool, str]:
        """
        Creates a new page under a parent page.
        Returns (True, new_page_id) or (False, error_msg).
        """
        try:
            new_page = self.client.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            )
            logger.info(f"Successfully created new page '{title}' with ID {new_page['id']}")
            return True, new_page["id"]
        except APIResponseError as e:
            msg = f"Error nativo de Notion API al crear página: {e.code} - {e.message}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error inesperado al crear página: {e}"
            logger.error(msg)
            return False, msg

    def read_page_content_as_text(self, page_id: str) -> str:
        """
        Fetches the blocks of a page and extracts a plain text representation.
        This is useful for injecting the LIVE existing content of a page into the LLM context.
        """
        try:
            blocks = self.get_page_blocks(page_id)
            if not blocks:
                return ""
            
            lines = []
            for block in blocks:
                b_type = block.get("type")
                if not b_type:
                    continue
                
                block_data = block.get(b_type, {})
                rich_text = block_data.get("rich_text", [])
                
                # Extract text
                text = "".join([rt.get("plain_text", "") for rt in rich_text])
                
                if text.strip():
                    if b_type in ["heading_1", "heading_2", "heading_3"]:
                        lines.append(f"\n# {text}")
                    elif b_type == "bulleted_list_item":
                        lines.append(f"- {text}")
                    else:
                        lines.append(text)
                        
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to read page content as text for {page_id}: {e}")
            return ""
