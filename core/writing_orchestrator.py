import json
from clients.notion_client import NotionAppClient
from clients.openai_client import OpenAIAppClient
from core.logger import get_logger
from core.spinner import RainbowSpinner

logger = get_logger("WritingOrchestrator")
CYAN = '\033[96m'
RESET = '\033[0m'

class WritingOrchestrator:
    """
    Desacopla la lógica pesada de llamadas a herramientas, resolución de intents y edición en Notion
    del ciclo conversacional del agente principal.
    """
    def __init__(self, openai_client: OpenAIAppClient, notion_client: NotionAppClient):
        self.openai_client = openai_client
        self.notion_client = notion_client

    def execute_analyze_local(self, tool_call) -> str:
        try:
            args = json.loads(tool_call.function.arguments)
            path = args.get("path", ".")
            
            from tools.local_analyzer import LocalProjectAnalyzer
            analyzer = LocalProjectAnalyzer(self.openai_client)
            
            print(f"{CYAN}🤖 Analizando proyecto local en: {path}...{RESET}")
            return analyzer.analyze_directory(path)
        except Exception as e:
            logger.error(f"Failed to analyze local project: {e}")
            return f"Error al ejecutar analyze_local_project: {e}"

    def execute_append_to_notion(self, tool_call, conversation_history, fragments, get_live_context_func) -> str:
        try:
            args = json.loads(tool_call.function.arguments)
            insight_content = args.get("insight_content", "No content provided.")
            
            print(f"{CYAN}🤖 Evaluando reglas de Grounding y Safe Editing...{RESET}")
            from assistant.action_state import IntentResolver
            resolver = IntentResolver(self.openai_client)
            state = resolver.resolve(conversation_history, fragments)
            
            intent = state.get("intent")
            target_name = state.get("target_name")
            target_id = state.get("resolved_target_id")
            parent_name = state.get("parent_name")
            parent_id = state.get("resolved_parent_id")
            
            if intent == "destructive_edit":
                return "Política de Seguridad: NO está permitido borrar, limpiar o reemplazar contenido destructivamente en Notion."
                
            if not target_name:
                return "Error: No se pudo determinar el nombre de la página objetivo."
                
            if intent == "append_to_page" and not target_id:
                print(f"{CYAN}[DEBUG] Target '{target_name}' no encontrado. Escalando a creación...{RESET}")
                intent = "create_page"
                
            if intent == "create_page" and not parent_id:
                parent_id = None
                for frag in fragments:
                    if frag.get("title") in ["Software", "Life"]:
                        parent_id = frag.get("id")
                        break
                if not parent_id and fragments:
                    parent_id = fragments[0].get("id")
                
            with RainbowSpinner("Estructurando nota y validando expansión..."):
                from generator.note_policy import NoteFormattingPolicy
                
                existing_content = ""
                if intent == "append_to_page" and target_id:
                    existing_content = get_live_context_func(target_id)
                    
                formatter = NoteFormattingPolicy(self.openai_client)
                structured_content = formatter.process(insight_content, existing_content)
                
            if intent == "create_page":
                if not parent_id:
                    return "Error: No se encontró una página padre válida para crear la nueva página."
                
                print(f"{CYAN}🤖 Creando página '{target_name}'...{RESET}")
                success, new_page_id = self.notion_client.create_page(parent_page_id=parent_id, title=target_name)
                if not success:
                    return f"Error al intentar crear la página: {new_page_id}"
                
                target_id = new_page_id
                intent = "append_to_page"
                
            if intent == "append_to_page":
                print(f"{CYAN}🤖 Añadiendo insight en '{target_name}'...{RESET}")
                success, msg = self.notion_client.append_toggle_to_page(
                    page_id=target_id,
                    title="Insight Documentado",
                    text_content=structured_content
                )
                if success:
                    return f"Éxito: Insight añadido correctamente en '{target_name}'."
                else:
                    return f"Error al añadir: {msg}"
                    
            return "Error: Intención no manejada."
            
        except Exception as e:
            logger.error(f"Failed to append to Notion: {e}")
            return f"Error interno al guardar: {e}"
