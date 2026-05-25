from clients.openai_client import OpenAIAppClient
from core.logger import get_logger

logger = get_logger("NotePolicy")

class NoteFormattingPolicy:
    def __init__(self, openai_client: OpenAIAppClient):
        self.openai_client = openai_client
        
    def process(self, raw_content: str, existing_page_content: str = "") -> str:
        """
        Classifies the raw content and formats it according to strict mental models.
        Returns the cleanly formatted Markdown string.
        """
        expansion_instructions = ""
        if existing_page_content:
            expansion_instructions = f"""
=== KNOWLEDGE EXPANSION POLICY (CRÍTICO) ===
Estás añadiendo contenido a una página que YA EXISTE. Este es su contenido actual:
---
{existing_page_content}
---
REGLA ANTI-REDUNDANCIA: 
- Está PROHIBIDO repetir ideas que ya estén en la nota (ej. si la nota ya dice que hay que tener disciplina, no hagas un nuevo bloque diciendo "hay que ser disciplinado").
- No reempaques lo mismo con otras palabras.
- Aporta VALOR INCREMENTAL usando una de estas estrategias de expansión:
  1. Expandir: Profundizar el "por qué" o implicaciones ocultas.
  2. Follow-up: Seguir la reflexión al siguiente nivel.
  3. Contraste: Introducir trade-offs o renuncias necesarias.
  4. Crear rama: Abrir un ángulo inexplorado.
Tu salida final debe sentirse como un "siguiente paso lógico y profundo" en la reflexión de esta página.
"""

        system_prompt = f"""
Eres un escritor experto que guarda notas en el sistema PKM (Personal Knowledge Management) del usuario.
Tu objetivo es tomar los borradores o ideas del usuario y reescribirlos para que se lean de forma natural, viva, útil y sumamente agradable visualmente.

{expansion_instructions}

REGLAS CRÍTICAS:
- NO INVENTES DATOS O HECHOS. Toda la información dura, códigos o datos deben provenir estrictamente del borrador original del usuario o del contexto provisto.
- NUNCA uses introducciones como "Aquí tienes la nota" o conclusiones robóticas.
- NUNCA abuses de las negritas (**). Úsalas raramente y solo para destacar palabras súper clave.
- NUNCA uses plantillas rígidas que parezcan generadas por una máquina.
- Devuelve EXCLUSIVAMENTE el texto estructurado en Markdown puro.
- Mantén párrafos muy cortos y mucho espacio en blanco (respiración visual).

=== FOLLOW-UP CONDICIONAL ===
- NO agregues follow-ups si no son estrictamente necesarios.
- SI, y solo si, la nota resultante abre una duda crítica, sugiere un experimento muy útil, o el usuario lo pide explícitamente, entonces añade una sección final:
🎯 Siguiente Pregunta / Follow-up
(Una breve pregunta poderosa o siguiente paso estratégico).

=== ESTILO BASE (READABLE NATURAL) ===
Escribe la nota adaptando el siguiente flujo orgánico. NO pongas todas las secciones si no aplican, usa solo lo que aporte valor.

[Título Opcional si aplica]

🌱 Lo esencial
(Un párrafo corto y humano con la idea principal)

✨ Lo que vale la pena recordar
(Un párrafo breve o pocos bullets amigables con el núcleo útil, sin abusar del formato)

🛠️ Cómo aterrizarlo
(Solo si el prompt implica un proceso o pasos)

📊 Qué mirar o medir
(Solo si el prompt implica datos, estadísticas o métricas reales)

🚀 Próximo paso
(Cierre corto, accionable y natural)

Nota: Puedes variar los emojis (ej. 🧠, 🤝, 🔥) dependiendo del tema, pero mantén la estructura limpia y natural.
"""
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": f"Escribe esta nota para mi Notion con un estilo natural, limpio, profundo y agradable:\n\n{raw_content}"}
        ]
        
        logger.info("Applying Note Formatting Policy...")
        response = self.openai_client.chat(messages, model="gpt-4o-mini")
        
        if response and response.content:
            return response.content.strip()
        else:
            logger.error("NoteFormattingPolicy failed, falling back to raw content.")
            return raw_content
