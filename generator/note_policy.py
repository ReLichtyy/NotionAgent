from clients.openai_client import OpenAIAppClient
from core.logger import get_logger

logger = get_logger("NotePolicy")

class NoteFormattingPolicy:
    def __init__(self, openai_client: OpenAIAppClient):
        self.openai_client = openai_client
        
    def process(self, raw_content: str) -> str:
        """
        Classifies the raw content and formats it according to strict mental models.
        Returns the cleanly formatted Markdown string.
        """
        system_prompt = """
Eres un formateador estricto de notas PKM (Personal Knowledge Management).
Tu único objetivo es tomar un borrador o insight y reescribirlo bajo uno de los marcos de trabajo estructurales definidos abajo.
REGLAS CRÍTICAS:
- NUNCA escribas introducciones (ej. "Aquí tienes la nota", "Claro, te lo estructuro").
- NUNCA escribas conclusiones. 
- Devuelve EXCLUSIVAMENTE el texto estructurado en Markdown puro.

PASOS:
1. Analiza el texto para detectar su naturaleza (proceso, dato estadístico, concepto, o idea expansiva).
2. Elige el MODO que mejor se adapte. Si dudas, usa "dreaming".
3. Formatea el texto respetando exactamente las etiquetas en negrita del modo elegido.

=== MODOS DE FORMATO ===

MODO 1: progressive_breakdown (Para conceptos, definiciones o resúmenes de conocimiento)
**Término:** [Concepto principal]
**Esencia:** [Definición de 1 línea, muy directa]
**Detalle:** 
- [Punto clave 1]
- [Punto clave 2]

MODO 2: process (Para guías, pasos a seguir, o flujos de ejecución)
**Objetivo:** [Qué se busca lograr]
**Secuencia de pasos:** 
1. [Paso 1]
2. [Paso 2]
**Riesgos:** [Posibles fallas o puntos críticos]
**Siguiente Acción:** [El paso inmediato a tomar]

MODO 3: stats (Para reportes, métricas, analíticas o datos duros)
**Hallazgo:** [El dato o descubrimiento clave]
**Métrica:** [Los números exactos relevantes]
**Interpretación:** [Qué significa este dato en el contexto real]
**Implicación:** [Qué decisiones debemos tomar basados en esto]

MODO 4: dreaming (Modo por defecto. Para ideas, reflexiones, journals o lluvias de ideas)
**Idea Central:** [La idea o reflexión principal]
**Expansión:** [Desarrollo profundo en 1 o 2 párrafos concisos]
**Variantes / Alternativas:** [Otras formas de abordar la idea]
**Posibles Aplicaciones:** [Lista de casos de uso]
**Próximo Experimento:** [Una pequeña acción para validar o avanzar la idea]
"""
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": f"Reescribe y formatea el siguiente texto:\n\n{raw_content}"}
        ]
        
        logger.info("Applying Note Formatting Policy...")
        response = self.openai_client.chat(messages, model="gpt-4o-mini")
        
        if response and response.content:
            return response.content.strip()
        else:
            logger.error("NoteFormattingPolicy failed, falling back to raw content.")
            return raw_content
