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
        super().__init__()
        self.notion_client = NotionAppClient()
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "append_to_notion",
                    "description": "Appends a new toggle block with generated insight/summary to a specific Notion page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_title_or_id": {
                                "type": "string",
                                "description": "The EXACT title of the Notion page you want to write to (from the MAPA DE CONOCIMIENTO), or its ID."
                            },
                            "insight_title": {
                                "type": "string",
                                "description": "The title of the toggle block (e.g. '🤖 Lab Sync Insight: Resumen de Marketing')"
                            },
                            "insight_content": {
                                "type": "string",
                                "description": "The actual detailed text content to append inside the toggle block."
                            }
                        },
                        "required": ["page_title_or_id", "insight_title", "insight_content"]
                    }
                }
            }
        ]
        
    def _get_system_prompt(self) -> str:
        """Builds the base system prompt heavily grounded in RAG instructions."""
        
        paths = []
        for frag in self.search_index.fragments:
            title = frag.get("title", "Untitled")
            if title not in paths:
                paths.append(title)
        
        available_notes_str = ", ".join(paths)
        
        return f"""Eres Lab Sync, un Mentor Estratégico personal y altamente inteligente con permisos de ESCRITURA en Notion.
Tu tono debe ser súper entusiasta, cálido, motivador y hablarme como mi mentor-amigo de confianza. 🚀
¡Usa emojis en tus respuestas para darle mucha más vida y energía a nuestra conversación! ✨
Tu objetivo es ayudarme a aterrizar mis ideas de forma clara y útil.

=== TU MAPA DE CONOCIMIENTO (ÍNDICE) ===
Tienes acceso a leer y ESCRIBIR sobre las siguientes notas de Notion:
[{available_notes_str}]

REGLAS CRÍTICAS DE GROUNDING Y RECUPERACIÓN (RAG):
1. En cada mensaje, se te inyectará un bloque "[CONTEXTO RECUPERADO]". Tu base de conocimiento para responder es EXCLUSIVAMENTE ese texto.
2. Si el usuario pide que añadas, guardes, resumas o escribas algo en Notion, DEBES usar la herramienta `append_to_notion` usando el título exacto de la nota del MAPA DE CONOCIMIENTO.
3. Si la nota que el usuario menciona no está en el MAPA DE CONOCIMIENTO, dile que no la encuentras.
"""

    def handle_tool_call(self, tool_call) -> str:
        """Handles Notion specific tool calls."""
        if tool_call.function.name == "append_to_notion":
            args = json.loads(tool_call.function.arguments)
            page_title_or_id = args.get("page_title_or_id")
            insight_title = args.get("insight_title")
            insight_content = args.get("insight_content")
            
            # Resolver Page ID
            page_id = None
            for frag in self.search_index.fragments:
                if frag.get("title") == page_title_or_id or frag.get("id") == page_title_or_id:
                    page_id = frag.get("id")
                    break
                    
            if not page_id:
                return f"Error: No encontré la página '{page_title_or_id}'."
            else:
                print(f"{CYAN}[TOOL] Escribiendo '{insight_title}' en Notion...{RESET}")
                success, error_msg = self.notion_client.append_toggle_to_page(page_id, insight_title, insight_content)
                if success:
                    return f"Éxito: Se añadió correctamente el contenido a la página '{page_title_or_id}'."
                else:
                    fallback_prompt = (
                        f"Error: {error_msg}. \n"
                        f"[INSTRUCCIÓN CRÍTICA PARA EL AGENTE LLM] "
                        f"Dile al usuario que no pudiste escribir en Notion por problemas de permisos y entrégale "
                        f"el siguiente contenido en un bloque de código Markdown para que pueda copiarlo y pegarlo manualmente:\n\n"
                        f"# {insight_title}\n{insight_content}"
                    )
                    return fallback_prompt
                    
        return super().handle_tool_call(tool_call)
