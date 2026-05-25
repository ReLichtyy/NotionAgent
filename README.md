# 🚀 Stars RAGS: Workspace Intelligence Unificado

**Stars RAGS** (anteriormente Lab Sync) es un **Orquestador Híbrido de Workspace**. Se ha reescrito la arquitectura para conectar de manera inteligente bases de conocimiento en la nube (Notion) con repositorios y archivos locales, transformando al agente en un analista seguro, de alta performance y sin redundancia.

## 🧠 Arquitectura de Estabilización

El sistema abandonó los agentes monolíticos en favor de una arquitectura orquestada y desacoplada:

1. **Source Resolver Híbrido (`IntentResolver`):** 
   - Aplica una heurística local de baja latencia para decidir si vale la pena consultar al LLM.
   - Si se activa, clasifica la consulta como `notion`, `local_files` o `hybrid`, y determina si es una operación de lectura, escritura o análisis.
2. **Writing Orchestrator (`core/writing_orchestrator.py`):**
   - Centraliza y desacopla la lógica pesada de las herramientas (tools).
   - Administra la edición segura en Notion, el fallback de creación y las políticas anti-redundancia.
3. **Local Project Analyzer (`tools/local_analyzer.py`):**
   - Escanea selectivamente archivos como `package.json`, `README.md`, y `docker-compose.yml`.
   - Genera reportes ejecutivos (Arquitectura, Deuda Técnica) que se inyectan en Notion sin volcar código crudo basura.
4. **Metrics Tracker (`core/metrics.py`):**
   - Instrumentación ligera que audita el gasto de tiempo (latencia) por fase del pipeline.
   - Loggea silenciosamente la telemetría de operaciones (append, expand, follow-up) para auditoría de tokens y uso.

## 🛡️ Políticas Estrictas de Edición

- **Safe Editing:** Las ediciones destructivas (`destructive_edit`) están bloqueadas por diseño a nivel orquestador. El modelo solo puede hacer `append_to_page` o crear nuevas ramas.
- **Knowledge Expansion Policy:** Si el contenido a agregar ya existe semánticamente en la página destino (Workspace-Grounded Retrieval en vivo), el sistema **jamás** repetirá el contenido. Tiene prohibición algorítmica de redacción pasiva, obligando al modelo a crear Follow-ups condicionales o profundizar el "por qué".
- **Context Safeguard:** Los volcados masivos en vivo de Notion están truncados dinámicamente a un umbral seguro para proteger el límite de contexto (`context window`) del LLM y evitar gasto innecesario de tokens.

## 🤖 Agentes Disponibles

1. **Notion Workspace Agent**: 
   - Lee, analiza y escribe en tu espacio de trabajo de Notion.
   - Bucle de chat bidireccional con herramientas dinámicas.

2. **Local File Manager Agent**: 
   - Analiza tus carpetas de proyectos de forma segura, filtrando extensiones válidas y evadiendo archivos pesados o binarios.
   - Genera contexto reutilizable sobre tu código fuente de manera aislada (sin vector DB, guardando indexación en `local_workspace_fragments.json`).
   - Mantiene la carpeta base guardada en `.local_config.json` para facilitar futuras ejecuciones rápidas.

## 📝 Logging y Telemetría

El orquestador genera un archivo de depuración local llamado `app_debug.log` donde se registra la latencia, crawling profundo, operaciones de la API y trazas del pipeline de generación. 
**Este archivo se ignora por defecto en `.gitignore`** para evitar subir volcados y ruido innecesario a GitHub.

## ⚙️ Requisitos y Variables de Entorno (.env)

- **Python:** 3.10+
- **OpenAI API Key:** Acceso a `gpt-4o` (escritura) y `gpt-4o-mini` (heurística rápida).
- **Notion Internal Integration Token:** Permisos completos de Leer/Escribir.

| Variable | Descripción |
|----------|-------------|
| `NOTION_API_KEY` | Token de integración de la API de Notion. |
| `OPENAI_API_KEY` | Token estándar de la API de OpenAI. |
| `NOTION_MAX_DEPTH` | (Opcional) Profundidad de crawler. |
| `NOTION_ROOT_PAGE_ID` | (Opcional) ID de la página raíz. |

## 🚀 Flujo de Ejecución (Cómo usarlo)

1. Instala dependencias con `pip install -r requirements.txt`.
2. Corre `python main.py`.
3. Al elegir el agente (Notion Workspace Agent / Local File Agent), los menús actuarán como fachadas para el orquestador principal.
4. Durante el chat, el sistema responderá en fracciones de segundo para queries abiertas.
5. Si detecta intención híbrida (ej: *"Analiza este repo y guárdalo en la nota de Notion llamada Software"*), activará las herramientas, validará permisos, medirá la latencia de RAG, y devolverá un bloque `Readable Natural`.

## 🚧 Limitaciones Actuales y Roadmap

- **Limitaciones de Retrieval:** El chunking local y el indexado de Notion son estáticos (requieren refresco manual). El límite en vivo para un `read_page` es de ~8,000 caracteres antes del truncamiento de seguridad.
- **Próximos Pasos (Roadmap de Escala):**
  - Implementación de Vectores reales (ChromaDB) para superar al actual `difflib`.
  - Cronjob en background para auto-refrescar `workspace_fragments.json`.
  - Expandir el analizador local a inferencia de dependencias de Python abstractas.
