import os
import json
from typing import List, Tuple, Callable
from core.agent_base import BaseAgent
from core.logger import get_logger

from crawler.local_crawler import LocalCrawler
from parser.local_parser import LocalParser
from assistant.local_agent import LocalMentorAgent

logger = get_logger("LocalFileAgent")

CONFIG_FILE = ".local_config.json"
FRAGMENTS_FILE = "local_workspace_fragments.json"

class LocalFileManagerAgent(BaseAgent):
    """
    Agent implementation for the Local File Workspace context.
    Encapsulates crawling local directories, parsing, and interactive chat loop.
    """
    
    def __init__(self):
        self.mentor_agent = None
        self.base_folder = self._load_base_folder()

    def _load_base_folder(self) -> str:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("base_folder", "")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return ""

    def _save_base_folder(self, path: str):
        self.base_folder = os.path.abspath(path)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"base_folder": self.base_folder}, f, indent=2)
            print(f"\n✅ Carpeta base guardada: {self.base_folder}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get_id(self) -> str:
        return "local_file_manager"

    def get_name(self) -> str:
        return "Local File Manager Agent"

    def get_description(self) -> str:
        return "Explora y conversa con tus archivos locales de código y texto."

    def is_ready(self) -> bool:
        """Checks if the context files exist and have content."""
        json_ready = os.path.exists(FRAGMENTS_FILE) and os.path.getsize(FRAGMENTS_FILE) > 0
        return json_ready

    def change_base_folder(self) -> None:
        print(f"\nCarpeta actual: {self.base_folder or 'Ninguna'}")
        new_path = input("Ingresa la ruta absoluta o relativa de la nueva carpeta base: ").strip()
        
        if not new_path:
            print("Operación cancelada.")
            return
            
        if not os.path.isdir(new_path):
            print(f"❌ Error: La ruta '{new_path}' no es un directorio válido.")
            return
            
        self._save_base_folder(new_path)
        print("💡 Te recomendamos ejecutar un 'Refresh' ahora para indexar esta nueva carpeta.")

    def refresh_knowledge(self) -> bool:
        """Runs the crawler and parser to update the local search index."""
        if not self.base_folder:
            print("\n❌ No hay una carpeta base configurada.")
            self.change_base_folder()
            if not self.base_folder:
                return False

        try:
            print(f"\n--- Escaneando carpeta: {self.base_folder} ---")
            crawler = LocalCrawler(self.base_folder)
            raw_files = crawler.crawl()
            
            if not raw_files:
                print("No se encontraron archivos válidos o la carpeta está vacía.")
                return False
                
            print("--- Generando Fragmentos Semánticos ---")
            parser = LocalParser()
            success = parser.parse_and_export(raw_files, export_path=FRAGMENTS_FILE)
            
            if success and self.is_ready():
                size = os.path.getsize(FRAGMENTS_FILE)
                print(f"✅ Conocimiento local actualizado. ({size} bytes generados)")
                return True
            else:
                logger.error("Failed to verify local context files after generation.")
                return False
                
        except Exception as e:
            logger.error(f"Local extraction pipeline failed: {e}")
            return False

    def start_chat(self) -> None:
        """Instantiates the mentor agent and starts the CLI loop."""
        if not self.is_ready():
            print("\n❌ Error: El conocimiento no está listo. Ejecuta un Refresh primero.")
            return
            
        self.mentor_agent = LocalMentorAgent()
        self.mentor_agent.start_chat_loop()

    def get_menu_options(self) -> List[Tuple[str, Callable]]:
        return [
            ("Usar contexto actual (Entrar al chat)", self.start_chat),
            ("Refrescar desde carpeta local", self.refresh_knowledge),
            ("Cambiar carpeta base", self.change_base_folder)
        ]
