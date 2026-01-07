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
from langchain_google_genai import ChatGoogleGenerativeAI
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
from core.citation_models import ToolOutputWithSources, Source, SourceType
from core.llm_manager import get_main_llm, get_fast_llm
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
logger = logging.getLogger(__name__)


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
    target_datasets: Optional[List[str]]

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
    llm_for_summary = get_fast_llm()
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
    # Log extra para depuración
    logger.info(f"[TÍTULO][DEBUG] Hilo {thread_id} - Título actual: '{current_title}' - Mensajes reales (sin resumen): {len(messages)}")
    # Si el título es 'Nuevo Chat' y hay al menos 5 mensajes, o si hay 20+ mensajes y el título es distinto
    if (current_title == "Nuevo Chat" and len(messages) >= 5) or (current_title != "Nuevo Chat" and len(messages) >= 20 and len(messages) % 20 == 0):
        
        conversation_text = '\n'.join([extract_text_content(m.content) if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = THREAD_TITLE_PROMPT.format(conversation_text=conversation_text)
        llm = get_fast_llm() or get_main_llm()
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
                
            logger.info(f"[TÍTULO] Título generado para hilo {thread_id}: '{new_title}'")
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
        llm = get_fast_llm()
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

            logger.info(f"Nuevo título generado para el hilo {thread_id}: '{new_title}'")
            
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
    logger.info(f"--- (Grafo) Nodo: Llama al Modelo para cuenta {state['account_id']} ---")
    
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
    # Importaciones necesarias para Source, SourceType y format_context_with_sources
    from typing import List
    from core.citation_models import Source, SourceType, format_context_with_sources

    # Combinar fuentes de RAG y Grafo, asegurando IDs únicos y secuenciales
    all_sources_for_llm: List[Source] = []
    final_sources_for_state = [] # Inicializar para evitar UnboundLocalError
    
    # 1. Añadir fuentes de RAG (que ahora vienen del rag_node en state['sources'])
    rag_sources_dicts = state.get('sources', [])
    if rag_sources_dicts:
        for s_dict in rag_sources_dicts:
            try:
                # Asegurar que s_dict es un diccionario
                if hasattr(s_dict, 'dict'):
                    s_dict = s_dict.dict()
                elif hasattr(s_dict, 'model_dump'):
                    s_dict = s_dict.model_dump()
                
                # Crear objeto Source
                source_obj = Source(**s_dict)
                all_sources_for_llm.append(source_obj)
            except Exception as e:
                logger.error(f"Error procesando fuente RAG para LLM: {e}")

    # 2. Añadir fuentes de Grafo (re-indexando para que sigan a las de RAG)
    if state.get("graph_sources"):
        graph_sources_val = state.get("graph_sources")
        if graph_sources_val:
            for s_dict in graph_sources_val:
                # Crear objeto Source desde dict
                try:
                    # Asegurarse de que el tipo sea GRAPH
                    s_dict['type'] = SourceType.GRAPH
                    source_obj = Source(**s_dict)
                    # Re-indexar basado en la posición actual en all_sources_for_llm
                    source_obj.id = len(all_sources_for_llm) + 1
                    all_sources_for_llm.append(source_obj)
                except Exception as e:
                    logger.error(f"Error procesando fuente del grafo: {e}")

    # 3. Generar el contexto formateado con los nuevos IDs
    if all_sources_for_llm:
        relevant_memories_text = format_context_with_sources(all_sources_for_llm)
        
        # Actualizar final_sources_for_state con los objetos Source (convertidos a dict)
        
        existing_urls = set()
        new_sources = [s.dict() for s in all_sources_for_llm]
        
        for ns in new_sources:
            if ns.get('url') not in existing_urls:
                final_sources_for_state.append(ns)
                existing_urls.add(ns.get('url'))
                
        logger.info(f"Consolidadas {len(all_sources_for_llm)} fuentes totales para el LLM (RAG + Grafo).")
    else:
        relevant_memories_text = "No se encontraron memorias o documentos relevantes en la base de conocimiento ni en el grafo."
    # --- FIN DE LA LÓGICA DE MANEJO DE FUENTES ---
        
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
    system_prompt_content = prompt_manager.build_system_prompt(
        user_profile=user_profile,
        relevant_memories=relevant_memories_text,
        summary_string="",
        custom_prompt_from_profile=str(user_profile.system_prompt) if user_profile and user_profile.system_prompt else None,
        workspace_prompt=None, # Este se rellena después
        tools=tools,
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id'),
        user_message=user_message,
        has_explicit_rag_context=has_explicit_rag_context,
        explicit_document_names=[name for name in document_names_for_rag if name is not None] if document_names_for_rag else None,
        context=state.get('context') # Pasar el contexto aquí
    )

    if state.get('workspace_id'):
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(state.get('workspace_id')))
            if workspace and workspace.system_prompt:
                workspace_prompt = str(workspace.system_prompt)

            system_prompt_content = prompt_manager.build_system_prompt(
                user_profile=user_profile,
                relevant_memories=relevant_memories_text,
                summary_string="",
                custom_prompt_from_profile=str(user_profile.system_prompt) if user_profile and user_profile.system_prompt else None,
                workspace_prompt=workspace_prompt, # Ahora sí se usa
                tools=tools,
                account_id=state['account_id'],
                telegram_id=state.get('telegram_id'),
                user_message=user_message,
                has_explicit_rag_context=has_explicit_rag_context,
                explicit_document_names=[str(name) for name in document_names_for_rag if name is not None] if document_names_for_rag else None,
                context=state.get('context') # Pasar el contexto aquí
            )
    
    llm = get_main_llm()
    
    # --- SOPORTE MULTIMODAL EN CHAT ---
    # Si el mensaje contiene una imagen, usamos el modelo de visión
    has_image = False
    if isinstance(last_message.content, list):
        for item in last_message.content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                has_image = True
                break
    
    if has_image:
        logger.info("📸 Imagen detectada en el chat. Cambiando al modelo de visión.")
        llm = get_vision_llm()
    # --- FIN SOPORTE MULTIMODAL ---

    if not llm:
        raise ValueError("El LLM principal no está disponible.")
         
    # Log del modelo en uso para confirmación visual
    model_name = getattr(llm, 'model_name', getattr(llm, 'model', settings.llm_model))
    logger.info(f"🤖 AGENT EXECUTION: Generando respuesta usando modelo: '{model_name}'")

    logger.debug(f"DEBUG (agent.py - call_model_node): System Prompt final antes de LLM: {system_prompt_content}")
    
    # --- BINDING DE HERRAMIENTAS COMPATIBLE CON CUALQUIER LLM ---
    # Usamos una conversión explícita a formato OpenAI (tools) porque es el estándar
    # más robusto para LiteLLM y OpenRouter, asegurando que los campos 'required' se mantengan.
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
        logger.debug(f"HERRAMIENTAS A VINCULAR: {[t['function']['name'] for t in openai_tools]}")
        
        # Usamos .bind(tools=...) que es lo que LiteLLM espera para casi todos los proveedores
        # También pasamos 'functions' para modelos legacy de OpenRouter que lo prefieran
        if openai_tools:
            # Extraer solo la parte 'function' para el parámetro legacy 'functions'
            # The 'functions' parameter is for legacy models and can cause duplication with modern APIs like Gemini.
            # We will only use the 'tools' parameter which is the modern standard.
            llm_with_tools = llm.bind(tools=openai_tools)
        else:
            llm_with_tools = llm
            
        logger.info(f"✅ Herramientas vinculadas correctamente al LLM '{model_name}'")
    except Exception as e:
        logger.error(f"❌ Error crítico al vincular herramientas al LLM '{model_name}': {e}", exc_info=True)
        llm_with_tools = llm

    # --- REFUERZO DE INSTRUCCIONES PARA MODELOS NO-GEMINI ---
    # Los modelos de OpenRouter a veces ignoran los argumentos si el prompt es largo.
    # Añadimos un recordatorio justo al final del prompt del sistema.
    final_system_content = system_prompt_content
    if "gemini" not in model_name.lower():
        final_system_content += "\n\n⚠️ **CRITICAL TECHNICAL REMINDER:** If you decide to use a tool, you MUST provide ALL required arguments in the 'args' field. Never send an empty 'args' object {{}} if the tool has required parameters."

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

    # --- LIMPIEZA DE HISTORIAL PARA MISTRAL/OPENROUTER ---
    # Mistral es extremadamente estricto con el orden y la paridad: 
    # User -> AI (tool calls) -> Tool (todas las respuestas) -> AI
    def clean_messages_for_mistral(messages):
        cleaned = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            # 1. Ignorar mensajes vacíos que no sean llamadas a herramientas
            if not msg.content and not (isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None)):
                i += 1
                continue
                
            if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
                # Encontrado un bloque de llamadas a herramientas. 
                # Debemos encontrar TODAS sus respuestas inmediatamente después.
                current_tool_calls = msg.tool_calls
                call_ids = {tc.get('id') for tc in current_tool_calls if tc.get('id')}
                
                responses = []
                next_i = i + 1
                while next_i < len(messages):
                    next_msg = messages[next_i]
                    if isinstance(next_msg, ToolMessage):
                        if next_msg.tool_call_id in call_ids:
                            responses.append(next_msg)
                            call_ids.remove(next_msg.tool_call_id)
                        else:
                            # ToolMessage que no pertenece a este bloque, ignorar o tratar como huérfano
                            logger.warning(f"⚠️ ToolMessage huérfano o desordenado detectado: {next_msg.tool_call_id}")
                    elif isinstance(next_msg, (HumanMessage, AIMessage, SystemMessage)):
                        # Si encontramos cualquier otro mensaje antes de completar las respuestas,
                        # Mistral fallará si dejamos llamadas sin respuesta.
                        break
                    next_i += 1
                
                # Reconstruir el AIMessage solo con las llamadas que SÍ tienen respuesta
                valid_call_ids = {r.tool_call_id for r in responses}
                filtered_tool_calls = [tc for tc in current_tool_calls if tc.get('id') in valid_call_ids]
                
                # Ordenar respuestas para que coincidan con el orden de las llamadas (Mistral strictness)
                order_map = {tc.get('id'): idx for idx, tc in enumerate(filtered_tool_calls)}
                responses.sort(key=lambda r: order_map.get(r.tool_call_id, 999))
                
                if filtered_tool_calls or msg.content:
                    # Crear una copia del mensaje con las llamadas filtradas
                    new_ai_msg = AIMessage(
                        content=msg.content,
                        tool_calls=filtered_tool_calls,
                        additional_kwargs=getattr(msg, 'additional_kwargs', {})
                    )
                    cleaned.append(new_ai_msg)
                    # Añadir las respuestas encontradas inmediatamente después
                    cleaned.extend(responses)
                else:
                    logger.warning("⚠️ Omitiendo AIMessage porque no tiene contenido ni llamadas válidas con respuesta.")
                
                # Saltar los mensajes procesados
                i = next_i
            elif isinstance(msg, ToolMessage):
                # ToolMessage huérfano (no precedido por su AIMessage)
                logger.warning(f"⚠️ Omitiendo ToolMessage huérfano: {msg.tool_call_id}")
                i += 1
            else:
                # Mensajes normales (Human, System, AI sin herramientas)
                cleaned.append(msg)
                i += 1
        
        return cleaned

    cleaned_messages = clean_messages_for_mistral(state["messages"])
    
    async for chunk in chain.astream({"messages": cleaned_messages}):
        if isinstance(chunk, AIMessage):
            if isinstance(chunk.content, str):
                full_ai_message_content += chunk.content
            elif isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        full_ai_message_content += part.get("text", "")
            
            if chunk.tool_calls:
                tool_calls_from_llm.extend(chunk.tool_calls)
            
            logger.debug(f"DEBUG (agent.py): Enviando stream_chunk para taskId {state.get('task_id')}: {chunk.content}")
            await send_personal_message(target_account_id, {
                "type": "stream_chunk",
                "thread_id": state['thread_id'],
                "taskId": state.get("task_id"),
                "chunk": str(chunk.content or ""),
                "full_text": full_ai_message_content
            }, connection_type=conn_type)
            
            final_response_message = chunk

    logger.debug(f"DEBUG (agent.py - call_model_node): Respuesta cruda del LLM (acumulada): {full_ai_message_content}")
    
    # --- DEBUG: Log detallado de tool_calls ---
    if tool_calls_from_llm:
        logger.info(f"🔧 DEBUG: LLM generó {len(tool_calls_from_llm)} tool_calls")
        for idx, tc in enumerate(tool_calls_from_llm):
            logger.info(f"🔧 DEBUG: Tool call [{idx}] estructura completa: {json.dumps(tc, ensure_ascii=False, indent=2)}")
            logger.info(f"🔧 DEBUG: Tool call [{idx}] - name: {tc.get('name')}, id: {tc.get('id')}, args: {tc.get('args')}, arguments: {tc.get('arguments')}")
    # --- END DEBUG ---

    # --- FIX: Ensure all tool calls have an ID and normalize arguments ---
    valid_tool_calls = []
    for tc in tool_calls_from_llm:
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
            
        valid_tool_calls.append(tc)
    
    tool_calls_from_llm = valid_tool_calls
    # --- END FIX ---

    if final_response_message:
        final_ai_message = AIMessage(
            content=full_ai_message_content,
            tool_calls=tool_calls_from_llm,
            additional_kwargs=final_response_message.additional_kwargs
        )
    else:
        final_ai_message = AIMessage(content=full_ai_message_content, tool_calls=tool_calls_from_llm)

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
    logger.info("--- (Grafo) Nodo: Generar Respuesta ---")
    # --- INICIO: Extracción de conocimiento en segundo plano ---
    # Ejecutar el nodo de extracción de forma asíncrona para no bloquear la respuesta
    # y evitar romper el flujo de streaming esperado por la API.
    import asyncio
    asyncio.create_task(knowledge_extraction_node(state))
    # --- FIN: Extracción de conocimiento ---
    return {"messages": state["messages"]}

async def tool_node(state: AgentState):
    """
    Ejecuta las herramientas llamadas por el agente y añade los resultados al estado.
    MODIFICADO: Ahora también extrae y propaga las 'sources' de las herramientas.
    """
    logger.info("--- (Grafo) Nodo: Llamar Herramienta ---")
    if not isinstance(state["messages"][-1], AIMessage):
        return {}

    agent_message = state["messages"][-1]
    # Asegurarse de que agent_message es un AIMessage antes de acceder a tool_calls
    tool_calls = agent_message.tool_calls if isinstance(agent_message, AIMessage) and hasattr(agent_message, 'tool_calls') else []
    
    if not tool_calls:
        return {}

    # Optimization: Instantiate only the requested tool using get_tool_by_name
    # tools = await get_all_langchain_tools(...) # Removed to avoid overhead
    # tool_map = {tool.name: tool for tool in tools} # Removed

    # Redundancia eliminada
    tool_messages = []
    # Cargar las fuentes existentes del estado para poder añadir nuevas
    current_sources = state.get("sources") or []
    # Usar un set para evitar duplicados basados en la URL
    existing_urls = {s['url'] for s in current_sources if 'url' in s and s['url']}

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        
        # Normalizar argumentos: manejar tanto "args" como "arguments"
        tool_args = tool_call.get("args")
        if tool_args is None:
            tool_args = tool_call.get("arguments")
        if tool_args is None:
            tool_args = {}

        # Asegurar que web_search siempre tenga un query válido
        if tool_name == "web_search" and ("query" not in tool_args or not tool_args.get("query")):
            # Inferir query del mensaje del usuario
            user_query = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_query = extract_text_content(msg.content)
                    break
            if user_query:
                tool_args["query"] = user_query
                logger.info(f"🔧 Asignado query inferido para web_search: {user_query}")
            else:
                logger.warning("No se pudo encontrar mensaje de usuario para web_search, usando query por defecto")
                tool_args["query"] = "información general"

        # Asegurar que deep_research siempre tenga un query válido
        if tool_name == "deep_research" and ("query" not in tool_args or not tool_args.get("query")):
            # Inferir query del mensaje del usuario
            user_query = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_query = extract_text_content(msg.content)
                    break
            if user_query:
                tool_args["query"] = user_query
                logger.info(f"🔧 Asignado query inferido para deep_research: {user_query}")
            else:
                logger.warning("No se pudo encontrar mensaje de usuario para deep_research, usando query por defecto")
                tool_args["query"] = "información general"

        # Asegurar que knowledge_graph siempre tenga un natural_language_query válido
        if tool_name == "knowledge_graph" and ("natural_language_query" not in tool_args or not tool_args.get("natural_language_query")):
            # Inferir query del mensaje del usuario
            user_query = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_query = extract_text_content(msg.content)
                    break
            if user_query:
                tool_args["natural_language_query"] = user_query
                logger.info(f"🔧 Asignado natural_language_query inferido para knowledge_graph: {user_query}")
            else:
                logger.warning("No se pudo encontrar mensaje de usuario para knowledge_graph, usando query por defecto")
                tool_args["natural_language_query"] = "información general"

        logger.info(f"🔧 Ejecutando tool_call: name={tool_name}, args={json.dumps(tool_args, ensure_ascii=False)}")
        
        # Enviar evento tool_start
        target_account_id = "telegram_bot_service" if state.get('telegram_id') else state['account_id']
        conn_type = "chat" if state.get('telegram_id') else None
        logger.debug(f"DEBUG (agent.py): Enviando tool_start para taskId {state.get('task_id')}, tool {tool_name}")
        await send_personal_message(target_account_id, {
            "type": "tool_start",
            "taskId": state.get("task_id"),
            "tool_name": tool_name,
        }, connection_type=conn_type)

        # Use get_tool_by_name from the new utils location
        from core.utils.tool_utils import get_tool_by_name
        
        # Utilizar herramientas del estado si están disponibles
        # --- FIX: definir account_id y telegram_id_str ANTES de la rama para evitar uso antes de asignación ---
        account_id = state['account_id']
        telegram_id_int = state.get('telegram_id')
        telegram_id_str = str(telegram_id_int) if telegram_id_int is not None else None
        workspace_id = state.get('workspace_id')

        if "tools" in state:
            all_tools = state["tools"]
        else:
            all_tools = await get_all_langchain_tools(
                account_id=account_id,
                telegram_id=telegram_id_int,
                thread_id=state['thread_id'], # Usamos thread_id del estado
                workspace_id=workspace_id
            )
            state["tools"] = all_tools

        selected_tool = await get_tool_by_name(
            tool_name=tool_name,
            all_tools=all_tools,
            account_id=account_id,
            telegram_id=telegram_id_str,
            workspace_id=workspace_id,
            graph_db=state.get('graph_db'),  # Pasar GraphDB del estado
            enhanced_memory_manager=state.get('enhanced_memory_manager') # Pasar EnhancedMemoryManager del estado
        )

        if not selected_tool:
            logger.error(f"Herramienta '{tool_name}' no encontrada o falló al instanciarse.")
            tool_messages.append(ToolMessage(
                content=f"Error: Herramienta '{tool_name}' no encontrada.",
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            # Enviar evento tool_end con error
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "status": "error",
                "result": f"Error: Herramienta '{tool_name}' no encontrada.",
                "error": True,
                "sources": []
            }, connection_type=conn_type)
            continue
        


        # --- INYECCIÓN DE ATRIBUTOS DE CONTEXTO Y CONFIGURACIÓN ---
        # Crear una RunnableConfig para pasar el contexto y el progress_callback
        async def progress_callback(progress: int, message: str, *args, **kwargs):
            await send_personal_message(target_account_id, {
                "type": "progress",
                "taskId": state.get("task_id"),
                "progress": progress,
                "message": message,
                "thread_id": state.get("thread_id")
            }, connection_type=conn_type)

        run_config = RunnableConfig(
            configurable={
                "account_id": state['account_id'],
                "workspace_id": state.get('workspace_id'),
                "telegram_id": state.get('telegram_id'),
                "thread_id": state.get('thread_id'),
                "task_id": state.get('task_id'),
                "progress_callback": progress_callback,
                "base_progress": 0, # Se puede ajustar si se necesita un progreso base diferente
                "max_sub_progress": 100 # Se puede ajustar si se necesita un rango de progreso diferente
            }
        )
        # --- FIN INYECCIÓN ---

        # --- TRACKING DE ERRORES Y PREVENCIÓN DE BUCLES ---
        # Inicializar el contador de errores si no existe
        if state.get('tool_error_counts') is None:
            state['tool_error_counts'] = {}
        
        # Verificar si ya se alcanzó el límite de reintentos para esta herramienta
        should_stop, stop_message = should_stop_retrying_tool(tool_name, state.get('tool_error_counts'))
        if should_stop:
            logger.warning(f"🛑 Límite de reintentos alcanzado para '{tool_name}'. Deteniendo ejecución.")
            tool_messages.append(ToolMessage(
                content=stop_message,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            # Enviar evento tool_end con límite alcanzado
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "status": "error",
                "result": stop_message,
                "error": True,
                "sources": []
            }, connection_type=conn_type)
            continue
        # --- FIN TRACKING ---

        # --- VALIDACIÓN PRE-EJECUCIÓN DE ARGUMENTOS ---
        # Validar argumentos ANTES de pasarlos a LangChain para evitar errores internos
        if not tool_name or tool_name.strip() == "":
            logger.error(f"❌ Nombre de herramienta vacío o inválido")
            error_message = """❌ Error: El LLM intentó llamar una herramienta sin especificar su nombre.

💡 INSTRUCCIONES:
1. Debes especificar el nombre de la herramienta que quieres usar
2. Revisa la lista de herramientas disponibles
3. Asegúrate de usar el nombre exacto de la herramienta

Por favor, intenta de nuevo especificando correctamente la herramienta."""
            
            tool_messages.append(ToolMessage(
                content=error_message,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name or "unknown",
                "status": "error",
                "result": error_message,
                "error": True,
                "sources": []
            }, connection_type=conn_type)
            continue
        
        
        # Validar que los argumentos no estén vacíos para herramientas que requieren parámetros
        # Usar hasattr para verificar la existencia de args_schema
        if hasattr(selected_tool, 'args_schema') and selected_tool.args_schema:
            try:
                # Acceder al args_schema de forma segura
                args_schema_instance = selected_tool.args_schema
                # Obtener los campos requeridos del schema (Pydantic v2 nativo)
                required_fields = []
                # Si es una instancia de Pydantic v2
                if hasattr(args_schema_instance, 'model_fields'):
                    schema_fields = args_schema_instance.model_fields
                    required_fields = [
                        field_name for field_name, field_info in schema_fields.items()
                        if field_info.is_required()
                    ]
                # Si es un diccionario (JSON Schema)
                elif isinstance(args_schema_instance, dict):
                    required_fields = args_schema_instance.get('required', [])
                # Si no es Pydantic v2 ni un diccionario, no hay campos requeridos conocidos
                else:
                    required_fields = []
                
                # Verificar si faltan campos requeridos
                missing_fields = []
                if not tool_args or not isinstance(tool_args, dict):
                    missing_fields = required_fields
                else:
                    missing_fields = [field for field in required_fields if field not in tool_args or tool_args[field] is None or (isinstance(tool_args[field], str) and tool_args[field].strip() == "")]
                
                if missing_fields:
                    logger.warning(f"⚠️ Argumentos faltantes detectados ANTES de ejecutar '{tool_name}': {missing_fields}")
                    
                    # Incrementar contador de errores
                    if state.get('tool_error_counts') is None:
                        state['tool_error_counts'] = {}
                    state['tool_error_counts'][tool_name] = state['tool_error_counts'].get(tool_name, 0) + 1
                    
                    # Generar mensaje de error detallado y conciso
                    error_message = f"ERROR: Faltan parámetros obligatorios para '{tool_name}': {', '.join(missing_fields)}. Por favor, vuelve a llamar a la herramienta incluyendo estos campos."
                    
                    tool_messages.append(ToolMessage(
                        content=error_message,
                        tool_call_id=tool_call.get("id") or str(uuid.uuid4()),
                        name=tool_name # Crucial para OpenRouter/OpenAI
                    ))
                    
                    await send_personal_message(target_account_id, {
                        "type": "tool_end",
                        "taskId": state.get("task_id"),
                        "tool_name": tool_name,
                        "status": "error",
                        "result": error_message,
                        "error": True,
                        "sources": []
                    }, connection_type=conn_type)
                    continue
            except Exception as validation_error:
                # Si hay error en la validación pre-ejecución, solo loguearlo y continuar
                logger.warning(f"⚠️ Error en validación pre-ejecución de '{tool_name}': {validation_error}")
        # --- FIN VALIDACIÓN PRE-EJECUCIÓN ---

        try:
            logger.info(f"Ejecutando herramienta '{tool_name}' con argumentos: {tool_args}")
            
            # Inyectar progress_callback si la herramienta es deep_research
            if tool_name == "deep_research":
                selected_tool.progress_callback = progress_callback
                logger.info(f"Inyectado progress_callback en herramienta '{tool_name}'")

            # La salida de la herramienta ahora siempre es un dict (model_dump de ToolOutputWithSources)
            output_dump = await selected_tool.ainvoke(tool_args, config=run_config)
            logger.info(f"Resultado de la herramienta '{tool_name}': {output_dump}")
            
            # Asegurar que tool_output siempre sea un objeto ToolOutputWithSources válido
            tool_output: ToolOutputWithSources
            context_content: str = ""
            sources_list = []

            if isinstance(output_dump, ToolOutputWithSources):
                tool_output = output_dump
            elif isinstance(output_dump, str):
                try:
                    parsed_output = json.loads(output_dump)
                    # Caso 1: Salida de knowledge_search con 'results'
                    if "results" in parsed_output and isinstance(parsed_output.get("results"), list):
                        logger.info(f"Procesando salida estructurada de '{tool_name}' con 'results'.")
                        context_parts = []
                        temp_sources = []
                        for i, result in enumerate(parsed_output["results"], start=1):
                            context_parts.append(f"Contexto [{i}] - {result.get('metadata', {}).get('file_name', 'Sin título')}:\\n{result.get('content', '')}\\n")
                            source = Source(
                                id=i,
                                title=result.get('metadata', {}).get('file_name', 'Fuente Desconocida'),
                                url=str(result.get('metadata', {}).get('document_id', '')),
                                snippet=result.get('content', ''),
                                type=SourceType.DOCUMENT,
                                metadata=result.get('metadata', {})
                            )
                            temp_sources.append(source)
                        context_content = "\\n".join(context_parts)
                        sources_list = temp_sources
                    # Caso 2: Salida de knowledge_graph con resumen textual
                    elif tool_name == "knowledge_graph" and "results" in parsed_output and isinstance(parsed_output.get("results"), list) and parsed_output["results"]:
                        logger.info(f"Procesando salida de knowledge_graph con resumen textual.")
                        context_parts = []
                        temp_sources = []
                        for i, result in enumerate(parsed_output["results"], start=1):
                            if isinstance(result, dict) and result.get("type") == "summary_text_insight":
                                # Es un resumen textual del grafo
                                summary_content = result.get('content', '')
                                context_parts.append(f"Resumen del Grafo [{i}]:\\n{summary_content}\\n")
                                source = Source(
                                    id=i,
                                    title=f"Resumen del Grafo de Conocimiento - {parsed_output.get('dataset', 'Desconocido')}",
                                    url=f"graph://summary_{parsed_output.get('dataset', 'unknown')}",
                                    snippet=summary_content,
                                    type=SourceType.GRAPH,
                                    metadata={
                                        "dataset": parsed_output.get('dataset', ''),
                                        "node_count": result.get('node_count', 0),
                                        "relationship_count": result.get('relationship_count', 0)
                                    }
                                )
                                temp_sources.append(source)
                            else:
                                # Otros tipos de resultados del grafo
                                context_parts.append(f"Resultado del Grafo [{i}]:\\n{str(result)}\\n")
                                source = Source(
                                    id=i,
                                    title=f"Resultado del Grafo - {parsed_output.get('dataset', 'Desconocido')}",
                                    url=f"graph://result_{i}",
                                    snippet=str(result),
                                    type=SourceType.GRAPH,
                                    metadata=result if isinstance(result, dict) else {}
                                )
                                temp_sources.append(source)
                        context_content = "\\n".join(context_parts)
                        sources_list = temp_sources
                    # Caso 3: Salida estándar con 'context_for_llm'
                    elif "context_for_llm" in parsed_output:
                        logger.info(f"Procesando salida estándar de '{tool_name}' con 'context_for_llm'.")
                        context_content = parsed_output["context_for_llm"]
                        sources_list = parsed_output.get("sources", [])
                    # Fallback para otros JSON
                    else:
                        logger.warning(f"La salida JSON de '{tool_name}' no tiene un formato esperado. Usando como texto plano.")
                        context_content = output_dump
                    
                    tool_output = ToolOutputWithSources(context_for_llm=context_content, sources=sources_list)

                except json.JSONDecodeError:
                    # Fallback para strings que no son JSON
                    logger.warning(f"La salida de '{tool_name}' no es un JSON válido. Usando como texto plano.")
                    context_content = output_dump
                    tool_output = ToolOutputWithSources(context_for_llm=context_content, sources=[])
            elif isinstance(output_dump, dict):
                if "context_for_llm" in output_dump:
                    context_content = output_dump["context_for_llm"]
                else:
                    context_content = json.dumps(output_dump, ensure_ascii=False) # Si no hay, usar el dict como string
                
                if "sources" in output_dump:
                    sources_list = output_dump["sources"]

                tool_output = ToolOutputWithSources(context_for_llm=context_content, sources=sources_list)
            else:
                context_content = str(output_dump)
                tool_output = ToolOutputWithSources(context_for_llm=context_content, sources=[])

            # --- INICIO: Procesamiento de salida de herramienta y extracción de fuentes ---
            tool_content_for_llm = tool_output.context_for_llm
            tool_sources_to_add: List[Dict[str, Any]] = []

            if tool_output.sources:
                logger.info(f"La herramienta '{tool_name}' devolvió {len(tool_output.sources)} fuentes. Re-indexando para mantener coherencia.")
                
                # Calcular el offset basado en las fuentes ya existentes en este turno
                # para que el LLM vea IDs continuos y no repetidos.
                current_offset = len(current_sources)
                
                reindexed_sources = []
                for i, s in enumerate(tool_output.sources):
                    s_dict = s.model_dump() if hasattr(s, 'model_dump') else (s.dict() if hasattr(s, 'dict') else s)
                    old_id = s_dict.get('id')
                    new_id = current_offset + i + 1
                    s_dict['id'] = new_id
                    reindexed_sources.append(s_dict)
                    
                    # REGLA CRÍTICA: Si el contenido para el LLM usa el ID viejo, lo actualizamos al nuevo
                    # Esto evita que el LLM cite [1] refiriéndose a la fuente 1 de la herramienta,
                    # cuando en realidad ahora es la fuente [N+1] del mensaje total.
                    if old_id is not None:
                        old_pattern = f"[{old_id}]"
                        new_pattern = f"[{new_id}]"
                        if old_pattern in tool_content_for_llm:
                            tool_content_for_llm = tool_content_for_llm.replace(old_pattern, new_pattern)
                        
                        # También manejar el formato "Contexto [N]"
                        old_ctx = f"Contexto [{old_id}]"
                        new_ctx = f"Contexto [{new_id}]"
                        if old_ctx in tool_content_for_llm:
                            tool_content_for_llm = tool_content_for_llm.replace(old_ctx, new_ctx)

                # Añadir las fuentes re-indexadas a la lista global del turno
                current_sources.extend(reindexed_sources)
                tool_sources_to_add = reindexed_sources
            else:
                tool_sources_to_add = []
            
            # --- TRUNCAMIENTO DE SEGURIDAD ---
            # Si la salida es demasiado larga, puede causar errores de límite de tokens en el LLM (400 Bad Request)
            MAX_TOOL_OUTPUT_CHARS = 30000 # Límite generoso pero seguro para modelos de 32k+ tokens
            if len(tool_content_for_llm) > MAX_TOOL_OUTPUT_CHARS:
                logger.warning(f"⚠️ La salida de la herramienta '{tool_name}' es demasiado larga ({len(tool_content_for_llm)} chars). Truncando a {MAX_TOOL_OUTPUT_CHARS}...")
                tool_content_for_llm = tool_content_for_llm[:MAX_TOOL_OUTPUT_CHARS] + "\n\n[... CONTENIDO TRUNCADO POR SEGURIDAD DEBIDO A SU EXTENSIÓN ...]"
            # --- FIN TRUNCAMIENTO ---

            tool_messages.append(ToolMessage(
                content=tool_content_for_llm,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            
            # Enviar evento tool_end con éxito
            logger.debug(f"DEBUG (agent.py): Enviando tool_end (success) para taskId {state.get('task_id')}, tool {tool_name}")
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "status": "end",
                "result": tool_content_for_llm,
                "sources": tool_sources_to_add, # Enviar las fuentes ya re-indexadas
            }, connection_type=conn_type)


        except ValidationError as e:
            # Error de validación de Pydantic - argumentos incorrectos o faltantes
            logger.error(f"❌ Error de validación en la herramienta {tool_name}: {e}", exc_info=True)
            
            # Incrementar contador de errores para esta herramienta
            if state.get('tool_error_counts') is None:
                state['tool_error_counts'] = {}
            state['tool_error_counts'][tool_name] = state['tool_error_counts'].get(tool_name, 0) + 1
            
            # Formatear error para el LLM
            error_message = format_validation_error_for_llm(e, tool_name, tool_args or {})
            
            tool_messages.append(ToolMessage(
                content=error_message,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            
            # Enviar evento tool_end con error de validación
            logger.debug(f"DEBUG (agent.py): Enviando tool_end (validation_error) para taskId {state.get('task_id')}, tool {tool_name}")
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "status": "error",
                "result": error_message,
                "error": True,
                "sources": []
            }, connection_type=conn_type)
            
        except Exception as e:
            # Otros errores generales
            logger.error(f"Error al ejecutar la herramienta {tool_name}: {e}", exc_info=True)
            
            # Incrementar contador de errores para esta herramienta
            if state.get('tool_error_counts') is None:
                state['tool_error_counts'] = {}
            state['tool_error_counts'][tool_name] = state['tool_error_counts'].get(tool_name, 0) + 1
            
            tool_messages.append(ToolMessage(
                content=f"Error: {e}",
                tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ))
            # Enviar evento tool_end con error
            logger.debug(f"DEBUG (agent.py): Enviando tool_end (error) para taskId {state.get('task_id')}, tool {tool_name}")
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "status": "error",
                "result": f"Error: {e}",
                "error": True,
                "sources": [] # No hay fuentes en caso de error
            }, connection_type=conn_type)
            
    # --- INICIO: Deduplicación y asignación de IDs secuenciales ---
    deduplicated_sources = []
    seen_source_identifiers = set()

    for source in current_sources:
        # Crear un identificador único para la deduplicación
        # Se puede ajustar para usar una combinación de campos si la URL no es suficiente
        identifier_parts = []
        if 'url' in source and source['url']:
            identifier_parts.append(source['url'])
        if 'type' in source and source['type']:
            identifier_parts.append(source['type'])
        if 'name' in source and source['name']:
            identifier_parts.append(source['name'])
        if 'title' in source and source['title']:
            identifier_parts.append(source['title'])
        
        source_identifier = "_".join(map(str, identifier_parts))
        
        if source_identifier and source_identifier not in seen_source_identifiers:
            deduplicated_sources.append(source)
            seen_source_identifiers.add(source_identifier)
        elif not source_identifier: # Si no hay identificador, añadirla de todos modos (ej. fuentes sin URL)
             deduplicated_sources.append(source)

    final_sources_with_sequential_ids = []
    for index, source in enumerate(deduplicated_sources, start=1):
        source_copy = source.copy()
        if 'id' in source_copy:
            source_copy['original_id'] = source_copy['id']
        source_copy['id'] = index
        final_sources_with_sequential_ids.append(source_copy)
    
    # --- FIN: Deduplicación y asignación de IDs secuenciales ---

    # Devolver los mensajes de la herramienta Y las fuentes actualizadas al estado del grafo
    # --- INICIO: Extracción de conocimiento en segundo plano ---
    # Ejecutar el nodo de extracción de forma asíncrona para no bloquear la respuesta
    # y evitar romper el flujo de streaming esperado por la API.
    import asyncio
    asyncio.create_task(knowledge_extraction_node(state))
    # --- FIN: Extracción de conocimiento ---

    return {"messages": tool_messages, "sources": final_sources_with_sequential_ids}

# --- 2. Enrutador ---

def should_continue(state: AgentState) -> str:
    """
    Decide si continuar con la ejecución de herramientas o finalizar.
    """
    logger.info("--- (Grafo) Nodo: Enrutamiento ---")
    last_message = state["messages"][-1]
    
    if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
        logger.info("Decisión del enrutador: Llamar a herramienta.")
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

def create_langgraph_agent():
    """
    Crea y compila el StateGraph para el agente KAI.
    """
    workflow = StateGraph(AgentState)

    # Añadir los nodos al grafo
    workflow.add_node("proactive_memory", proactive_memory_node)
    workflow.add_node("graph_router", graph_router_node) # Nodo de decisión del grafo
    workflow.add_node("graph_reasoning", graph_reasoning_node) # Nodo de ejecución del grafo
    workflow.add_node("rag_node", rag_node) # NUEVO: Nodo de RAG paralelo
    workflow.add_node("agent", call_model_node)
    workflow.add_node("action", tool_node)
    workflow.add_node("generateResponse", generate_response_node)
    workflow.add_node("knowledge_extraction", knowledge_extraction_node)

    # Definir las aristas (el flujo de trabajo)
    workflow.set_entry_point("proactive_memory")
    
    # PARALELISMO: Desde proactive_memory, bifurcamos a RAG y (condicionalmente) al Grafo
    # should_use_graph_reasoning ahora devuelve una lista de nodos destino
    workflow.add_conditional_edges(
        "proactive_memory",
        should_use_graph_reasoning
    )
    
    # El router siempre pasa al razonamiento
    workflow.add_edge("graph_router", "graph_reasoning")

    # CONVERGENCIA: Tanto RAG como Grafo alimentan al Agente
    workflow.add_edge("rag_node", "agent")
    workflow.add_edge("graph_reasoning", "agent")

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
    """
    global _knowledge_extraction_node_instance
    
    # 1. Asegurarse de que las dependencias del grafo existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get('graph_db')
    
    if not graph_db:
        logger.warning("Saltando nodo de extracción de conocimiento: GraphDB no está disponible.")
        return state

    # 2. Inicializar el nodo de extracción si es necesario (singleton)
    if _knowledge_extraction_node_instance is None:
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
    destinations = ["rag_node"] # RAG siempre se ejecuta
    
    last_message = state["messages"][-1] if state["messages"] else None
    if not isinstance(last_message, HumanMessage):
        return destinations

    user_message = extract_text_content(last_message.content)
    
    # 1. Filtro rápido de longitud
    if len(user_message.strip()) < 5:
        return destinations

    # 2. Decisión vía Fast LLM
    llm = get_fast_llm()
    if not llm:
        logger.warning("No hay LLM rápido disponible para el enrutador de grafo. Usando RAG solamente.")
        return destinations

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
            destinations.append("graph_router")
        else:
            logger.info(f"🔍 Enrutador Inteligente: Solo RAG para: '{user_message[:50]}...'")
            
    except Exception as e:
        logger.error(f"Error en la decisión inteligente del enrutador: {e}")
        # Fallback: si falla el LLM, podríamos usar el filtro de palabras clave anterior o solo RAG
        # Por seguridad, usaremos solo RAG para no bloquear el flujo
    
    return destinations

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
        # Devolver el incremento de turn_count
        return {"turn_count": state.get('turn_count', 0) + 1}

    user_content = extract_text_content(last_message.content)
    if not user_content or len(user_content.strip()) < 10:
        logger.info("Saltando memoria proactiva: contenido del usuario muy corto o vacío.")
        return {"turn_count": state.get('turn_count', 0) + 1}

    # 2. Incrementar el contador de turnos
    current_turn_count = state.get('turn_count', 0) + 1
    state['turn_count'] = current_turn_count
    logger.info(f"Contador de turnos: {current_turn_count}")

    # 3. Decidir si es momento de procesar la memoria proactiva (cada 5 turnos)
    if current_turn_count % 5 != 0:
        logger.info("Saltando memoria proactiva: no es un turno de procesamiento.")
        return {"turn_count": current_turn_count}

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

    return {"turn_count": current_turn_count}
