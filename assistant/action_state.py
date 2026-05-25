import json
import difflib
from typing import Dict, Any, List
from clients.openai_client import OpenAIAppClient
from core.logger import get_logger

logger = get_logger("IntentResolver")

class IntentResolver:
    def __init__(self, openai_client: OpenAIAppClient):
        self.openai_client = openai_client

    def _fuzzy_match_page(self, raw_target: str, available_fragments: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Attempts to securely resolve a raw string into an existing Notion page ID.
        Uses normalization and difflib for fuzzy matching.
        """
        if not raw_target:
            return {"status": "none"}
            
        raw_norm = raw_target.strip().lower()
        
        # Build mapping of normalized title -> {id, title}
        title_map = {}
        for frag in available_fragments:
            t = frag.get("title", "")
            if t:
                title_map[t.strip().lower()] = {"id": frag.get("id"), "original_title": t}
                
        # 1. Exact match (case insensitive)
        if raw_norm in title_map:
            return {"status": "exact", "id": title_map[raw_norm]["id"], "title": title_map[raw_norm]["original_title"]}
            
        # 2. Fuzzy match
        matches = difflib.get_close_matches(raw_norm, title_map.keys(), n=1, cutoff=0.7)
        if matches:
            best_match = matches[0]
            # cutoff=0.7 implies a relatively strong match
            return {"status": "fuzzy", "id": title_map[best_match]["id"], "title": title_map[best_match]["original_title"]}
            
        return {"status": "not_found", "raw": raw_target}

    def resolve(self, conversation_history: List[Dict[str, str]], available_fragments: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyzes the recent conversation history to determine the user's exact writing intent, 
        resolving the target entity using fuzzy matching.
        """
        # Filter out system prompts and tool calls for the resolver, only user/assistant text
        filtered_msgs = [m for m in conversation_history if m.get("role") in ["user", "assistant"]]
        recent_msgs = filtered_msgs[-3:]
        
        chat_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent_msgs])
        
        # Get list of known titles to help the resolver match existing entities
        known_titles = list(set([f.get("title") for f in available_fragments if f.get("title")]))
        
        prompt = f"""
Eres el "Intent Resolver" del sistema Lab Sync.
Tu trabajo es analizar la conversación más reciente y determinar la intención exacta de ESCRITURA del usuario en Notion.

REGLA DE ORO 1 (CONTEXT DRAGGING): Presta atención absoluta al ÚLTIMO mensaje del usuario. Si antes hablaban de "Notes of life", pero ahora dice "crea una pagina llamada Life fight", el target activo es "Life fight". La última instrucción sobrescribe todo.
REGLA DE ORO 2 (SAFE EDITING): Por defecto NO somos destructivos. Usa 'append_to_page' si pide guardar, añadir, o poner algo en una página existente. Usa 'create_page' si pide crear una página nueva.
REGLA DE ORO 3 (DESTRUCTIVE): SOLO usa 'destructive_edit' si pide EXPLÍCITAMENTE borrar o reemplazar contenido existente.
REGLA DE ORO 4 (PARENT): Si pide crear una página "dentro de X", 'target_name' es la nueva página y 'parent_name' es X. Si no es create_page, 'parent_name' debe estar vacío.

Páginas conocidas: {known_titles}

Historial reciente:
{chat_text}

Debes devolver UNICAMENTE un JSON válido con esta estructura:
{{
    "intent": "create_page" | "append_to_page" | "destructive_edit" | "ambiguous",
    "target_name": "Nombre de la página destino o la página nueva",
    "parent_name": "Nombre de la página padre (sólo si intent=create_page)"
}}
"""
        result = {
            "intent": "ambiguous",
            "target_name": "",
            "parent_name": "",
            "resolved_target_id": None,
            "resolved_parent_id": None
        }

        try:
            logger.info("Resolving user intent...")
            response = self.openai_client.chat([{"role": "system", "content": prompt}], model="gpt-4o-mini")
            if response and response.content:
                clean_json = response.content.replace("```json", "").replace("```", "").strip()
                llm_state = json.loads(clean_json)
                
                result["intent"] = llm_state.get("intent", "ambiguous")
                target_raw = llm_state.get("target_name", "")
                parent_raw = llm_state.get("parent_name", "")
                
                result["target_name"] = target_raw
                result["parent_name"] = parent_raw
                
                # Apply robust fuzzy matching
                if result["intent"] in ["append_to_page", "destructive_edit"]:
                    match_info = self._fuzzy_match_page(target_raw, available_fragments)
                    if match_info["status"] in ["exact", "fuzzy"]:
                        result["resolved_target_id"] = match_info["id"]
                        result["target_name"] = match_info["title"] # Use normalized correct name
                        logger.info(f"Target Resolved: {target_raw} -> {match_info['title']} ({match_info['status']})")
                    else:
                        logger.warning(f"Target '{target_raw}' not found in Notion index.")
                        
                elif result["intent"] == "create_page" and parent_raw:
                    match_info = self._fuzzy_match_page(parent_raw, available_fragments)
                    if match_info["status"] in ["exact", "fuzzy"]:
                        result["resolved_parent_id"] = match_info["id"]
                        result["parent_name"] = match_info["title"]
                        logger.info(f"Parent Resolved: {parent_raw} -> {match_info['title']} ({match_info['status']})")
                    else:
                        logger.warning(f"Parent '{parent_raw}' not found in Notion index.")
                        
                return result
        except Exception as e:
            logger.error(f"Failed to resolve intent: {e}")
            
        return result

    def resolve_source_and_context(self, user_input: str, notion_fragments: List[Dict[str, str]], local_fragments: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyzes the user input to determine:
        1. Source: 'notion', 'local_files', 'hybrid'
        2. Intent: 'read_page', 'analyze_local', 'open_query'
        3. Target Name: specific page or folder name
        """
        known_notion = list(set([f.get("title") for f in notion_fragments if f.get("title")]))
        
        prompt = f"""
Eres el 'Source Resolver' del Workspace Intelligence.
Tu tarea es clasificar la consulta del usuario antes de que el agente principal responda.

FUENTES POSIBLES (source):
- 'notion': Si menciona notas, páginas, o conceptos guardados en Notion.
- 'local_files': Si pide analizar proyectos, código, repositorios o carpetas locales.
- 'hybrid': Si pide cruzar ambas cosas (ej. "analiza este proyecto y conéctalo con mi nota de Arquitectura").

INTENCIÓN (intent):
- 'navigate_path': Si pide navegar o encontrar una página exacta usando una ruta (ej. "ve a la página IA dentro de Lab").
- 'list_children': Si pide ver qué más hay o listar el contenido de una carpeta/página (ej. "qué más hay en All Time").
- 'read_page': Quiere extraer explícitamente el contenido puntual de UNA nota del workspace.
- 'read_page_tree': Quiere extraer TODO lo que hay DENTRO, un resumen completo, o la descendencia de una página principal.
- 'analyze_local': Pide explícitamente analizar código o proyecto local.
- 'open_query': Consulta teórica, pregunta abierta o de chat normal.

Páginas conocidas en Notion: {known_notion}

Mensaje del usuario:
{user_input}

Debes devolver UNICAMENTE un JSON válido con esta estructura:
{{
    "intent": "navigate_path" | "list_children" | "read_page" | "read_page_tree" | "analyze_local" | "open_query",
    "source": "notion" | "local_files" | "hybrid",
    "target_page_or_path": "Nombre de la página o ruta (ej. 'Lab > IA > RAG', vacío si es open_query)",
    "operation_type": "EXACT_MATCH" | "FUZZY_SEARCH" | "READ_CONTENT",
    "confidence": 0.95
}}
"""
        result = {
            "intent": "open_query",
            "source": "notion", 
            "target_name": "", 
            "target_page_or_path": "",
            "operation_type": "READ_CONTENT",
            "confidence": 1.0,
            "resolved_target_id": None
        }
        
        try:
            logger.info("Resolving source and context intent...")
            response = self.openai_client.chat([{"role": "system", "content": prompt}], model="gpt-4o-mini")
            if response and response.content:
                clean_json = response.content.replace("```json", "").replace("```", "").strip()
                llm_state = json.loads(clean_json)
                
                result["source"] = llm_state.get("source", "notion")
                result["intent"] = llm_state.get("intent", "open_query")
                target_raw = llm_state.get("target_page_or_path", "")
                result["target_page_or_path"] = target_raw
                # For backwards compatibility and fuzzy matching:
                result["target_name"] = target_raw.split(" > ")[-1].strip() if " > " in target_raw else target_raw
                
                result["operation_type"] = llm_state.get("operation_type", "READ_CONTENT")
                result["confidence"] = llm_state.get("confidence", 1.0)
                
                # If confidence is low, fall back to open_query
                if result["confidence"] < 0.70 and result["intent"] != "open_query":
                    logger.warning(f"Low confidence ({result['confidence']}) for intent {result['intent']}. Falling back to open_query.")
                    result["intent"] = "open_query"
                
                if result["intent"] in ["read_page", "read_page_tree", "navigate_path", "list_children"] and result["target_name"] and result["source"] in ["notion", "hybrid"]:
                    match_info = self._fuzzy_match_page(result["target_name"], notion_fragments)
                    if match_info["status"] in ["exact", "fuzzy"]:
                        result["resolved_target_id"] = match_info["id"]
                        result["target_name"] = match_info["title"]
                        logger.info(f"Read Target Resolved: {target_raw} -> {match_info['title']} ({result['intent']})")
                    else:
                        result["intent"] = "open_query"
                        logger.warning(f"Read Target '{target_raw}' not found, falling back to open_query.")
                        
        except Exception as e:
            logger.error(f"Failed to resolve source intent: {e}")
            
        return result
