import json
import difflib
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from clients.openai_client import OpenAIAppClient
from core.logger import get_logger

logger = get_logger("ActionStateRouter")


class Source(str, Enum):
    NOTION = "notion"
    LOCAL = "local"
    HYBRID = "hybrid"


class ActionType(str, Enum):
    NAVIGATE = "navigate"          
    LIST_CHILDREN = "list_children"
    READ_NODE = "read_node"        
    READ_TREE = "read_tree"        
    SEARCH_CONTENT = "search_content" 
    WRITE_NOTE = "write_note"      
    CLARIFY = "clarify"            
    IDLE = "idle"                  


class NodeState(str, Enum):
    ACTIVE = "active"
    INACCESSIBLE = "inaccessible"  
    STALE_ID = "stale_id"          
    MISSING = "missing"            


class SearchFilters(BaseModel):
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    sources: List[Source] = Field(default_factory=list)


class PageFocusState(BaseModel):
    is_focused: bool = False
    current_node_id: Optional[str] = None
    current_node_name: Optional[str] = None
    parent_node_id: Optional[str] = None
    path: Optional[str] = None
    node_state: NodeState = NodeState.ACTIVE
    breadcrumb: List[str] = Field(default_factory=list)


class ActionState(BaseModel):
    action_type: ActionType
    source: Source
    focus: PageFocusState = Field(default_factory=PageFocusState)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    confidence: float = 1.0
    last_query: Optional[str] = None
    target_node_name: Optional[str] = None 


class ActionStateRouter:
    def __init__(self, openai_client: OpenAIAppClient):
        self.openai_client = openai_client

    def resolve_navigation_target(self, target_query: str, nav_index, search_index) -> Optional[PageFocusState]:
        """Algoritmo de 3 niveles para encontrar el Page Focus."""
        
        # 1. Exact/Fuzzy Title Match
        title_matches = nav_index.find_by_title(target_query)
        if title_matches:
            node = title_matches[0]
            node_state = NodeState.ACTIVE if node.accessible else NodeState.INACCESSIBLE
            return PageFocusState(is_focused=True, current_node_id=node.id, current_node_name=node.title, parent_node_id=node.parent_id, path=node.path, node_state=node_state, breadcrumb=node.breadcrumb)
            
        # 2. Path Match
        path_match = nav_index.resolve_path(target_query)
        if path_match:
            node_state = NodeState.ACTIVE if path_match.accessible else NodeState.INACCESSIBLE
            return PageFocusState(is_focused=True, current_node_id=path_match.id, current_node_name=path_match.title, parent_node_id=path_match.parent_id, path=path_match.path, node_state=node_state, breadcrumb=path_match.breadcrumb)
            
        # 3. Semantic Search Fallback
        semantic_matches = search_index.search(target_query, top_k=1)
        if semantic_matches:
            frag = semantic_matches[0]
            # Extraer info completa usando el nav_index si existe
            # SimpleSearchIndex usa path. Nav index usa id, asi que usamos search por id
            node_id = frag.get("id")
            if node_id:
                # In navigation_index, we can traverse or just search.
                # Para simplificar si no hay get_node directo:
                def find_node_by_id(nodes, tid):
                    for n in nodes:
                        if n.id == tid: return n
                        res = find_node_by_id(n.children, tid)
                        if res: return res
                    return None
                    
                node = find_node_by_id(nav_index.root_nodes, node_id)
                if node:
                    node_state = NodeState.ACTIVE if node.accessible else NodeState.INACCESSIBLE
                    return PageFocusState(is_focused=True, current_node_id=node.id, current_node_name=node.title, parent_node_id=node.parent_id, path=node.path, node_state=node_state, breadcrumb=node.breadcrumb)
                
            # Fallback si no esta en nav_index pero si en search
            return PageFocusState(is_focused=True, current_node_id=node_id, current_node_name=frag.get("title"), path=frag.get("path"), breadcrumb=[frag.get("title")])
                
        return None

    def route(self, last_state: ActionState, user_message: str, nav_index, search_index) -> ActionState:
        # Extraemos títulos conocidos limitados
        known_notion = [n.title for n in nav_index.root_nodes][:10]
        
        prompt = f"""
Eres el 'Action Router' del sistema.
Tu tarea es decidir el próximo estado de acción basándote en el mensaje del usuario y su estado actual.

ESTADO ACTUAL:
{last_state.model_dump_json(indent=2)}

FUENTES (source): 'notion', 'local', 'hybrid'
ACCIONES (action_type):
- 'navigate': Moverse por el árbol o página concreta (ej. "entra a Lab", "ve a X")
- 'list_children': Ver qué hay aquí (ej. "qué hay en esta carpeta")
- 'read_node': Leer un archivo/página puntual (ej. "lee esta nota")
- 'read_tree': Leer un nodo y sus hijos (ej. "analiza este proyecto entero")
- 'search_content': RAG, buscar información basada en una pregunta (ej. "busca comandos git", "cómo funciona X")
- 'write_note': Crear o editar nota
- 'idle': Conversación general abierta

Páginas principales en Notion: {known_notion}

Mensaje del usuario: "{user_message}"

Instrucciones:
Analiza la intención. Devuelve un JSON con los DELTAS para actualizar el estado.
Solo incluye lo que cambie.
Si el usuario hace una búsqueda que implica moverse a una página, usa 'navigate'.
Si el usuario hace una pregunta sobre un tema, usa 'search_content'.

Campos posibles en tu JSON de respuesta:
{{
    "action_type": "...", 
    "source": "...", 
    "target_node_name": "Nombre a navegar o afectar (solo si cambia)",
    "topic": "Tema de búsqueda (solo si action es search_content)",
    "is_new_search": true 
}}
"""
        try:
            logger.info("Routing user intent with LLM...")
            response = self.openai_client.chat([{"role": "system", "content": prompt}], model="gpt-4o-mini")
            
            llm_decision = {}
            if response and response.content:
                clean_json = response.content.replace("```json", "").replace("```", "").strip()
                llm_decision = json.loads(clean_json)
                
            return self.update_action_state(last_state, user_message, llm_decision, nav_index, search_index)
            
        except Exception as e:
            logger.error(f"Failed to route intent: {e}")
            fallback = last_state.model_copy(deep=True)
            fallback.action_type = ActionType.IDLE
            fallback.last_query = user_message
            return fallback

    def update_action_state(self, last_state: ActionState, user_message: str, llm_decision: dict, nav_index, search_index) -> ActionState:
        new_state = last_state.model_copy(deep=True)
        new_state.last_query = user_message
        
        # 1. Heurísticas explícitas (Sube un nivel)
        up_keywords = ["sube un nivel", "ir atras", "volver arriba", "nivel superior"]
        if any(k in user_message.lower() for k in up_keywords):
            if new_state.focus.parent_node_id:
                # Encontrar el nodo padre en el nav_index
                def find_node(nodes, target_id):
                    for n in nodes:
                        if n.id == target_id: return n
                        res = find_node(n.children, target_id)
                        if res: return res
                    return None
                    
                parent_node = find_node(nav_index.root_nodes, new_state.focus.parent_node_id)
                if parent_node:
                    node_state = NodeState.ACTIVE if parent_node.accessible else NodeState.INACCESSIBLE
                    new_state.focus = PageFocusState(is_focused=True, current_node_id=parent_node.id, current_node_name=parent_node.title, parent_node_id=parent_node.parent_id, path=parent_node.path, node_state=node_state, breadcrumb=parent_node.breadcrumb)
                    new_state.action_type = ActionType.NAVIGATE
                    return new_state
            else:
                # Ya estamos en la raíz o foco global
                new_state.focus = PageFocusState(is_focused=False)
                new_state.action_type = ActionType.NAVIGATE
                return new_state

        # 2. Heurísticas ("En qué page estás")
        status_keywords = ["en que page", "donde estamos", "ubicacion actual"]
        if any(k in user_message.lower() for k in status_keywords):
            new_state.action_type = ActionType.IDLE
            return new_state

        # 3. Heurísticas (Limpieza de búsqueda)
        limpieza_keywords = ["elimina mi búsqueda", "borra la búsqueda", "limpia los filtros", "borrar búsqueda", "quita los filtros"]
        if any(k in user_message.lower() for k in limpieza_keywords):
            new_state.filters = SearchFilters() 
            new_state.action_type = ActionType.NAVIGATE 
            return new_state

        new_action = llm_decision.get("action_type")
        if new_action:
            new_state.action_type = ActionType(new_action)
            
        new_source = llm_decision.get("source")
        if new_source:
            new_state.source = Source(new_source)
            
        if new_state.action_type == ActionType.SEARCH_CONTENT:
            new_topic = llm_decision.get("topic")
            if new_topic:
                new_state.filters.topic = new_topic
            if llm_decision.get("is_new_search"):
                new_state.filters = SearchFilters(topic=new_topic)

        target_node = llm_decision.get("target_node_name")
        if target_node:
            new_state.target_node_name = target_node
            
            if new_state.action_type in [ActionType.NAVIGATE, ActionType.READ_NODE, ActionType.READ_TREE, ActionType.LIST_CHILDREN]:
                new_focus = self.resolve_navigation_target(target_node, nav_index, search_index)
                if new_focus:
                    new_state.focus = new_focus
                else:
                    new_state.action_type = ActionType.CLARIFY
                    new_state.focus.node_state = NodeState.MISSING
                
        return new_state


# --- Backward compatibility shim for old IntentResolver ---
class IntentResolver:
    def __init__(self, openai_client):
        self.openai_client = openai_client

    def _fuzzy_match_page(self, raw_target: str, available_fragments: List[Dict[str, str]]) -> Dict[str, Any]:
        if not raw_target:
            return {"status": "none"}
            
        raw_norm = raw_target.strip().lower()
        title_map = {}
        for frag in available_fragments:
            t = frag.get("title", "")
            if t:
                title_map[t.strip().lower()] = {"id": frag.get("id"), "original_title": t}
                
        if raw_norm in title_map:
            return {"status": "exact", "id": title_map[raw_norm]["id"], "title": title_map[raw_norm]["original_title"]}
            
        matches = difflib.get_close_matches(raw_norm, title_map.keys(), n=1, cutoff=0.7)
        if matches:
            best_match = matches[0]
            return {"status": "fuzzy", "id": title_map[best_match]["id"], "title": title_map[best_match]["original_title"]}
            
        return {"status": "not_found", "raw": raw_target}

    def resolve(self, conversation_history: List[Dict[str, str]], available_fragments: List[Dict[str, str]]) -> Dict[str, Any]:
        filtered_msgs = [m for m in conversation_history if m.get("role") in ["user", "assistant"]]
        recent_msgs = filtered_msgs[-3:]
        
        chat_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent_msgs])
        known_titles = list(set([f.get("title") for f in available_fragments if f.get("title")]))
        
        prompt = f"""
Eres el "Intent Resolver" del sistema Lab Sync.
Tu trabajo es analizar la conversación más reciente y determinar la intención exacta de ESCRITURA del usuario en Notion.

REGLA DE ORO 1 (CONTEXT DRAGGING): Presta atención absoluta al ÚLTIMO mensaje del usuario. 
REGLA DE ORO 2 (SAFE EDITING): Por defecto NO somos destructivos. Usa 'append_to_page' o 'create_page'.
REGLA DE ORO 3 (DESTRUCTIVE): SOLO usa 'destructive_edit' si pide EXPLÍCITAMENTE borrar o reemplazar contenido existente.
REGLA DE ORO 4 (PARENT): Si pide crear una página "dentro de X", 'target_name' es la nueva página y 'parent_name' es X.

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
                
                if result["intent"] in ["append_to_page", "destructive_edit"]:
                    match_info = self._fuzzy_match_page(target_raw, available_fragments)
                    if match_info["status"] in ["exact", "fuzzy"]:
                        result["resolved_target_id"] = match_info["id"]
                        result["target_name"] = match_info["title"]
                        
                elif result["intent"] == "create_page" and parent_raw:
                    match_info = self._fuzzy_match_page(parent_raw, available_fragments)
                    if match_info["status"] in ["exact", "fuzzy"]:
                        result["resolved_parent_id"] = match_info["id"]
                        result["parent_name"] = match_info["title"]
                        
                return result
        except Exception as e:
            logger.error(f"Failed to resolve intent: {e}")
            
        return result

    def resolve_source_and_context(self, user_input, notion_frags, local_frags):
        return {
            "source": "notion",
            "intent": "open_query",
            "target_name": "",
            "target_page_or_path": "",
            "operation_type": "READ_CONTENT",
            "confidence": 1.0,
            "resolved_target_id": None
        }
