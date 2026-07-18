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
import json  # Importar el módulo json
import re
from pydantic import ValidationError

# --- Langchain Core ---
# from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import update
from langchain_core.messages import ToolMessage

# --- LiteLLM Optimization ---
try:
    import litellm

    litellm.set_verbose = False
    litellm.suppress_debug_info = True
    # Desactivar logs ruidosos de proveedores
    logging.getLogger("litellm").setLevel(logging.WARNING)
    from litellm.exceptions import (
        MidStreamFallbackError as _LiteLLMMidStreamFallbackError,
    )
except ImportError:
    _LiteLLMMidStreamFallbackError = None

try:
    from litellm.exceptions import APIError as _LiteLLMAPIError
except ImportError:
    _LiteLLMAPIError = None

# langchain.agents no se usa en esta versión
# Las funcionalidades se han movido a langgraph o langchain_core


# --- Módulos del Proyecto ---
from core.tools import get_all_langchain_tools
from core.memory_manager import (
    get_user_profile,
    add_memory_to_vector_db,
    get_relevant_memories,
    get_document_chunks,
)
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession

# from utils.helpers import sanitize_html
from core.config import settings
from core.citation_models import (
    ToolOutputWithSources,
    Source,
    SourceType,
    format_context_with_sources,
)
from core.llm_manager import (
    get_main_llm,
    get_fast_llm,
    get_llm_for_user,
)
from core.prompts import SUMMARIZATION_PROMPT, THREAD_TITLE_PROMPT
from core.enhanced_memory_manager import EnhancedMemoryManager
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_reasoning_node import GraphReasoningNode  # NUEVO
from core.skill_manager import get_skill_manager

# --- Claves para estado temporal ---

# from skills.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select

from core.websocket_manager import (
    send_personal_message,
)  # Importar aquí para evitar circular imports
from utils.postgres_chat_history import (
    close_postgres_chat_message_history,
    get_postgres_history_connection_url,
)

THREAD_TITLE_UPDATE_SEMAPHORE = asyncio.Semaphore(
    settings.thread_title_update_concurrency
)

# Semáforo para limitar la concurrencia de herramientas paralelas.
# Evita saturar APIs externas cuando el LLM solicita muchas tools a la vez.
MAX_PARALLEL_TOOLS = getattr(settings, "max_parallel_tools", 5)
_TOOL_EXECUTION_SEMAPHORE = asyncio.Semaphore(MAX_PARALLEL_TOOLS)


def is_multimodal_model(model_name: Optional[str]) -> bool:
    """
    Determina si un modelo es multimodal (soporta visión) según su nombre.
    """
    if not model_name:
        return False
    model_name_lower = model_name.lower()
    multimodal_indicators = [
        "gemini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4-vision",
        "claude-3",
        "claude-3-5",
        "vision",
        "pixtral",
        "llava",
        "bakllava",
        "nova-canvas",
        "nova-pro",
        "nova-lite",
        "qwen-vl",
        "qwen2.5-vl",
        "qwen-2.5-vl",
        "qwen-2-vl",
        "-vl",
        "deepseek-vl",
        "step-",
    ]
    return any(indicator in model_name_lower for indicator in multimodal_indicators)


def normalize_image_url(url_or_base64: Optional[str]) -> str:
    """
    Normaliza URLs de imagen y datos Base64 asegurando el esquema data: URI correcto
    para evitar errores de formato en proveedores LLM multimodal y LiteLLM.
    """
    if not url_or_base64:
        return ""
    url_str = str(url_or_base64).strip()
    if not url_str:
        return ""
    if url_str.startswith("http://") or url_str.startswith("https://") or url_str.startswith("data:"):
        return url_str
    if url_str.startswith("iVBORw0KGgo"):
        mime = "image/png"
    elif url_str.startswith("/9j/"):
        mime = "image/jpeg"
    elif url_str.startswith("R0lGOD"):
        mime = "image/gif"
    elif url_str.startswith("UklGR"):
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{url_str}"
    return f"data:{mime};base64,{url_str}"


from core.tool_call_parser import parse_tool_calls_from_text

_graph_db_instance = None
_enhanced_memory_manager_instance = None

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
                    password=str(settings.neo4j_password),
                )
                _graph_db_instance.connect()
                logger.info("✅ Shared GraphDB instance created and connected.")

            if not _enhanced_memory_manager_instance:
                _enhanced_memory_manager_instance = EnhancedMemoryManager(
                    graph_db=_graph_db_instance
                )
                logger.info("✅ Shared EnhancedMemoryManager instance created.")

            return _graph_db_instance, _enhanced_memory_manager_instance
        else:
            logger.warning(
                "⚠️ Missing Neo4j credentials, graph-based enhanced memory will not be available."
            )
            return None, None
    except Exception as e:
        logger.error(
            f"❌ Error initializing shared graph dependencies: {e}", exc_info=True
        )
        return None, None


def sanitize_json_content(content):
    """
    Sanitiza el contenido de un mensaje para eliminar caracteres Unicode inválidos
    que puedan causar problemas al serializar a JSON en PostgreSQL.
    """
    if isinstance(content, str):
        # Remover caracteres de control (0x00-0x1F) excepto tab (\t), newline (\n), carriage return (\r)
        sanitized = "".join(
            char for char in content if ord(char) >= 32 or char in "\t\n\r"
        )
        return sanitized
    elif isinstance(content, dict):
        sanitized_dict = {}
        for key, value in content.items():
            if isinstance(value, str):
                sanitized_dict[key] = "".join(
                    char for char in value if ord(char) >= 32 or char in "\t\n\r"
                )
            elif isinstance(value, list):
                sanitized_dict[key] = sanitize_json_content(value)
            elif isinstance(value, dict):
                sanitized_dict[key] = sanitize_json_content(value)
            else:
                sanitized_dict[key] = value
        return sanitized_dict
    elif isinstance(content, list):
        # Si es una lista (contenido multimodal), sanitizar cada elemento
        sanitized_list = []
        for item in content:
            if isinstance(item, dict):
                sanitized_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        sanitized_item[key] = "".join(
                            char
                            for char in value
                            if ord(char) >= 32 or char in "\t\n\r"
                        )
                    elif isinstance(value, list):
                        sanitized_item[key] = sanitize_json_content(value)
                    elif isinstance(value, dict):
                        sanitized_item[key] = sanitize_json_content(value)
                    else:
                        sanitized_item[key] = value
                sanitized_list.append(sanitized_item)
            elif isinstance(item, str):
                sanitized_list.append(
                    "".join(
                        char for char in item if ord(char) >= 32 or char in "\t\n\r"
                    )
                )
            elif isinstance(item, list):
                sanitized_list.append(sanitize_json_content(item))
            elif isinstance(item, dict):
                sanitized_list.append(sanitize_json_content(item))
            else:
                sanitized_list.append(item)
        return sanitized_list
    else:
        return content


# --- Configuración del Logger ---
from core.utils.logging_utils import AgentLogger

logger = AgentLogger(__name__)


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


def _get_context_item_display_name(item: Dict[str, Any]) -> str:
    return str(
        item.get("file_name")
        or item.get("name")
        or item.get("title")
        or item.get("id")
        or "sin-nombre"
    )


# ==============================================================================
# SECCIÓN 2: VALIDACIÓN DE HERRAMIENTAS Y MANEJO DE ERRORES
# ==============================================================================


def format_validation_error_for_llm(
    error: ValidationError, tool_name: str, tool_args: dict
) -> str:
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
        field = err.get("loc", ["unknown"])[0]
        error_type = err.get("type", "unknown")

        if error_type == "missing":
            error_messages.append(f"- Falta el parámetro requerido '{field}'")
        elif error_type == "string_type":
            error_messages.append(
                f"- El parámetro '{field}' debe ser una cadena de texto (string)"
            )
        elif error_type == "int_parsing":
            error_messages.append(f"- El parámetro '{field}' debe ser un número entero")
        else:
            error_messages.append(
                f"- Error en '{field}': {err.get('msg', 'error desconocido')}"
            )

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


def should_stop_retrying_tool(
    tool_name: str, error_counts: Optional[Dict[str, int]], max_retries: int = 3
) -> tuple[bool, str]:
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
    account_id: str,  # Añadir account_id para add_memory_to_vector_db
    workspace_id: Optional[
        str
    ] = None,  # Añadir workspace_id para add_memory_to_vector_db
):
    """
    Resume mensajes en segundo plano y añade un resumen al historial, pero NO borra los mensajes previos.
    El resumen se usará solo para el contexto del LLM, pero el historial completo se conserva para el frontend.
    """
    llm_for_summary = await get_llm_for_user(account_id, purpose="fast")
    if not llm_for_summary:
        logger.warning("⚠️ No hay LLM disponible para la sumarización en segundo plano.")
        return

    logger.info(
        f"Tarea en segundo plano: Resumiendo {len(history_to_summarize)} mensajes..."
    )
    try:
        summarization_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=SUMMARIZATION_PROMPT),
                MessagesPlaceholder(variable_name="history"),
            ]
        )
        summarization_chain = summarization_prompt | llm_for_summary
        messages_for_summarization_input = [
            msg
            for msg in history_to_summarize
            if not (
                hasattr(msg, "additional_kwargs")
                and msg.additional_kwargs.get("role") == "summary"
            )
        ]
        if not messages_for_summarization_input:
            return
        summary_response = await summarization_chain.ainvoke(
            {"history": messages_for_summarization_input}
        )
        summary_content = str(summary_response)
        summary_message = HumanMessage(
            content=f"Resumen de la conversación anterior: {summary_content}",
            additional_kwargs={"role": "summary"},
        )
        # Guardar el resumen como un mensaje más, sin borrar el historial
        sanitized_summary_message = HumanMessage(
            content=sanitize_json_content(summary_message.content),
            additional_kwargs=summary_message.additional_kwargs,
        )
        await chat_message_history.aadd_messages([sanitized_summary_message])
        logger.info(
            "✅ Sumarización en segundo plano completada y resumen añadido al historial."
        )

        # --- MODIFICACIÓN: Guardar resumen en memoria vectorial con workspace_id ---
        await add_memory_to_vector_db(
            account_id=account_id,
            content=summary_content,
            type="thread_summary",
            workspace_id=workspace_id,  # Pasar workspace_id
        )
        logger.info(
            f"✅ Resumen del hilo guardado en memoria vectorial como 'thread_summary' para workspace {workspace_id}."
        )

    except Exception as e:
        logger.error(f"❌ Error en la tarea de sumarización: {e}", exc_info=True)


def extract_text_content(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
    return str(content)


async def _load_thread_history_messages(thread_id: str) -> Optional[list]:
    connection_url = get_postgres_history_connection_url(
        settings.database_url or os.getenv("DATABASE_URL")
    )
    if not connection_url:
        logger.error("DATABASE_URL no esta configurada para el historial de chat.")
        return None

    for attempt in range(3):
        chat_message_history = None
        try:
            chat_message_history = PostgresChatMessageHistory(
                connection_string=connection_url,
                session_id=thread_id,
                table_name="langchain_chat_history",
            )
            return await chat_message_history.aget_messages()
        except Exception as e:
            error_msg = str(e)
            logger.warning(
                f"⚠️ Intento {attempt + 1} fallido al conectar con el historial para título del hilo {thread_id}: {error_msg}"
            )

            if "object has no attribute 'cursor'" in error_msg:
                logger.error(
                    "❌ Error de inicialización en PostgresChatMessageHistory (posible fallo de conexión a DB)"
                )

            if attempt == 2:
                logger.error(
                    f"❌ No se pudo conectar con el historial del hilo {thread_id} tras 3 intentos: {error_msg}"
                )
                return None

            await asyncio.sleep(attempt + 1)
        finally:
            close_postgres_chat_message_history(chat_message_history, logger=logger)

    return None


async def update_thread_title_if_needed(thread_id: str, messages: list):
    """
    Genera o actualiza el título del hilo usando el LLM de tareas rápidas.
    Si el hilo tiene de título 'Nuevo Chat' y al menos 5 mensajes, lo asigna.
    Si ya tiene título distinto y hay 20+ mensajes, lo actualiza.
    """
    if not messages:
        logger.info(
            f"[TÍTULO] No hay mensajes para el hilo {thread_id}, no se genera título."
        )
        return
    # Obtener el título actual
    async with DBSession(SessionLocal) as db:
        thread = await db.get(ChatThread, uuid.UUID(thread_id))
        current_title = thread.title if thread else None
        account_id = str(thread.account_id) if thread else None
    # Log extra para depuración
    logger.info(
        f"[TÍTULO][DEBUG] Hilo {thread_id} - Título actual: '{current_title}' - Mensajes reales (sin resumen): {len(messages)}"
    )
    # Si el título es 'Nuevo Chat' y hay al menos 5 mensajes, o si hay 20+ mensajes y el título es distinto
    if (current_title == "Nuevo Chat" and len(messages) >= 5) or (
        current_title != "Nuevo Chat"
        and len(messages) >= 20
        and len(messages) % 20 == 0
    ):
        conversation_text = "\n".join(
            [
                extract_text_content(m.content) if hasattr(m, "content") else str(m)
                for m in messages[-20:]
            ]
        )
        prompt = THREAD_TITLE_PROMPT.format(conversation_text=conversation_text)
        llm = (
            await get_llm_for_user(account_id, purpose="fast")
            if account_id
            else (get_fast_llm() or get_main_llm())
        )
        if not llm:
            logger.warning(
                f"[TÍTULO] No hay LLM disponible para generar título del hilo {thread_id}."
            )
            return
        try:
            logger.info(
                f"[TÍTULO] Solicitando título para hilo {thread_id} con {len(messages)} mensajes..."
            )
            response = await llm.ainvoke(prompt)
            new_title = (
                str(response.content).strip()
                if hasattr(response, "content")
                else str(response).strip()
            )

            # Limpieza y truncamiento de seguridad
            new_title = new_title.strip('"').strip("'")
            if len(new_title) > 100:
                new_title = new_title[:97] + "..."

            logger.info(f"[TÍTULO] Título generado para hilo {thread_id}.")
            async with DBSession(SessionLocal) as db:
                await db.execute(
                    update(ChatThread)
                    .where(ChatThread.id == uuid.UUID(thread_id))
                    .values(title=new_title)
                )
                await db.commit()  # FIX: commit para que el cambio se persista

            # FIX: enviar notificación WebSocket para que el sidebar se actualice en tiempo real
            if account_id:
                try:
                    await send_personal_message(
                        account_id,
                        {
                            "type": "thread_title_updated",
                            "thread_id": thread_id,
                            "new_title": new_title,
                        },
                    )
                    logger.info(
                        f"📡 [TÍTULO] Notificación WebSocket enviada para hilo {thread_id}"
                    )
                except Exception as ws_err:
                    logger.warning(
                        f"[TÍTULO] No se pudo enviar notificación WebSocket para el hilo {thread_id}: {ws_err}"
                    )
        except Exception as e:
            logger.error(
                f"[TÍTULO] Error actualizando título del hilo {thread_id}: {e}"
            )
    else:
        logger.info(
            f"[TÍTULO] El hilo {thread_id} no cumple condiciones para actualizar título."
        )


async def force_update_thread_title(thread_id: str):
    """
    Fuerza la actualización del título de un hilo de chat específico.
    """
    async with DBSession(SessionLocal) as db:
        thread = await db.get(ChatThread, uuid.UUID(thread_id))
        if not thread:
            logger.error(
                f"No se encontró el hilo {thread_id} para forzar la actualización del título."
            )
            return
        account_id = str(thread.account_id)
    messages = await _load_thread_history_messages(thread_id)
    if messages is None:
        return
    if not messages:
        logger.info(f"No hay mensajes en el hilo {thread_id} para generar un título.")
        return

    conversation_text = "\n".join(
        [
            extract_text_content(m.content) if hasattr(m, "content") else str(m)
            for m in messages[-20:]
        ]
    )
    prompt = THREAD_TITLE_PROMPT.format(conversation_text=conversation_text)
    llm = await get_llm_for_user(account_id, purpose="fast")
    if not llm:
        logger.warning(
            f"No hay LLM disponible para generar título del hilo {thread_id}."
        )
        return

    try:
        logger.info(f"Forzando la generación de título para el hilo {thread_id}...")
        response = await llm.ainvoke(prompt)
        new_title = (
            str(response.content).strip()
            if hasattr(response, "content")
            else str(response).strip()
        )

        new_title = new_title.strip('"').strip("'")
        if len(new_title) > 100:
            new_title = new_title[:97] + "..."

        logger.info(f"Nuevo título generado para el hilo {thread_id}.")

        async with DBSession(SessionLocal) as db:
            await db.execute(
                update(ChatThread)
                .where(ChatThread.id == uuid.UUID(thread_id))
                .values(title=new_title)
            )
            await db.commit()

        try:
            await send_personal_message(
                account_id,
                {
                    "type": "thread_title_updated",
                    "thread_id": thread_id,
                    "new_title": new_title,
                },
            )
            logger.info(
                f"📡 Notificación WebSocket enviada para actualización de título del hilo {thread_id}"
            )
        except Exception as e:
            logger.warning(
                f"No se pudo enviar notificación WebSocket para el hilo {thread_id}: {e}"
            )
    except Exception as e:
        logger.error(
            f"Error al forzar la actualización del título del hilo {thread_id}: {e}"
        )


async def force_update_all_thread_titles(account_id: str):
    """
    Fuerza la actualización de títulos de todos los hilos de chat para una cuenta específica.
    """
    logger.info(
        f"Forzando actualización de títulos de todos los hilos para la cuenta {account_id}..."
    )
    async with DBSession(SessionLocal) as db:
        # Seleccionar solo los hilos de la cuenta especificada
        threads = (
            (
                await db.execute(
                    select(ChatThread).where(
                        ChatThread.account_id == uuid.UUID(account_id)
                    )
                )
            )
            .scalars()
            .all()
        )

        if not threads:
            logger.info(f"No se encontraron hilos para la cuenta {account_id}.")
            return

    thread_ids = [str(thread.id) for thread in threads]
    logger.info(
        f"Actualizando {len(thread_ids)} hilos con concurrencia maxima de {settings.thread_title_update_concurrency}."
    )

    async def _force_update_with_limit(thread_id: str):
        async with THREAD_TITLE_UPDATE_SEMAPHORE:
            try:
                await force_update_thread_title(thread_id)
                return True
            except Exception as e:
                logger.error(
                    f"Error inesperado al actualizar el titulo del hilo {thread_id}: {e}",
                    exc_info=True,
                )
                return False

    results = await asyncio.gather(
        *[_force_update_with_limit(thread_id) for thread_id in thread_ids],
        return_exceptions=False,
    )
    processed_count = sum(1 for result in results if result)

    logger.info(
        f"Actualización de títulos completada para la cuenta {account_id}. Hilos procesados: {processed_count}/{len(thread_ids)}."
    )


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


async def get_or_create_heartbeat_thread(account_id: str) -> str:
    """
    Retorna el ID del hilo de heartbeat personalizado para la cuenta dada.
    Si ya existe un hilo con platform='heartbeat', lo reutiliza.
    De lo contrario, crea uno nuevo marcado con platform='heartbeat'.
    Esto evita acumular múltiples chats idénticos en el sidebar.
    """
    account_uuid = uuid.UUID(account_id)
    async with DBSession(SessionLocal) as db:
        existing_stmt = (
            select(ChatThread)
            .where(
                ChatThread.account_id == account_uuid,
                ChatThread.platform == "heartbeat",
            )
            .order_by(ChatThread.created_at.asc())
            .limit(1)
        )
        result = await db.execute(existing_stmt)
        existing = result.scalars().first()
        if existing:
            return str(existing.id)

        new_thread = ChatThread(
            account_id=account_uuid,
            title="Heartbeat Personalizado",
            platform="heartbeat",
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return str(new_thread.id)


async def get_or_create_specific_heartbeat_thread(
    account_id: str, heartbeat_id: str, heartbeat_name: str
) -> str:
    """
    Retorna el ID del hilo de heartbeat específico para la cuenta y heartbeat dados.
    """
    account_uuid = uuid.UUID(account_id)
    async with DBSession(SessionLocal) as db:
        existing_stmt = (
            select(ChatThread)
            .where(
                ChatThread.account_id == account_uuid,
                ChatThread.platform == f"heartbeat_{heartbeat_id}",
            )
            .order_by(ChatThread.created_at.asc())
            .limit(1)
        )
        result = await db.execute(existing_stmt)
        existing = result.scalars().first()
        if existing:
            return str(existing.id)

        new_thread = ChatThread(
            account_id=account_uuid,
            title=f"Heartbeat - {heartbeat_name}",
            platform=f"heartbeat_{heartbeat_id}",
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return str(new_thread.id)


# ==============================================================================
# SECCIÓN 4: AGENTE LANGGRAPH REFACTORIZADO
# ==============================================================================

from langgraph.graph import StateGraph, END

# --- 1. Nodos del Grafo ---


async def call_model_node(state: AgentState):
    """
    Nodo principal que invoca al LLM para decidir el siguiente paso (herramienta o respuesta).
    """
    logger.debug(
        f"--- (Grafo) Nodo: Llama al Modelo para cuenta {state['account_id']} ---"
    )
    logger.debug(
        f"DEBUG (call_model_node): account_id={state.get('account_id')}, telegram_id={state.get('telegram_id')}, workspace_id={state.get('workspace_id')}"
    )

    # --- TURN COUNT LOGIC REMOVED FROM HERE (Now handled in proactive_memory_node) ---
    # turn_count is now calculated based on history to ensure persistence

    # --- FIX: Sanitize messages from history to ensure tool_call_ids and names are present ---
    # This prevents crashes if the DB contains messages with null IDs or empty names from previous bugs
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage):
            # Usar getattr para acceder de forma segura a tool_call_id y name
            if not getattr(msg, "tool_call_id", None):
                logger.warning(
                    f"Found ToolMessage with missing tool_call_id in history. Patching with random UUID."
                )
                msg.tool_call_id = str(uuid.uuid4())  # type: ignore
            if not getattr(msg, "name", None):
                logger.warning(
                    f"Found ToolMessage with missing/empty name in history. Patching with 'unknown_tool'."
                )
                msg.name = "unknown_tool"  # type: ignore

        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if not tc.get("id"):
                    logger.warning(
                        f"Found AIMessage tool_call with missing id in history. Patching with random UUID."
                    )
                    tc["id"] = str(uuid.uuid4())
                if not tc.get("name"):
                    logger.warning(
                        f"Found AIMessage tool_call with missing/empty name in history. Patching with 'unknown_tool'."
                    )
                    tc["name"] = "unknown_tool"
    # --- END FIX ---

    # Definir last_message al inicio para evitar NameError
    last_message = state["messages"][-1] if state["messages"] else None
    # Obtener context y rag_context del state para usarlos en todo el nodo
    context = state.get("context")
    rag_context = state.get("rag_context")

    workspace_name = None
    workspace_prompt = None
    if state.get("workspace_id"):
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(state.get("workspace_id")))
            if workspace:
                workspace_name = workspace.name
                if workspace.system_prompt:
                    workspace_prompt = str(workspace.system_prompt)

    # 1. Construir el prompt del sistema dinámicamente y cargar metadatos en paralelo
    user_message = extract_text_content(state["messages"][-1].content)

    # Construir un query context-aware combinando el último mensaje y los últimos mensajes humanos
    # Esto evita que las herramientas desaparezcan en turnos de confirmación (ej: "sí, hazlo")
    tool_query_parts = []
    if state.get("messages"):
        last_msg_text = extract_text_content(state["messages"][-1].content)
        if last_msg_text.strip():
            tool_query_parts.append(last_msg_text)
    
    human_messages = [msg for msg in state.get("messages", []) if isinstance(msg, HumanMessage)]
    for hm in human_messages[-3:]:
        hm_text = extract_text_content(hm.content)
        if hm_text.strip() and hm_text not in tool_query_parts:
            tool_query_parts.append(hm_text)
            
    tool_query = " ".join(tool_query_parts)

    logger.info(
        f"🚀 Cargando metadatos del agente en paralelo para cuenta {state['account_id']}..."
    )

    # Preparamos las tareas
    user_profile_task = get_user_profile(state["account_id"])
    tools_task = get_all_langchain_tools(
        account_id=state["account_id"],
        telegram_id=state.get("telegram_id"),
        thread_id=state["thread_id"],
        workspace_id=state.get("workspace_id"),
        query=tool_query,
    )
    llm_preview_task = get_llm_for_user(state["account_id"], purpose="main")

    # Semantic skill search (async)
    skill_manager = get_skill_manager()
    semantic_skills_task = skill_manager.search_skills_semantic(
        tool_query,
        top_k=4,
        account_id=state["account_id"],
        workspace_name=workspace_name,
    )

    # Ejecutar todas en paralelo
    metadata_results = await asyncio.gather(
        user_profile_task,
        tools_task,
        llm_preview_task,
        semantic_skills_task,
        return_exceptions=True,
    )

    user_profile = (
        metadata_results[0] if not isinstance(metadata_results[0], Exception) else None
    )
    tools_result = metadata_results[1]
    if isinstance(tools_result, Exception) or tools_result is None:
        logger.error(f"Error cargando herramientas: {tools_result}")
        full_toolbox = []
    else:
        full_toolbox = tools_result
    _llm_preview = (
        metadata_results[2] if not isinstance(metadata_results[2], Exception) else None
    )
    relevant_skills = (
        metadata_results[3] if not isinstance(metadata_results[3], Exception) else []
    )
    if isinstance(metadata_results[0], Exception):
        logger.error(f"Error cargando perfil: {metadata_results[0]}")
    if isinstance(metadata_results[2], Exception):
        logger.error(f"Error cargando LLM preview: {metadata_results[2]}")
    if isinstance(metadata_results[3], Exception):
        logger.error(f"Error en búsqueda semántica de skills: {metadata_results[3]}")

    document_ids_for_rag = None
    document_names_for_rag = None  # Nuevo
    filter_topics = None
    has_explicit_rag_context = False

    if rag_context:
        logger.info(
            f"Aplicando RAG explícito con {len(rag_context)} item(s) de contexto. Se priorizará la búsqueda en estos documentos."
        )
        document_ids_for_rag = [
            item["id"] for item in rag_context if item.get("type") == "document"
        ]
        document_names_for_rag = [
            _get_context_item_display_name(item)
            for item in rag_context
            if item.get("type") == "document"
        ]

        # Extraer topics si hay colecciones pasadas directamente en el rag_context
        collection_topics = [
            item.get("topic") or item.get("name")
            for item in rag_context
            if item.get("type") == "collection"
        ]
        if collection_topics:
            filter_topics = collection_topics
            logger.info(
                f"Filtro de colección (topics) extraídos desde rag_context: {filter_topics}"
            )
            if not document_names_for_rag:
                document_names_for_rag = []
            document_names_for_rag.extend(collection_topics)

        has_explicit_rag_context = True

    # Soporte para contexto de colección (legacy mode)
    if context and context.get("type") == "collection":
        topic = context.get("id")
        if topic:
            logger.info(f"Aplicando filtro de colección RAG para el tema: {topic}")
            if not filter_topics:
                filter_topics = [topic]
            elif topic not in filter_topics:
                filter_topics.append(topic)
            has_explicit_rag_context = True
            # Si no hay nombres de documentos explícitos, usamos el nombre de la colección
            if not document_names_for_rag:
                document_names_for_rag = [
                    context.get("snapshot", {}).get("name", topic)
                ]
    # --- CONSOLIDACIÓN Y RE-INDEXACIÓN DE FUENTES PARA EL LLM ---
    # Combinar fuentes de todas las ramas (RAG, Proactive, Graph), asegurando IDs secuenciales desde 1
    # PRIORIDAD DE ORDEN: 1. Tool/Proactive Sources (RAG), 2. Graph Sources, 3. RAG Context (como fallback)
    all_sources_for_llm: List[Source] = []
    final_sources_for_state = []
    seen_source_identifiers = set()
    documents_with_content = set()  # Track docs that already have at least one chunk

    def get_source_identifier(s: Dict[str, Any]) -> str:
        s_type = s.get("type", "web")
        if hasattr(s_type, "value"):
            s_type = s_type.value
        s_type = str(s_type)

        s_url = s.get("url") or s.get("id") or ""
        s_url = str(s_url)

        s_snippet = s.get("snippet", "")
        # Usar un hash del snippet para permitir múltiples fragmentos del mismo documento
        import hashlib

        snippet_hash = (
            hashlib.md5(s_snippet.strip().encode()).hexdigest()[:8]
            if s_snippet.strip()
            else "empty"
        )
        return f"{s_type}:{s_url}:{snippet_hash}"

    # OPTIMIZACIÓN: Identificar el último HumanMessage escaneando desde el final con límite
    # En historiales largos, solo necesitamos los últimos ~10 mensajes para detectar el turno actual
    last_human_idx = -1
    current_turn_tool_source_idents = set()
    if state.get("messages"):
        # Limitar escaneo a últimos 20 mensajes para evitar O(N) en historiales largos
        scan_start = max(0, len(state["messages"]) - 20)
        messages_subset = state["messages"][scan_start:]
        for idx in range(len(messages_subset) - 1, -1, -1):
            if isinstance(messages_subset[idx], HumanMessage):
                last_human_idx = scan_start + idx
                break

    # Recopilar identificadores de fuentes SOLO del turno actual (últimos N mensajes)
    if last_human_idx != -1:
        messages_to_scan = state["messages"][last_human_idx + 1:]
    else:
        # Si no hay human messages recientes, limitar a últimos 10 mensajes
        messages_to_scan = state["messages"][-10:] if len(state["messages"]) > 10 else state.get("messages", [])

    for msg in messages_to_scan:
        if isinstance(msg, ToolMessage):
            t_sources = msg.additional_kwargs.get("sources") or []
            for ts in t_sources:
                ts_dict = (
                    ts.dict()
                    if hasattr(ts, "dict")
                    else (ts.model_dump() if hasattr(ts, "model_dump") else ts)
                )
                current_turn_tool_source_idents.add(get_source_identifier(ts_dict))

    raw_sources = []

    # 1. Procesar Fuentes de RAG General y Herramientas (vienen en state['sources'])
    # PRIORIDAD ALTA: Estos son resultados directos de herramientas activadas por el usuario o el agente.
    # Filtrados para incluir únicamente fuentes del turno actual (evitando referencias antiguas/acumuladas)
    if state.get("sources"):
        for s in state["sources"]:
            ident = get_source_identifier(s)
            if ident in current_turn_tool_source_idents:
                if ident not in seen_source_identifiers:
                    raw_sources.append(s)
                    seen_source_identifiers.add(ident)
                    # Marcar documento como "con contenido"
                    if (
                        s.get("type") == "document"
                        or s.get("type") == SourceType.DOCUMENT
                    ):
                        doc_id = s.get("url") or s.get("id")
                        if doc_id:
                            documents_with_content.add(str(doc_id))
            else:
                logger.debug(
                    f"[Consolidación Fuentes] Ignorando fuente acumulada de turnos previos: {ident}"
                )

    # 2. Procesar Fuentes de Grafo (vienen en state['graph_sources'])
    # PRIORIDAD MEDIA: Contexto relacional del grafo
    if state.get("graph_sources"):
        for s in state["graph_sources"]:
            ident = get_source_identifier(s)
            if ident not in seen_source_identifiers:
                raw_sources.append(s)
                seen_source_identifiers.add(ident)
                # Marcar documento como "con contenido" si es un documento
                if s.get("type") == "document" or s.get("type") == SourceType.DOCUMENT:
                    doc_id = s.get("url") or s.get("id")
                    if doc_id:
                        documents_with_content.add(str(doc_id))

    # 3. Procesar RAG Context (Documentos adjuntos explícitamente por el usuario)
    # SOLO los añadimos si no hemos encontrado ya contenido real para ellos
    if state.get("rag_context"):
        for item in state["rag_context"]:
            doc_id = str(item.get("id"))
            if doc_id in documents_with_content:
                continue  # Ya tenemos fragmentos reales de este documento, no añadir la entrada vacía

            # Normalizar para que parezca una fuente citable (como fallback sin snippet)
            normalized = {
                "id": item.get("id"),
                "title": item.get("name") or item.get("title") or "Documento Adjunto",
                "url": item.get("url")
                or item.get("id")
                or f"document://{item.get('id')}",
                "snippet": item.get("content")
                or item.get("snippet")
                or "",  # Estará vacío probablemente
                "type": item.get("type", "document"),
                "metadata": item.get("metadata", {}),
            }
            ident = get_source_identifier(normalized)
            if ident not in seen_source_identifiers:
                raw_sources.append(normalized)
                seen_source_identifiers.add(ident)
    # 2. Procesar y re-indexar secuencialmente para que el LLM use [1], [2], [3]...
    for i, s_dict in enumerate(raw_sources, start=1):
        try:
            # Asegurar que s_dict es un diccionario de datos
            if hasattr(s_dict, "dict"):
                s_dict = s_dict.dict()
            elif hasattr(s_dict, "model_dump"):
                s_dict = s_dict.model_dump()

            # Crear una copia para no modificar el original en el historial si es compartido
            s_dict_copy = s_dict.copy()
            # ASIGNAR EL NUEVO ID SECUENCIAL
            s_dict_copy["id"] = i

            # Crear objeto Source para el formateador
            source_obj = Source(**s_dict_copy)
            all_sources_for_llm.append(source_obj)
            final_sources_for_state.append(s_dict_copy)
        except Exception as e:
            logger.error(f"Error procesando fuente {i} para LLM: {e}")

    # 2.5. Actualizar los mensajes de tipo ToolMessage en el historial para que usen los IDs consolidados
    try:
        # Construir mapa de búsqueda por identificador de fuente
        consolidated_source_by_ident = {}
        for source_obj in all_sources_for_llm:
            s_dict = (
                source_obj.dict()
                if hasattr(source_obj, "dict")
                else source_obj.model_dump()
            )
            ident = get_source_identifier(s_dict)
            consolidated_source_by_ident[ident] = source_obj

        # OPTIMIZACIÓN: Solo procesar ToolMessages del turno actual (últimos 20 mensajes)
        # Evita O(N) en historiales largos donde los IDs anteriores ya están consolidados
        if state.get("messages"):
            messages_to_update = state["messages"][-20:] if len(state["messages"]) > 20 else state["messages"]
            for msg in messages_to_update:
                if isinstance(msg, ToolMessage):
                    tool_sources = msg.additional_kwargs.get("sources")
                    if tool_sources and isinstance(tool_sources, list):
                        updated_tool_sources = []
                        id_replacement_map = {}

                        for ts in tool_sources:
                            ts_dict = (
                                ts.dict()
                                if hasattr(ts, "dict")
                                else (
                                    ts.model_dump() if hasattr(ts, "model_dump") else ts
                                )
                            )
                            ident = get_source_identifier(ts_dict)
                            local_id = ts_dict.get("id")

                            if ident in consolidated_source_by_ident:
                                new_source_obj = consolidated_source_by_ident[ident]
                                updated_tool_sources.append(new_source_obj)
                                if local_id is not None:
                                    id_replacement_map[local_id] = new_source_obj.id
                                    logger.debug(
                                        f"[Consolidación Fuentes] Alineando ID de fuente: {ident} | Local ID: {local_id} -> Nuevo ID: {new_source_obj.id}"
                                    )
                            else:
                                logger.debug(
                                    f"Source {ident} in ToolMessage not found in consolidated list, leaving as is."
                                )
                                try:
                                    if isinstance(ts, dict):
                                        updated_tool_sources.append(Source(**ts))
                                    else:
                                        updated_tool_sources.append(ts)
                                except Exception as parse_err:
                                    logger.error(
                                        f"Error fallback parsing source: {parse_err}"
                                    )
                                    updated_tool_sources.append(ts)

                        # Guardar las fuentes actualizadas
                        msg.additional_kwargs["sources"] = [
                            s.dict()
                            if hasattr(s, "dict")
                            else s.model_dump()
                            if hasattr(s, "model_dump")
                            else s
                            for s in updated_tool_sources
                        ]

                        # Actualizar texto del ToolMessage con los nuevos IDs
                        content_str = msg.content
                        if isinstance(content_str, str) and id_replacement_map:
                            # Ordenar viejos IDs de forma descendente para evitar colisiones parciales (ej: 10 vs 1)
                            sorted_old_ids = sorted(
                                id_replacement_map.keys(),
                                key=lambda x: int(x) if str(x).isdigit() else 0,
                                reverse=True,
                            )
                            for old_id in sorted_old_ids:
                                new_id = id_replacement_map[old_id]
                                content_str = content_str.replace(
                                    f"[{old_id}]", f"[{new_id}]"
                                )
                                content_str = content_str.replace(
                                    f"Contexto [{old_id}]", f"Contexto [{new_id}]"
                                )
                            msg.content = content_str
    except Exception as update_err:
        logger.error(
            f"Error actualizando ToolMessages con IDs consolidados: {update_err}",
            exc_info=True,
        )

    # 3. Generar el contexto formateado con los nuevos IDs [1], [2], ...
    if all_sources_for_llm:
        relevant_memories_text = format_context_with_sources(all_sources_for_llm)
        logger.info(
            f"Consolidadas {len(all_sources_for_llm)} fuentes totales para el LLM (RAG + Grafo) con IDs secuenciales 1-{len(all_sources_for_llm)}."
        )
    else:
        relevant_memories_text = "No se encontraron memorias o documentos relevantes en la base de conocimiento ni en el grafo."

    from core.prompt_manager import PromptManager

    prompt_manager = PromptManager(
        settings={"default_system_prompt": settings.default_system_prompt}
    )

    # Detectar si el modelo es Ollama para aplicar límites de contexto reducidos
    # (esto se hace antes de filter_relevant_tools para conocer el límite correcto)
    _is_ollama_model = False
    if _llm_preview is not None:
        from core.ollama_direct import OllamaDirectChatModel

        _is_ollama_model = isinstance(_llm_preview, OllamaDirectChatModel)

    _tool_limit = 6 if _is_ollama_model else 12

    # DINÁMICO: Filtramos solo las herramientas relevantes para esta consulta específica
    # Esto evita enviar 50+ herramientas al LLM, ahorrando tokens y mejorando la estabilidad.
    # CARGA COMPLETA: El usuario prefiere no usar filtrado dinámico para máxima efectividad.
    tools = full_toolbox
    logger.info(
        f"🧰 Selección dinámica: {len(tools)} herramientas de {len(full_toolbox)} cargadas (límite={'Ollama' if _is_ollama_model else 'estándar'})."
    )

    # workspace_prompt was already loaded asynchronously at the start of call_model_node

    # --- CONFIGURACIÓN DE HERRAMIENTAS Y LLM ---
    # Reutilizamos el LLM ya obtenido arriba para la detección de Ollama
    llm = _llm_preview

    def _message_has_image_parts(message) -> bool:
        if not isinstance(getattr(message, "content", None), list):
            return False
        for part in message.content:
            if not isinstance(part, dict):
                continue
            part_type = part.get("type")
            if part_type in {"image_url", "input_image"}:
                return True
            if "image_url" in part:
                return True
        return False

    # Soporte multimodal (visión) si hay imágenes en el último mensaje humano del estado
    latest_human_msg = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
    has_image = _message_has_image_parts(latest_human_msg) if latest_human_msg else False
    if has_image:
        main_model_name = getattr(llm, "model_name", getattr(llm, "model", ""))
        if not is_multimodal_model(main_model_name):
            logger.info(
                f"🔄 El modelo principal '{main_model_name}' no es multimodal. Activando vision_model."
            )
            llm = await get_llm_for_user(state["account_id"], purpose="vision")
        else:
            logger.info(
                f"👁️ El modelo principal '{main_model_name}' es multimodal, se utilizará directamente para procesar las imágenes."
            )


    if not llm:
        raise ValueError("El LLM no está disponible.")

    model_name = getattr(llm, "model_name", getattr(llm, "model", settings.llm_model))
    lower_model = model_name.lower()

    # ESTRATEGIA: Casi todos los modelos modernos (incluyendo :free) soportan tools nativas.
    # El usuario puede forzar el modo 'prompt_tooling' manualmente desde los ajustes.
    supports_native_tools = True
    if user_profile and user_profile.account:
        supports_native_tools = not getattr(
            user_profile.account, "use_prompt_tooling", False
        )

    # OPTIMIZACIÓN: Solo inyectamos el manual de herramientas en el prompt si el modelo NO las soporta nativamente
    # o si es un modelo muy pequeño que requiere refuerzo extremo.
    # Evitamos activarlo solo por ser OpenRouter, ya que modelos como Trinity o DeepSeek son excelentes con tools nativas.
    use_prompt_tooling_guidance = not supports_native_tools

    # REFUERZO: Si hay skills de usuario presentes, forzamos el modo prompt_tooling
    # para asegurar que tengan documentación explícita en el system prompt además de la definición nativa.
    has_user_skills = any(getattr(t, "is_user_skill", False) for t in tools)
    if has_user_skills:
        logger.info(
            "🛠️ User skills detected. Enabling prompt_tooling mode for extra guidance."
        )

    # OPTIMIZACIÓN: Construir el prompt una sola vez con toda la información consolidada
    system_prompt_content = prompt_manager.build_system_prompt(
        user_profile=user_profile,
        relevant_memories=relevant_memories_text,
        summary_string="",
        custom_prompt_from_profile=str(user_profile.system_prompt)
        if user_profile and user_profile.system_prompt
        else None,
        workspace_prompt=workspace_prompt,  # Se usa si existe
        tools=tools,
        account_id=state["account_id"],
        telegram_id=state.get("telegram_id"),
        user_message=user_message,
        has_explicit_rag_context=has_explicit_rag_context,
        explicit_document_names=[
            str(name) for name in document_names_for_rag if name is not None
        ]
        if document_names_for_rag
        else None,
        explicit_rag_context_items=rag_context,
        context=state.get("context"),  # Pasar el contexto aquí
        compact_mode=_is_ollama_model,
        mode="prompt_tooling"
        if (use_prompt_tooling_guidance or has_user_skills)
        else None,  # Usar modo documentación como refuerzo
        relevant_skills=relevant_skills,
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
                        logger.warning(
                            f"⚠️ Herramienta duplicada detectada y eliminada: '{tool_name}'"
                        )
                except Exception as e:
                    logger.error(
                        f"❌ Error al convertir herramienta '{tool.name}': {e}"
                    )

            logger.info(
                f"🔧 Vinculando {len(openai_tools)} herramientas al modelo '{model_name}'"
            )

            # Usamos .bind(tools=...) que es lo que LiteLLM espera para casi todos los proveedores
            if openai_tools:
                # --- FIX CRÍTICO PARA OPENROUTER Y MODELOS OSS ---
                # Forzamos tool_choice='auto' para OpenRouter Y para cualquier modelo que no sea nativo de OpenAI/Gemini
                # Esto soluciona el error 'No endpoints found that support tool use'
                lower_model = model_name.lower()
                is_openrouter = (
                    "openrouter" in lower_model
                    or getattr(llm, "is_openrouter_proxy", False)
                    or "openrouter.ai" in str(getattr(llm, "api_base", ""))
                )
                is_openai = "gpt-" in lower_model and not is_openrouter
                is_gemini = "gemini" in lower_model and not is_openrouter

                if is_openrouter:
                    logger.info(
                        f"🔧 Forzando tool_choice='auto' y filtrado de proveedores para OpenRouter: {model_name}"
                    )
                    # En OpenRouter, pasar tool_choice="auto" ayuda a LiteLLM a filtrar proveedores que SI soportan herramientas
                    llm_with_tools = llm.bind(tools=openai_tools, tool_choice="auto")
                elif not (is_openai or is_gemini):
                    # Para modelos OSS (Llama, DeepSeek, etc) fuera de OpenRouter también es recomendable
                    logger.info(
                        f"🔧 Aplicando tool_choice='auto' para modelo especializado: {model_name}"
                    )
                    llm_with_tools = llm.bind(tools=openai_tools, tool_choice="auto")
                else:
                    llm_with_tools = llm.bind(tools=openai_tools)
            else:
                llm_with_tools = llm

            logger.info(
                f"✅ Herramientas vinculadas correctamente al LLM '{model_name}'"
            )
        except Exception as e:
            logger.error(
                f"❌ Error crítico al vincular herramientas al LLM '{model_name}': {e}",
                exc_info=True,
            )
            llm_with_tools = llm
    else:
        logger.info(
            f"ℹ️ Usando modelo '{model_name}' SIN vinculación de herramientas nativa (Modo Prompt Tooling)"
        )
        llm_with_tools = llm

    # --- REFUERZO DE INSTRUCCIONES PARA MODELOS OSS, REASONING Y OPENROUTER ---
    # Los modelos de OpenRouter/OSS a veces ignoran el formato de herramientas si no es explícito.
    # Y los modelos de razonamiento (DeepSeek R1, etc.) a veces se detienen tras pensar sin responder.
    final_system_content = system_prompt_content
    model_lower = model_name.lower()

    if "gemini" not in model_lower:
        is_oss = any(
            x in model_lower
            for x in ["oss", "llama", "mistral", "mixtral", "deepseek", "qwen", "phi"]
        )
        is_openrouter = (
            "openrouter" in model_lower
            or getattr(llm, "is_openrouter_proxy", False)
            or "openrouter.ai" in str(getattr(llm, "api_base", ""))
        )
        is_reasoning = any(
            x in model_lower for x in ["r1", "reasoning", "thought", "o1", "o3", "step"]
        )

        if is_oss or is_openrouter or is_reasoning:
            logger.info(
                f"Adding extra instructions for {model_name} (OSS/Reasoning/OpenRouter)"
            )

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
                '  "name": "web_search",\n'
                '  "args": {\n'
                '    "query": "últimas noticias sobre inteligencia artificial"\n'
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
                '{"argumento1": "valor1", "argumento2": "valor2"}\n\n'
            )
            final_system_content += extra_instructions
        else:
            final_system_content += "\n\n⚠️ **CRITICAL TECHNICAL REMINDER:** Use your internal reasoning/thinking ONLY if the task is complex. Always provide a clear final response. If you use a tool, you MUST provide ALL required arguments."

    # --- ESCAPE GLOBAL PARA LANGCHAIN (CRÍTICO) ---
    # Escapamos todas las llaves '{' y '}' para evitar que LangChain intente parsear JSONs
    # de herramientas o manuales como variables del prompt.
    # El placeholder "messages" se maneja por separado vía MessagesPlaceholder.
    final_system_content_escaped = final_system_content.replace("{", "{{").replace(
        "}", "}}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", final_system_content_escaped),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | llm_with_tools

    full_ai_message_content = ""
    tool_calls_from_llm = []
    final_response_message = None
    in_thinking_tag = False

    target_account_id = (
        "telegram_bot_service" if state.get("telegram_id") else state["account_id"]
    )
    conn_type = "chat" if state.get("telegram_id") else None

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

        # OPTIMIZACIÓN: Early return para historiales pequeños sin tool calls
        # Evita O(N) overhead en conversaciones simples (saludos, preguntas directas)
        if len(messages) <= 12 and not any(
            isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None)
            for msg in messages
        ):
            return [m for m in messages if not isinstance(m, SystemMessage)]

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
                content = [
                    p
                    for p in content
                    if not (
                        isinstance(p, dict)
                        and p.get("type") == "text"
                        and not p.get("text", "").strip()
                    )
                ]
                if not content:
                    content = ""

            # Si el contenido es un string vacío y no hay tool_calls, ignorar
            has_tool_calls = isinstance(msg, AIMessage) and bool(
                getattr(msg, "tool_calls", None)
            )
            if not content and not has_tool_calls and not isinstance(msg, ToolMessage):
                continue

            sanitized.append(msg)

        if not sanitized:
            return []

        # 2. Fase de emparejamiento Assistant -> Tool(s) y fusión de roles consecutivos
        cleaned = []
        # LIMITACIÓN DE HISTORIAL configurable.
        # Si se usa Ollama, aplicamos su ventana específica; en otros modelos usamos la general.
        history_limit = (
            settings.agent_history_limit_ollama
            if _is_ollama_model
            else settings.agent_history_limit_default
        )
        if len(sanitized) > history_limit:
            start_idx = len(sanitized) - history_limit
            # Garantizar ancla humana al inicio de la ventana para no perder el hilo.
            while start_idx > 0 and not isinstance(sanitized[start_idx], HumanMessage):
                start_idx -= 1
            sanitized_subset = sanitized[start_idx:]
        else:
            sanitized_subset = sanitized

        latest_human_in_subset = next(
            (m for m in reversed(sanitized_subset) if isinstance(m, HumanMessage)),
            None,
        )

        # En conversaciones cortas, evitar limpieza agresiva que puede degradar el contexto.
        # Esto mejora continuidad en los primeros turnos (1-3 intercambios).
        if len(sanitized_subset) <= 8:
            return sanitized_subset

        i = 0
        while i < len(sanitized_subset):
            msg = sanitized_subset[i]

            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                # Encontrado un bloque de assistant que pide herramientas.
                # Debemos encontrar TODAS sus respuestas correspondientes.
                current_tool_calls = msg.tool_calls
                call_ids = {tc.get("id") for tc in current_tool_calls if tc.get("id")}

                responses = []
                next_i = i + 1
                while next_i < len(sanitized_subset):
                    next_msg = sanitized_subset[next_i]
                    if isinstance(next_msg, ToolMessage):
                        if next_msg.tool_call_id in call_ids:
                            responses.append(next_msg)
                            call_ids.remove(next_msg.tool_call_id)
                        else:
                            # ToolMessage que no pertenece a este bloque, ignorar
                            logger.warning(
                                f"⚠️ ToolMessage huérfano detectado: {next_msg.tool_call_id}"
                            )
                    elif isinstance(next_msg, (HumanMessage, AIMessage)):
                        # Otro rol interrumpe, Mistral es estricto: no puede haber llamadas sin respuesta
                        break
                    next_i += 1

                # Solo incluimos el AIMessage si podemos emparejar al menos una llamada (o tiene contenido)
                valid_call_ids = {r.tool_call_id for r in responses}
                filtered_tool_calls = [
                    tc for tc in current_tool_calls if tc.get("id") in valid_call_ids
                ]

                if filtered_tool_calls or msg.content:
                    # Asegurar orden de respuestas (Mistral strictness)
                    order_map = {
                        tc.get("id"): idx for idx, tc in enumerate(filtered_tool_calls)
                    }
                    responses.sort(key=lambda r: order_map.get(r.tool_call_id, 999))

                    new_ai_msg = AIMessage(
                        content=msg.content or "",
                        tool_calls=filtered_tool_calls
                        or [],  # Usar [] para evitar error de validación AIMessage
                        additional_kwargs=getattr(msg, "additional_kwargs", {}),
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
                if (
                    cleaned
                    and type(msg) == type(cleaned[-1])
                    and not isinstance(msg, ToolMessage)
                ):
                    last_msg = cleaned[-1]
                    # Fusionar contenidos si son strings
                    if isinstance(last_msg.content, str) and isinstance(
                        msg.content, str
                    ):
                        last_msg.content += "\n\n" + msg.content
                        logger.debug(
                            f"🔄 Fusionados dos mensajes consecutivos de tipo {type(msg).__name__}"
                        )
                    else:
                        # Si no se pueden fusionar fácilmente, los mantenemos (algunos proveedores lo permiten)
                        cleaned.append(msg)
                else:
                    cleaned.append(msg)
                i += 1

        # 3. Asegurar que el primer mensaje después del sistema sea 'human'
        if cleaned and not isinstance(cleaned[0], HumanMessage):
            first_human_idx = next(
                (idx for idx, m in enumerate(cleaned) if isinstance(m, HumanMessage)),
                -1,
            )

            if first_human_idx > 0:
                dropped = [type(m).__name__ for m in cleaned[:first_human_idx]]
                logger.warning(
                    f"⚠️ Recortando {first_human_idx} mensajes iniciales no-humanos para cumplir paridad: {dropped}"
                )
                cleaned = cleaned[first_human_idx:]
            elif first_human_idx == -1:
                if latest_human_in_subset:
                    logger.warning(
                        "⚠️ Historial limpiado sin mensajes humanos; usando el último HumanMessage del subset como fallback."
                    )
                    return [latest_human_in_subset]
                logger.warning(
                    "⚠️ Historial limpiado sin mensajes humanos y sin fallback disponible; devolviendo historial vacío."
                )
                return []

        return cleaned

    cleaned_messages = clean_messages_history(state["messages"])

    # ✅ SOLUCION BUG MULTIMODAL:
    # Solo activar ruteo vision si el ULTIMO mensaje humano contiene imagenes.
    # Evita que imagenes historicas fuercen el modelo vision en turnos de texto.
    has_images = False
    latest_human_with_content = None
    for msg in reversed(cleaned_messages):
        if isinstance(msg, HumanMessage):
            latest_human_with_content = msg
            break

    if latest_human_with_content:
        has_images = _message_has_image_parts(latest_human_with_content)

    if not has_images:
        # Si el turno actual no es visual, removemos partes de imagen del historial
        # para evitar enviar imágenes antiguas a modelos de texto (ej. Ollama no-vision).
        stripped_messages = 0
        for msg in cleaned_messages:
            if not isinstance(getattr(msg, "content", None), list):
                continue

            text_parts = []
            had_image_part = False
            for part in msg.content:
                if isinstance(part, str):
                    text_parts.append(part)
                    continue
                if not isinstance(part, dict):
                    text_parts.append(str(part))
                    continue

                part_type = part.get("type")
                if part_type in {"image_url", "input_image"} or "image_url" in part:
                    had_image_part = True
                    continue
                if part_type in {"text", "input_text"}:
                    text_parts.append(part.get("text", ""))
                    continue
                if "text" in part and isinstance(part.get("text"), str):
                    text_parts.append(part.get("text", ""))

            if had_image_part:
                msg.content = "\n".join([t for t in text_parts if t]).strip()
                stripped_messages += 1

        if stripped_messages:
            logger.info(
                f"🧹 Removidas partes de imagen de {stripped_messages} mensajes del historial en turno no-visual."
            )

    # Si hay imágenes en el turno actual, configurar tag vision_model conservando la cadena con herramientas vinculadas
    if has_images:
        logger.info(
            f"👁️ Detectadas imágenes en el mensaje actual. Ejecutando modelo multimodal '{model_name}' "
            f"con herramientas vinculadas y tag 'vision_model'."
        )
        chain = chain.with_config(tags=["vision_model"])

        # Normalizar todas las partes de imagen en los mensajes para asegurar esquemas data: URI válidos
        for msg in cleaned_messages:
            if isinstance(getattr(msg, "content", None), list):
                for part in msg.content:
                    if isinstance(part, dict):
                        if part.get("type") in {"image_url", "input_image"} and isinstance(part.get("image_url"), dict):
                            raw_url = part["image_url"].get("url", "")
                            part["image_url"]["url"] = normalize_image_url(raw_url)
                        elif "image_url" in part and isinstance(part.get("image_url"), str):
                            part["image_url"] = normalize_image_url(part["image_url"])


    full_ai_message_content = ""
    full_reasoning_content = ""  # Acumulador para razonamiento
    tool_calls_from_llm = []
    final_response_message = None
    in_thinking_tag = False

    # Normalización de seguridad para proveedores custom (KiloCode)
    # Si el LLM tiene un nombre de modelo con prefijo kilocode/, nos aseguramos de que
    # LiteLLM lo vea como openai/ pero con la api_base correcta ya configurada.
    for llm_attr in ["llm", "vision_llm"]:
        target_llm = locals().get(llm_attr)
        if target_llm and hasattr(target_llm, "model_name") and target_llm.model_name:
            if target_llm.model_name.startswith("kilocode/"):
                logger.info(
                    f"🔄 Normalizando modelo {llm_attr} para LiteLLM: {target_llm.model_name} -> openai/..."
                )
                target_llm.model_name = target_llm.model_name.replace(
                    "kilocode/", "openai/"
                )
                if not getattr(target_llm, "custom_llm_provider", None):
                    target_llm.custom_llm_provider = "openai"

    # --- Streaming con reintentos para errores transitorios de proveedor ---
    _MAX_STREAM_RETRIES = 2
    _STREAM_RETRY_DELAY = 3.0  # segundos entre reintentos

    def _is_transient_provider_error(exc: Exception) -> bool:
        """Detecta si una excepción es un error transitorio del proveedor (timeout, unavailable)."""
        exc_str = str(exc).lower()
        transient_keywords = [
            "upstream idle timeout",
            "provider_unavailable",
            "timeout",
            "connection reset",
            "service unavailable",
            "overloaded",
            "rate limit",
        ]
        if any(kw in exc_str for kw in transient_keywords):
            return True
        if _LiteLLMMidStreamFallbackError and isinstance(
            exc, _LiteLLMMidStreamFallbackError
        ):
            return True
        if _LiteLLMAPIError and isinstance(exc, _LiteLLMAPIError):
            return True
        return False

    for _stream_attempt in range(_MAX_STREAM_RETRIES + 1):
        try:
            if has_images:
                last_human = next((m for m in reversed(cleaned_messages) if isinstance(m, HumanMessage)), None)
                img_count = 0
                if last_human and isinstance(last_human.content, list):
                    img_count = sum(1 for p in last_human.content if isinstance(p, dict) and (p.get("type") in {"image_url", "input_image"} or "image_url" in p))
                logger.info(
                    f"📸 Diagnostic Log: Sending multimodal payload to model '{model_name}'. "
                    f"Cleaned messages count: {len(cleaned_messages)}, Image parts in current turn: {img_count}."
                )

            async for chunk in chain.astream({"messages": cleaned_messages}):

                if isinstance(chunk, AIMessage):
                    # DEBUG: Log del chunk completo para ver el formato crudo
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"🔍 CHUNK CRUDO: content={chunk.content}, tool_calls={chunk.tool_calls}, additional_kwargs={chunk.additional_kwargs}"
                        )

                    # 1. Detectar razonamiento (Chain of Thought) en metadatos (OpenRouter / LiteLLM / DeepSeek)
                    reasoning_chunk = ""
                    add_kwargs = getattr(chunk, "additional_kwargs", {})
                    resp_meta = getattr(chunk, "response_metadata", {})

                    # Lista de claves posibles donde los proveedores esconden el razonamiento
                    reasoning_keys = [
                        "reasoning",
                        "reasoning_content",
                        "thought",
                        "thinking",
                        "reflection",
                        "chain_of_thought",
                    ]

                    # Buscar en additional_kwargs
                    for key in reasoning_keys:
                        if (
                            key in add_kwargs
                            and isinstance(add_kwargs[key], str)
                            and add_kwargs[key]
                        ):
                            reasoning_chunk = add_kwargs[key]
                            break

                    # Buscar en response_metadata si no se encontró
                    if not reasoning_chunk:
                        for key in reasoning_keys:
                            if (
                                key in resp_meta
                                and isinstance(resp_meta[key], str)
                                and resp_meta[key]
                            ):
                                reasoning_chunk = resp_meta[key]
                                break

                    if reasoning_chunk:
                        full_reasoning_content += reasoning_chunk
                        await send_personal_message(
                            target_account_id,
                            {
                                "type": "reasoning_chunk",
                                "thread_id": state["thread_id"],
                                "taskId": state.get("task_id"),
                                "chunk": reasoning_chunk,
                                "full_reasoning": full_reasoning_content,
                            },
                            connection_type=conn_type,
                        )

                    # 2. Procesar contenido normal y DETECCIÓN DE ETIQUETAS 认 robusta
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
                        # Lógica de detección de etiquetas 认 para modelos como DeepSeek-R1
                        processed_content = ""

                        # Caso simple: El chunk contiene 认
                        if "认" in current_content:
                            parts = current_content.split("认")
                            processed_content += parts[0]  # Texto antes de 认
                            in_thinking_tag = True
                            thinking_part = parts[1] if len(parts) > 1 else ""

                            # Si también contiene 认 en el mismo chunk
                            if "认" in thinking_part:
                                subparts = thinking_part.split("认")
                                reasoning_to_send = subparts[0]
                                full_reasoning_content += reasoning_to_send
                                in_thinking_tag = False
                                processed_content += (
                                    subparts[1] if len(subparts) > 1 else ""
                                )

                                # Enviar el razonamiento acumulado en el tag
                                await send_personal_message(
                                    target_account_id,
                                    {
                                        "type": "reasoning_chunk",
                                        "thread_id": state["thread_id"],
                                        "taskId": state.get("task_id"),
                                        "chunk": reasoning_to_send,
                                        "full_reasoning": full_reasoning_content,
                                    },
                                    connection_type=conn_type,
                                )
                            else:
                                # Todo el resto del chunk es razonamiento
                                full_reasoning_content += thinking_part
                                await send_personal_message(
                                    target_account_id,
                                    {
                                        "type": "reasoning_chunk",
                                        "thread_id": state["thread_id"],
                                        "taskId": state.get("task_id"),
                                        "chunk": thinking_part,
                                        "full_reasoning": full_reasoning_content,
                                    },
                                    connection_type=conn_type,
                                )

                        # Caso: Estamos dentro de un tag de pensamiento abierto en chunks anteriores
                        elif in_thinking_tag:
                            if "认" in current_content:
                                parts = current_content.split("认")
                                reasoning_to_send = parts[0]
                                full_reasoning_content += reasoning_to_send
                                in_thinking_tag = False
                                processed_content += parts[1] if len(parts) > 1 else ""

                                await send_personal_message(
                                    target_account_id,
                                    {
                                        "type": "reasoning_chunk",
                                        "thread_id": state["thread_id"],
                                        "taskId": state.get("task_id"),
                                        "chunk": reasoning_to_send,
                                        "full_reasoning": full_reasoning_content,
                                    },
                                    connection_type=conn_type,
                                )
                            else:
                                # Todo el chunk sigue siendo razonamiento
                                full_reasoning_content += current_content
                                await send_personal_message(
                                    target_account_id,
                                    {
                                        "type": "reasoning_chunk",
                                        "thread_id": state["thread_id"],
                                        "taskId": state.get("task_id"),
                                        "chunk": current_content,
                                        "full_reasoning": full_reasoning_content,
                                    },
                                    connection_type=conn_type,
                                )

                        # Caso: Posible tag cortado al final (heurística simple para evitar mostrar <t etc)
                        # Si no estamos pensando y el chunk termina en <, <t, <th... no lo procesamos aun
                        # (Esta es una mejora compleja, por ahora asumimos atomicidad razonable)
                        else:
                            processed_content = current_content

                        if processed_content:
                            full_ai_message_content += processed_content
                            logger.debug(
                                f"DEBUG (agent.py): Enviando stream_chunk para taskId {state.get('task_id')}"
                            )
                            await send_personal_message(
                                target_account_id,
                                {
                                    "type": "stream_chunk",
                                    "thread_id": state["thread_id"],
                                    "taskId": state.get("task_id"),
                                    "chunk": processed_content,
                                    "full_text": full_ai_message_content,
                                },
                                connection_type=conn_type,
                            )

                    # 3. Procesar tool calls nativos (USANDO ACUMULADOR MANUAL PARA EVITAR FRAGMENTACIÓN)
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc_chunk in chunk.tool_call_chunks:
                            # Buscar si ya tenemos esta llamada (por su index o ID)
                            idx = tc_chunk.get("index")
                            found = False

                            for existing_tc in tool_calls_from_llm:
                                if (
                                    idx is not None and existing_tc.get("index") == idx
                                ) or (
                                    tc_chunk.get("id")
                                    and existing_tc.get("id") == tc_chunk.get("id")
                                ):
                                    found = True
                                    # Actualizar el existente
                                    if tc_chunk.get("name"):
                                        existing_tc["name"] = tc_chunk["name"]
                                    if tc_chunk.get("args"):
                                        # Unir strings de argumentos (vienen fragmentados)
                                        current_args_str = existing_tc.get(
                                            "_args_str", ""
                                        )
                                        new_args_str = tc_chunk["args"]
                                        existing_tc["_args_str"] = (
                                            current_args_str + new_args_str
                                        )
                                        try:
                                            # Intentar parsear el acumulado
                                            existing_tc["args"] = json.loads(
                                                existing_tc["_args_str"]
                                            )
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
                                    "index": idx,
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

                    # Guardamos texto parcial para poder recuperarlo si el usuario cancela (Botón Stop)
                    if state.get("task_id"):
                        from core.websocket_manager import (
                            partial_task_messages,
                            partial_task_reasoning,
                        )

                        if full_ai_message_content:
                            partial_task_messages[state.get("task_id")] = (
                                full_ai_message_content
                            )
                        if full_reasoning_content:
                            partial_task_reasoning[state.get("task_id")] = (
                                full_reasoning_content
                            )

                    final_response_message = chunk
            break  # Stream completó sin error, salir del bucle de reintentos
        except asyncio.CancelledError:
            raise  # No reintentar si fue cancelado por el usuario
        except Exception as _stream_exc:
            if (
                _is_transient_provider_error(_stream_exc)
                and _stream_attempt < _MAX_STREAM_RETRIES
            ):
                logger.warning(
                    f"⚠️ Error transitorio del proveedor en stream (intento {_stream_attempt + 1}/{_MAX_STREAM_RETRIES + 1}): "
                    f"{type(_stream_exc).__name__}: {_stream_exc}. "
                    f"Reintentando en {_STREAM_RETRY_DELAY}s..."
                )
                # Limpiar estado parcial antes de reintentar
                full_ai_message_content = ""
                full_reasoning_content = ""
                tool_calls_from_llm = []
                final_response_message = None
                in_thinking_tag = False
                await asyncio.sleep(_STREAM_RETRY_DELAY)
            else:
                logger.error(
                    f"❌ Error en stream del LLM (intento {_stream_attempt + 1}/{_MAX_STREAM_RETRIES + 1}): "
                    f"{type(_stream_exc).__name__}: {_stream_exc}. Ejecutando fallback no-stream (ainvoke)..."
                )
                try:
                    full_ai_message_content = ""
                    full_reasoning_content = ""
                    tool_calls_from_llm = []
                    
                    non_stream_res = await chain.ainvoke({"messages": cleaned_messages})
                    if isinstance(non_stream_res, AIMessage):
                        if isinstance(non_stream_res.content, str):
                            full_ai_message_content = non_stream_res.content
                        elif isinstance(non_stream_res.content, list):
                            for p in non_stream_res.content:
                                if isinstance(p, dict) and p.get("type") == "text":
                                    full_ai_message_content += p.get("text", "")
                        
                        if getattr(non_stream_res, "tool_calls", None):
                            tool_calls_from_llm = list(non_stream_res.tool_calls)
                        
                        if full_ai_message_content:
                            await send_personal_message(
                                target_account_id,
                                {
                                    "type": "stream_chunk",
                                    "thread_id": state["thread_id"],
                                    "taskId": state.get("task_id"),
                                    "chunk": full_ai_message_content,
                                    "full_text": full_ai_message_content,
                                },
                                connection_type=conn_type,
                            )
                        final_response_message = non_stream_res
                        break
                except Exception as _ainvoke_exc:
                    logger.error(f"❌ Fallback no-stream (ainvoke) también falló: {_ainvoke_exc}")
                    raise _stream_exc


    logger.debug(
        f"DEBUG (agent.py - call_model_node): Respuesta cruda del LLM acumulada."
    )

    # --- LOG ULTRA-DETALLADO ---
    if final_response_message:
        try:
            full_data = {
                "content": full_ai_message_content,
                "reasoning": full_reasoning_content,
                "tool_calls": tool_calls_from_llm,
                "additional_kwargs": getattr(
                    final_response_message, "additional_kwargs", {}
                ),
                "response_metadata": getattr(
                    final_response_message, "response_metadata", {}
                ),
            }
            logger.debug(
                f"🔥 DATA COMPLETA DEL MODELO:\n{json.dumps(full_data, indent=2)}"
            )
        except Exception as e:
            logger.debug(f"Error al loguear data completa: {e}")

    # Log de tool calls crudos para debugging
    if tool_calls_from_llm:
        # Usar logger.info simplificado para no saturar
        logger.info(
            f"🔍 Herramientas solicitadas por el modelo: {[tc.get('name') for tc in tool_calls_from_llm]}"
        )
        logger.debug(
            f"Tool calls recibidos del modelo ({len(tool_calls_from_llm)}): {json.dumps(tool_calls_from_llm, indent=2)}"
        )
    else:
        logger.info("ℹ️ No se recibieron tool calls del modelo")
        if not full_ai_message_content.strip() and full_reasoning_content.strip():
            logger.warning(
                "⚠️ El modelo generó razonamiento pero la respuesta final está VACÍA. Esto puede deberse a un corte prematuro del proveedor o a instrucciones contradictorias."
            )
        logger.debug(
            f"Contenido de respuesta del modelo: {full_ai_message_content[:500]}..."
        )

    # --- END DEBUG ---

    # --- PARSER HÍBRIDO DE TOOL CALLS (Sistema Kogniterm) ---
    # Complementar o reemplazar tool calls nativos con parseo del texto
    # Esto maneja modelos que no formatean correctamente los tool calls

    logger.info("🔍 Iniciando parser híbrido de tool calls...")
    combined_text = full_ai_message_content + "\n" + full_reasoning_content
    parsed_tool_calls = parse_tool_calls_from_text(combined_text, tools)

    if parsed_tool_calls:
        logger.info(
            f"✅ Parser híbrido extrajo {len(parsed_tool_calls)} tool calls del texto"
        )

        # --- LIMPIEZA DE CONTENIDO ---
        # Removido el indicador de herramienta para que no sea visible para el usuario
        patterns_to_strip = [
            r"LLAMADA_A_HERRAMIENTA:\s*\w+.*?(?=\n|$)",
            r"Herramienta:\s*\w+.*?(?=\n|$)",
            r"\[TOOL_CALL\]\s*\w+.*?(?=\n|$)",
            r"Tool:\s*\w+.*?(?=\n|$)",
            r"<tool>\s*\w+\s*</tool>",
            r'\{[\s\n]*"[\w\d_]+":[\s\S]*?\}',
        ]

        cleaned_content = full_ai_message_content
        for p in patterns_to_strip:
            cleaned_content = re.sub(
                p, "", cleaned_content, flags=re.IGNORECASE | re.DOTALL
            )

        cleaned_content = re.sub(r"\n{3,}", "\n\n", cleaned_content).strip()

        if cleaned_content != full_ai_message_content:
            logger.info("🧹 Mensaje limpiado de instrucciones técnicas.")
            full_ai_message_content = cleaned_content

        # Si el modelo no devolvió tool calls nativos, usar los parseados
        if not tool_calls_from_llm:
            tool_calls_from_llm = parsed_tool_calls
            logger.info(
                "📝 Usando tool calls parseados del texto (modelo no devolvió nativos)"
            )
        else:
            # Si el modelo devolvió tool calls pero con args vacíos, complementar con los parseados
            for native_tc in tool_calls_from_llm:
                if not native_tc.get("args") or native_tc.get("args") == {}:
                    # Buscar el mismo tool call en los parseados
                    for parsed_tc in parsed_tool_calls:
                        if parsed_tc["name"] == native_tc.get("name"):
                            # Actualizar con los args parseados
                            native_tc["args"] = parsed_tc["args"]
                            logger.info(
                                f"🔧 Complementados args vacíos de '{native_tc.get('name')}' con parseo de texto"
                            )
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
                logger.debug(
                    f"✅ Argumentos fusionados para {existing.get('name')}: {existing['args']}"
                )

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
                logger.warning(
                    f"⚠️ No se pudo parsear argumentos como JSON para {tc_name}: {args}"
                )
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
    if final_response_message and hasattr(final_response_message, "additional_kwargs"):
        final_kwargs = final_response_message.additional_kwargs.copy()

    if model_name:
        final_kwargs["model_name"] = model_name

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
            tool_calls=tool_calls_to_use,  # Cambiado para usar la variable segura
            additional_kwargs=final_kwargs,
        )
    else:
        final_ai_message = AIMessage(
            content=full_ai_message_content,
            tool_calls=tool_calls_to_use,
            additional_kwargs=final_kwargs,
        )

    # Adjuntar fuentes y tool_calls a la respuesta del LLM si existen
    if (
        final_sources_for_state
    ):  # Usar las fuentes que se han acumulado en final_sources_for_state
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
        "sources": final_sources_for_state,  # Asegurarse de que las fuentes se propaguen en el estado
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

    Paralelismo controlado:
    - Todas las herramientas se lanzan concurrentemente con asyncio.gather.
    - Un semáforo (_TOOL_EXECUTION_SEMAPHORE) limita la concurrencia máxima real
      para evitar saturar APIs externas (configurable vía settings.max_parallel_tools).
    - return_exceptions=True garantiza que el fallo de una herramienta no cancele las demás.
    """
    logger.debug(f"--- (Grafo) Nodo: Llamar Herramienta (Paralelo) ---")
    if not isinstance(state["messages"][-1], AIMessage):
        return {}

    agent_message = state["messages"][-1]
    tool_calls = (
        agent_message.tool_calls
        if isinstance(agent_message, AIMessage) and hasattr(agent_message, "tool_calls")
        else []
    )

    if not tool_calls:
        return {}

    account_id = state["account_id"]
    telegram_id_int = state.get("telegram_id")
    telegram_id_str = str(telegram_id_int) if telegram_id_int is not None else None
    workspace_id = state.get("workspace_id")
    target_account_id = (
        "telegram_bot_service" if state.get("telegram_id") else state["account_id"]
    )
    conn_type = "chat" if state.get("telegram_id") else None

    logger.info(
        f"🔀 tool_node: Ejecutando {len(tool_calls)} herramienta(s) en paralelo (máx. concurrencia: {MAX_PARALLEL_TOOLS})"
    )

    # Cargar todas las herramientas disponibles una sola vez para todas las llamadas paralelas
    all_tools = await get_all_langchain_tools(
        account_id=account_id,
        telegram_id=telegram_id_int,
        thread_id=state["thread_id"],
        workspace_id=workspace_id,
    )

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
            "web_search": "query",
            "deep_research": "query",
            "knowledge_graph": "natural_language_query",
            "comprehensive_web_analyzer": "query",
            "add_note": "content",
            "create_document": "content",
            "add_event": "title",
            "web_scraper_tool": "url",
        }

        if tool_name in query_based_tools:
            required_arg = query_based_tools[tool_name]
            val = tool_args.get(required_arg)
            if val is None or (isinstance(val, str) and not val.strip()):
                if required_arg == "url":
                    import re

                    urls = re.findall(
                        r'https?://[^\s<>"{}|\\^`\[\]]+', user_query or ""
                    )
                    inferred_val = urls[0] if urls else "https://example.com"
                else:
                    # Si es create_pdf_tool, intentamos usar el mensaje anterior al tool call si es del modelo
                    inferred_val = (
                        user_query if user_query else "Contenido no especificado"
                    )
                tool_args[required_arg] = inferred_val

        logger.tool_call(tool_name, tool_args)

        # Evento tool_start
        await send_personal_message(
            target_account_id,
            {
                "type": "tool_start",
                "taskId": state.get("task_id"),
                "tool_name": tool_name,
                "thread_id": state.get("thread_id"),
            },
            connection_type=conn_type,
        )

        selected_tool = await get_tool_by_name(
            tool_name=tool_name,
            all_tools=all_tools,
            account_id=account_id,
            telegram_id=telegram_id_str,
            workspace_id=workspace_id,
            graph_db=state.get("graph_db"),
            enhanced_memory_manager=state.get("enhanced_memory_manager"),
        )

        if not selected_tool:
            error_msg = f"Error: Herramienta '{tool_name}' no encontrada."
            await send_personal_message(
                target_account_id,
                {
                    "type": "tool_end",
                    "taskId": state.get("task_id"),
                    "tool_name": tool_name,
                    "status": "error",
                    "result": error_msg,
                    "error": True,
                    "sources": [],
                },
                connection_type=conn_type,
            )
            return ToolMessage(
                content=error_msg, tool_call_id=tool_call.get("id") or str(uuid.uuid4())
            ), []

        # Configuración y reintentos
        if state.get("tool_error_counts") is None:
            state["tool_error_counts"] = {}
        should_stop, stop_message = should_stop_retrying_tool(
            tool_name, state["tool_error_counts"]
        )
        if should_stop:
            await send_personal_message(
                target_account_id,
                {
                    "type": "tool_end",
                    "taskId": state.get("task_id"),
                    "tool_name": tool_name,
                    "status": "error",
                    "result": stop_message,
                    "error": True,
                    "sources": [],
                },
                connection_type=conn_type,
            )
            return ToolMessage(
                content=stop_message,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4()),
            ), []

        async def progress_callback(progress: int, message: str, *args, **kwargs):
            # 1. Enviar evento de progreso estándar
            progress_payload = {
                "type": "progress",
                "taskId": state.get("task_id"),
                "progress": progress,
                "message": message,
                "thread_id": state.get("thread_id"),
            }
            await send_personal_message(
                target_account_id, progress_payload, connection_type=conn_type
            )

            # 2. Si hay datos con un fragmento de stream, enviarlo como stream_chunk
            data = kwargs.get("data") or (
                args[0] if args and isinstance(args[0], dict) else None
            )
            if data and "stream_chunk" in data:
                chunk_payload = {
                    "type": "stream_chunk",
                    "taskId": state.get("task_id"),
                    "chunk": data["stream_chunk"],
                    "thread_id": state.get("thread_id"),
                }
                await send_personal_message(
                    target_account_id, chunk_payload, connection_type=conn_type
                )

            # 3. Mantener compatibilidad con otros metadatos (opcional)
            elif data:
                progress_payload["data"] = data
                await send_personal_message(
                    target_account_id, progress_payload, connection_type=conn_type
                )

        run_config = RunnableConfig(
            configurable={
                "account_id": account_id,
                "workspace_id": workspace_id,
                "telegram_id": state.get("telegram_id"),
                "thread_id": state.get("thread_id"),
                "task_id": state.get("task_id"),
                "progress_callback": progress_callback,
            }
        )

        try:
            if tool_name == "deep_research":
                selected_tool.progress_callback = progress_callback

            # Ejecutar la herramienta bajo el semáforo de concurrencia.
            # Esto asegura que no haya más de MAX_PARALLEL_TOOLS herramientas
            # ejecutándose simultáneamente, incluso si el LLM solicita más.
            async with _TOOL_EXECUTION_SEMAPHORE:
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
                context_content = output_dump.get(
                    "context_for_llm", json.dumps(output_dump)
                )
                sources_list = output_dump.get("sources", [])
                visual_schema = output_dump.get("visual_schema")
                recommendations = output_dump.get("recommendations", [])
            else:
                context_content = str(output_dump)

            # Inyectar instrucción de parada si es un reporte de investigación profunda completo
            if tool_name == "deep_research" and (
                "# Resumen Ejecutivo" in context_content
                or "# Introducción" in context_content
            ):
                context_content += "\n\n--- INSTRUCCIÓN DEL SISTEMA: La investigación se ha completado. Proporcione la respuesta final al usuario ahora. NO vuelva a llamar a la herramienta 'deep_research'. ---"

            # Re-indexación local
            tool_sources = []
            for i, s in enumerate(sources_list):
                s_dict = (
                    s.model_dump()
                    if hasattr(s, "model_dump")
                    else (s.dict() if hasattr(s, "dict") else s)
                )
                tool_sources.append(s_dict)

            if len(context_content) > 30000:
                context_content = context_content[:30000] + "\n\n[... TRUNCADO ...]"

            await send_personal_message(
                target_account_id,
                {
                    "type": "tool_end",
                    "taskId": state.get("task_id"),
                    "tool_name": tool_name,
                    "status": "end",
                    "result": context_content,
                    "sources": tool_sources,
                    "visual_schema": visual_schema,
                    "recommendations": recommendations,
                    "thread_id": state.get("thread_id"),
                },
                connection_type=conn_type,
            )

            tool_message = ToolMessage(
                content=context_content,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4()),
            )
            tool_message.additional_kwargs["sources"] = tool_sources
            if visual_schema:
                tool_message.additional_kwargs["visual_schema"] = visual_schema
            if recommendations:
                tool_message.additional_kwargs["recommendations"] = recommendations

            return tool_message, tool_sources

        except Exception as e:
            logger.error(f"Error paralelo en {tool_name}: {e}")
            state["tool_error_counts"][tool_name] = (
                state["tool_error_counts"].get(tool_name, 0) + 1
            )

            # Si es un error de validación, usar el formateador especializado
            if isinstance(e, ValidationError):
                error_text = format_validation_error_for_llm(e, tool_name, tool_args)
            else:
                error_text = f"Error: {e}"

            await send_personal_message(
                target_account_id,
                {
                    "type": "tool_end",
                    "taskId": state.get("task_id"),
                    "tool_name": tool_name,
                    "status": "error",
                    "result": error_text,
                    "error": True,
                    "sources": [],
                },
                connection_type=conn_type,
            )
            tool_msg = ToolMessage(
                content=error_text,
                tool_call_id=tool_call.get("id") or str(uuid.uuid4()),
            )
            tool_msg.additional_kwargs["sources"] = []
            return tool_msg, []

    # 2. Ejecutar todas las llamadas en paralelo.
    # return_exceptions=True garantiza aislamiento: el fallo de una herramienta
    # no cancela las demás ni propaga una excepción al gather.
    tasks = [execute_single_tool(tc) for tc in tool_calls]
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Consolidar resultados, manejando excepciones individuales.
    tool_messages = []
    all_new_sources = []
    for i, result in enumerate(parallel_results):
        tc = tool_calls[i]
        if isinstance(result, Exception):
            # Un fallo no capturado dentro de execute_single_tool (caso inesperado).
            # Lo reportamos y seguimos con el resto de herramientas.
            logger.error(
                f"❌ Excepción no capturada en execute_single_tool para '{tc.get('name')}': {result}"
            )
            error_msg = f"Error inesperado ejecutando '{tc.get('name')}': {result}"
            tool_messages.append(
                ToolMessage(
                    content=error_msg, tool_call_id=tc.get("id") or str(uuid.uuid4())
                )
            )
        else:
            msg, sources = result
            tool_messages.append(msg)
            all_new_sources.extend(sources)

    # 4. Inserción de nuevas fuentes (evitando duplicados mediante identificador robusto)
    def get_source_identifier(s: Dict[str, Any]) -> str:
        s_type = s.get("type", "web")
        if hasattr(s_type, "value"):
            s_type = s_type.value
        s_type = str(s_type)

        s_url = s.get("url") or s.get("id") or ""
        s_url = str(s_url)

        s_snippet = s.get("snippet", "")
        # Usar un hash del snippet para permitir múltiples fragmentos del mismo documento
        import hashlib

        snippet_hash = (
            hashlib.md5(s_snippet.strip().encode()).hexdigest()[:8]
            if s_snippet.strip()
            else "empty"
        )
        return f"{s_type}:{s_url}:{snippet_hash}"

    logger.debug(
        f"[Tool Node] Consolidando fuentes de herramientas ejecutadas. Total nuevas recibidas: {len(all_new_sources)}"
    )
    actual_new_sources_to_return = []
    current_sources = state.get("sources") or []
    seen_identifiers = {get_source_identifier(s) for s in current_sources}

    for s in all_new_sources:
        s_dict = (
            s.model_dump()
            if hasattr(s, "model_dump")
            else (s.dict() if hasattr(s, "dict") else s)
        )
        ident = get_source_identifier(s_dict)
        if ident not in seen_identifiers:
            actual_new_sources_to_return.append(s_dict)
            seen_identifiers.add(ident)
            logger.debug(f"[Tool Node] Agregando nueva fuente única: {ident}")
        else:
            logger.debug(f"[Tool Node] Omitiendo fuente duplicada: {ident}")

    logger.info(
        f"✅ tool_node: Añadiendo {len(actual_new_sources_to_return)} nuevas fuentes al estado. (Total previo: {len(current_sources)})"
    )

    # OPTIMIZACIÓN: Se elimina la extracción de conocimiento aquí para evitar redundancia
    # Se ejecutará una sola vez en generate_response_node
    return {
        "messages": tool_messages,
        "sources": actual_new_sources_to_return,
        "loop_count": state.get("loop_count", 0) + 1,
    }


# --- 2. Enrutador ---


def should_continue(state: AgentState) -> str:
    """
    Decide si continuar con la ejecución de herramientas o finalizar.
    """
    logger.info("--- (Grafo) Nodo: Enrutamiento ---")
    last_message = state["messages"][-1]

    # Loop protection: máximo configurable de iteraciones de herramientas
    loop_count = state.get("loop_count", 0)
    if loop_count >= settings.max_agent_loops:
        logger.warning(
            f"⚠️ Alerta de bucle detectada (loop_count={loop_count}). Forzando finalización."
        )
        return "generate_response"

    if isinstance(last_message, AIMessage) and getattr(
        last_message, "tool_calls", None
    ):
        logger.info(
            f"Decisión del enrutador: Llamar a herramienta (Intento {loop_count + 1})."
        )
        return "continue"

    logger.info("Decisión del enrutador: Generar respuesta final.")
    return "generate_response"


# --- 3. Ensamblaje del Grafo ---

# Global cache for the compiled agent graph (singleton pattern)
_compiled_agent_graph = None
_graph_reasoning_node_instance = None  # NUEVO: Singleton para el nodo de razonamiento
_knowledge_extraction_node_instance = (
    None  # NUEVO: Singleton para el nodo de extracción
)


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
    Nodo orquestador optimizado que ejecuta RAG, Recuperación Proactiva y la Decisión del Router en paralelo para reducir significativamente la latencia de respuesta.
    """
    logger.info("--- (Grafo) Nodo: Orquestador de Contexto Unificado (Ultra-Optimizado) ---")

    # 0. Heurística ultra-rápida (0ms) para decidir si activamos el enrutador de grafo
    # Esto elimina la necesidad de un LLM secuencial y permite lanzar el router en paralelo.
    use_graph = False
    last_message = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_message, HumanMessage):
        user_message = extract_text_content(last_message.content)
        if len(user_message.strip()) >= 5:
            user_lower = user_message.lower()
            graph_keywords = [
                "relacion", "conexion", "conecta", "vinculo", "grafo", "mapa", 
                "estructura", "depende", "impacta", "quien", "historia", 
                "contexto", "analiza", "profundo", "explic", "resum", "proyecto",
                "arquitectura", "base de datos", "sistema", "codigo"
            ]
            if any(kw in user_lower for kw in graph_keywords) or len(user_message.split()) > 6:
                use_graph = True

    # 1. Lanzamos RAG y Recuperación Proactiva en PARALELO.
    # Si la heurística lo indica, incluimos el graph_router_node también en paralelo.
    tasks = [
        rag_node(state),
        retrieve_proactive_memories_node(state),
    ]

    if use_graph:
        logger.info("🧠 Enrutador Heurístico: Activando Graph Router en paralelo.")
        tasks.append(graph_router_node(state))
    else:
        logger.info("🔍 Enrutador Heurístico: Solo RAG y Memoria Proactiva para consulta simple.")

    logger.info(f"🚀 Iniciando {len(tasks)} tareas de contexto en paralelo...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 2. Consolidar resultados en el estado
    combined_updates = {}
    router_updates = None

    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Error en rama paralela de contexto: {res}", exc_info=True)
            continue

        if isinstance(res, dict):
            # Identificamos si este resultado viene del router de grafos
            if "target_datasets" in res:
                router_updates = res

            # MERGE SEGURO: Si varios nodos devuelven 'sources', los combinamos
            for key, value in res.items():
                if (
                    key == "sources"
                    and key in combined_updates
                    and isinstance(value, list)
                    and isinstance(combined_updates[key], list)
                ):
                    combined_updates[key].extend(value)
                else:
                    combined_updates[key] = value

    # 3. Ejecutar Razonamiento de Grafo condicionalmente
    # Si el router se ejecutó y devolvió datasets, lanzamos el razonamiento del grafo
    if router_updates and router_updates.get("target_datasets"):
        logger.info(
            f"🧠 El router resolvió datasets. Ejecutando razonamiento de grafo para: {router_updates['target_datasets']}..."
        )

        graph_state = dict(state)
        graph_state.update(combined_updates)

        graph_updates = await graph_reasoning_node(graph_state)
        if isinstance(graph_updates, dict):
            for key, value in graph_updates.items():
                if (
                    key == "sources"
                    and key in combined_updates
                    and isinstance(value, list)
                    and isinstance(combined_updates[key], list)
                ):
                    combined_updates[key].extend(value)
                else:
                    combined_updates[key] = value

    return combined_updates

def create_langgraph_agent():
    """
    Crea y compila el StateGraph para el agente KAI.
    """
    workflow = StateGraph(AgentState)

    # Añadir los nodos al grafo
    workflow.add_node("proactive_memory", proactive_memory_node)
    workflow.add_node(
        "unified_context", unified_context_node
    )  # Nodo único de convergencia
    workflow.add_node("agent", call_model_node)
    workflow.add_node("action", tool_node)
    workflow.add_node("generateResponse", generate_response_node)

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
        },
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
        },
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
    if state.get("graph_db") and state.get("enhanced_memory_manager"):
        return state

    graph_db, enhanced_memory_manager = await get_shared_graph_dependencies()
    if graph_db and enhanced_memory_manager:
        state["graph_db"] = graph_db
        state["enhanced_memory_manager"] = enhanced_memory_manager
        logger.info("✅ Dependencias del grafo inicializadas y añadidas al estado.")
    else:
        logger.warning(
            "⚠️ No se pudieron obtener las dependencias del grafo. La memoria mejorada no estará disponible."
        )
        state["graph_db"] = None
        state["enhanced_memory_manager"] = None

    return state


async def graph_reasoning_node(state: AgentState):
    """
    Ejecuta el nodo de razonamiento del grafo para enriquecer el contexto.
    """
    global _graph_reasoning_node_instance

    # 1. Asegurarse de que las dependencias del grafo existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get("graph_db")

    if not graph_db:
        logger.warning(
            "Saltando nodo de razonamiento del grafo: GraphDB no está disponible."
        )
        return state

    # 2. Inicializar el nodo de razonamiento si es necesario (singleton)
    if _graph_reasoning_node_instance is None:
        _graph_reasoning_node_instance = GraphReasoningNode(graph_db)
        logger.info("✅ Instancia de GraphReasoningNode creada.")

    # 3. Invocar el nodo y obtener el contexto enriquecido
    # Pasar target_datasets si existen en el estado
    graph_output = await _graph_reasoning_node_instance.ainvoke(
        cast(dict, state), target_datasets=state.get("target_datasets")
    )

    # 4. Actualizar el estado con la salida del nodo
    updates = {}
    if graph_output:
        updates["graph_context"] = graph_output.get("graph_context")
        updates["graph_sources"] = graph_output.get("graph_sources")
        updates["mermaid_diagram"] = graph_output.get("mermaid_diagram")

        context_preview = (
            updates["graph_context"][:200] + "..."
            if updates["graph_context"]
            else "Sin contexto"
        )
        logger.info(
            f"✅ Salida del GraphReasoningNode preparada.\nContexto Previo: {context_preview}\nFuentes: {len(updates['graph_sources'] or [])}"
        )

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

    account_id = state.get("account_id")
    llm = (
        await get_llm_for_user(account_id, purpose="fast")
        if account_id
        else get_fast_llm()
    )
    if not llm:
        logger.warning(
            "No hay LLM rápido para verificar relevancia de memoria. Saltando."
        )
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
            logger.info(
                "🧠 Selective Memory: Decisión negativa. No se extraerá conocimiento de este turno."
            )
            return {}

        logger.info(
            "🧠 Selective Memory: Decisión POSITIVA. Procediendo a extracción de conocimiento."
        )

    except Exception as e:
        logger.error(f"Error en chequeo de memoria selectiva: {e}")
        # En caso de error, ser conservador y no extraer para ahorrar recursos
        return {}

    # 1. Asegurarse de que las dependencias del grafo existan
    state = await ensure_graph_dependencies(state)
    graph_db = state.get("graph_db")

    if not graph_db:
        logger.warning(
            "Saltando nodo de extracción de conocimiento: GraphDB no está disponible."
        )
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
    graph_db = state.get("graph_db")
    enhanced_memory_manager = state.get("enhanced_memory_manager")

    # Determinar el nombre del dataset de memorias del agente
    agent_memory_dataset = "Agent Memories"

    if not graph_db:
        return {"target_datasets": [agent_memory_dataset]}

    # 2. Obtener datasets disponibles
    try:
        datasets_info = await graph_db.get_available_datasets(
            state["account_id"], workspace_id=state.get("workspace_id")
        )
        if not datasets_info:
            logger.info("No hay datasets disponibles en el grafo.")
            state["target_datasets"] = [agent_memory_dataset]  # Fallback mínimo
            return state

        datasets_list = [d["name"] for d in datasets_info]
        logger.info(f"Datasets disponibles: {datasets_list}")
    except Exception as e:
        logger.error(f"Error obteniendo datasets: {e}")
        state["target_datasets"] = [agent_memory_dataset]
        return state

    # 3. Usar LLM para decidir con lógica de doble indagación
    account_id = state.get("account_id")
    llm = (
        await get_llm_for_user(account_id, purpose="fast")
        if account_id
        else get_fast_llm()
    )
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
1.  **{agent_memory_dataset}**: Selecciona este dataset si la pregunta es sobre el usuario, sus gustos, su historia personal, sus tareas, sus contactos o cualquier cosa que el asistente deba "recordar" sobre él.
2.  **Datasets de Conocimiento**: Selecciona los nombres de los datasets que correspondan a temas técnicos, documentos específicos o colecciones de información externa que el usuario haya cargado.

**Reglas**:
- Puedes seleccionar varios datasets.
- Si la pregunta es general o ambigua, incluye siempre `{agent_memory_dataset}`.
- Responde ÚNICAMENTE con una lista JSON de los nombres de los datasets relevantes.

**Respuesta (solo JSON)**:
"""
    try:
        response = await llm.ainvoke(prompt)
        content = str(response.content).strip()

        # Limpiar posible formato markdown y extraer JSON de forma robusta
        from core.utils.llm_utils import safe_json_loads

        selected = safe_json_loads(content)

        # Validar que los seleccionados existan en la lista real
        if selected is None:
            selected = []
        target_datasets = [d for d in selected if d in datasets_list]

        # Asegurar que si no se seleccionó nada, al menos use Agent Memories
        if not target_datasets:
            target_datasets = [agent_memory_dataset]

        logger.info(
            f"🎯 Router de Grafo: Datasets seleccionados para indagación: {target_datasets}"
        )
        return {
            "target_datasets": target_datasets,
            "graph_db": graph_db,
            "enhanced_memory_manager": enhanced_memory_manager,
        }
    except Exception as e:
        logger.error(f"Error en la decisión del router: {e}")
        return {
            "target_datasets": [agent_memory_dataset],
            "graph_db": graph_db,
            "enhanced_memory_manager": enhanced_memory_manager,
        }


async def should_use_graph_reasoning(state: AgentState):
    """
    DEPRECATED: La lógica de decisión heurística se ha movido directamente a unified_context_node
    para evitar el overhead de una tarea asíncrona separada y reducir la latencia general.
    Se mantiene por compatibilidad.
    """
    curr_destinations = [
        "rag_node",
        "proactive_retrieval",
    ]  # SIEMPRE ejecutamos RAG y Proactive Retrieval en paralelo

    last_message = state["messages"][-1] if state.get("messages") else None
    if not isinstance(last_message, HumanMessage):
        return curr_destinations

    user_message = extract_text_content(last_message.content)

    # 1. Filtro rápido de longitud
    if len(user_message.strip()) < 5:
        return curr_destinations

    # 2. Heurística rápida (Sin LLM)
    user_lower = user_message.lower()
    graph_keywords = [
        "relacion", "conexion", "conecta", "vinculo", "grafo", "mapa", 
        "estructura", "depende", "impacta", "quien", "historia", 
        "contexto", "analiza", "profundo", "explic", "resum", "proyecto",
        "arquitectura", "base de datos", "sistema", "codigo"
    ]
    
    if any(kw in user_lower for kw in graph_keywords) or len(user_message.split()) > 6:
        curr_destinations.append("graph_router")
        
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
        explicit_doc_ids = [
            item["id"] for item in rag_context if item.get("type") == "document"
        ]

        # Extraer topics si hay colecciones en rag_context
        collection_topics = [
            item.get("topic") or item.get("name")
            for item in rag_context
            if item.get("type") == "collection"
        ]
        if collection_topics:
            filter_topics = collection_topics

    if context and context.get("type") == "collection":
        topic = context.get("id")
        if topic:
            if not filter_topics:
                filter_topics = [topic]
            elif topic not in filter_topics:
                filter_topics.append(topic)

    try:
        logger.info(
            f"🔍 Ejecutando RAG en nodo paralelo. Workspace: {state.get('workspace_id')}"
        )

        rag_output = await get_relevant_memories(
            account_id=state["account_id"],
            query=user_message,
            workspace_id=state.get("workspace_id"),
            explicit_document_ids=explicit_doc_ids,
            filter_topics=filter_topics,
            k=10,
        )

        # --- FALLBACK PARA CONTEXTO EXPLÍCITO ---
        # Si el usuario seleccionó documentos pero la búsqueda semántica no encontró nada relevante
        # (ej: por una pregunta muy genérica), recuperamos proactivamente los primeros fragmentos.
        if not (rag_output and rag_output.sources) and explicit_doc_ids:
            logger.info(
                f"⚠️ RAG semántico no encontró resultados para {len(explicit_doc_ids)} documentos. Aplicando fallback de fragmentos secuenciales."
            )
            fallback_docs = await get_document_chunks(
                account_id=state["account_id"],
                document_ids=explicit_doc_ids,
                limit=10,
                workspace_id=state.get("workspace_id"),
            )

            if fallback_docs:
                from core.citation_models import create_document_source

                sources_dicts = []
                for i, doc in enumerate(fallback_docs):
                    source = create_document_source(
                        source_id=i + 1,
                        title=doc.metadata.get("file_name", "Documento"),
                        file_path=doc.metadata.get("document_id", ""),
                        snippet=doc.page_content,
                        metadata=doc.metadata,
                    )
                    sources_dicts.append(source.dict())

                logger.info(
                    f"✅ Fallback completado. {len(sources_dicts)} fragmentos secuenciales recuperados."
                )
                return {"sources": sources_dicts}

        if (
            rag_output and rag_output.sources
        ):  # Convertir fuentes a diccionarios para el estado
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
    llm: BaseChatModel,
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
        logger.info(
            "Invocando LLM para extracción de memoria proactiva (en segundo plano)..."
        )
        response = await llm.ainvoke(prompt)
        response_content = (
            response.content if hasattr(response, "content") else str(response)
        )

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

        logger.info(
            f"Se extrajeron {len(memories_to_save)} memorias proactivas (en segundo plano): {memories_to_save}"
        )

        for memory_content in memories_to_save:
            await add_memory_to_vector_db(
                account_id=account_id,
                content=memory_content,
                type="user_memory_proactive_llm",
                workspace_id=workspace_id,
                telegram_id=str(telegram_id) if telegram_id else None,
                thread_id=thread_id,
            )
            logger.info(
                f"Memoria proactiva guardada (en segundo plano) para la cuenta {account_id}: '{memory_content}'"
            )

        if account_id:
            from knowledge_graph.memory_graph_processor import (
                schedule_memory_graph_processing,
            )

            asyncio.create_task(schedule_memory_graph_processing(account_id=account_id))
            logger.info(
                f"Procesamiento del grafo de conocimiento programado (en segundo plano) tras memoria proactiva para la cuenta {account_id}."
            )

    except json.JSONDecodeError:
        logger.error(
            f"Error de decodificación JSON en memoria proactiva (en segundo plano). Respuesta del LLM no fue un JSON válido: {response_content}"
        )
    except Exception as e:
        logger.error(
            f"Error en la tarea de memoria proactiva en segundo plano: {e}",
            exc_info=True,
        )


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
        logger.info(
            "Saltando memoria proactiva: contenido del usuario muy corto o vacío."
        )
        calc_turn = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
        return {"turn_count": calc_turn}

    # 2. Calcular el contador de turnos real basado en el número de mensajes del usuario en el historial
    # Esto asegura que el contador sea persistente incluso si el estado del grafo se reinicia
    current_turn_count = len(
        [m for m in state["messages"] if isinstance(m, HumanMessage)]
    )
    logger.info(
        f"Contador de turnos real (basado en mensajes humanos): {current_turn_count}"
    )

    # 3. Decidir si es momento de procesar la memoria proactiva (cada 5 turnos)
    if current_turn_count % 5 != 0:
        logger.info("Saltando memoria proactiva: no es un turno de procesamiento.")
        return {"turn_count": current_turn_count, "loop_count": 0}

    # 4. Preparar el LLM
    account_id = state.get("account_id")
    llm = (
        await get_llm_for_user(account_id, purpose="fast")
        if account_id
        else get_fast_llm()
    )
    if not llm:
        logger.warning(
            "No hay un LLM rápido disponible para la memoria proactiva. Saltando nodo."
        )
        return state

    # 5. Formatear historial para el prompt (últimos 10 mensajes)
    # Excluimos el mensaje actual del usuario para no duplicar en "Último mensaje del usuario"
    history_for_prompt = "\n".join(
        [
            f"{'Usuario' if isinstance(m, HumanMessage) else 'Asistente'}: {extract_text_content(m.content)}"
            for m in state["messages"][-11:-1]
        ]
    )  # Últimos 10 mensajes excluyendo el actual

    # 6. Programar la tarea de procesamiento de memoria en segundo plano
    asyncio.create_task(
        _process_proactive_memory_task(
            account_id=state["account_id"],
            workspace_id=state.get("workspace_id"),
            telegram_id=state.get("telegram_id"),
            thread_id=state.get("thread_id"),
            user_content=user_content,
            history_for_prompt=history_for_prompt,
            llm=llm,
        )
    )
    logger.info(
        "Tarea de memoria proactiva programada en segundo plano. El grafo continuará su ejecución."
    )

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
        logger.info(
            f"🔍 Buscando específicamente memorias proactivas para: '{user_query[:50]}...'"
        )

        proactive_output = await get_relevant_memories(
            account_id=state["account_id"],
            query=user_query,
            workspace_id=state.get("workspace_id"),
            content_types=["user_memory_proactive_llm"],  # Solo buscar este tipo
            k=5,  # Top 5 es suficiente
            similarity_threshold=0.65,  # Un poco más permisivo
        )

        if proactive_output and proactive_output.sources:
            # Marcar estas fuentes para que el LLM sepa que son proactivas/importantes
            sources_dicts = []
            for s in proactive_output.sources:
                s_dict = s.dict()
                s_dict["metadata"]["is_proactive"] = True
                s_dict["metadata"]["source_type_label"] = "Memoria Proactiva"
                sources_dicts.append(s_dict)

            logger.info(
                f"✅ Encontradas {len(sources_dicts)} memorias proactivas relevantes."
            )
            return {"sources": sources_dicts}
        else:
            logger.info("No se encontraron memorias proactivas relevantes.")
            return {"sources": []}

    except Exception as e:
        logger.error(f"❌ Error recuperando memorias proactivas: {e}", exc_info=True)
        return {"sources": []}


async def run_custom_user_heartbeat(
    account_id: str,
    workspace_id: Optional[str] = None,
    allowed_tools: Optional[list] = None,
    heartbeat_id: Optional[str] = None,
) -> str:
    """
    Ejecuta el heartbeat personalizado del usuario utilizando el agente LangGraph.
    Crea un hilo dedicado y ejecuta las instrucciones del usuario.
    """
    from core.database import CustomHeartbeat

    instructions = ""
    hb_name = "Heartbeat Personalizado"

    async with DBSession(SessionLocal) as db:
        if heartbeat_id:
            # Buscar heartbeat específico
            hb = await db.get(CustomHeartbeat, uuid.UUID(heartbeat_id))
            if not hb or not hb.is_active:
                return f"Heartbeat '{heartbeat_id}' no encontrado o inactivo."
            instructions = hb.instructions
            hb_name = hb.name
            if allowed_tools is None:
                allowed_tools = hb.allowed_tools or []
        else:
            # Fallback a la cuenta
            account = await db.get(Account, uuid.UUID(account_id))
            if not account or not account.custom_heartbeat_instructions:
                return "No hay heartbeat personalizado configurado."
            instructions = account.custom_heartbeat_instructions
            if allowed_tools is None:
                allowed_tools = account.custom_heartbeat_allowed_tools or []

        if allowed_tools:
            instructions += f"\n\nATENCIÓN: Para esta tarea, SOLO tienes permitido utilizar las siguientes herramientas: {', '.join(allowed_tools)}. Limita tu ejecución a estas capacidades."

    logger.info(
        f"🚀 Iniciando heartbeat personalizado '{hb_name}' para la cuenta {account_id}"
    )

    # Reutilizar el hilo único de heartbeat en vez de crear uno nuevo cada vez
    if heartbeat_id:
        thread_id = await get_or_create_specific_heartbeat_thread(
            account_id, heartbeat_id, hb_name
        )
    else:
        thread_id = await get_or_create_heartbeat_thread(account_id)

    # Importaciones necesarias
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_community.chat_message_histories import PostgresChatMessageHistory

    agent_app = get_langgraph_agent()

    initial_human_message = HumanMessage(content=instructions)
    initial_state: AgentState = {
        "messages": [initial_human_message],
        "account_id": account_id,
        "task_id": str(uuid.uuid4()),
        "telegram_id": None,
        "workspace_id": workspace_id,
        "rag_context": None,
        "sources": [],
        "thread_id": thread_id,
        "context": {"type": "custom_heartbeat"},
        "loop_count": 0,
        "turn_count": 0,
        "tool_error_counts": {},
        "graph_db": None,
        "enhanced_memory_manager": None,
        "graph_context": None,
        "graph_sources": None,
        "mermaid_diagram": None,
        "target_datasets": None,
    }

    db_sync_url = settings.database_url.replace("+psycopg", "")
    chat_message_history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=thread_id,
        table_name="langchain_chat_history",
    )

    sanitized_human_message = HumanMessage(
        content=sanitize_json_content(initial_human_message.content),
        additional_kwargs=initial_human_message.additional_kwargs,
    )
    await chat_message_history.aadd_messages([sanitized_human_message])

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}

    try:
        final_graph_state = await agent_app.ainvoke(initial_state, config=config)

        final_node_output = final_graph_state.get("generateResponse", {})
        final_messages = final_node_output.get("messages", [])

        final_ai_message = next(
            (msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)),
            None,
        )

        if final_ai_message:
            # Reconstruir content_parts para persistencia en base de datos
            ai_content_parts: List[Dict[str, Any]] = []

            # 1. Extraer razonamiento si existe
            reasoning_text = final_ai_message.additional_kwargs.get(
                "reasoning"
            ) or final_ai_message.additional_kwargs.get("think")
            if reasoning_text:
                ai_content_parts.append(
                    {"type": "reasoning", "content": reasoning_text}
                )

            # 2. Identificar el último HumanMessage para procesar solo el turno actual
            last_human_idx = -1
            for idx in range(len(final_messages) - 1, -1, -1):
                if isinstance(final_messages[idx], HumanMessage):
                    last_human_idx = idx
                    break

            # 3. Extraer mensajes intermedios del turno actual
            intermediate_messages = []
            if last_human_idx != -1:
                intermediate_messages = final_messages[last_human_idx + 1 : -1]

            # 4. Agrupar resultados de herramientas
            tool_results = {}
            for msg in intermediate_messages:
                if isinstance(msg, ToolMessage):
                    tool_results[msg.tool_call_id] = msg

            # 5. Parsear llamadas de herramientas
            for msg in intermediate_messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_call_id = tool_call.get("id")
                        tool_name = tool_call.get("name")

                        tool_msg = tool_results.get(tool_call_id)
                        status = "end"
                        content = f"Usando {tool_name}..."
                        pty_session = None

                        if tool_msg:
                            content = str(tool_msg.content)
                            if tool_name == "terminal_executor":
                                import re

                                match = re.search(r'data-session-id="([^"]+)"', content)
                                if match:
                                    pty_session = {"session_id": match.group(1)}
                                    match_cmd = re.search(
                                        r'data-cmd="([^"]+)"', content
                                    )
                                    if match_cmd:
                                        import html

                                        pty_session["command"] = html.unescape(
                                            match_cmd.group(1)
                                        )
                        else:
                            status = "error"

                        ai_content_parts.append(
                            {
                                "type": "tool_call",
                                "content": content,
                                "tool_name": tool_name,
                                "status": status,
                                "pty_session": pty_session,
                                "id": tool_call_id,
                            }
                        )

            # 6. Extraer texto final del AI
            def _extract_text(message: AIMessage) -> str:
                if isinstance(message.content, str):
                    return message.content
                if isinstance(message.content, list):
                    text = ""
                    for part in message.content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text += part.get("text", "")
                    return text
                return ""

            final_text = _extract_text(final_ai_message)
            if final_text:
                ai_content_parts.append({"type": "text", "content": final_text})

            # 7. Obtener la sesión PTY para el nivel raíz si aplica
            root_pty_session = None
            for part in ai_content_parts:
                if part.get("type") == "tool_call" and part.get("pty_session"):
                    root_pty_session = part["pty_session"]
                    break

            # 8. Modificar additional_kwargs
            additional_kwargs = dict(final_ai_message.additional_kwargs)
            additional_kwargs["content_parts"] = ai_content_parts
            if root_pty_session:
                additional_kwargs["pty_session"] = root_pty_session

            sanitized_ai_message = AIMessage(
                content=sanitize_json_content(final_ai_message.content),
                tool_calls=final_ai_message.tool_calls,
                additional_kwargs=additional_kwargs,
            )
            await chat_message_history.aadd_messages([sanitized_ai_message])

            # Enviar notificación websocket
            await send_personal_message(
                account_id,
                {
                    "type": "custom_heartbeat_completed",
                    "thread_id": thread_id,
                    "message": "Heartbeat personalizado ejecutado con éxito.",
                },
            )
            return f"Heartbeat personalizado completado exitosamente en el hilo {thread_id}."

        return "El agente no devolvió ninguna respuesta."
    except Exception as e:
        logger.error(f"Error ejecutando heartbeat personalizado: {e}", exc_info=True)
        return f"Error: {e}"
