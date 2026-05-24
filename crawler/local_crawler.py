import os
from core.logger import get_logger
from agents.local_source_manifest import LocalSourceManifest

logger = get_logger("LocalCrawler")

IGNORED_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.venv', '.idea', '.vscode'}
MAX_FILE_SIZE_BYTES = 1024 * 1024 * 5  # 5 MB max per file

class LocalCrawler:
    def __init__(self, manifest: LocalSourceManifest):
        self.manifest = manifest

    def crawl(self) -> list[dict]:
        """
        Scans folders and files based on the manifest.
        Returns a list of dictionaries containing raw file data.
        """
        scanned_files = []
        processed_paths = set()

        # Helper function to process a single file
        def process_file(file_path: str):
            if file_path in processed_paths:
                return
                
            # Check exclusions
            for ex in self.manifest.excluded_paths:
                if file_path.startswith(ex):
                    return
                    
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.manifest.allowed_extensions:
                return
                
            try:
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE_BYTES:
                    logger.warning(f"Skipping large file ({file_size} bytes): {file_path}")
                    return
            except OSError as e:
                logger.warning(f"Could not access {file_path}: {e}")
                return

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Store absolute path as relative path to keep it readable, but unique
                scanned_files.append({
                    "id": file_path, 
                    "path": file_path,
                    "title": os.path.basename(file_path),
                    "type": ext[1:],
                    "text": content,
                    "size": file_size
                })
                processed_paths.add(file_path)
            except UnicodeDecodeError:
                logger.warning(f"Skipping binary or non-utf8 file: {file_path}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")

        # 1. Process specific files
        for file_path in self.manifest.included_files:
            if os.path.exists(file_path):
                process_file(file_path)

        # 2. Process folders
        for folder_path in self.manifest.included_folders:
            if not os.path.exists(folder_path):
                continue
                
            for root, dirs, files in os.walk(folder_path):
                # Filter out ignored dirs and excluded paths
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                
                # Check folder exclusion
                if any(root.startswith(ex) for ex in self.manifest.excluded_paths):
                    continue

                for file in files:
                    full_path = os.path.join(root, file)
                    process_file(full_path)

        logger.info(f"Crawled {len(scanned_files)} valid text files based on manifest.")
        return scanned_files
