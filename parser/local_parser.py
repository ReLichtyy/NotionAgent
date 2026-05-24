import json
import os
from core.logger import get_logger

logger = get_logger("LocalParser")

class LocalParser:
    """
    Takes the raw scanned files from the crawler and formats them into
    standard semantic fragments.
    """
    def parse_and_export(self, raw_files: list[dict], export_path: str = "local_workspace_fragments.json") -> bool:
        fragments = []
        for file_data in raw_files:
            # We can do chunking here if we want, but for MVP we keep the whole file 
            # if it's small enough, which the crawler already ensures.
            fragment = {
                "id": file_data["id"],
                "title": file_data["title"],
                "path": file_data["path"],
                "type": file_data["type"],
                "text": file_data["text"]
            }
            fragments.append(fragment)
            
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(fragments, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported {len(fragments)} fragments to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export fragments: {e}")
            return False
