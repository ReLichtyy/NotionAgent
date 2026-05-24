import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from clients.openai_client import OpenAIAppClient
from assistant.search_index import SimpleSearchIndex
from core.logger import get_logger

logger = get_logger("BaseAgent")

# ANSI Colors for debug
GREEN = '\033[92m'
CYAN = '\033[96m'
RESET = '\033[0m'

class BaseMentorAgent(ABC):
    """
    Abstract base class for interactive mentor agents using the OpenAI client and a SimpleSearchIndex.
    """
    def __init__(self, fragments_file: str = "workspace_fragments.json"):
        self.openai_client = OpenAIAppClient()
        self.conversation_history: List[Dict[str, str]] = []
        self.search_index = SimpleSearchIndex(fragments_file=fragments_file)
        self.tools = [] # Subclasses should populate this if needed

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
                    
                # 1. Recuperación Semántica
                top_fragments = self.search_index.search(user_input, top_k=4)
                context_str = ""
                if top_fragments:
                    print(f"{CYAN}[DEBUG] Se encontraron {len(top_fragments)} fragmentos relevantes.{RESET}")
                    for idx, frag in enumerate(top_fragments):
                        context_str += f"\n--- Fragmento {idx+1} ---\nTítulo: {frag.get('title')}\nRuta: {frag.get('path')}\nContenido:\n{frag.get('text')}\n"
                
                # 2. Construir Prompt
                dynamic_user_prompt = f"[CONTEXTO RECUPERADO]\n{context_str}\n\n[CONSULTA DEL USUARIO]\n{user_input}"
                self.conversation_history.append({"role": "user", "content": dynamic_user_prompt})
                
                print("🤖 Lab Sync (Pensando...)", end="\r")
                message = self.openai_client.chat(self.conversation_history, tools=self.tools if self.tools else None)
                print(" " * 30 + "\r", end="") 
                
                if not message:
                    print("🤖 Lab Sync: Error al comunicarse con la IA.")
                    continue
                    
                # 3. Manejo de Tool Calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Registrar el llamado de la IA en el historial
                    tool_calls_data = [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in message.tool_calls]
                    self.conversation_history.append({"role": "assistant", "content": message.content, "tool_calls": tool_calls_data})
                    
                    for tool_call in message.tool_calls:
                        tool_result = self.handle_tool_call(tool_call)
                        
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": tool_result or "Error inesperado en herramienta."
                        })
                    
                    # Llamar nuevamente al modelo para que genere la respuesta final al usuario
                    print("🤖 Lab Sync (Confirmando...)", end="\r")
                    final_message = self.openai_client.chat(self.conversation_history)
                    print(" " * 30 + "\r", end="") 
                    final_text = final_message.content if final_message else "Hecho."
                    print(f"🤖 Lab Sync: {final_text}")
                    
                    # Restauramos el query original en vez del bloque de RAG masivo
                    self.conversation_history = [m for m in self.conversation_history if m.get("role") != "user" or m.get("content") != dynamic_user_prompt]
                    self.conversation_history.append({"role": "user", "content": user_input})
                    self.conversation_history.append({"role": "assistant", "content": final_text})
                    
                else:
                    text_response = message.content or "No entendí."
                    print(f"🤖 Lab Sync: {text_response}")
                    
                    # Restauramos el query original
                    self.conversation_history[-1] = {"role": "user", "content": user_input}
                    self.conversation_history.append({"role": "assistant", "content": text_response})

            except KeyboardInterrupt:
                print("\n🤖 Lab Sync: Sesión interrumpida. ¡Hasta luego!")
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"\n❌ Error inesperado: {e}")
