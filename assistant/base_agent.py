import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from clients.openai_client import OpenAIAppClient
from assistant.search_index import SimpleSearchIndex
from core.logger import get_logger
from core.ui_formatter import UIFormatter

logger = get_logger("BaseAgent")

# ANSI Colors for debug
GREEN = '\033[92m'
CYAN = '\033[96m'
RESET = '\033[0m'

class BaseMentorAgent(ABC):
    """
    Abstract base class for interactive mentor agents using the OpenAI client and a SimpleSearchIndex.
    """
    def __init__(self, fragments_file: str = "workspace_fragments.json", theme_color: str = "white"):
        self.openai_client = OpenAIAppClient()
        self.conversation_history: List[Dict[str, str]] = []
        self.search_index = SimpleSearchIndex(fragments_file=fragments_file)
        
        # Load local fragments as well for hybrid source resolution
        self.local_search_index = SimpleSearchIndex(fragments_file="local_workspace_fragments.json")
        
        self.tools = [] # Subclasses should populate this if needed
        self.theme_color = theme_color

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Builds the base system prompt for the specific agent."""
        pass

    def handle_tool_call(self, tool_call) -> Optional[str]:
        """
        Subclasses should override this to handle their specific tools.
        Return the string result of the tool call, or None if the tool is unrecognized.
        """
        return f"Error: Tool {tool_call.function.name} not implemented."

    def _get_live_context(self, target_id: str) -> str:
        """Override in subclasses to fetch live content if needed."""
        return ""

    def start_chat_loop(self):
        """Starts an interactive CLI chat session with Semantic Retrieval and Tool Calling."""
        print("\n" + "="*50)
        print("🧠 INICIANDO LAB SYNC: MODO MENTOR (BIDIRECCIONAL) 🧠")
        print("="*50)
        
        if not self.search_index.fragments:
            print(f"{GREEN}[DEBUG] ERROR: No se cargaron fragmentos.{RESET}")
        else:
            print(f"{GREEN}[DEBUG] Índice Semántico inicializado con {len(self.search_index.fragments)} fragmentos.{RESET}")

        print("\nConectado usando el modelo GPT-4o-mini (Calidad/Precio).")
        print("Escribe 'salir' o 'exit' para terminar la sesión.\n")

        self.conversation_history = [
            {"role": "system", "content": self._get_system_prompt()}
        ]

        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                if user_input.lower() in ["salir", "exit", "quit"]:
                    print("\n🤖 Lab Sync: Nos vemos pronto. ¡Sigue aterrizando ideas!")
                    break
                if not user_input:
                    continue
                    
                from assistant.action_state import IntentResolver
                from core.spinner import RainbowSpinner
                from core.metrics import MetricsTracker
                import re
                
                metrics = MetricsTracker()
                
                live_context = ""
                source_state = {"source": "notion", "intent": "open_query", "target_name": ""}
                
                # Heuristic Pre-filter: Only invoke IntentResolver if it looks like a read/write/analyze command
                # Keywords: guarda, anota, resume, analiza, contexto de, pagina, nota, proyecto, sube, escribe, añade
                heuristic_pattern = r"(guarda|anot|resum|analiza|context|pagina|nota|proyect|sube|escrib|añad|agrega)"
                needs_resolver = bool(re.search(heuristic_pattern, user_input.lower()))
                
                if needs_resolver:
                    metrics.start_phase("Intent Resolver")
                    with RainbowSpinner("Enrutando contexto (Source Resolver)..."):
                        resolver = IntentResolver(self.openai_client)
                        source_state = resolver.resolve_source_and_context(
                            user_input, 
                            self.search_index.fragments, 
                            self.local_search_index.fragments
                        )
                        
                        if source_state.get("intent") == "read_page" and source_state.get("resolved_target_id"):
                            t_id = source_state.get("resolved_target_id")
                            t_name = source_state.get("target_name")
                            # Fetch live text but truncate to avoid context blowup (Etapa 4 Fix P4)
                            raw_text = self._get_live_context(t_id)
                            live_text = raw_text[:8000] + "\n[...Truncado por seguridad de contexto...]" if len(raw_text) > 8000 else raw_text
                            
                            if live_text:
                                live_context = f"\n=== [CONTENIDO EN VIVO DE LA PÁGINA: {t_name}] ===\n{live_text}\n====================\n"
                    metrics.end_phase("Intent Resolver")

                # Build context based on source
                metrics.start_phase("Semantic Search")
                context_str = live_context
                
                source = source_state.get("source", "notion")
                
                # Fetch semantic fragments depending on source
                notion_frags = []
                local_frags = []
                
                if source in ["notion", "hybrid"]:
                    notion_frags = self.search_index.search(user_input, top_k=3)
                if source in ["local_files", "hybrid"]:
                    local_frags = self.local_search_index.search(user_input, top_k=3)
                    
                if notion_frags:
                    for idx, frag in enumerate(notion_frags):
                        context_str += f"\n--- Fragmento Notion {idx+1} ---\nTítulo: {frag.get('title')}\nRuta: {frag.get('path')}\nContenido:\n{frag.get('text')}\n"
                
                if local_frags:
                    for idx, frag in enumerate(local_frags):
                        context_str += f"\n--- Fragmento Local {idx+1} ---\nTítulo: {frag.get('title')}\nRuta: {frag.get('path')}\nContenido:\n{frag.get('text')}\n"
                metrics.end_phase("Semantic Search")
                
                # 2. Construir Prompt
                dynamic_user_prompt = f"[CONTEXTO DEL WORKSPACE ({source.upper()})]\n{context_str}\n\n[CONSULTA DEL USUARIO]\n{user_input}"
                self.conversation_history.append({"role": "user", "content": dynamic_user_prompt})
                
                from core.spinner import RainbowSpinner
                
                metrics.start_phase("LLM Generation")
                with RainbowSpinner("Pensando..."):
                    message = self.openai_client.chat(
                        self.conversation_history, 
                        model="gpt-4o",
                        tools=self.tools if self.tools else None
                    )
                metrics.end_phase("LLM Generation")
                
                if not message:
                    print("🤖 Lab Sync: Error al comunicarse con la IA.")
                    continue
                    
                # 3. Manejo de Tool Calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Registrar el llamado de la IA en el historial
                    tool_calls_data = [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in message.tool_calls]
                    self.conversation_history.append({"role": "assistant", "content": message.content, "tool_calls": tool_calls_data})
                    
                    for tool_call in message.tool_calls:
                        metrics.start_phase(f"Tool {tool_call.function.name}")
                        tool_result = self.handle_tool_call(tool_call)
                        
                        # Background OP Logging for analytics
                        if tool_call.function.name == "append_to_notion":
                            metrics.log_operation("append_to_notion", "NotionPage")
                        elif tool_call.function.name == "analyze_local_project":
                            metrics.log_operation("analyze_local_project", "LocalPath")
                            
                        metrics.end_phase(f"Tool {tool_call.function.name}")
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": tool_result or "Error inesperado en herramienta."
                        })
                    
                    # Llamar nuevamente al modelo para que genere la respuesta final al usuario
                    metrics.start_phase("LLM Final Response")
                    with RainbowSpinner("Lab Sync escribiendo insight..."):
                        final_message = self.openai_client.chat(self.conversation_history)
                    metrics.end_phase("LLM Final Response")
                        
                    final_text = final_message.content if final_message else "Hecho."
                    
                    UIFormatter.print_agent_avatar(self.theme_color)
                    UIFormatter.print_typewriter_markdown(final_text)
                    
                    # Restauramos el query original en vez del bloque de RAG masivo
                    self.conversation_history = [m for m in self.conversation_history if m.get("role") != "user" or m.get("content") != dynamic_user_prompt]
                    self.conversation_history.append({"role": "user", "content": user_input})
                    self.conversation_history.append({"role": "assistant", "content": final_text})
                    
                else:
                    text_response = message.content or "No entendí."
                    
                    UIFormatter.print_agent_avatar(self.theme_color)
                    UIFormatter.print_typewriter_markdown(text_response)
                    
                    # Restauramos el query original
                    self.conversation_history[-1] = {"role": "user", "content": user_input}
                    self.conversation_history.append({"role": "assistant", "content": text_response})

                metrics.print_summary()

            except KeyboardInterrupt:
                print("\n🤖 Lab Sync: Sesión interrumpida. ¡Hasta luego!")
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"\n❌ Error inesperado: {e}")
