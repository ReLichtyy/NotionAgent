import os
from core.logger import get_logger

logger = get_logger("LocalCrawler")

ALLOWED_EXTENSIONS = {'.md', '.txt', '.py', '.json', '.csv'}
IGNORED_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.venv', '.idea', '.vscode'}
MAX_FILE_SIZE_BYTES = 1024 * 1024 * 5  # 5 MB max per file

class LocalCrawler:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def crawl(self) -> list[dict]:
        """
        Recursively scans the base_dir.
        Returns a list of dictionaries containing raw file data.
        """
        if not os.path.exists(self.base_dir):
            logger.error(f"Directory {self.base_dir} does not exist.")
            return []

        if not os.path.isdir(self.base_dir):
            logger.error(f"Path {self.base_dir} is not a directory.")
            return []

        scanned_files = []
        
        for root, dirs, files in os.walk(self.base_dir):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Check file size
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE_BYTES:
                        logger.warning(f"Skipping large file ({file_size} bytes): {file_path}")
                        continue
                except OSError as e:
                    logger.warning(f"Could not access {file_path}: {e}")
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    rel_path = os.path.relpath(file_path, self.base_dir)
                    
                    scanned_files.append({
                        "id": file_path, # Absolute path as unique ID
                        "path": rel_path,
                        "title": file,
                        "type": ext[1:], # e.g. 'md', 'py'
                        "text": content,
                        "size": file_size
                    })
                except UnicodeDecodeError:
                    logger.warning(f"Skipping binary or non-utf8 file: {file_path}")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")

        logger.info(f"Crawled {len(scanned_files)} valid text files from {self.base_dir}")
        return scanned_files
