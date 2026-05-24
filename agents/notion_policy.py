import os
from enum import Enum
from dataclasses import dataclass
from core.config import get_settings

class StartupStatus(Enum):
    READY = "ready"
    MISSING_FILES = "missing_files"
    EMPTY_FILES = "empty_files"

@dataclass
class StartupResult:
    status: StartupStatus
    is_ready: bool
    message: str

class NotionStartupPolicy:
    """
    Evaluates if the Notion Agent's local knowledge context is ready for chat.
    """
    def __init__(self):
        self.settings = get_settings()
        
    def evaluate(self) -> StartupResult:
        md_path = self.settings.NOTION_MD_PATH
        json_path = self.settings.NOTION_JSON_PATH
        
        # Check existence
        if not os.path.exists(md_path) or not os.path.exists(json_path):
            return StartupResult(
                status=StartupStatus.MISSING_FILES,
                is_ready=False,
                message="No se encontraron los archivos de caché. Debes correr el Full Crawl para extraer el conocimiento de Notion."
            )
            
        # Check size
        if os.path.getsize(md_path) == 0 or os.path.getsize(json_path) == 0:
            return StartupResult(
                status=StartupStatus.EMPTY_FILES,
                is_ready=False,
                message="Los archivos de caché existen pero están vacíos. Debes ejecutar el Full Crawl de nuevo."
            )
            
        return StartupResult(
            status=StartupStatus.READY,
            is_ready=True,
            message="El contexto está listo para iniciar el chat."
        )
