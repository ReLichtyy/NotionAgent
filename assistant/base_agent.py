import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import re

from clients.openai_client import OpenAIAppClient
from assistant.search_index import SimpleSearchIndex
from core.logger import get_logger
from core.ui_formatter import UIFormatter, FocusPresenter
from assistant.action_state import ActionState, Source, ActionType, ActionStateRouter, NodeState
from core.spinner import RainbowSpinner
from core.metrics import MetricsTracker

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
        
        # Load structural navigation tree
        from core.navigation_index import NavigationIndex
        self.nav_index = NavigationIndex()
        self.nav_index.load()
        
        self.tools = [] # Subclasses should populate this if needed
        self.theme_color = theme_color
        
        self.action_state = ActionState(
            action_type=ActionType.IDLE,
            source=Source.NOTION
        )
        self.router = ActionStateRouter(self.openai_client)

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
                    
                metrics = MetricsTracker()
                live_context = ""
                
                metrics.start_phase("ActionState Router")
                with RainbowSpinner("Enrutando estado de acción..."):
                    self.action_state = self.router.route(
                        self.action_state,
                        user_input,
                        self.nav_index,
                        self.search_index
                    )
                metrics.end_phase("ActionState Router")
                
                st = self.action_state
                bypass_semantic = False
                
                if st.action_type == ActionType.READ_NODE and st.focus.is_focused and st.focus.current_node_id:
                    t_id = st.focus.current_node_id
                    t_name = st.focus.current_node_name
                    raw_text = self._get_live_context(t_id)
                    live_text = raw_text[:8000] + "\n[...Truncado por seguridad de contexto...]" if len(raw_text) > 8000 else raw_text
                    
                    if live_text:
                        live_context = f"\n=== [CONTENIDO EN VIVO DE LA PÁGINA: {t_name}] ===\n{live_text}\n====================\n"
                        
                elif st.action_type == ActionType.READ_TREE and st.focus.is_focused and st.focus.current_node_id:
                    t_name = st.focus.current_node_name
                    root_nav = self.nav_index.get_node(st.focus.current_node_id)
                    if root_nav:
                        descendants = self.nav_index.get_descendants(root_nav.id)
                        if descendants:
                            tree_text = ""
                            for d in descendants:
                                if not d.accessible:
                                    tree_text += f"\n--- {d.title} ({d.path}) ---\n[Recurso Inaccesible/Restringido]\n"
                                    continue
                                    
                                frag_text = ""
                                for f in self.search_index.fragments:
                                    if f.get("id") == d.id:
                                        frag_text = f.get("text", "")
                                        break
                                        
                                if len(frag_text) > 1500:
                                    frag_text = frag_text[:1500] + "\n[...Truncado (1500 chars limit)]"
                                tree_text += f"\n--- {d.title} ({d.path}) ---\n{frag_text}\n"
                            
                            if len(tree_text) > 10000:
                                tree_text = tree_text[:10000] + "\n\n[... Árbol truncado globalmente por seguridad (10,000 chars).]"
                                
                            live_context = f"\n=== [ÁRBOL DE CONTENIDO PROFUNDO: {root_nav.breadcrumb}] ===\n{tree_text}\n====================\n"
                        else:
                            logger.warning(f"Tree requested for {t_name} but no descendants found.")
                            
                elif st.action_type == ActionType.NAVIGATE and st.focus.is_focused and st.focus.current_node_id:
                    node = self.nav_index.get_node(st.focus.current_node_id)
                    if node:
                        frag_text = ""
                        for f in self.search_index.fragments:
                            if f.get("id") == node.id:
                                frag_text = f.get("text", "")
                                break
                                
                        if not node.accessible:
                            frag_text = "[Recurso Inaccesible/Restringido]"
                            
                        live_context = f"\n=== [NAVEGACIÓN EXITOSA: {node.title}] ===\nRuta exacta: {node.path}\nContenido:\n{frag_text[:2000]}\n====================\n"
                        bypass_semantic = True
                        
                elif st.action_type == ActionType.LIST_CHILDREN and st.focus.is_focused and st.focus.current_node_id:
                    node = self.nav_index.get_node(st.focus.current_node_id)
                    if node:
                        children = self.nav_index.list_children(node.id)
                        if children:
                            children_list = "\n".join([f"- {c.icon or '📄'} {c.title} (Ruta: {c.path}) {'[Restringido]' if not c.accessible else ''}" for c in children])
                            live_context = f"\n=== [CONTENIDO DENTRO DE: {node.breadcrumb}] ===\n{children_list}\n====================\n"
                            bypass_semantic = True

                # Build context based on source
                metrics.start_phase("Semantic Search")
                context_str = live_context
                
                notion_frags = []
                local_frags = []
                
                # Only use RAG if it's SEARCH_CONTENT or if we don't have enough context from navigation
                if st.action_type == ActionType.SEARCH_CONTENT and not bypass_semantic:
                    # Si hay focus, limitamos la busqueda semantica (idealmente filtrando por parent_id,
                    # pero SimpleSearchIndex no soporta filtro por id directamente. Por simplicidad, agregamos el path al query)
                    search_query = st.filters.topic or user_input
                    if st.focus.is_focused and st.focus.current_node_name:
                         search_query += f" {st.focus.current_node_name}"
                         
                    if st.source in [Source.NOTION, Source.HYBRID]:
                        notion_frags = self.search_index.search(search_query, top_k=3)
                    if st.source in [Source.LOCAL, Source.HYBRID]:
                        local_frags = self.local_search_index.search(search_query, top_k=3)
                    
                if notion_frags:
                    for idx, frag in enumerate(notion_frags):
                        context_str += f"\n--- Fragmento Notion {idx+1} ---\nTítulo: {frag.get('title')}\nRuta: {frag.get('path')}\nContenido:\n{frag.get('text')}\n"
                
                if local_frags:
                    for idx, frag in enumerate(local_frags):
                        context_str += f"\n--- Fragmento Local {idx+1} ---\nTítulo: {frag.get('title')}\nRuta: {frag.get('path')}\nContenido:\n{frag.get('text')}\n"
                metrics.end_phase("Semantic Search")
                
                # 2. Construir Prompt
                dynamic_user_prompt = f"[CONTEXTO DEL WORKSPACE ({st.source.upper()})]\n{context_str}\n\n[CONSULTA DEL USUARIO]\n{user_input}"
                self.conversation_history.append({"role": "user", "content": dynamic_user_prompt})
                
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
                    tool_calls_data = [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in message.tool_calls]
                    self.conversation_history.append({"role": "assistant", "content": message.content, "tool_calls": tool_calls_data})
                    
                    for tool_call in message.tool_calls:
                        metrics.start_phase(f"Tool {tool_call.function.name}")
                        tool_result = self.handle_tool_call(tool_call)
                        
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
                    
                    metrics.start_phase("LLM Final Response")
                    with RainbowSpinner("Lab Sync escribiendo insight..."):
                        final_message = self.openai_client.chat(self.conversation_history)
                    metrics.end_phase("LLM Final Response")
                        
                    final_text = final_message.content if final_message else "Hecho."
                    
                    # RENDER UX BANNER
                    FocusPresenter.render_focus_banner(self.action_state)
                    UIFormatter.print_agent_avatar(self.theme_color)
                    UIFormatter.print_typewriter_markdown(final_text)
                    
                    self.conversation_history = [m for m in self.conversation_history if m.get("role") != "user" or m.get("content") != dynamic_user_prompt]
                    self.conversation_history.append({"role": "user", "content": user_input})
                    self.conversation_history.append({"role": "assistant", "content": final_text})
                    
                else:
                    text_response = message.content or "No entendí."
                    
                    # RENDER UX BANNER
                    FocusPresenter.render_focus_banner(self.action_state)
                    UIFormatter.print_agent_avatar(self.theme_color)
                    UIFormatter.print_typewriter_markdown(text_response)
                    
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
