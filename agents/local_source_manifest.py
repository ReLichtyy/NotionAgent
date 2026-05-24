import os
import json
from datetime import datetime
from typing import List, Dict, Any
from core.logger import get_logger

logger = get_logger("LocalSourceManifest")

class LocalSourceManifest:
    """
    Manages the selection of local files and folders to be indexed.
    """
    def __init__(self, manifest_path: str = "local_manifest.json"):
        self.manifest_path = manifest_path
        self.included_folders: List[str] = []
        self.included_files: List[str] = []
        self.excluded_paths: List[str] = []
        self.allowed_extensions: List[str] = [".py", ".md", ".txt", ".json", ".csv", ".js", ".ts", ".html", ".css"]
        self.selection_mode: str = "mixed" # 'folders_only', 'files_only', 'mixed'
        self.last_updated: str = None
        
        self.load()

    def load(self):
        """Loads manifest from disk if it exists."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.included_folders = data.get("included_folders", [])
                    self.included_files = data.get("included_files", [])
                    self.excluded_paths = data.get("excluded_paths", [])
                    self.allowed_extensions = data.get("allowed_extensions", self.allowed_extensions)
                    self.selection_mode = data.get("selection_mode", "mixed")
                    self.last_updated = data.get("last_updated")
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")

    def save(self):
        """Saves manifest to disk."""
        data = {
            "included_folders": self.included_folders,
            "included_files": self.included_files,
            "excluded_paths": self.excluded_paths,
            "allowed_extensions": self.allowed_extensions,
            "selection_mode": self.selection_mode,
            "last_updated": self.last_updated
        }
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def add_folder(self, path: str):
        path = os.path.abspath(path)
        if path not in self.included_folders:
            self.included_folders.append(path)
            self.save()
            return True
        return False

    def add_file(self, path: str):
        path = os.path.abspath(path)
        if path not in self.included_files:
            self.included_files.append(path)
            self.save()
            return True
        return False

    def remove_path(self, path: str):
        path = os.path.abspath(path)
        removed = False
        if path in self.included_folders:
            self.included_folders.remove(path)
            removed = True
        if path in self.included_files:
            self.included_files.remove(path)
            removed = True
        if path in self.excluded_paths:
            self.excluded_paths.remove(path)
            removed = True
        if removed:
            self.save()
        return removed

    def clear(self):
        self.included_folders = []
        self.included_files = []
        self.save()

    def mark_updated(self):
        self.last_updated = datetime.now().isoformat()
        self.save()
        
    def get_summary_dict(self) -> dict:
        return {
            "Carpetas incluidas": len(self.included_folders),
            "Archivos sueltos": len(self.included_files),
            "Último refresh": self.last_updated or "Nunca"
        }
