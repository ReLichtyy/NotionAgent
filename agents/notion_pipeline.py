import os
from core.logger import get_logger
from core.config import get_settings

from crawler.notion_crawler import NotionCrawler
from parser.notion_parser import NotionParser
from generator.markdown_generator import MarkdownGenerator
from generator.json_generator import JsonFragmentGenerator

logger = get_logger("NotionExtractionPipeline")

class NotionExtractionPipeline:
    """
    Encapsulates the multi-phase process to extract data from Notion
    and build local search indexes (Markdown and JSON).
    """
    def __init__(self):
        self.settings = get_settings()

    def run(self) -> bool:
        """
        Executes the extraction pipeline.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("--- Phase 1: Crawling (Global/Targeted) ---")
            crawler = NotionCrawler(max_depth=self.settings.NOTION_MAX_DEPTH)
            
            if self.settings.NOTION_ROOT_PAGE_ID:
                logger.info(f"Crawling specific root page: {self.settings.NOTION_ROOT_PAGE_ID}")
                raw_root_node = crawler.crawl_from_root(self.settings.NOTION_ROOT_PAGE_ID)
            else:
                logger.info("Crawling all accessible workspace objects...")
                raw_root_node = crawler.crawl_all_workspace()
                
            if not raw_root_node:
                logger.error("Crawler returned no data.")
                return False
                
            logger.info("--- Phase 2: Parsing ---")
            parser = NotionParser()
            parsed_root_node = parser.parse(raw_root_node)
            
            if not parsed_root_node:
                logger.error("Parser returned no data.")
                return False
                
            logger.info("--- Phase 3: Generating Markdown ---")
            md_generator = MarkdownGenerator()
            markdown_str = md_generator.generate(parsed_root_node)
            md_generator.export_to_file(markdown_str, self.settings.NOTION_MD_PATH)
            
            logger.info("--- Phase 4: Generating Semantic Fragments ---")
            json_generator = JsonFragmentGenerator()
            fragments = json_generator.generate(parsed_root_node)
            json_generator.export_to_file(fragments, self.settings.NOTION_JSON_PATH)
            
            if os.path.exists(self.settings.NOTION_JSON_PATH):
                size = os.path.getsize(self.settings.NOTION_JSON_PATH)
                logger.info(f"Extraction pipeline completed successfully. Generated JSON size: {size} bytes")
                return True
            else:
                logger.error("Failed to write output files.")
                return False
                
        except Exception as e:
            logger.error(f"Extraction pipeline failed: {e}")
            return False
