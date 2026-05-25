import json
from clients.notion_client import NotionAppClient
from assistant.base_agent import BaseMentorAgent
from core.logger import get_logger

logger = get_logger("NotionAgent")

# ANSI Colors for debug
CYAN = '\033[96m'
RESET = '\033[0m'

class NotionMentorAgent(BaseMentorAgent):
    def __init__(self):
        super().__init__(theme_color="cyan")
        self.notion_client = NotionAppClient()
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "append_to_notion",
                    "description": "Formatea una idea estructurada y la guarda (crea o añade) en Notion usando el intent resolver dinámico.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "insight_content": {
                                "type": "string",
                                "description": "El borrador de la nota, reflexión o información a guardar."
                            }
                        },
                        "required": ["insight_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_local_project",
                    "description": "Escanea una ruta local, lee archivos clave (package.json, README, etc.) y devuelve un reporte estructurado de arquitectura, riesgos y deuda técnica.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "La ruta absoluta o relativa del proyecto local a analizar."
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]
        
    def _get_live_context(self, target_id: str) -> str:
        """Fetches live content from Notion API for grounded reading/writing."""
        return self.notion_client.read_page_content_as_text(target_id)
        
    def _get_system_prompt(self) -> str:
        """Builds the base system prompt heavily grounded in RAG instructions."""
        
        paths = []
        for frag in self.search_index.fragments:
            title = frag.get("title", "Untitled")
            if title not in paths:
                paths.append(title)
        
        available_notes_str = ", ".join(paths)
        
        return f"""Eres Lab Sync, un Mentor Estratégico personal y altamente eficiente con permisos de ESCRITURA en Notion.
Tu tono debe ser directo, maduro, útil y sin exageraciones dramáticas (no uses frases como "¡Vamos a triunfar!" o "¡No me rindo!").
Habla como un asesor experto de confianza. Responde con naturalidad si algo falla y ofrece alternativas.

=== TU MAPA DE CONOCIMIENTO (ÍNDICE) ===
Tienes acceso a leer y ESCRIBIR sobre las siguientes notas de Notion:
[{available_notes_str}]

REGLAS CRÍTICAS DE GROUNDING Y RECUPERACIÓN (RAG):
1. En cada mensaje se inyectará un bloque "[CONTEXTO RECUPERADO]". Úsalo para responder.
2. Si el usuario pide que guardes, añadas o escribas algo en Notion, DEBES usar la herramienta `append_to_notion` sin intentar adivinar los IDs precisos (escribe el nombre que el usuario te pidió, el sistema lo resolverá internamente).
3. No le expliques al usuario los JSONs internos ni las herramientas, mantén la respuesta limpia.
4. REGLA DE GROUNDING ESTRICTO: Si el usuario te pide navegar a una página, leerla o listar su contenido, y el bloque [CONTEXTO RECUPERADO] está vacío o no contiene la información pedida, TIENES ESTRICTAMENTE PROHIBIDO inventar o sugerir contenido genérico. En su lugar, debes admitir explícitamente que no encontraste la información y ofrecer una lista de páginas candidatas cercanas o pedir confirmación de la ruta exacta.
"""

    def handle_tool_call(self, tool_call) -> str:
        """Handles internal tool calls by delegating to the WritingOrchestrator."""
        from core.writing_orchestrator import WritingOrchestrator
        orchestrator = WritingOrchestrator(self.openai_client, self.notion_client)
        
        if tool_call.function.name == "analyze_local_project":
            return orchestrator.execute_analyze_local(tool_call)

        elif tool_call.function.name == "append_to_notion":
            return orchestrator.execute_append_to_notion(
                tool_call, 
                self.conversation_history, 
                self.search_index.fragments,
                self._get_live_context
            )
        
        return "Herramienta no implementada."
