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

import os
from typing import List, Tuple, Callable
from core.agent_base import BaseAgent
from core.logger import get_logger

from crawler.local_crawler import LocalCrawler
from parser.local_parser import LocalParser
from assistant.local_agent import LocalMentorAgent
from agents.local_source_manifest import LocalSourceManifest

logger = get_logger("LocalFileAgent")

FRAGMENTS_FILE = "local_workspace_fragments.json"

class LocalFileManagerAgent(BaseAgent):
    """
    Agent implementation for the Local File Workspace context.
    Encapsulates crawling local directories, parsing, and interactive chat loop.
    """
    
    def __init__(self):
        self.mentor_agent = None
        self.manifest = LocalSourceManifest()

    def get_id(self) -> str:
        return "local_file_manager"

    def get_name(self) -> str:
        return "Local File Manager Agent"

    def get_description(self) -> str:
        return "Explora y conversa con tus archivos locales de código y texto."

    def is_ready(self) -> bool:
        """Checks if the context files exist and have content."""
        return os.path.exists(FRAGMENTS_FILE) and os.path.getsize(FRAGMENTS_FILE) > 0

    def get_status_info(self) -> dict:
        """Returns the status info dict for the menu."""
        is_ready = self.is_ready()
        summary = self.manifest.get_summary_dict()
        
        info = {
            "Fuente": "Archivos Locales",
            "Conocimiento actual": "Disponible" if is_ready else "No disponible (Requiere refrescar)",
            "Carpetas configuradas": str(summary["Carpetas incluidas"]),
            "Archivos configurados": str(summary["Archivos sueltos"]),
            "Último refresh": str(summary["Último refresh"]),
            "Capacidades": "Chat, Configuración de fuentes mixtas, Indexación local"
        }
        return info

    def view_current_selection(self) -> None:
        print("\n" + "=" * 40)
        print(" SELECCIÓN ACTUAL (MANIFEST)")
        print("=" * 40)
        
        print(f"\n📁 Carpetas incluidas ({len(self.manifest.included_folders)}):")
        for f in self.manifest.included_folders:
            print(f"  - {f}")
            
        print(f"\n📄 Archivos específicos ({len(self.manifest.included_files)}):")
        for f in self.manifest.included_files:
            print(f"  - {f}")
            
        print(f"\n🚫 Rutas excluidas ({len(self.manifest.excluded_paths)}):")
        for f in self.manifest.excluded_paths:
            print(f"  - {f}")
            
        print(f"\n⚙️ Extensiones permitidas: {', '.join(self.manifest.allowed_extensions)}")
        print("=" * 40 + "\n")

    def select_local_sources(self) -> None:
        while True:
            print("\n--- Configuración de Fuentes Locales ---")
            print("1. Agregar carpeta completa")
            print("2. Agregar archivos específicos")
            print("3. Quitar una ruta de la selección")
            print("4. Limpiar selección")
            print("5. Volver")
            
            choice = input("\nElige una opción [1-5]: ").strip()
            
            if choice == "5":
                break
                
            elif choice == "1":
                path = input("Ingresa la ruta absoluta de la carpeta: ").strip()
                if os.path.isdir(path):
                    if self.manifest.add_folder(path):
                        print(f"✅ Carpeta agregada: {path}")
                    else:
                        print("⚠️ La carpeta ya estaba incluida.")
                else:
                    print("❌ Ruta inválida o no es un directorio.")
                    
            elif choice == "2":
                path = input("Ingresa la ruta absoluta del archivo: ").strip()
                if os.path.isfile(path):
                    if self.manifest.add_file(path):
                        print(f"✅ Archivo agregado: {path}")
                    else:
                        print("⚠️ El archivo ya estaba incluido.")
                else:
                    print("❌ Ruta inválida o no es un archivo.")
                    
            elif choice == "3":
                path = input("Ingresa la ruta exacta a quitar: ").strip()
                if self.manifest.remove_path(path):
                    print("✅ Ruta removida correctamente.")
                else:
                    print("⚠️ No se encontró la ruta en el manifest.")
                    
            elif choice == "4":
                confirm = input("¿Estás seguro de limpiar toda la selección? (s/n): ").strip().lower()
                if confirm == 's':
                    self.manifest.clear()
                    print("✅ Selección limpiada.")
                    
            else:
                print("Opción inválida.")

    def refresh_knowledge(self) -> bool:
        """Runs the crawler and parser to update the local search index."""
        if not self.manifest.included_folders and not self.manifest.included_files:
            print("\n❌ No hay rutas configuradas. Usa 'Seleccionar fuentes locales' primero.")
            return False

        try:
            print("\n--- Escaneando fuentes locales ---")
            crawler = LocalCrawler(self.manifest)
            raw_files = crawler.crawl()
            
            if not raw_files:
                print("No se encontraron archivos válidos con las extensiones permitidas.")
                return False
                
            print("--- Generando Fragmentos Semánticos ---")
            parser = LocalParser()
            success = parser.parse_and_export(raw_files, export_path=FRAGMENTS_FILE)
            
            if success and self.is_ready():
                size = os.path.getsize(FRAGMENTS_FILE)
                self.manifest.mark_updated()
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
            ("Refrescar conocimiento local", self.refresh_knowledge),
            ("Seleccionar fuentes locales", self.select_local_sources),
            ("Ver selección actual", self.view_current_selection)
        ]
