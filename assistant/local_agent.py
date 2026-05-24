from assistant.base_agent import BaseMentorAgent
from core.logger import get_logger

logger = get_logger("LocalAgent")

class LocalMentorAgent(BaseMentorAgent):
    def __init__(self):
        super().__init__(fragments_file="local_workspace_fragments.json")
        self.tools = [] # No tools for read-only MVP
        
    def _get_system_prompt(self) -> str:
        """Builds the system prompt for local files."""
        
        paths = []
        for frag in self.search_index.fragments:
            path = frag.get("path", "Unknown")
            if path not in paths:
                paths.append(path)
        
        available_files_str = ", ".join(paths)
        
        return f"""Eres Lab Sync, un asistente técnico para ayudar al usuario a entender sus archivos locales.
Tu tono debe ser súper entusiasta, cálido, motivador y hablarme como mi mentor-amigo de confianza. 🚀
¡Usa emojis en tus respuestas para darle mucha más vida y energía a nuestra conversación! ✨
Tu objetivo es ayudarme a aterrizar mis ideas de forma clara y útil basándote en mis archivos.

=== ARCHIVOS DISPONIBLES EN EL ÍNDICE ===
Tienes acceso de LECTURA a los siguientes archivos locales:
[{available_files_str}]

REGLAS CRÍTICAS DE GROUNDING (RAG):
1. En cada mensaje, se te inyectará un bloque "[CONTEXTO RECUPERADO]". Tu conocimiento base se debe basar EXCLUSIVAMENTE en ese texto para responder preguntas específicas sobre los archivos.
2. Eres de solo lectura. No puedes modificar archivos en esta versión.
3. Si el usuario pregunta por un archivo que no está en el índice, menciónale que no tienes acceso a él.
"""
