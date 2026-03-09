# telegram_bot/agent.py

"""
Módulo del Agente de IA de LangChain.

Este módulo es el núcleo de la inteligencia del asistente. Se encarga de orquestar
la interacción entre el modelo de lenguaje (LLM), las herramientas disponibles y la
memoria del usuario para generar respuestas coherentes y útiles.

Arquitectura Clave:
1.  **Manejo Manual de Memoria:** Se abandona el uso de clases de memoria de LangChain
    en favor de un ciclo explícito: Cargar historial -> Procesar -> Guardar historial.
    Esto proporciona un control total y es más robusto en un entorno de API.
2.  **Prompt Dinámico Centralizado:** Se construye un único `SystemMessage` al inicio de
    cada ejecución, que integra el perfil del usuario, las memorias relevantes, el
    prompt de personalidad y las instrucciones sobre el uso de `account_id` y
    herramientas.
3.  **Inyección Explícita de IDs:** El `account_id` y `telegram_id` se pasan al
    `AgentExecutor` a través del parámetro `config`, que es el mecanismo moderno de
    LangChain para pasar datos de sesión a las herramientas.
4.  **Inicialización de LLMs:** La función `initialize_llms` se encarga de cargar los
    modelos de lenguaje al inicio del servidor, asegurando que estén listos para
    ser utilizados.
"""

import logging
import asyncio
from typing import Optional, List, Any, cast, TypedDict, Dict
import uuid
import os
import json # Importar el módulo json
from pydantic import ValidationError

# --- Langchain Core ---
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableConfig
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.agents import AgentAction, AgentFinish # Importar AgentAction y AgentFinish
from sqlalchemy import update
from langchain_core.messages import ToolMessage

# --- Módulos del Proyecto ---
from core.tools import get_all_langchain_tools
from core.memory_manager import get_user_profile, add_memory_to_vector_db, get_relevant_memories
from core.context_cache import get_cached_context, cache_context
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession
#from utils.helpers import sanitize_html
from core.config import settings
from core.citation_models import ToolOutputWithSources, Source, SourceType, format_context_with_sources
from core.llm_manager import get_main_llm, get_fast_llm, get_vision_llm, get_llm_for_user
from core.prompts import SUMMARIZATION_PROMPT, THREAD_TITLE_PROMPT
from core.enhanced_memory_manager import EnhancedMemoryManager
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_reasoning_node import GraphReasoningNode # NUEVO
from knowledge_graph.knowledge_extraction_node import KnowledgeExtractionNode # NUEVO
from tools.deep_research_tool import DeepResearchTool # Importar DeepResearchTool

# --- Claves para estado temporal ---
from utils.image_generation import GENERATED_IMAGE_KEY
# from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.websocket_manager import send_personal_message # Importar aquí para evitar circular imports

# --- PARSER HÍBRIDO DE TOOL CALLS ---
def _extract_balanced_json(text: str, start_idx: int) -> Optional[str]:
    """
    Extrae un bloque JSON balanceado comenzando desde start_idx.
    Retorna el string JSON completo o None si no está balanceado.
    """
    if start_idx >= len(text) or text[start_idx] != '{':
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start_idx:i+1]
    
    return None

def _parse_tool_calls_from_text(text: str, available_tools: List[Any]) -> List[Dict[str, Any]]:
    """
    Parser híbrido multi-estrategia para extraer tool calls del texto.
    Basado en el sistema de Kogniterm que soporta múltiples formatos.
    
    Estrategias:
    A) Patrones explícitos: "LLAMADA_A_HERRAMIENTA: nombre"
    B) Bloques JSON estructurados: {"name": "...", "args": {...}}
    C) Formato legacy: nombre_herramienta({args})
    """
    tool_calls = []
    tool_map = {t.name: t for t in available_tools}
    
    # ESTRATEGIA A: Patrones explícitos
    explicit_patterns = [
        r'LLAMADA_A_HERRAMIENTA:\s*(\w+)',
        r'Herramienta:\s*(\w+)',
        r'\[TOOL_CALL\]\s*(\w+)',
        r'Tool:\s*(\w+)',
        r'<tool>\s*(\w+)\s*</tool>',
    ]
    
    import re
    for pattern in explicit_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            tool_name = match.group(1)
            if tool_name in tool_map:
                # Buscar JSON de argumentos después del nombre usando extracción balanceada
                remaining_text = text[match.end():]
                first_curly = remaining_text.find('{')
                args = {}
                if first_curly != -1:
                    json_str = _extract_balanced_json(remaining_text, first_curly)
                    if json_str:
                        try:
                            args = json.loads(json_str)
                        except:
                            pass
                
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": tool_name.strip(),
                    "args": args
                })
    
    # ESTRATEGIA B: Bloques JSON estructurados (más fiable)
    for i in range(len(text)):
        if text[i] == '{':
            json_str = _extract_balanced_json(text, i)
            if not json_str:
                continue
                
            try:
                data = json.loads(json_str)
                
                # Formato 1: {"name": "...", "args": {...}}
                name = data.get("name") or data.get("tool") or data.get("function")
                args = data.get("args") or data.get("arguments") or data.get("parameters") or {}
                
                # Manejar el formato de OpenAI: {"function": {"name": "...", "arguments": "{...}"}}
                if isinstance(name, dict):
                    args_val = name.get("arguments") or name.get("args") or args
                    if isinstance(args_val, str):
                        try:
                            args_val = json.loads(args_val)
                        except:
                            args_val = {}
                    args = args_val
                    name = name.get("name")
                
                if isinstance(name, str) and name in tool_map:
                    tool_calls.append({
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "args": args if isinstance(args, dict) else {}
                    })
                    continue
                
                # Formato 2: {"tool_name": {...args...}}
                if len(data) == 1:
                    potential_name = list(data.keys())[0]
                    if potential_name in tool_map:
                        potential_args = data[potential_name]
                        tool_calls.append({
                            "id": str(uuid.uuid4()),
                            "name": potential_name,
                            "args": potential_args if isinstance(potential_args, dict) else {}
                        })
            except json.JSONDecodeError:
                continue
    
    # ESTRATEGIA C: Formato legacy tipo código: nombre_herramienta({args})
    legacy_pattern = r'(\w+)\s*\((\{.*?\})\)'
    matches = re.finditer(legacy_pattern, text, re.DOTALL)
    for match in matches:
        potential_name = match.group(1)
        if potential_name in tool_map:
            try:
                args = json.loads(match.group(2))
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": potential_name,
                    "args": args if isinstance(args, dict) else {}
                })
            except:
                continue
    
    # Eliminar duplicados (mismo nombre y args)
    seen = set()
    unique_calls = []
    for tc in tool_calls:
        key = (tc["name"], json.dumps(tc["args"], sort_keys=True))
        if key not in seen:
            seen.add(key)
            unique_calls.append(tc)
    
    return unique_calls

# --- Global singletons for shared dependencies ---
_graph_db_instance = None
_enhanced_memory_manager_instance = None
_knowledge_extraction_node_instance = None

async def get_shared_graph_dependencies():
    """
    Returns shared instances of GraphDB and EnhancedMemoryManager, initializing them if necessary.
    """
    global _graph_db_instance, _enhanced_memory_manager_instance
    
    if _graph_db_instance and _enhanced_memory_manager_instance:
        return _graph_db_instance, _enhanced_memory_manager_instance

    try:
        if settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password:
            if not _graph_db_instance:
                _graph_db_instance = GraphDB(
                    uri=str(settings.neo4j_uri),
                    user=str(settings.neo4j_user),
                    password=str(settings.neo4j_password)
                )
                _graph_db_instance.connect()
                logger.info("✅ Shared GraphDB instance created and connected.")
            
            if not _enhanced_memory_manager_instance:
                _enhanced_memory_manager_instance = EnhancedMemoryManager(graph_db=_graph_db_instance)
                logger.info("✅ Shared EnhancedMemoryManager instance created.")
                
            return _graph_db_instance, _enhanced_memory_manager_instance
        else:
            logger.warning("⚠️ Missing Neo4j credentials, graph-based enhanced memory will not be available.")
            return None, None
    except Exception as e:
        logger.error(f"❌ Error initializing shared graph dependencies: {e}", exc_info=True)
        return None, None


def sanitize_json_content(content):
    """
    Sanitiza el contenido de un mensaje para eliminar caracteres Unicode inválidos
    que puedan causar problemas al serializar a JSON en PostgreSQL.
    """
    if isinstance(content, str):
        # Remover caracteres de control (0x00-0x1F) excepto tab (\t), newline (\n), carriage return (\r)
        sanitized = ''.join(char for char in content if ord(char) >= 32 or char in '\t\n\r')
        return sanitized
    elif isinstance(content, list):
        # Si es una lista (contenido multimodal), sanitizar cada elemento
        sanitized_list = []
        for item in content:
            if isinstance(item, dict):
                sanitized_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        sanitized_item[key] = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
                    else:
                        sanitized_item[key] = value
                sanitized_list.append(sanitized_item)
            else:
                sanitized_list.append(item)
        return sanitized_list
    else:
        return content




# --- Configuración del Logger ---
from core.utils.logging_utils import AgentLogger
logger = AgentLogger(__name__)


def convert_langchain_tools_to_openai_format(tools: List[Any]) -> List[Dict[str, Any]]:
    """
    Convierte herramientas de LangChain al formato de OpenAI function calling.
    
    Esto es necesario porque LiteLLM a veces no convierte correctamente
    las herramientas cuando se usa bind_tools con modelos OpenAI/GPT.
    
    Compatible con Pydantic v1 y v2.
    
    Args:
        tools: Lista de herramientas de LangChain
        
    Returns:
        Lista de herramientas en formato OpenAI function calling
    """
    openai_tools = []
    
    for tool in tools:
        try:
            # Extraer el schema de argumentos de la herramienta
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # Convertir el schema de Pydantic a JSON Schema
                # Compatible con Pydantic v1 (schema()) y v2 (model_json_schema())
                if hasattr(tool.args_schema, 'model_json_schema'):
                    # Pydantic v2
                    schema = tool.args_schema.model_json_schema()
                elif hasattr(tool.args_schema, 'schema'):
                    # Pydantic v1
                    schema = tool.args_schema.schema()
                else:
                    logger.warning(f"⚠️ Herramienta '{tool.name}' tiene args_schema pero no se puede extraer el schema")
                    continue
                
                # Formato OpenAI function calling
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": schema
                    }
                }
                openai_tools.append(openai_tool)
                logger.debug(f"🔧 Herramienta '{tool.name}' convertida a formato OpenAI")
            else:
                logger.warning(f"⚠️ Herramienta '{tool.name}' no tiene args_schema, saltando conversión")
        except Exception as e:
            logger.error(f"❌ Error al convertir herramienta '{tool.name}' a formato OpenAI: {e}", exc_info=True)
    
    return openai_tools


# ==============================================================================
# SECCIÓN 1: DEFINICIÓN DEL ESTADO DEL GRAFO (NUEVO)
# ==============================================================================

from typing import Annotated
import operator

class AgentState(TypedDict):
    """
    Define la estructura de datos para el estado que fluye a través del grafo.
    """
    # Mensajes de la conversación (el historial) - Usamos Annotated con operator.add para permitir actualizaciones paralelas
    messages: Annotated[List[BaseMessage], operator.add]
    # El ID de la cuenta, para pasarlo a las herramientas
    account_id: str
    # El ID de Telegram, también para las herramientas
    telegram_id: Optional[int]
    # El ID del workspace para el contexto
    workspace_id: Optional[str]
    # El contexto RAG explícito seleccionado por el usuario
    rag_context: Optional[List[Dict[str, Any]]]
    # Las fuentes recuperadas para la citación - Usamos Annotated con operator.add para permitir actualizaciones paralelas
    sources: Annotated[List[Dict[str, Any]], operator.add]
    # El ID de la tarea para los eventos de WebSocket
    task_id: Optional[str]
    # El ID del hilo de chat
    thread_id: Optional[str]
    # Tracking de errores de herramientas para prevenir bucles infinitos
    tool_error_counts: Optional[Dict[str, int]]
    # Instancias de grafo de conocimiento y gestor de memoria mejorada
    graph_db: Optional[GraphDB]
    enhanced_memory_manager: Optional[EnhancedMemoryManager]
    # Salida del nuevo nodo de razonamiento del grafo
    graph_context: Optional[str]
    graph_sources: Optional[List[Dict[str, Any]]]
    mermaid_diagram: Optional[str]
    turn_count: int  # Nuevo: Contador de turnos para la memoria proactiva
    # Contexto específico del chat (tablas, grafos, análisis)
    context: Optional[Dict[str, Any]]
    # Datasets seleccionados para la consulta al grafo
    # Datasets seleccionados para la consulta al grafo
    target_datasets: Optional[List[str]]
    # Contador de iteraciones (loop protector)
    loop_count: int

# ==============================================================================
# SECCIÓN 2: VALIDACIÓN DE HERRAMIENTAS Y MANEJO DE ERRORES
# ==============================================================================

def format_validation_error_for_llm(error: ValidationError, tool_name: str, tool_args: dict) -> str:
    """
    Convierte un error de validación de Pydantic en un mensaje claro y útil para el LLM.
    
    Args:
        error: El error de validación de Pydantic
        tool_name: Nombre de la herramienta que falló
        tool_args: Los argumentos que se intentaron pasar
    
    Returns:
        Mensaje de error formateado para que el LLM lo entienda
    """
    errors = error.errors()
    error_messages = []
    
    for err in errors:
        field = err.get('loc', ['unknown'])[0]
        error_type = err.get('type', 'unknown')
        
        if error_type == 'missing':
            error_messages.append(f"- Falta el parámetro requerido '{field}'")
        elif error_type == 'string_type':
            error_messages.append(f"- El parámetro '{field}' debe ser una cadena de texto (string)")
        elif error_type == 'int_parsing':
            error_messages.append(f"- El parámetro '{field}' debe ser un número entero")
        else:
            error_messages.append(f"- Error en '{field}': {err.get('msg', 'error desconocido')}")
    
    # Construir mensaje completo
    error_msg = f"""❌ Error al ejecutar la herramienta '{tool_name}':

{chr(10).join(error_messages)}

Argumentos recibidos: {json.dumps(tool_args, ensure_ascii=False, indent=2)}

💡 INSTRUCCIONES PARA CORREGIR:
1. Revisa la descripción de la herramienta '{tool_name}' para ver qué parámetros requiere
2. Asegúrate de proporcionar TODOS los parámetros requeridos
3. Verifica que los tipos de datos sean correctos (string, int, etc.)
4. Si no estás seguro de cómo usar esta herramienta, intenta responder la pregunta del usuario sin usarla o usa una herramienta diferente

Por favor, vuelve a intentar con los parámetros correctos."""
    
    return error_msg

def should_stop_retrying_tool(tool_name: str, error_counts: Optional[Dict[str, int]], max_retries: int = 3) -> tuple[bool, str]:
    """
    Determina si se debe dejar de intentar ejecutar una herramienta después de múltiples fallos.
    
    Args:
        tool_name: Nombre de la herramienta
        error_counts: Diccionario con conteo de errores por herramienta
        max_retries: Número máximo de reintentos permitidos
    
    Returns:
        (should_stop, message): Tupla con booleano y mensaje para el LLM si debe detenerse
    """
    if not error_counts:
        return False, ""
    
    count = error_counts.get(tool_name, 0)
    
    if count >= max_retries:
        message = f"""🛑 LÍMITE DE REINTENTOS ALCANZADO para la herramienta '{tool_name}'.

Has intentado usar esta herramienta {count} veces sin éxito. 

💡 INSTRUCCIONES:
1. NO vuelvas a intentar usar la herramienta '{tool_name}' en esta conversación
2. Intenta responder la pregunta del usuario SIN usar esta herramienta
3. Si necesitas buscar información, considera usar una herramienta DIFERENTE
4. Si no puedes responder sin esta herramienta, explícale al usuario la situación

Por favor, genera una respuesta útil para el usuario sin usar '{tool_name}'."""
        return True, message
    
    return False, ""

# ==============================================================================
# SECCIÓN 3: MANEJO DE CONTEXTO Y MEMORIA
# ==============================================================================

async def summarize_history_in_background(
    history_to_summarize: List[BaseMessage],
    chat_message_history: PostgresChatMessageHistory,
    account_id: str, # Añadir account_id para add_memory_to_vector_db
    workspace_id: Optional[str] = None # Añadir workspace_id para add_memory_to_vector_db
):
    """
    Resume mensajes en segundo plano y añade un resumen al historial, pero NO borra los mensajes previos.
    El resumen se usará solo para el contexto del LLM, pero el historial completo se conserva para el frontend.
    """
    llm_for_summary = await get_llm_for_user(account_id, purpose="fast")
    if not llm_for_summary:
        logger.warning("⚠️ No hay LLM disponible para la sumarización en segundo plano.")
        return

    logger.info(f"Tarea en segundo plano: Resumiendo {len(history_to_summarize)} mensajes...")
    try:
        summarization_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SUMMARIZATION_PROMPT),
            MessagesPlaceholder(variable_name="history"),
        ])
        summarization_chain = summarization_prompt | llm_for_summary
        messages_for_summarization_input = [msg for msg in history_to_summarize if not (hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary")]
        if not messages_for_summarization_input:
            return
        summary_response = await summarization_chain.ainvoke({"history": messages_for_summarization_input})
        summary_content = str(summary_response)
        summary_message = HumanMessage(
            content=f"Resumen de la conversación anterior: {summary_content}",
            additional_kwargs={"role": "summary"}
        )
        # Guardar el resumen como un mensaje más, sin borrar el historial
        sanitized_summary_message = HumanMessage(
            content=sanitize_json_content(summary_message.content),
            additional_kwargs=summary_message.additional_kwargs
        )
        await chat_message_history.aadd_messages([sanitized_summary_message])
        logger.info("✅ Sumarización en segundo plano completada y resumen añadido al historial.")

        # --- MODIFICACIÓN: Guardar resumen en memoria vectorial con workspace_id ---
        await add_memory_to_vector_db(
            account_id=account_id,
            content=summary_content,
            type="thread_summary",
            workspace_id=workspace_id # Pasar workspace_id
        )
        logger.info(f"✅ Resumen del hilo guardado en memoria vectorial como 'thread_summary' para workspace {workspace_id}.")

    except Exception as e:
        logger.error(f"❌ Error en la tarea de sumarización: {e}", exc_info=True)

def extract_text_content(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                return item.get('text', '')
    return str(content)


async def update_thread_title_if_needed(thread_id: str, messages: list):
    """
    Genera o actualiza el título del hilo usando el LLM de tareas rápidas.
    Si el hilo tiene de título 'Nuevo Chat' y al menos 5 mensajes, lo asigna.
    Si ya tiene título distinto y hay 20+ mensajes, lo actualiza.
    """
    if not messages:
        logger.info(f"[TÍTULO] No hay mensajes para el hilo {thread_id}, no se genera título.")
        return
    # Obtener el título actual
    async with DBSession(SessionLocal) as db:
        thread = await db.get(ChatThread, uuid.UUID(thread_id))
        current_title = thread.title if thread else None
        account_id = str(thread.account_id) if thread else None
    # Log extra para depuración
    logger.info(f"[TÍTULO][DEBUG] Hilo {thread_id} - Título actual: '{current_title}' - Mensajes reales (sin resumen): {len(messages)}")
    # Si el título es 'Nuevo Chat' y hay al menos 5 mensajes, o si hay 20+ mensajes y el título es distinto
    if (current_title == "Nuevo Chat" and len(messages) >= 5) or (current_title != "Nuevo Chat" and len(messages) >= 20 and len(messages) % 20 == 0):
        
        conversation_text = '\n'.join([extract_text_content(m.content) if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = THREAD_TITLE_PROMPT.format(conversation_text=conversation_text)
        llm = await get_llm_for_user(account_id, purpose="fast") if account_id else (get_fast_llm() or get_main_llm())
        if not llm:
            logger.warning(f"[TÍTULO] No hay LLM disponible para generar título del hilo {thread_id}.")
            return
        try:
            logger.info(f"[TÍTULO] Solicitando título para hilo {thread_id} con {len(messages)} mensajes...")
            response = await llm.ainvoke(prompt)
            new_title = str(response.content).strip() if hasattr(response, 'content') else str(response).strip()
            
            # Limpieza y truncamiento de seguridad
            new_title = new_title.strip('"').strip("'")
            if len(new_title) > 100:
                new_title = new_title[:97] + "..."
                
            logger.info(f"[TÍTULO] Título generado para hilo {thread_id}.")
            async with DBSession(SessionLocal) as db:
                await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(title=new_title))
        except Exception as e:
            logger.error(f"[TÍTULO] Error actualizando título del hilo {thread_id}: {e}")
    else:
        logger.info(f"[TÍTULO] El hilo {thread_id} no cumple condiciones para actualizar título.")

async def force_update_thread_title(thread_id: str):
    """
    Fuerza la actualización del título de un hilo de chat específico.
    """
    async with DBSession(SessionLocal) as db:
        thread = await db.get(ChatThread, uuid.UUID(thread_id))
        if not thread:
            logger.error(f"No se encontró el hilo {thread_id} para forzar la actualización del título.")
            return
        account_id = str(thread.account_id)

        db_url = settings.database_url or os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL no está configurada para el historial de chat.")
            return

        db_sync_url = db_url.replace("+psycopg", "")
        
        # Robustez: Intentar inicializar el historial con reintentos
        chat_message_history = None
        messages = []
        for attempt in range(3):
            try:
                # Asegurarnos de que la URL no tenga el driver de sqlalchemy si se usa directamente
                connection_url = db_sync_url
                if connection_url.startswith("postgresql+psycopg://"):
                    connection_url = connection_url.replace("postgresql+psycopg://", "postgresql://")
                elif connection_url.startswith("postgresql+psycopg2://"):
                    connection_url = connection_url.replace("postgresql+psycopg2://", "postgresql://")
                
                chat_message_history = PostgresChatMessageHistory(
                    connection_string=connection_url,
                    session_id=thread_id,
                    table_name="langchain_chat_history",
                )
                # Intentar obtener mensajes para validar la conexión
                messages = await chat_message_history.aget_messages()
                break
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Intento {attempt + 1} fallido al conectar con el historial para título del hilo {thread_id}: {error_msg}")
                
                # Si el error es el famoso 'no attribute cursor', es un fallo de inicialización de LangChain
                if "object has no attribute 'cursor'" in error_msg:
                    logger.error(f"❌ Error de inicialización en PostgresChatMessageHistory (posible fallo de conexión a DB)")
                
                if attempt == 2:
                    logger.error(f"❌ No se pudo conectar con el historial del hilo {thread_id} tras 3 intentos: {error_msg}")
                    return
                
                # Limpiar el objeto fallido para evitar problemas en el destructor
                chat_message_history = None
                await asyncio.sleep(1 * (attempt + 1))

        
        if not messages:
            logger.info(f"No hay mensajes en el hilo {thread_id} para generar un título.")
            return

        conversation_text = '\n'.join([extract_text_content(m.content) if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = THREAD_TITLE_PROMPT.format(conversation_text=conversation_text)
        llm = await get_llm_for_user(account_id, purpose="fast")
        if not llm:
            logger.warning(f"No hay LLM disponible para generar título del hilo {thread_id}.")
            return
        try:
            logger.info(f"Forzando la generación de título para el hilo {thread_id}...")
            response = await llm.ainvoke(prompt)
            new_title = str(response.content).strip() if hasattr(response, 'content') else str(response).strip()
            
            # Limpieza y truncamiento de seguridad
            new_title = new_title.strip('"').strip("'")
            if len(new_title) > 100:
                new_title = new_title[:97] + "..."

            logger.info(f"Nuevo título generado para el hilo {thread_id}.")
            
            # Obtener account_id para la notificación ANTES de hacer commit
            account_id = str(thread.account_id)
            
            await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(title=new_title))
            await db.commit()

            # --- NOTIFICACIÓN WEBSOCKET ---
            try:
                from core.websocket_manager import send_personal_message
                await send_personal_message(
                    account_id,
                    {
                        "type": "thread_title_updated",
                        "thread_id": thread_id,
                        "new_title": new_title,
                    }
                )
                logger.info(f"📡 Notificación WebSocket enviada para actualización de título del hilo {thread_id}")
            except Exception as e:
                logger.warning(f"No se pudo enviar notificación WebSocket para el hilo {thread_id}: {e}")
            # --- FIN NOTIFICACIÓN ---
        except Exception as e:
            logger.error(f"Error al forzar la actualización del título del hilo {thread_id}: {e}")

async def force_update_all_thread_titles(account_id: str):
    """
    Fuerza la actualización de títulos de todos los hilos de chat para una cuenta específica.
    """
    logger.info(f"Forzando actualización de títulos de todos los hilos para la cuenta {account_id}...")
    async with DBSession(SessionLocal) as db:
        # Seleccionar solo los hilos de la cuenta especificada
        threads = (await db.execute(
            select(ChatThread).where(ChatThread.account_id == uuid.UUID(account_id))
        )).scalars().all()

        if not threads:
            logger.info(f"No se encontraron hilos para la cuenta {account_id}.")
            return

        # Crear tareas para actualizar títulos en paralelo
        tasks = [force_update_thread_title(str(thread.id)) for thread in threads]
        # Usar asyncio.gather para ejecutar las tareas concurrentemente
        await asyncio.gather(*tasks, return_exceptions=False)

    logger.info(f"Actualización de títulos completada para la cuenta {account_id}.")

# ==============================================================================
# SECCIÓN 3: EJECUCIÓN PRINCIPAL DEL AGENTE (OBSOLETA)
# ==============================================================================

async def create_thread_for_account(account_id: str, title: str = "Nuevo Chat") -> str:
    """
    Crea un nuevo hilo de chat para la cuenta dada y retorna el ID del hilo.
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, uuid.UUID(account_id))
        if not account:
            raise ValueError(f"No existe la cuenta {account_id}")
        new_thread = ChatThread(account_id=account.id, title=title)
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return str(new_thread.id)

# ==============================================================================
# SECCIÓN 4: AGENTE LANGGRAPH REFACTORIZADO
# ==============================================================================

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- 1. Nodos del Grafo ---

async def call_model_node(state: AgentState):
    """
    Nodo principal que invoca al LLM para decidir el siguiente paso (herramienta o respuesta).
    """
    logger.debug(f"--- (Grafo) Nodo: Llama al Modelo para cuenta {state['account_id']} ---")
    logger.debug(f"DEBUG (call_model_node): account_id={state.get('account_id')}, telegram_id={state.get('telegram_id')}, workspace_id={state.get('workspace_id')}")
    
    # --- TURN COUNT LOGIC REMOVED FROM HERE (Now handled in proactive_memory_node) ---
    # turn_count is now calculated based on history to ensure persistence

    
    # --- FIX: Sanitize messages from history to ensure tool_call_ids and names are present ---
    # This prevents crashes if the DB contains messages with null IDs or empty names from previous bugs
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage):
            # Usar getattr para acceder de forma segura a tool_call_id y name
            if not getattr(msg, 'tool_call_id', None):
                logger.warning(f"Found ToolMessage with missing tool_call_id in history. Patching with random UUID.")
                msg.tool_call_id = str(uuid.uuid4()) # type: ignore
            if not getattr(msg, 'name', None):
                logger.warning(f"Found ToolMessage with missing/empty name in history. Patching with 'unknown_tool'.")
                msg.name = "unknown_tool" # type: ignore

        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if not tc.get("id"):
                     logger.warning(f"Found AIMessage tool_call with missing id in history. Patching with random UUID.")
                     tc["id"] = str(uuid.uuid4())
                if not tc.get("name"):
                     logger.warning(f"Found AIMessage tool_call with missing/empty name in history. Patching with 'unknown_tool'.")
                     tc["name"] = "unknown_tool"
    # --- END FIX ---

    # Definir last_message al inicio para evitar NameError
    last_message = state["messages"][-1] if state["messages"] else None

    # 1. Construir el prompt del sistema dinámicamente
    user_message = extract_text_content(state["messages"][-1].content)
    user_profile = await get_user_profile(state['account_id'])

    rag_context = state.get("rag_context")
    context = state.get("context")
    document_ids_for_rag = None
    document_names_for_rag = None # Nuevo
    filter_topics = None
    has_explicit_rag_context = False

    if rag_context:
        logger.info(f"Aplicando RAG explícito con {len(rag_context)} item(s) de contexto. Se priorizará la búsqueda en estos documentos.")
        document_ids_for_rag = [item['id'] for item in rag_context if item.get('type') == 'document']
        document_names_for_rag = [item.get('name') for item in rag_context if item.get('type') == 'document' and item.get('name')] # Manejar 'name' de forma segura
        has_explicit_rag_context = True

    # Soporte para contexto de colección
    if context and context.get("type") == "collection":
        topic = context.get("id")
        if topic:
            logger.info(f"Aplicando filtro de colección RAG para el tema: {topic}")
            filter_topics = [topic]
            has_explicit_rag_context = True
            # Si no hay nombres de documentos explícitos, usamos el nombre de la colección
            if not document_names_for_rag:
                document_names_for_rag = [context.get("snapshot", {}).get("name", topic)]
    # --- CONSOLIDACIÓN Y RE-INDEXACIÓN DE FUENTES PARA EL LLM ---
    # Combinar fuentes de todas las ramas (RAG, Proactive, Graph), asegurando IDs secuenciales desde 1
    # PRIORIDAD DE ORDEN: 1. RAG Context (adjuntos), 2. Graph Sources, 3. Tool/Proactive Sources
    # Esto asegura que los IDs sean estables si el agente decide llamar a herramientas después
    all_sources_for_llm: List[Source] = []
    final_sources_for_state = []
    seen_source_identifiers = set()

    def get_source_identifier(s: Dict[str, Any]) -> str:
        s_type = s.get('type', 'web')
        s_url = s.get('url') or s.get('id') or ''
        return f"{s_type}:{s_url}"

    raw_sources = []
    
    # 1. Procesar RAG Context (Documentos adjuntos explícitamente por el usuario)
    if state.get('rag_context'):
        for item in state['rag_context']:
            # Normalizar para que parezca una fuente citable
            normalized = {
                "id": item.get('id'),
                "title": item.get('name') or item.get('title') or "Documento Adjunto",
                "url": item.get('url') or item.get('id') or f"document://{item.get('id')}",
                "snippet": item.get('content') or item.get('snippet') or "",
                "type": item.get('type', 'document'),
                "metadata": item.get('metadata', {})
            }
            ident = get_source_identifier(normalized)
            if ident not in seen_source_identifiers:
                raw_sources.append(normalized)
                seen_source_identifiers.add(ident)

    # 2. Procesar Fuentes de Grafo (vienen en state['graph_sources'])
    if state.get('graph_sources'):
        for s in state['graph_sources']:
            ident = get_source_identifier(s)
            if ident not in seen_source_identifiers:
                raw_sources.append(s)
                seen_source_identifiers.add(ident)

    # 3. Procesar Fuentes de RAG General y Herramientas (vienen en state['sources'])
    if state.get('sources'):
        for s in state['sources']:
            ident = get_source_identifier(s)
            if ident not in seen_source_identifiers:
                raw_sources.append(s)
                seen_source_identifiers.add(ident)

    # 2. Procesar y re-indexar secuencialmente para que el LLM use [1], [2], [3]...
    for i, s_dict in enumerate(raw_sources, start=1):
        try:
            # Asegurar que s_dict es un diccionario de datos
            if hasattr(s_dict, 'dict'):
                s_dict = s_dict.dict()
            elif hasattr(s_dict, 'model_dump'):
                s_dict = s_dict.model_dump()
            
            # Crear una copia para no modificar el original en el historial si es compartido
            s_dict_copy = s_dict.copy()
            # ASIGNAR EL NUEVO ID SECUENCIAL
            s_dict_copy['id'] = i
            
            # Crear objeto Source para el formateador
            source_obj = Source(**s_dict_copy)
            all_sources_for_llm.append(source_obj)
            final_sources_for_state.append(s_dict_copy)
        except Exception as e:
            logger.error(f"Error procesando fuente {i} para LLM: {e}")

    # 3. Generar el contexto formateado con los nuevos IDs [1], [2], ...
    if all_sources_for_llm:
        relevant_memories_text = format_context_with_sources(all_sources_for_llm)
        logger.info(f"Consolidadas {len(all_sources_for_llm)} fuentes totales para el LLM (RAG + Grafo) con IDs secuenciales 1-{len(all_sources_for_llm)}.")
    else:
        relevant_memories_text = "No se encontraron memorias o documentos relevantes en la base de conocimiento ni en el grafo."

        
    from core.prompt_manager import PromptManager
    prompt_manager = PromptManager(settings={"default_system_prompt": settings.default_system_prompt})
        
    # Obtener herramientas si no están en el estado
    if "tools" not in state:
        tools = await get_all_langchain_tools(
            account_id=state['account_id'],
            telegram_id=state.get('telegram_id'),
            thread_id=state['thread_id'],
            workspace_id=state.get('workspace_id')
        )
        state["tools"] = tools
    else:
        tools = state["tools"]
    
    workspace_prompt = None
    if state.get('workspace_id'):
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(state.get('workspace_id')))
            if workspace and workspace.system_prompt:
                workspace_prompt = str(workspace.system_prompt)

    # --- CONFIGURACIÓN DE HERRAMIENTAS Y LLM ---
    # Obtenemos el LLM real del usuario para conocer el modelo exacto
    llm = await get_llm_for_user(state['account_id'], purpose="main")
    
    # Soporte multimodal (visión) si hay imágenes
    has_image = any(isinstance(item, dict) and item.get("type") == "image_url" 
                   for msg in state["messages"][-1:] if isinstance(msg.content, list) 
                   for item in msg.content)
    if has_image:
        llm = await get_llm_for_user(state['account_id'], purpose="vision")

    if not llm: raise ValueError("El LLM no está disponible.")
    
    model_name = getattr(llm, 'model_name', getattr(llm, 'model', settings.llm_model))
    lower_model = model_name.lower()
    
    # ESTRATEGIA: Casi todos los modelos modernos (incluyendo :free) soportan tools nativas.
    # El usuario puede forzar el modo 'prompt_tooling' manualmente desde los ajustes.
    supports_native_tools = True
    if user_profile and user_profile.account:
        supports_native_tools = not getattr(user_profile.account, 'use_prompt_tooling', False)
    
    # Inyectamos el manual de herramientas en el prompt si el usuario lo forzó o si es un modelo OSS
    use_prompt_tooling_guidance = not supports_native_tools or "openrouter" in lower_model or any(x in lower_model for x in ["llama", "mistral", "deepseek"])

    # OPTIMIZACIÓN: Construir el prompt una sola vez con toda la información consolidada
    system_prompt_content = prompt_manager.build_system_prompt(
        user_profile=user_profile,
        relevant_memories=relevant_memories_text,
        summary_string="",
        custom_prompt_from_profile=str(user_profile.system_prompt) if user_profile and user_profile.system_prompt else None,
        workspace_prompt=workspace_prompt, # Se usa si existe
        tools=tools,
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id'),
        user_message=user_message,
        has_explicit_rag_context=has_explicit_rag_context,
        explicit_document_names=[str(name) for name in document_names_for_rag if name is not None] if document_names_for_rag else None,
        context=state.get('context'), # Pasar el contexto aquí
        mode="prompt_tooling" if use_prompt_tooling_guidance else None # Usar modo documentación como refuerzo
    )
    
    logger.model_start(model_name)
    logger.debug(f"DEBUG (agent.py - call_model_node): System Prompt final construido.")
    
    # --- BINDING DE HERRAMIENTAS COMPATIBLE CON CUALQUIER LLM ---
    # Si el modelo soporta herramientas nativas, procedemos con el bind. Si no, usamos el llm crudo.
    if supports_native_tools:
        try:
            from langchain_core.utils.function_calling import convert_to_openai_tool
            
            openai_tools = []
            seen_tool_names = set()
            for tool in tools:
                try:
                    # convert_to_openai_tool es el método moderno que genera el formato {"type": "function", "function": {...}}
                    tool_dict = convert_to_openai_tool(tool)
                    tool_name = tool_dict["function"]["name"]
                    if tool_name not in seen_tool_names:
                        openai_tools.append(tool_dict)
                        seen_tool_names.add(tool_name)
                    else:
                        logger.warning(f"⚠️ Herramienta duplicada detectada y eliminada: '{tool_name}'")
                except Exception as e:
                    logger.error(f"❌ Error al convertir herramienta '{tool.name}': {e}")

            logger.info(f"🔧 Vinculando {len(openai_tools)} herramientas al modelo '{model_name}'")
            
            # Usamos .bind(tools=...) que es lo que LiteLLM espera para casi todos los proveedores
            if openai_tools:
                # --- FIX CRÍTICO PARA OPENROUTER Y MODELOS OSS ---
                # Forzamos tool_choice='auto' para OpenRouter Y para cualquier modelo que no sea nativo de OpenAI/Gemini
                # Esto soluciona el error 'No endpoints found that support tool use'
                lower_model = model_name.lower()
                is_openrouter = "openrouter" in lower_model
                is_openai = "gpt-" in lower_model and "openrouter" not in lower_model
                is_gemini = "gemini" in lower_model and "openrouter" not in lower_model
                
                if is_openrouter:
                    logger.info(f"🔧 Forzando tool_choice='auto' y filtrado de proveedores para OpenRouter: {model_name}")
                    # En OpenRouter, pasar tool_choice="auto" ayuda a LiteLLM a filtrar proveedores que SI soportan herramientas
                    llm_with_tools = llm.bind(tools=openai_tools, tool_choice="auto")
                elif not (is_openai or is_gemini):
                    # Para modelos OSS (Llama, DeepSeek, etc) fuera de OpenRouter también es recomendable
                    logger.info(f"🔧 Aplicando tool_choice='auto' para modelo especializado: {model_name}")
                    llm_with_tools = llm.bind(tools=openai_tools, tool_choice="auto")
                else:
                    llm_with_tools = llm.bind(tools=openai_tools)
            else:
                llm_with_tools = llm
                
            logger.info(f"✅ Herramientas vinculadas correctamente al LLM '{model_name}'")
        except Exception as e:
            logger.error(f"❌ Error crítico al vincular herramientas al LLM '{model_name}': {e}", exc_info=True)
            llm_with_tools = llm
    else:
        logger.info(f"ℹ️ Usando modelo '{model_name}' SIN vinculación de herramientas nativa (Modo Prompt Tooling)")
        llm_with_tools = llm

    # --- REFUERZO DE INSTRUCCIONES PARA MODELOS OSS, REASONING Y OPENROUTER ---
    # Los modelos de OpenRouter/OSS a veces ignoran el formato de herramientas si no es explícito.
    # Y los modelos de razonamiento (DeepSeek R1, etc.) a veces se detienen tras pensar sin responder.
    final_system_content = system_prompt_content
    model_lower = model_name.lower()
    
    if "gemini" not in model_lower:
        is_oss = any(x in model_lower for x in ["oss", "llama", "mistral", "mixtral", "deepseek", "qwen", "phi"])
        is_openrouter = "openrouter" in model_lower
        is_reasoning = any(x in model_lower for x in ["r1", "reasoning", "thought", "o1", "o3", "step"])
        
        if is_oss or is_openrouter or is_reasoning:
            logger.info(f"Adding extra instructions for {model_name} (OSS/Reasoning/OpenRouter)")
            
            extra_instructions = "\n\n### 🔧 INSTRUCCIONES TÉCNICAS CRÍTICAS:\n\n"
            
            if is_reasoning or "deepseek" in model_lower:
                extra_instructions += (
                    "**⚠️ REGLA DE RAZONAMIENTO DINÁMICO:**\n"
                    "Si eres un modelo con capacidad de 'razonamiento' o 'pensamiento' (como DeepSeek R1):\n"
                    "1. USA el bloque de pensamiento (thinking/reasoning) SOLO si la consulta del usuario es compleja, ambigua o requiere un análisis profundo.\n"
                    "2. Si la tarea es simple, directa o una continuación obvia, puedes OMITIR el bloque de pensamiento para ser más eficiente.\n"
                    "3. **SIEMPRE:** Si decides generar un razonamiento, DEBES proporcionar la respuesta final completa inmediatamente después.\n\n"
                )

            extra_instructions += (
                "**⚠️ ADVERTENCIA DE HERRAMIENTAS:** args: {} vacío = FALLO GARANTIZADO.\n"
                "El sistema RECHAZARÁ cualquier tool call sin argumentos.\n\n"
                "**REGLA ABSOLUTA:** Si decides usar una herramienta, DEBES incluir TODOS los argumentos requeridos.\n"
                "NUNCA envíes un objeto de argumentos vacío o null.\n\n"
                "**EJEMPLO CORRECTO de llamada a herramienta web_search:**\n"
                "```json\n"
                "{\n"
                "  \"name\": \"web_search\",\n"
                "  \"args\": {\n"
                "    \"query\": \"últimas noticias sobre inteligencia artificial\"\n"
                "  }\n"
                "}\n"
                "```\n\n"
                "**INSTRUCCIONES:**\n"
                "1. Si decides usar una herramienta, genera LA LLAMADA INMEDIATAMENTE. No escribas introducciones.\n"
                "2. El campo 'args' DEBE contener TODOS los parámetros requeridos.\n"
                "3. NO inventes herramientas que no existen en la lista.\n\n"
                
                "**⚠️ FORMATO ALTERNATIVO (USA ESTE SI EL ANTERIOR FALLA):**\n"
                "Si tienes problemas con el formato JSON para herramientas, usa este formato exacto:\n\n"
                
                "LLAMADA_A_HERRAMIENTA: nombre_herramienta\n"
                "{\"argumento1\": \"valor1\", \"argumento2\": \"valor2\"}\n\n"
            )
            # Escapar para LangChain
            extra_instructions = extra_instructions.replace('{', '{{').replace('}', '}}')
            final_system_content += extra_instructions
        else:
            final_system_content += "\n\n⚠️ **CRITICAL TECHNICAL REMINDER:** Use your internal reasoning/thinking ONLY if the task is complex. Always provide a clear final response. If you use a tool, you MUST provide ALL required arguments."

    prompt = ChatPromptTemplate.from_messages([
        ("system", final_system_content),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm_with_tools

    full_ai_message_content = ""
    tool_calls_from_llm = []
    final_response_message = None
    
    target_account_id = "telegram_bot_service" if state.get('telegram_id') else state['account_id']
    conn_type = "chat" if state.get('telegram_id') else None

    # --- LIMPIEZA DE HISTORIAL ROBUSTA (Mistral/OpenRouter/OSS Compatible) ---
    def clean_messages_history(messages):
        """
        Limpia y normaliza el historial de mensajes para cumplir con las reglas estrictas de 
        proveedores como Mistral, OpenRouter y modelos OSS.
        Reglas:
        1. Elimina todos los SystemMessages (ya proporcionamos uno al principio).
        2. Une mensajes consecutivos del mismo rol.
        3. Asegura que cada ToolMessage esté precedido por su AIMessage (tool_calls).
        4. Elimina mensajes con contenido vacío (a menos que sean tool_calls).
        5. Asegura que el primer mensaje no-sistema sea del rol 'user'.
        """
        if not messages:
            return []

        # 1. Fase de filtrado y saneamiento inicial
        sanitized = []
        for msg in messages:
            # Ignorar SystemMessages del historial para evitar duplicación y errores de posición
            if isinstance(msg, SystemMessage):
                continue
            
            # Normalizar contenido
            content = msg.content
            if isinstance(content, list):
                # Filtrar partes de texto vacías en contenido multimodal
                content = [p for p in content if not (isinstance(p, dict) and p.get("type") == "text" and not p.get("text", "").strip())]
                if not content: content = ""
            
            # Si el contenido es un string vacío y no hay tool_calls, ignorar
            has_tool_calls = isinstance(msg, AIMessage) and bool(getattr(msg, 'tool_calls', None))
            if not content and not has_tool_calls and not isinstance(msg, ToolMessage):
                continue
                
            sanitized.append(msg)

        if not sanitized:
            return []

        # 2. Fase de emparejamiento Assistant -> Tool(s) y fusión de roles consecutivos
        cleaned = []
        i = 0
        while i < len(sanitized):
            msg = sanitized[i]
            
            if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
                # Encontrado un bloque de assistant que pide herramientas. 
                # Debemos encontrar TODAS sus respuestas correspondientes.
                current_tool_calls = msg.tool_calls
                call_ids = {tc.get('id') for tc in current_tool_calls if tc.get('id')}
                
                responses = []
                next_i = i + 1
                while next_i < len(sanitized):
                    next_msg = sanitized[next_i]
                    if isinstance(next_msg, ToolMessage):
                        if next_msg.tool_call_id in call_ids:
                            responses.append(next_msg)
                            call_ids.remove(next_msg.tool_call_id)
                        else:
                            # ToolMessage que no pertenece a este bloque, ignorar
                            logger.warning(f"⚠️ ToolMessage huérfano detectado: {next_msg.tool_call_id}")
                    elif isinstance(next_msg, (HumanMessage, AIMessage)):
                        # Otro rol interrumpe, Mistral es estricto: no puede haber llamadas sin respuesta
                        break
                    next_i += 1
                
                # Solo incluimos el AIMessage si podemos emparejar al menos una llamada (o tiene contenido)
                valid_call_ids = {r.tool_call_id for r in responses}
                filtered_tool_calls = [tc for tc in current_tool_calls if tc.get('id') in valid_call_ids]
                
                if filtered_tool_calls or msg.content:
                    # Asegurar orden de respuestas (Mistral strictness)
                    order_map = {tc.get('id'): idx for idx, tc in enumerate(filtered_tool_calls)}
                    responses.sort(key=lambda r: order_map.get(r.tool_call_id, 999))
                    
                    new_ai_msg = AIMessage(
                        content=msg.content or "",
                        tool_calls=filtered_tool_calls or [], # Usar [] para evitar error de validación AIMessage
                        additional_kwargs=getattr(msg, 'additional_kwargs', {})
                    )
                    cleaned.append(new_ai_msg)
                    cleaned.extend(responses)
                
                i = next_i
            elif isinstance(msg, ToolMessage):
                # Ignorar ToolMessages que no fueron procesados en el bloque anterior (huérfanos)
                i += 1
            else:
                # Mensaje normal (Human o AI sin tools)
                # Fusión opcional de roles consecutivos para evitar: User, User... o Assistant, Assistant...
                if cleaned and type(msg) == type(cleaned[-1]) and not isinstance(msg, ToolMessage):
                    last_msg = cleaned[-1]
                    # Fusionar contenidos si son strings
                    if isinstance(last_msg.content, str) and isinstance(msg.content, str):
                        last_msg.content += "\n\n" + msg.content
                        logger.debug(f"🔄 Fusionados dos mensajes consecutivos de tipo {type(msg).__name__}")
                    else:
                        # Si no se pueden fusionar fácilmente, los mantenemos (algunos proveedores lo permiten)
                        cleaned.append(msg)
                else:
                    cleaned.append(msg)
                i += 1
        
        # 3. Asegurar que el primer mensaje después del sistema sea 'human'
        while cleaned and not isinstance(cleaned[0], HumanMessage):
            logger.warning(f"⚠️ Eliminando mensaje inicial no-humano ({type(cleaned[0]).__name__}) para cumplir paridad.")
            cleaned.pop(0)

        return cleaned

    cleaned_messages = clean_messages_history(state["messages"])
    full_ai_message_content = ""
    full_reasoning_content = "" # Acumulador para razonamiento
    tool_calls_from_llm = []
    final_response_message = None
    in_thinking_tag = False
    
    async for chunk in chain.astream({"messages": cleaned_messages}):
        if isinstance(chunk, AIMessage):
            # DEBUG: Log del chunk completo para ver el formato crudo
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"🔍 CHUNK CRUDO: content={chunk.content}, tool_calls={chunk.tool_calls}, additional_kwargs={chunk.additional_kwargs}")
            
            # 1. Detectar razonamiento (Chain of Thought) en metadatos (OpenRouter / LiteLLM / DeepSeek)
            reasoning_chunk = ""
            add_kwargs = getattr(chunk, 'additional_kwargs', {})
            resp_meta = getattr(chunk, 'response_metadata', {})
            
            # Lista de claves posibles donde los proveedores esconden el razonamiento
            reasoning_keys = ["reasoning", "reasoning_content", "thought", "thinking", "reflection", "chain_of_thought"]
            
            # Buscar en additional_kwargs
            for key in reasoning_keys:
                if key in add_kwargs and isinstance(add_kwargs[key], str) and add_kwargs[key]:
                    reasoning_chunk = add_kwargs[key]
                    break
            
            # Buscar en response_metadata si no se encontró
            if not reasoning_chunk:
                for key in reasoning_keys:
                    if key in resp_meta and isinstance(resp_meta[key], str) and resp_meta[key]:
                        reasoning_chunk = resp_meta[key]
                        break
            
            if reasoning_chunk:
                full_reasoning_content += reasoning_chunk
                await send_personal_message(target_account_id, {
                    "type": "reasoning_chunk",
                    "thread_id": state['thread_id'],
                    "taskId": state.get("task_id"),
                    "chunk": reasoning_chunk,
                    "full_reasoning": full_reasoning_content
                }, connection_type=conn_type)

            # 2. Procesar contenido normal y DETECCIÓN DE ETIQUETAS <think> ROBUSTA
            current_content = ""
            if isinstance(chunk.content, str):
                current_content = chunk.content
            elif isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        current_content += part.get("text", "")
            
            # Buffer para tags cortados (simple: si termina en <, <t, <th... o </, </t...)
            # Nota: Implementar un buffer completo es complejo aqui, usamos heuristica de tags
            
            if current_content:
                # Lógica de detección de etiquetas <think> para modelos como DeepSeek-R1
                processed_content = ""
                
                # Caso simple: El chunk contiene <think>
                if "<think>" in current_content:
                    parts = current_content.split("<think>")
                    processed_content += parts[0] # Texto antes de <think>
                    in_thinking_tag = True
                    thinking_part = parts[1] if len(parts) > 1 else ""
                    
                    # Si también contiene </think> en el mismo chunk
                    if "</think>" in thinking_part:
                        subparts = thinking_part.split("</think>")
                        reasoning_to_send = subparts[0]
                        full_reasoning_content += reasoning_to_send
                        in_thinking_tag = False
                        processed_content += subparts[1] if len(subparts) > 1 else ""
                        
                        # Enviar el razonamiento acumulado en el tag
                        await send_personal_message(target_account_id, {
                            "type": "reasoning_chunk",
                            "thread_id": state['thread_id'],
                            "taskId": state.get("task_id"),
                            "chunk": reasoning_to_send,
                            "full_reasoning": full_reasoning_content
                        }, connection_type=conn_type)
                    else:
                        # Todo el resto del chunk es razonamiento
                        full_reasoning_content += thinking_part
                        await send_personal_message(target_account_id, {
                            "type": "reasoning_chunk",
                            "thread_id": state['thread_id'],
                            "taskId": state.get("task_id"),
                            "chunk": thinking_part,
                            "full_reasoning": full_reasoning_content
                        }, connection_type=conn_type)
                
                # Caso: Estamos dentro de un tag de pensamiento abierto en chunks anteriores
                elif in_thinking_tag:
                    if "</think>" in current_content:
                        parts = current_content.split("</think>")
                        reasoning_to_send = parts[0]
                        full_reasoning_content += reasoning_to_send
                        in_thinking_tag = False
                        processed_content += parts[1] if len(parts) > 1 else ""
                        
                        await send_personal_message(target_account_id, {
                            "type": "reasoning_chunk",
                            "thread_id": state['thread_id'],
                            "taskId": state.get("task_id"),
                            "chunk": reasoning_to_send,
                            "full_reasoning": full_reasoning_content
                        }, connection_type=conn_type)
                    else:
                        # Todo el chunk sigue siendo razonamiento
                        full_reasoning_content += current_content
                        await send_personal_message(target_account_id, {
                            "type": "reasoning_chunk",
                            "thread_id": state['thread_id'],
                            "taskId": state.get("task_id"),
                            "chunk": current_content,
                            "full_reasoning": full_reasoning_content
                        }, connection_type=conn_type)
                
                # Caso: Posible tag cortado al final (heurística simple para evitar mostrar <t etc)
                # Si no estamos pensando y el chunk termina en <, <t, <th... no lo procesamos aun
                # (Esta es una mejora compleja, por ahora asumimos atomicidad razonable)
                else:
                    processed_content = current_content


                if processed_content:
                    full_ai_message_content += processed_content
                    logger.debug(f"DEBUG (agent.py): Enviando stream_chunk para taskId {state.get('task_id')}")
                    await send_personal_message(target_account_id, {
                        "type": "stream_chunk",
                        "thread_id": state['thread_id'],
                        "taskId": state.get("task_id"),
                        "chunk": processed_content,
                        "full_text": full_ai_message_content
                    }, connection_type=conn_type)
            
            # 3. Procesar tool calls nativos (USANDO ACUMULADOR MANUAL PARA EVITAR FRAGMENTACIÓN)
            if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                for tc_chunk in chunk.tool_call_chunks:
                    # Buscar si ya tenemos esta llamada (por su index o ID)
                    idx = tc_chunk.get("index")
                    found = False
                    
                    for existing_tc in tool_calls_from_llm:
                        if (idx is not None and existing_tc.get("index") == idx) or (tc_chunk.get("id") and existing_tc.get("id") == tc_chunk.get("id")):
                            found = True
                            # Actualizar el existente
                            if tc_chunk.get("name"):
                                existing_tc["name"] = tc_chunk["name"]
                            if tc_chunk.get("args"):
                                # Unir strings de argumentos (vienen fragmentados)
                                current_args_str = existing_tc.get("_args_str", "")
                                new_args_str = tc_chunk["args"]
                                existing_tc["_args_str"] = current_args_str + new_args_str
                                try:
                                    # Intentar parsear el acumulado
                                    existing_tc["args"] = json.loads(existing_tc["_args_str"])
                                except:
                                    pass
                            if tc_chunk.get("id"):
                                existing_tc["id"] = tc_chunk["id"]
                            break
                    
                    if not found:
                        new_tc = {
                            "name": tc_chunk.get("name", ""),
                            "args": {},
                            "_args_str": tc_chunk.get("args", ""),
                            "id": tc_chunk.get("id"),
                            "index": idx
                        }
                        if new_tc["_args_str"]:
                            try:
                                new_tc["args"] = json.loads(new_tc["_args_str"])
                            except:
                                pass
                        tool_calls_from_llm.append(new_tc)

            elif chunk.tool_calls:
                for tc in chunk.tool_calls:
                    if tc not in tool_calls_from_llm:
                        tool_calls_from_llm.append(tc)
            
            final_response_message = chunk


    logger.debug(f"DEBUG (agent.py - call_model_node): Respuesta cruda del LLM acumulada.")
    
    # --- LOG ULTRA-DETALLADO ---
    if final_response_message:
        try:
            full_data = {
                "content": full_ai_message_content,
                "reasoning": full_reasoning_content,
                "tool_calls": tool_calls_from_llm,
                "additional_kwargs": getattr(final_response_message, 'additional_kwargs', {}),
                "response_metadata": getattr(final_response_message, 'response_metadata', {})
            }
            logger.debug(f"🔥 DATA COMPLETA DEL MODELO:\n{json.dumps(full_data, indent=2)}")
        except Exception as e:
            logger.debug(f"Error al loguear data completa: {e}")
    
    # Log de tool calls crudos para debugging
    if tool_calls_from_llm:
        # Usar logger.info simplificado para no saturar
        logger.info(f"🔍 Herramientas solicitadas por el modelo: {[tc.get('name') for tc in tool_calls_from_llm]}")
        logger.debug(f"Tool calls recibidos del modelo ({len(tool_calls_from_llm)}): {json.dumps(tool_calls_from_llm, indent=2)}")
    else:
        logger.info("ℹ️ No se recibieron tool calls del modelo")
        if not full_ai_message_content.strip() and full_reasoning_content.strip():
            logger.warning("⚠️ El modelo generó razonamiento pero la respuesta final está VACÍA. Esto puede deberse a un corte prematuro del proveedor o a instrucciones contradictorias.")
        logger.debug(f"Contenido de respuesta del modelo: {full_ai_message_content[:500]}...")
    
    # --- END DEBUG ---

    # --- PARSER HÍBRIDO DE TOOL CALLS (Sistema Kogniterm) ---
    # Complementar o reemplazar tool calls nativos con parseo del texto
    # Esto maneja modelos que no formatean correctamente los tool calls
    
    logger.info("🔍 Iniciando parser híbrido de tool calls...")
    combined_text = full_ai_message_content + "\n" + full_reasoning_content
    parsed_tool_calls = _parse_tool_calls_from_text(combined_text, tools)
    
    if parsed_tool_calls:
        logger.info(f"✅ Parser híbrido extrajo {len(parsed_tool_calls)} tool calls del texto")
        
        # Si el modelo no devolvió tool calls nativos, usar los parseados
        if not tool_calls_from_llm:
            tool_calls_from_llm = parsed_tool_calls
            logger.info("📝 Usando tool calls parseados del texto (modelo no devolvió nativos)")
        else:
            # Si el modelo devolvió tool calls pero con args vacíos, complementar con los parseados
            for native_tc in tool_calls_from_llm:
                if not native_tc.get("args") or native_tc.get("args") == {}:
                    # Buscar el mismo tool call en los parseados
                    for parsed_tc in parsed_tool_calls:
                        if parsed_tc["name"] == native_tc.get("name"):
                            # Actualizar con los args parseados
                            native_tc["args"] = parsed_tc["args"]
                            logger.info(f"🔧 Complementados args vacíos de '{native_tc.get('name')}' con parseo de texto")
                            break

    # --- FIX: Fusión de Tool Calls Fragmentados (OpenRouter Bug) ---
    # Algunos modelos envían el nombre en un fragmento y los argumentos en otro con el mismo ID.
    merged_tool_calls = {}
    for tc in tool_calls_from_llm:
        tc_id = tc.get("id")
        if not tc_id:
            # Si no tiene ID, le asignamos uno para procesarlo individualmente
            tc_id = str(uuid.uuid4())
            tc["id"] = tc_id
            
        if tc_id not in merged_tool_calls:
            merged_tool_calls[tc_id] = tc
        else:
            # Fusionar con el existente
            existing = merged_tool_calls[tc_id]
            logger.info(f"🔄 Fusionando fragmentos de tool call ID: {tc_id}")
            
            # Si el existente no tiene nombre pero el nuevo sí, lo actualizamos
            if (not existing.get("name")) and tc.get("name"):
                existing["name"] = tc["name"]
            
            # Si el existente no tiene argumentos (o están vacíos) y el nuevo sí tiene, los fusionamos
            new_args = tc.get("args") or {}
            if new_args:
                current_args = existing.get("args") or {}
                # Fusionar diccionarios de argumentos
                current_args.update(new_args)
                existing["args"] = current_args
                logger.debug(f"✅ Argumentos fusionados para {existing.get('name')}: {existing['args']}")

    final_tool_calls_list = list(merged_tool_calls.values())

    # --- FIX: Ensure all tool calls have an ID and normalize arguments ---
    valid_tool_calls = []
    for tc in final_tool_calls_list:
        # Filtrar tool calls basura (sin nombre o con nombre vacío)
        tc_name = tc.get("name")
        if not tc_name or (isinstance(tc_name, str) and not tc_name.strip()):
            logger.warning(f"⚠️ Ignorando tool call inválido (sin nombre): {tc}")
            continue
            
        if not tc.get("id"):
            logger.warning(f"Tool call {tc.get('name')} missing ID. Generating one.")
            tc["id"] = str(uuid.uuid4())
        
        # Normalizar argumentos: algunos LLMs usan "arguments" en lugar de "args"
        # O envían una cadena JSON en lugar de un diccionario
        args = tc.get("args")
        if args is None:
            args = tc.get("arguments")
        
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                logger.warning(f"⚠️ No se pudo parsear argumentos como JSON para {tc_name}: {args}")
                args = {}
        
        tc["args"] = args if isinstance(args, dict) else {}
        
        # ELIMINAR CAMPOS TEMPORALES QUE HACEN FALLAR A LANGCHAIN/PYDANTIC
        tc.pop("_args_str", None)
        tc.pop("index", None)
            
        valid_tool_calls.append(tc)
    
    tool_calls_from_llm = valid_tool_calls
    # --- END FIX ---

    # --- FIX: Construcción robusta del mensaje final ---
    # Asegurar que el razonamiento acumulado se guarde en additional_kwargs
    final_kwargs = {}
    if final_response_message and hasattr(final_response_message, 'additional_kwargs'):
        final_kwargs = final_response_message.additional_kwargs.copy()
    
    # Inyectar el razonamiento completo capturado durante el streaming
    if full_reasoning_content:
        final_kwargs["reasoning"] = full_reasoning_content
        # Compatibilidad: Asegurar que exista un campo 'thinking' si el frontend lo busca
        if "thinking" not in final_kwargs:
            final_kwargs["thinking"] = {"content": full_reasoning_content}

    tool_calls_to_use = tool_calls_from_llm if tool_calls_from_llm is not None else []

    if final_response_message:
        final_ai_message = AIMessage(
            content=full_ai_message_content,
            tool_calls=tool_calls_to_use, # Cambiado para usar la variable segura
            additional_kwargs=final_kwargs
        )
    else:
        final_ai_message = AIMessage(content=full_ai_message_content, tool_calls=tool_calls_to_use, additional_kwargs=final_kwargs)

    # Adjuntar fuentes y tool_calls a la respuesta del LLM si existen
    if final_sources_for_state: # Usar las fuentes que se han acumulado en final_sources_for_state
        final_ai_message.additional_kwargs["sources"] = final_sources_for_state
    
    if final_ai_message.tool_calls:
        tool_code_data = [
            {
                "name": tc.get("name"),
                "arguments": tc.get("args"),
            }
            for tc in final_ai_message.tool_calls
        ]
        final_ai_message.additional_kwargs["tool_code"] = json.dumps(tool_code_data)
            
    return {
        "messages": [final_ai_message],
        "sources": final_sources_for_state # Asegurarse de que las fuentes se propaguen en el estado
    }
async def generate_response_node(state: AgentState):
    """
    Nodo final que simplemente pasa el estado para que el consumidor lo reciba.
    Actúa como un punto de salida nombrado que 'api/chat.py' puede escuchar.
    """
    logger.debug("--- (Grafo) Nodo: Generar Respuesta ---")
    # --- INICIO: Extracción de conocimiento en segundo plano ---
    # Ejecutar el nodo de extracción de forma asíncrona para no bloquear la respuesta
    # y evitar romper el flujo de streaming esperado por la API.
    import asyncio
    asyncio.create_task(knowledge_extraction_node(state))
    # --- FIN: Extracción de conocimiento ---
    return {"messages": state["messages"]}

async def tool_node(state: AgentState):
    """
    Ejecuta las herramientas llamadas por el agente en paralelo y añade los resultados al estado.
    """
    logger.debug(f"--- (Grafo) Nodo: Llamar Herramienta (Paralelo) ---")
    if not isinstance(state["messages"][-1], AIMessage):
        return {}

    agent_message = state["messages"][-1]
    tool_calls = agent_message.tool_calls if isinstance(agent_message, AIMessage) and hasattr(agent_message, 'tool_calls') else []
    
    if not tool_calls:
        return {}

    account_id = state['account_id']
    telegram_id_int = state.get('telegram_id')
    telegram_id_str = str(telegram_id_int) if telegram_id_int is not None else None
    workspace_id = state.get('workspace_id')
    target_account_id = "telegram_bot_service" if state.get('telegram_id') else state['account_id']
    conn_type = "chat" if state.get('telegram_id') else None

    # Obtener todas las herramientas
    if "tools" in state:
        all_tools = state["tools"]
    else:
        all_tools = await get_all_langchain_tools(
            account_id=account_id,
            telegram_id=telegram_id_int,
            thread_id=state['thread_id'],
            workspace_id=workspace_id
        )
        state["tools"] = all_tools

    # 1. Definir la función de ejecución de una sola herramienta
    from core.utils.tool_utils import get_tool_by_name

    async def execute_single_tool(tool_call):
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args") or tool_call.get("arguments") or {}

        # Inferencia de argumentos faltantes
        user_query = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                user_query = extract_text_content(msg.content)
                break
        
        query_based_tools = {
            "web_search": "query", "deep_research": "query", "knowledge_graph": "natural_language_query",
            "comprehensive_web_analyzer": "query", "add_note": "content", "create_document": "content",
            "add_event": "title", "web_scraper_tool": "url"
        }
        
        if tool_name in query_based_tools:
            required_arg = query_based_tools[tool_name]
            val = tool_args.get(required_arg)
            if val is None or (isinstance(val, str) and not val.strip()):
                if required_arg == "url":
                    import re
                    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', user_query or "")
                    inferred_val = urls[0] if urls else "https://example.com"
                else:
                    # Si es create_pdf_tool, intentamos usar el mensaje anterior al tool call si es del modelo
                    inferred_val = user_query if user_query else "Contenido no especificado"
                tool_args[required_arg] = inferred_val

        logger.tool_call(tool_name, tool_args)
        
        # Evento tool_start
        await send_personal_message(target_account_id, {
            "type": "tool_start", "taskId": state.get("task_id"), "tool_name": tool_name, "thread_id": state.get("thread_id")
        }, connection_type=conn_type)

        selected_tool = await get_tool_by_name(
            tool_name=tool_name, all_tools=all_tools, account_id=account_id,
            telegram_id=telegram_id_str, workspace_id=workspace_id,
            graph_db=state.get('graph_db'), enhanced_memory_manager=state.get('enhanced_memory_manager')
        )

        if not selected_tool:
            error_msg = f"Error: Herramienta '{tool_name}' no encontrada."
            await send_personal_message(target_account_id, {
                "type": "tool_end", "taskId": state.get("task_id"), "tool_name": tool_name,
                "status": "error", "result": error_msg, "error": True, "sources": []
            }, connection_type=conn_type)
            return ToolMessage(content=error_msg, tool_call_id=tool_call.get("id") or str(uuid.uuid4())), []

        # Configuración y reintentos
        if state.get('tool_error_counts') is None: state['tool_error_counts'] = {}
        should_stop, stop_message = should_stop_retrying_tool(tool_name, state['tool_error_counts'])
        if should_stop:
            await send_personal_message(target_account_id, {
                "type": "tool_end", "taskId": state.get("task_id"), "tool_name": tool_name,
                "status": "error", "result": stop_message, "error": True, "sources": []
            }, connection_type=conn_type)
            return ToolMessage(content=stop_message, tool_call_id=tool_call.get("id") or str(uuid.uuid4())), []

        async def progress_callback(progress: int, message: str, *args, **kwargs):
            # 1. Enviar evento de progreso estándar
            progress_payload = {
                "type": "progress", 
                "taskId": state.get("task_id"), 
                "progress": progress,
                "message": message, 
                "thread_id": state.get("thread_id")
            }
            await send_personal_message(target_account_id, progress_payload, connection_type=conn_type)

            # 2. Si hay datos con un fragmento de stream, enviarlo como stream_chunk
            data = kwargs.get("data") or (args[0] if args and isinstance(args[0], dict) else None)
            if data and "stream_chunk" in data:
                chunk_payload = {
                    "type": "stream_chunk",
                    "taskId": state.get("task_id"),
                    "chunk": data["stream_chunk"],
                    "thread_id": state.get("thread_id")
                }
                await send_personal_message(target_account_id, chunk_payload, connection_type=conn_type)

            # 3. Mantener compatibilidad con otros metadatos (opcional)
            elif data:
                progress_payload["data"] = data
                await send_personal_message(target_account_id, progress_payload, connection_type=conn_type)

        run_config = RunnableConfig(configurable={
            "account_id": account_id, "workspace_id": workspace_id, "telegram_id": state.get('telegram_id'),
            "thread_id": state.get('thread_id'), "task_id": state.get('task_id'), "progress_callback": progress_callback
        })

        try:
            if tool_name == "deep_research": selected_tool.progress_callback = progress_callback
            
            output_dump = await selected_tool.ainvoke(tool_args, config=run_config)
            
            context_content = ""
            sources_list = []
            visual_schema = None
            recommendations = []

            if isinstance(output_dump, ToolOutputWithSources):
                context_content = output_dump.context_for_llm
                sources_list = output_dump.sources
                visual_schema = output_dump.visual_schema
                recommendations = output_dump.recommendations
            elif isinstance(output_dump, str):
                try:
                    parsed = json.loads(output_dump)
                    context_content = parsed.get("context_for_llm", output_dump)
                    sources_list = parsed.get("sources", [])
                    visual_schema = parsed.get("visual_schema")
                    recommendations = parsed.get("recommendations", [])
                except:
                    context_content = output_dump
            elif isinstance(output_dump, dict):
                context_content = output_dump.get("context_for_llm", json.dumps(output_dump))
                sources_list = output_dump.get("sources", [])
                visual_schema = output_dump.get("visual_schema")
                recommendations = output_dump.get("recommendations", [])
            else:
                context_content = str(output_dump)

            # Inyectar instrucción de parada si es un reporte de investigación profunda completo
            if tool_name == "deep_research" and ("# Resumen Ejecutivo" in context_content or "# Introducción" in context_content):
                context_content += "\n\n--- INSTRUCCIÓN DEL SISTEMA: La investigación se ha completado. Proporcione la respuesta final al usuario ahora. NO vuelva a llamar a la herramienta 'deep_research'. ---"


            # Re-indexación local
            tool_sources = []
            for i, s in enumerate(sources_list):
                s_dict = s.model_dump() if hasattr(s, 'model_dump') else (s.dict() if hasattr(s, 'dict') else s)
                tool_sources.append(s_dict)

            if len(context_content) > 30000:
                context_content = context_content[:30000] + "\n\n[... TRUNCADO ...]"

            await send_personal_message(target_account_id, {
                "type": "tool_end", "taskId": state.get("task_id"), "tool_name": tool_name,
                "status": "end", "result": context_content, "sources": tool_sources, 
                "visual_schema": visual_schema, "recommendations": recommendations,
                "thread_id": state.get("thread_id")
            }, connection_type=conn_type)

            tool_message = ToolMessage(content=context_content, tool_call_id=tool_call.get("id") or str(uuid.uuid4()))
            if visual_schema:
                tool_message.additional_kwargs["visual_schema"] = visual_schema
            if recommendations:
                tool_message.additional_kwargs["recommendations"] = recommendations
                
            return tool_message, tool_sources


        except Exception as e:
            logger.error(f"Error paralelo en {tool_name}: {e}")
            state['tool_error_counts'][tool_name] = state['tool_error_counts'].get(tool_name, 0) + 1
            
            # Si es un error de validación, usar el formateador especializado
            if isinstance(e, ValidationError):
                error_text = format_validation_error_for_llm(e, tool_name, tool_args)
            else:
                error_text = f"Error: {e}"

            await send_personal_message(target_account_id, {
                "type": "tool_end", "taskId": state.get("task_id"), "tool_name": tool_name,
                "status": "error", "result": error_text, "error": True, "sources": []
            }, connection_type=conn_type)
            return ToolMessage(content=error_text, tool_call_id=tool_call.get("id") or str(uuid.uuid4())), []

    # 2. Ejecutar todas las llamadas en paralelo
    tasks = [execute_single_tool(tc) for tc in tool_calls]
    parallel_results = await asyncio.gather(*tasks)

    # 3. Consolidar resultados
    tool_messages = []
    all_new_sources = []
    for msg, sources in parallel_results:
        tool_messages.append(msg)
        all_new_sources.extend(sources)

    # 4. Re-indexación global secuencial
    # 4. Inserción de nuevas fuentes (evitando duplicados)
    actual_new_sources_to_return = []
    current_sources = state.get("sources") or []
    # Crear conjunto de URLs ya vistas en el estado actual para no duplicar
    seen_urls = {s.get('url') for s in current_sources if s.get('url')}
    
    for s in all_new_sources:
        url = s.get('url')
        # Si no tiene URL o la URL no ha sido vista, es nueva
        if not url or url not in seen_urls:
            actual_new_sources_to_return.append(s)
            if url: seen_urls.add(url)
    
    logger.info(f"✅ tool_node: Añadiendo {len(actual_new_sources_to_return)} nuevas fuentes al estado. (Total previo: {len(current_sources)})")

    asyncio.create_task(knowledge_extraction_node(state))
    # Devolver SOLO las nuevas fuentes, ya que LangGraph usa operator.add
    return {"messages": tool_messages, "sources": actual_new_sources_to_return, "loop_count": state.get("loop_count", 0) + 1}

# --- 2. Enrutador ---

def should_continue(state: AgentState) -> str:
    """
    Decide si continuar con la ejecución de herramientas o finalizar.
    """
    logger.info("--- (Grafo) Nodo: Enrutamiento ---")
    last_message = state["messages"][-1]
    
    # Loop protection: máximo 10 iteraciones de herramientas
    loop_count = state.get("loop_count", 0)
    if loop_count >= 10:
        logger.warning(f"⚠️ Alerta de bucle detectada (loop_count={loop_count}). Forzando finalización.")
        return "generate_response"

    if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
        logger.info(f"Decisión del enrutador: Llamar a herramienta (Intento {loop_count + 1}).")
        return "continue"
    
    logger.info("Decisión del enrutador: Generar respuesta final.")
    return "generate_response"

# --- 3. Ensamblaje del Grafo ---

# Global cache for the compiled agent graph (singleton pattern)
_compiled_agent_graph = None
_graph_reasoning_node_instance = None # NUEVO: Singleton para el nodo de razonamiento
_knowledge_extraction_node_instance = None # NUEVO: Singleton para el nodo de extracción

def get_langgraph_agent():
    """
    Retorna el grafo compilado del agente, creándolo y cacheándolo en la primera llamada.
    
    Optimization: El grafo es stateless (el estado se pasa como parámetro AgentState),
    por lo que es seguro y eficiente cachearlo globalmente como singleton.
    
    Returns:
        CompiledGraph: El grafo LangGraph compilado y listo para usar.
    """
    global _compiled_agent_graph
    
    if _compiled_agent_graph is None:
        logger.info("🔧 Compilando grafo LangGraph del agente por primera vez...")
        _compiled_agent_graph = create_langgraph_agent()
        logger.info("✅ Grafo LangGraph compilado y cacheado exitosamente")
    
    return _compiled_agent_graph

async def unified_context_node(state: AgentState):
    """
    Nodo orquestador que ejecuta RAG, Recuperación Proactiva y Razonamiento de Grafo
    en paralelo para asegurar que el agente reciba todo el contexto de una sola vez
    y se ejecute una única vez.
    """
    logger.info("--- (Grafo) Nodo: Orquestador de Contexto Unificado ---")
    
    # 1. Determinar qué ramas ejecutar
    # Usamos la lógica de should_use_graph_reasoning internamente o algo similar
    destinations = await should_use_graph_reasoning(state)
    
    tasks = []
    
    # Siempre ejecutamos RAG y Proactive Retrieval (están en destinations por defecto)
    if "rag_node" in destinations:
        tasks.append(rag_node(state))
    if "proactive_retrieval" in destinations:
        tasks.append(retrieve_proactive_memories_node(state))
        
    # Condicionalmente el razonamiento de grafo
    if "graph_router" in destinations or "graph_reasoning" in destinations:
        # Nota: El router y el razonamiento se pueden simplificar aquí
        tasks.append(graph_reasoning_node(state))

    # 2. Ejecutar todo en paralelo
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 3. Consolidar resultados en el estado
    combined_updates = {}
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Error en rama paralela de contexto: {res}")
            continue
        if isinstance(res, dict):
            combined_updates.update(res)
            
    return combined_updates

def create_langgraph_agent():
    """
    Crea y compila el StateGraph para el agente KAI.
    """
    workflow = StateGraph(AgentState)

    # Añadir los nodos al grafo
    workflow.add_node("proactive_memory", proactive_memory_node)
    workflow.add_node("unified_context", unified_context_node) # Nodo único de convergencia
    workflow.add_node("agent", call_model_node)
    workflow.add_node("action", tool_node)
    workflow.add_node("generateResponse", generate_response_node)
    workflow.add_node("knowledge_extraction", knowledge_extraction_node)

    # Definir las aristas (flujo lineal para evitar duplicaciones por fan-in)
    workflow.set_entry_point("proactive_memory")
    
    workflow.add_edge("proactive_memory", "unified_context")
    workflow.add_edge("unified_context", "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "generate_response": "generateResponse",
        }
    )
    
    workflow.add_edge("action", "agent")
    workflow.add_edge("generateResponse", END)

    # Compilar el grafo
    return workflow.compile()

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "action",
            "generate_response": "generateResponse",
        }
    )
    
    workflow.add_edge("action", "agent")
    workflow.add_edge("generateResponse", END)

    # Compilar el grafo
    return workflow.compile()

async def ensure_graph_dependencies(state: AgentState):
    """
    Asegura que las instancias de GraphDB y EnhancedMemoryManager estén disponibles en el estado.
    Si no lo están, las inicializa y las añade al estado.
    """
    if state.get('graph_db') and state.get('enhanced_memory_manager'):
        return state
    
    graph_db, enhanced_memory_manager = await get_shared_graph_dependencies()
    if graph_db and enhanced_memory_manager:
        state['graph_db'] = graph_db
        state['enhanced_memory_manager'] = enhanced_memory_manager
        logger.info("✅ Dependencias del grafo inicializadas y añadidas al estado.")
    else:
        logger.warning("⚠️ No se pudieron obtener las dependencias del grafo. La memoria mejorada no estará disponible.")
        state['graph_db'] = None
        state['enhanced_memory_manager'] = None
    
    return state


async def graph_reasoning_node(state: AgentState):
    """
    Ejecuta el nodo de razonamiento del grafo para enriquecer el contexto.
    """
    global _graph_reasoning_node_instance
    
    # 1. Asegurarse de que las dependencias del grafo existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get('graph_db')
    
    if not graph_db:
        logger.warning("Saltando nodo de razonamiento del grafo: GraphDB no está disponible.")
        return state

    # 2. Inicializar el nodo de razonamiento si es necesario (singleton)
    if _graph_reasoning_node_instance is None:
        _graph_reasoning_node_instance = GraphReasoningNode(graph_db)
        logger.info("✅ Instancia de GraphReasoningNode creada.")

    # 3. Invocar el nodo y obtener el contexto enriquecido
    # Pasar target_datasets si existen en el estado
    graph_output = await _graph_reasoning_node_instance.ainvoke(
        cast(dict, state), 
        target_datasets=state.get('target_datasets')
    )

    # 4. Actualizar el estado con la salida del nodo
    updates = {}
    if graph_output:
        updates['graph_context'] = graph_output.get('graph_context')
        updates['graph_sources'] = graph_output.get('graph_sources')
        updates['mermaid_diagram'] = graph_output.get('mermaid_diagram')
        
        context_preview = updates['graph_context'][:200] + "..." if updates['graph_context'] else "Sin contexto"
        logger.info(f"✅ Salida del GraphReasoningNode preparada.\nContexto Previo: {context_preview}\nFuentes: {len(updates['graph_sources'] or [])}")

    return updates


async def knowledge_extraction_node(state: AgentState):
    """
    Ejecuta el nodo de extracción de conocimiento para persistir información en el grafo.
    Ahora incluye una verificación inteligente para no ejecutarse en cada turno.
    """
    global _knowledge_extraction_node_instance
    
    # 0. Verificación Inteligente de Relevancia (Selective Memory)
    messages = state.get("messages", [])
    if len(messages) < 2:
        return {}

    last_human = None
    last_ai = None
    
    # Buscar el último par de interacción
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not last_ai:
            last_ai = extract_text_content(msg.content)
        elif isinstance(msg, HumanMessage) and not last_human:
            last_human = extract_text_content(msg.content)
        
        if last_human and last_ai:
            break
            
    if not last_human or not last_ai:
        return {}

    # Filtro trivial
    if len(last_human) < 10 and len(last_ai) < 20:
        return {}

    llm = get_fast_llm()
    if not llm:
        logger.warning("No hay LLM rápido para verificar relevancia de memoria. Saltando.")
        return {}

    check_prompt = f"""
    Analiza la siguiente interacción y decide si contiene **NUEVO CONOCIMIENTO PERMANENTE** sobre el usuario (hechos, preferencias, relaciones) o el dominio que merezca ser guardado en un Grafo de Conocimiento.
    
    Usuario: "{last_human}"
    Asistente: "{last_ai}"
    
    Responde ÚNICAMENTE "SÍ" si hay hechos valiosos y permanentes a extraer.
    Responde "NO" si es charla trivial, saludos, agradecimientos, preguntas simples o información efímera.
    
    Respuesta:
    """
    
    try:
        decision_response = await llm.ainvoke(check_prompt)
        decision = str(decision_response.content).strip().upper()
        
        if "SÍ" not in decision and "SI" not in decision and "YES" not in decision:
            logger.info("🧠 Selective Memory: Decisión negativa. No se extraerá conocimiento de este turno.")
            return {}
            
        logger.info("🧠 Selective Memory: Decisión POSITIVA. Procediendo a extracción de conocimiento.")
        
    except Exception as e:
        logger.error(f"Error en chequeo de memoria selectiva: {e}")
        # En caso de error, ser conservador y no extraer para ahorrar recursos
        return {}

    # 1. Asegurarse de que las dependencias del grafo existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get('graph_db')
    
    if not graph_db:
        logger.warning("Saltando nodo de extracción de conocimiento: GraphDB no está disponible.")
        return state

    # 2. Inicializar el nodo de extracción si es necesario (singleton)
    if _knowledge_extraction_node_instance is None:
        from knowledge_graph.knowledge_extraction_node import KnowledgeExtractionNode
        _knowledge_extraction_node_instance = KnowledgeExtractionNode(graph_db)
        logger.info("✅ Instancia de KnowledgeExtractionNode creada.")

    # 3. Invocar el nodo para extraer y persistir conocimiento
    try:
        # El método ainvoke de KnowledgeExtractionNode espera el estado y devuelve el estado modificado
        # o realiza efectos secundarios (persistencia) y devuelve el estado.
        await _knowledge_extraction_node_instance.ainvoke(cast(dict, state))
        logger.info("✅ Extracción de conocimiento completada exitosamente.")
    except Exception as e:
        logger.error(f"❌ Error en el nodo de extracción de conocimiento: {e}")

    return {}


async def graph_router_node(state: AgentState):
    """
    Nodo de decisión que identifica qué datasets del grafo son relevantes para la consulta.
    Diferencia entre 'Agent Memories' (personal) y datasets de conocimiento (documentos).
    """
    logger.info("--- (Grafo) Nodo: Enrutador de Datasets ---")
    
    # 1. Asegurarse de que las dependencias existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get('graph_db')
    enhanced_memory_manager = state.get('enhanced_memory_manager')
    
    if not graph_db:
        return {"target_datasets": ["Agent Memories"]}

    # 2. Obtener datasets disponibles
    try:
        datasets_info = await graph_db.get_available_datasets(state['account_id'])
        if not datasets_info:
            logger.info("No hay datasets disponibles en el grafo.")
            state['target_datasets'] = ["Agent Memories"] # Fallback mínimo
            return state
        
        datasets_list = [d['name'] for d in datasets_info]
        logger.info(f"Datasets disponibles: {datasets_list}")
    except Exception as e:
        logger.error(f"Error obteniendo datasets: {e}")
        state['target_datasets'] = ["Agent Memories"]
        return state

    # 3. Usar LLM para decidir con lógica de doble indagación
    llm = get_fast_llm()
    last_message = ""
    if state["messages"]:
        last_msg_obj = state["messages"][-1]
        last_message = extract_text_content(last_msg_obj.content)
    
    prompt = f"""
Analiza la siguiente pregunta del usuario y decide qué datasets del grafo de conocimiento son relevantes para responder con precisión.

**Datasets Disponibles**:
{json.dumps(datasets_list, indent=2)}

**Pregunta del Usuario**: "{last_message}"

**Instrucciones de Clasificación**:
1.  **Agent Memories**: Selecciona este dataset si la pregunta es sobre el usuario, sus gustos, su historia personal, sus tareas, sus contactos o cualquier cosa que el asistente deba "recordar" sobre él.
2.  **Datasets de Conocimiento**: Selecciona los nombres de los datasets que correspondan a temas técnicos, documentos específicos o colecciones de información externa que el usuario haya cargado.

**Reglas**:
- Puedes seleccionar varios datasets.
- Si la pregunta es general o ambigua, incluye siempre `Agent Memories`.
- Responde ÚNICAMENTE con una lista JSON de los nombres de los datasets relevantes.

**Respuesta (solo JSON)**:
"""
    try:
        response = await llm.ainvoke(prompt)
        content = str(response.content).strip()
        
        # Limpiar posible formato markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        selected = json.loads(content)
        
        # Validar que los seleccionados existan en la lista real
        target_datasets = [d for d in selected if d in datasets_list]
        
        # Asegurar que si no se seleccionó nada, al menos use Agent Memories
        if not target_datasets:
            target_datasets = ["Agent Memories"]
            
        logger.info(f"🎯 Router de Grafo: Datasets seleccionados para indagación: {target_datasets}")
        return {"target_datasets": target_datasets, "graph_db": graph_db, "enhanced_memory_manager": enhanced_memory_manager}
    except Exception as e:
        logger.error(f"Error en la decisión del router: {e}")
        return {"target_datasets": ["Agent Memories"], "graph_db": graph_db, "enhanced_memory_manager": enhanced_memory_manager}


async def should_use_graph_reasoning(state: AgentState):
    """
    Decide inteligentemente si se debe activar la rama de razonamiento del grafo.
    Utiliza un LLM rápido para analizar si la consulta se beneficiaría de un análisis relacional.
    """
    curr_destinations = ["rag_node", "proactive_retrieval"] # SIEMPRE ejecutamos RAG y Proactive Retrieval en paralelo
    
    last_message = state["messages"][-1] if state["messages"] else None
    if not isinstance(last_message, HumanMessage):
        return curr_destinations

    user_message = extract_text_content(last_message.content)
    
    # 1. Filtro rápido de longitud
    if len(user_message.strip()) < 5:
        return curr_destinations

    # 2. Decisión vía Fast LLM
    llm = get_fast_llm()
    if not llm:
        logger.warning("No hay LLM rápido disponible para el enrutador de grafo. Usando RAG solamente.")
        return curr_destinations

    prompt = f"""
Analiza si la siguiente consulta del usuario requiere explorar relaciones, entidades, conexiones históricas o contexto profundo en un grafo de conocimiento.

Consulta: "{user_message}"

Responde ÚNICAMENTE con la palabra "SÍ" si crees que el grafo aportaría valor, o "NO" si es una consulta simple o puramente transaccional.
Respuesta:"""

    try:
        response = await llm.ainvoke(prompt)
        decision = str(response.content).strip().upper()
        
        if "SÍ" in decision or "SI" in decision or "YES" in decision:
            logger.info(f"🧠 Enrutador Inteligente: Activando rama de Grafo para: '{user_message[:50]}...'")
            curr_destinations.append("graph_router")
        else:
            logger.info(f"🔍 Enrutador Inteligente: Solo RAG para: '{user_message[:50]}...'")
            
    except Exception as e:
        logger.error(f"Error en la decisión inteligente del enrutador: {e}")
        # Fallback: si falla el LLM, podríamos usar el filtro de palabras clave anterior o solo RAG
        # Por seguridad, usaremos solo RAG para no bloquear el flujo
    
    return curr_destinations

async def rag_node(state: AgentState):
    """
    Nodo dedicado para realizar la búsqueda RAG (Recuperación Aumentada por Generación) en paralelo.
    """
    logger.info("--- (Grafo) Nodo: RAG (Búsqueda Vectorial) ---")
    
    user_message = ""
    last_message = state["messages"][-1] if state["messages"] else None
    
    # Si el último mensaje es una herramienta, no hacemos RAG
    if isinstance(last_message, ToolMessage):
        return {}

    if isinstance(last_message, HumanMessage):
        user_message = extract_text_content(last_message.content)
    
    if not user_message:
        return state

    rag_context = state.get("rag_context")
    context = state.get("context")
    filter_topics = None
    explicit_doc_ids = None

    # Preparar filtros
    if rag_context:
        explicit_doc_ids = [item['id'] for item in rag_context if item.get('type') == 'document']
    
    if context and context.get("type") == "collection":
        topic = context.get("id")
        if topic:
            filter_topics = [topic]

    try:
        logger.info(f"🔍 Ejecutando RAG en nodo paralelo. Workspace: {state.get('workspace_id')}")
        
        rag_output = await get_relevant_memories(
            account_id=state['account_id'],
            query=user_message,
            workspace_id=state.get('workspace_id'),
            explicit_document_ids=explicit_doc_ids,
            filter_topics=filter_topics,
            k=10
        )
        
        if rag_output and rag_output.sources:
            # Convertir fuentes a diccionarios para el estado
            sources_dicts = [s.dict() for s in rag_output.sources]
            logger.info(f"✅ RAG completado. Fuentes encontradas: {len(sources_dicts)}")
            return {"sources": sources_dicts}
        else:
            return {"sources": []}
            
    except Exception as e:
        logger.error(f"❌ Error en nodo RAG: {e}", exc_info=True)
        return {"sources": []}

from core.prompts import PROACTIVE_MEMORY_PROMPT
import json

async def _process_proactive_memory_task(
    account_id: str,
    workspace_id: Optional[str],
    telegram_id: Optional[int],
    thread_id: Optional[str],
    user_content: str,
    history_for_prompt: str,
    llm: BaseChatModel
):
    """
    Tarea en segundo plano para invocar al LLM y guardar memorias proactivas.
    """
    logger.info("Iniciando tarea en segundo plano para memoria proactiva...")
    prompt = f"""{PROACTIVE_MEMORY_PROMPT}
---
**Conversación:**
{history_for_prompt}

**Último mensaje del usuario:** "{user_content}"

**Tu salida JSON (solo el JSON, nada más):**
"""
    try:
        logger.info("Invocando LLM para extracción de memoria proactiva (en segundo plano)...")
        response = await llm.ainvoke(prompt)
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        json_str = str(response_content).strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        
        extracted_data = json.loads(json_str)
        memories_to_save = extracted_data.get("memories", [])

        if not memories_to_save:
            logger.info("No se extrajeron memorias proactivas (en segundo plano).")
            return

        logger.info(f"Se extrajeron {len(memories_to_save)} memorias proactivas (en segundo plano): {memories_to_save}")

        for memory_content in memories_to_save:
            await add_memory_to_vector_db(
                account_id=account_id,
                content=memory_content,
                type="user_memory_proactive_llm",
                workspace_id=workspace_id,
                telegram_id=str(telegram_id) if telegram_id else None,
                thread_id=thread_id
            )
            logger.info(f"Memoria proactiva guardada (en segundo plano) para la cuenta {account_id}: '{memory_content}'")

        if account_id:
            from knowledge_graph.memory_graph_processor import schedule_memory_graph_processing
            asyncio.create_task(schedule_memory_graph_processing(account_id=account_id))
            logger.info(f"Procesamiento del grafo de conocimiento programado (en segundo plano) tras memoria proactiva para la cuenta {account_id}.")

    except json.JSONDecodeError:
        logger.error(f"Error de decodificación JSON en memoria proactiva (en segundo plano). Respuesta del LLM no fue un JSON válido: {response_content}")
    except Exception as e:
        logger.error(f"Error en la tarea de memoria proactiva en segundo plano: {e}", exc_info=True)


async def proactive_memory_node(state: AgentState):
    """
    Este nodo se ejecuta después de la entrada del usuario para analizar proactivamente
    y guardar memorias sin esperar a que el agente principal lo haga.
    Utiliza un LLM rápido para extraer hechos y los guarda en la base de datos vectorial.
    """
    logger.info("--- (Grafo) Nodo: Memoria Proactiva ---")
    
    # 1. Validar que el último mensaje sea del usuario y no esté vacío
    last_message = state["messages"][-1]
    if not isinstance(last_message, HumanMessage):
        logger.info("Saltando memoria proactiva: el último mensaje no es del usuario.")
        # Calculamos el turno actual incluso si saltamos para mantener el estado consistente
        calc_turn = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
        return {"turn_count": calc_turn}

    user_content = extract_text_content(last_message.content)
    if not user_content or len(user_content.strip()) < 10:
        logger.info("Saltando memoria proactiva: contenido del usuario muy corto o vacío.")
        calc_turn = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
        return {"turn_count": calc_turn}

    # 2. Calcular el contador de turnos real basado en el número de mensajes del usuario en el historial
    # Esto asegura que el contador sea persistente incluso si el estado del grafo se reinicia
    current_turn_count = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
    logger.info(f"Contador de turnos real (basado en mensajes humanos): {current_turn_count}")


    # 3. Decidir si es momento de procesar la memoria proactiva (cada 5 turnos)
    if current_turn_count % 5 != 0:
        logger.info("Saltando memoria proactiva: no es un turno de procesamiento.")
        return {"turn_count": current_turn_count, "loop_count": 0}

    # 4. Preparar el LLM
    llm = get_fast_llm()
    if not llm:
        logger.warning("No hay un LLM rápido disponible para la memoria proactiva. Saltando nodo.")
        return state

    # 5. Formatear historial para el prompt (últimos 10 mensajes)
    # Excluimos el mensaje actual del usuario para no duplicar en "Último mensaje del usuario"
    history_for_prompt = "\n".join([f"{'Usuario' if isinstance(m, HumanMessage) else 'Asistente'}: {extract_text_content(m.content)}" for m in state["messages"][-11:-1]]) # Últimos 10 mensajes excluyendo el actual

    # 6. Programar la tarea de procesamiento de memoria en segundo plano
    asyncio.create_task(
        _process_proactive_memory_task(
            account_id=state['account_id'],
            workspace_id=state.get('workspace_id'),
            telegram_id=state.get('telegram_id'),
            thread_id=state.get('thread_id'),
            user_content=user_content,
            history_for_prompt=history_for_prompt,
            llm=llm
        )
    )
    logger.info("Tarea de memoria proactiva programada en segundo plano. El grafo continuará su ejecución.")

    return {"turn_count": current_turn_count, "loop_count": 0}

async def retrieve_proactive_memories_node(state: AgentState):
    """
    Nodo específico para recuperar memorias proactivas guardadas previamente.
    Se asegura de que estas memorias (user_memory_proactive_llm) sean consideradas.
    """
    logger.info("--- (Grafo) Nodo: Recuperación de Memorias Proactivas ---")
    
    last_message = state["messages"][-1] if state["messages"] else None
    if not isinstance(last_message, HumanMessage):
        return {}

    user_query = extract_text_content(last_message.content)
    if not user_query:
        return {}

    try:
        logger.info(f"🔍 Buscando específicamente memorias proactivas para: '{user_query[:50]}...'")
        
        proactive_output = await get_relevant_memories(
            account_id=state['account_id'],
            query=user_query,
            workspace_id=state.get('workspace_id'),
            content_types=["user_memory_proactive_llm"], # Solo buscar este tipo
            k=5, # Top 5 es suficiente
            similarity_threshold=0.65 # Un poco más permisivo
        )
        
        if proactive_output and proactive_output.sources:
            # Marcar estas fuentes para que el LLM sepa que son proactivas/importantes
            sources_dicts = []
            for s in proactive_output.sources:
                s_dict = s.dict()
                s_dict["metadata"]["is_proactive"] = True
                s_dict["metadata"]["source_type_label"] = "Memoria Proactiva"
                sources_dicts.append(s_dict)
                
            logger.info(f"✅ Encontradas {len(sources_dicts)} memorias proactivas relevantes.")
            return {"sources": sources_dicts}
        else:
            logger.info("No se encontraron memorias proactivas relevantes.")
            return {"sources": []}

    except Exception as e:
        logger.error(f"❌ Error recuperando memorias proactivas: {e}", exc_info=True)
        return {"sources": []}
