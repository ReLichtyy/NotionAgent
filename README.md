# Lab Sync: Multi-Agent Launcher

**Lab Sync** ha evolucionado de ser un script único a un **Ecosistema Multi-Agente** basado en un patrón *Registry*. Permite lanzar diferentes inteligencias artificiales especializadas desde un solo menú principal, manteniendo el código limpio, escalable y modular.

Actualmente incluye:
1. **Notion Workspace Agent:** Un Mentor Estratégico Bidireccional conectado a tu espacio de trabajo de Notion. Extrae, consolida, responde preguntas y *escribe* resúmenes o conclusiones de vuelta en tus páginas de Notion.
2. **Local File Manager Agent:** (En desarrollo) Un agente para interactuar con tus archivos locales.

## Arquitectura Multi-Agente

El sistema opera bajo un patrón estricto:
- `core/agent_base.py`: Define el contrato abstracto `BaseAgent` (`get_name`, `is_ready`, `start_chat`, etc.).
- `core/registry.py`: Registra y orquesta los agentes disponibles.
- `main.py`: Launcher agnóstico que dibuja menús dinámicos sin acoplarse a la lógica de ningún agente en particular.

## Notion Workspace Agent (Refactorizado)

El agente de Notion fue reescrito para ser altamente robusto:
- **Configuración centralizada:** Usa `core/config.py` para inyectar variables de entorno (`NOTION_MAX_DEPTH`, `NOTION_ROOT_PAGE_ID`, etc.).
- **Políticas de Arranque:** `agents/notion_policy.py` decide de forma inteligente si el contexto caché existe, si está vacío y qué mensajes de error mostrar al usuario.
- **Pipeline Aislado:** `agents/notion_pipeline.py` orquesta la extracción (Crawl -> Parse -> MD -> JSON) de forma segura.
- **Búsqueda Difusa (Fuzzy RAG):** El índice en memoria (`assistant/search_index.py`) utiliza `difflib` y normalización de acentos para tolerar errores tipográficos y consultas imprecisas.

## Requisitos previos

- **Python:** 3.9 o superior (recomendado 3.10+).
- **Conexiones Externas:**
  - Acceso a la API de Notion (Internal Integration Token).
  - API Key de OpenAI activa (usa modelo `gpt-4o-mini`).

## Variables de entorno (.env)

| Variable | Obligatoria | Descripción | Ejemplo de valor |
|----------|-------------|-------------|------------------|
| `NOTION_API_KEY` | Sí | Token de integración de la API de Notion. | `secret_A1B2C3D4...` |
| `OPENAI_API_KEY` | Sí | Token estándar de la API de OpenAI. | `sk-proj-xyz...` |
| `NOTION_MAX_DEPTH` | No | Profundidad máxima del crawler (Default: 3). | `3` |
| `NOTION_ROOT_PAGE_ID` | No | ID de la página raíz para escaneo acotado. Si está vacío, escanea todo el workspace. | `1234abcd...` |
| `NOTION_SEARCH_TOP_K` | No | Fragmentos inyectados por consulta al LLM (Default: 4). | `5` |

## Instalación local paso a paso

1. **Crear y activar el entorno virtual:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configurar el entorno:**
   Crea un archivo `.env` en la raíz copiando las variables de la tabla superior.
4. **Ejecutar el proyecto:**
   ```bash
   python main.py
   ```

## Flujo de ejecución

1. Corres `python main.py`.
2. Verás la pantalla de "Selección de Agente".
3. Al seleccionar el **Notion Workspace Agent**, el `NotionStartupPolicy` evaluará si tienes contexto.
4. Si no tienes contexto, usas "Refrescar conocimiento". El `NotionExtractionPipeline` bajará tus notas a `.md` y `.json`.
5. Durante el chat, el agente usa Búsqueda Difusa. Si le pides escribir en Notion, ejecutará la herramienta bidireccional `append_to_notion`.

## Próximos pasos sugeridos

- Implementar Sincronización Incremental (basado en `last_edited_time`) en el `NotionExtractionPipeline`.
- Migrar el `SimpleSearchIndex` difuso a una base de datos vectorial real (Ej. ChromaDB) para búsquedas semánticas profundas.
