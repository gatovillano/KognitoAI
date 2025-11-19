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

# --- Langchain Core ---
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.agents import AgentAction, AgentFinish # Importar AgentAction y AgentFinish
from sqlalchemy import update
from langchain_core.messages import ToolMessage

# --- Módulos del Proyecto ---
from core.tools import get_all_langchain_tools
from core.memory_manager import get_user_profile, add_memory_to_vector_db
from core.context_cache import get_cached_context, cache_context
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession
#from utils.helpers import sanitize_html
from core.config import settings
from core.citation_models import ToolOutputWithSources, Source
from core.llm_manager import get_main_llm, get_fast_llm
from core.prompts import SUMMARIZATION_PROMPT, THREAD_TITLE_PROMPT
from core.enhanced_memory_manager import EnhancedMemoryManager
from knowledge_graph.graph_database import GraphDB

# --- Claves para estado temporal ---
from utils.image_generation import GENERATED_IMAGE_KEY
# from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.websocket_manager import send_personal_message # Importar aquí para evitar circular imports

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




# ==============================================================================
# SECCIÓN 1: DEFINICIÓN DEL ESTADO DEL GRAFO (NUEVO)
# ==============================================================================

class AgentState(TypedDict):
    """
    Define la estructura de datos para el estado que fluye a través del grafo.
    """
    # Mensajes de la conversación (el historial)
    messages: List[BaseMessage]
    # El ID de la cuenta, para pasarlo a las herramientas
    account_id: str
    # El ID de Telegram, también para las herramientas
    telegram_id: Optional[int]
    # El ID del workspace para el contexto
    workspace_id: Optional[str]
    # El contexto RAG explícito seleccionado por el usuario
    rag_context: Optional[List[Dict[str, Any]]]
    # Las fuentes recuperadas para la citación
    sources: Optional[List[Dict[str, Any]]]
    # El ID de la tarea para los eventos de WebSocket
    task_id: Optional[str]
    # El ID del hilo de chat
    thread_id: Optional[str]

# ==============================================================================
# SECCIÓN 2: MANEJO DE CONTEXTO Y MEMORIA
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
            new_title = response.content.strip() if hasattr(response, 'content') else str(response).strip()
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
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )
        messages = await chat_message_history.aget_messages()
        
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
            new_title = response.content.strip() if hasattr(response, 'content') else str(response).strip()
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
        await asyncio.gather(*tasks)

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
    
    # 1. Construir el prompt del sistema dinámicamente
    user_message = extract_text_content(state["messages"][-1].content)
    user_profile = await get_user_profile(state['account_id'])

    rag_context = state.get("rag_context")
    document_ids_for_rag = None
    document_names_for_rag = None # Nuevo
    has_explicit_rag_context = False

    if rag_context:
        logger.info(f"Aplicando RAG explícito con {len(rag_context)} item(s) de contexto. Se priorizará la búsqueda en estos documentos.")
        document_ids_for_rag = [item['id'] for item in rag_context if item.get('type') == 'document']
        document_names_for_rag = [item.get('name') for item in rag_context if item.get('type') == 'document' and item.get('name')] # Manejar 'name' de forma segura
        has_explicit_rag_context = True
    # --- INICIO DE LA LÓGICA DE MEMORIA MEJORADA ---
    # Se ejecuta solo si no venimos de una llamada a herramienta, para no sobrescribir sus fuentes.
    last_message = state["messages"][-1] if state["messages"] else None
    is_after_tool_call = isinstance(last_message, ToolMessage)

    relevant_memories_text = ""
    final_sources_for_state = state.get('sources', []) # Mantener las fuentes existentes si las hay

    if not is_after_tool_call:
        logger.info("Ejecutando búsqueda RAG del agente (no es una vuelta de herramienta).")
        graph_db = GraphDB(
            uri=str(settings.neo4j_uri) if settings.neo4j_uri else "",
            user=str(settings.neo4j_user) if settings.neo4j_user else "",
            password=str(settings.neo4j_password) if settings.neo4j_password else ""
        )
        graph_db.connect()
        enhanced_memory_manager = EnhancedMemoryManager(graph_db=graph_db)

        enhanced_context = await enhanced_memory_manager.get_enhanced_context(
            user_query=user_message,
            user_id=state['account_id'],
            workspace_id=state.get('workspace_id'),
            explicit_document_ids=document_ids_for_rag
        )

        all_sources_objects = []
        if enhanced_context:
            traditional_sources_raw = enhanced_context.get('sources', {}).get('traditional_embeddings', {}).get('results', [])
            all_sources_objects.extend(traditional_sources_raw)

            insights = enhanced_context.get('enhanced_insights', [])
            for insight in insights:
                all_sources_objects.append(Source(
                    id=f"insight_{uuid.uuid4().hex[:10]}",
                    title=f"Insight del Grafo: {insight.get('type', 'Desconocido')}",
                    snippet=insight.get('description', 'Sin descripción.'),
                    type='graph', metadata=insight, url=f"graph://insight_{uuid.uuid4().hex[:10]}"
                ))

            paths = enhanced_context.get('reasoning_paths', [])
            for path in paths:
                steps_desc = "\\n".join([f" - {s.get('from', '?')} -> {s.get('to', '?')}" for s in path.get('steps', [])])
                snippet = f"{path.get('description', 'Sin descripción.')}\\n{steps_desc}"
                all_sources_objects.append(Source(
                    id=f"path_{uuid.uuid4().hex[:10]}",
                    title=f"Ruta de Razonamiento: {path.get('type', 'Desconocido')}",
                    snippet=snippet, type='graph', metadata=path, url=f"graph://path_{uuid.uuid4().hex[:10]}"
                ))

            # Re-indexar todas las fuentes con IDs numéricos secuenciales
            relevant_memories_parts = []
            final_sources_for_state = [] # Reiniciar si se encontraron nuevas fuentes RAG
            for i, source_obj in enumerate(all_sources_objects, start=1):
                relevant_memories_parts.append(f"[{i}] {source_obj.snippet}")
                source_dict = source_obj.dict()
                if hasattr(source_obj, 'id'):
                    source_dict['original_id'] = source_obj.id
                source_dict['id'] = i
                final_sources_for_state.append(source_dict)
            
            relevant_memories_text = "\\n\\n".join(relevant_memories_parts)
            state['sources'] = final_sources_for_state # Actualizar el estado con las nuevas fuentes RAG
            logger.info(f"✅ {len(final_sources_for_state)} fuentes combinadas y re-indexadas añadidas al estado.")
        else:
            logger.info("No se generó contexto enriquecido.")
    else:
        logger.info("Saltando la búsqueda RAG del agente porque es una vuelta de herramienta. Manteniendo fuentes existentes.")
        # Si ya hay fuentes en el estado (de tool_node), usarlas para el prompt
        if final_sources_for_state:
            relevant_memories_parts = []
            for i, source_dict in enumerate(final_sources_for_state, start=1):
                relevant_memories_parts.append(f"[{i}] {source_dict.get('snippet', '')}")
            relevant_memories_text = "\\n\\n".join(relevant_memories_parts)
    # --- FIN DE LA LÓGICA DE MANEJO DE FUENTES ---
        
    from core.prompt_manager import PromptManager
    prompt_manager = PromptManager(settings={"default_system_prompt": settings.default_system_prompt})
        
    tools = await get_all_langchain_tools(
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id')
    )
    
    workspace_prompt = None
    system_prompt_content = prompt_manager.build_system_prompt(
        user_profile=user_profile,
        relevant_memories=relevant_memories_text,
        summary_string="",
        custom_prompt_from_profile=str(user_profile.system_prompt) if user_profile and user_profile.system_prompt else None,
        workspace_prompt=None,
        tools=tools,
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id'),
        user_message=user_message,
        has_explicit_rag_context=has_explicit_rag_context,
        explicit_document_names=[name for name in document_names_for_rag if name is not None] if document_names_for_rag else None
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
                workspace_prompt=workspace_prompt,
                tools=tools,
                account_id=state['account_id'],
                telegram_id=state.get('telegram_id'),
                user_message=user_message,
                has_explicit_rag_context=has_explicit_rag_context,
                explicit_document_names=[str(name) for name in document_names_for_rag if name is not None] if document_names_for_rag else None
            )
    
    llm = get_main_llm()
    if not llm:
        raise ValueError("El LLM principal no está disponible.")
        
    logger.debug(f"DEBUG (agent.py - call_model_node): System Prompt final antes de LLM: {system_prompt_content}")
    llm_with_tools = cast(ChatGoogleGenerativeAI, llm).bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_content),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm_with_tools

    full_ai_message_content = ""
    tool_calls_from_llm = []
    final_response_message = None
    
    target_account_id = "telegram_bot_service" if state.get('telegram_id') else state['account_id']
    conn_type = "chat" if state.get('telegram_id') else None

    async for chunk in chain.astream({"messages": state["messages"]}):
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
                "chunk": str(chunk.content or "")
            }, connection_type=conn_type)
            
            final_response_message = chunk

    logger.debug(f"DEBUG (agent.py - call_model_node): Respuesta cruda del LLM (acumulada): {full_ai_message_content}")
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
        "messages": state["messages"] + [final_ai_message],
        "sources": final_sources_for_state # Asegurarse de que las fuentes se propaguen en el estado
    }
async def generate_response_node(state: AgentState):
    """
    Nodo final que simplemente pasa el estado para que el consumidor lo reciba.
    Actúa como un punto de salida nombrado que 'api/chat.py' puede escuchar.
    """
    logger.info("--- (Grafo) Nodo: Generar Respuesta ---")
    if isinstance(state["messages"][-1], AIMessage):
        logger.debug(f"DEBUG (agent.py - generate_response_node): AIMessage final del agente: {state['messages'][-1].content}")
    return {"messages": state["messages"]}

async def tool_node(state: AgentState):
    """
    Ejecuta las herramientas llamadas por el agente y añade los resultados al estado.
    MODIFICADO: Ahora también extrae y propaga las 'sources' de las herramientas.
    """
    logger.info("--- (Grafo) Nodo: Llamar Herramienta ---")
    if not isinstance(state["messages"][-1], AIMessage):
        return {"messages": state["messages"]}

    agent_message = state["messages"][-1]
    tool_calls = agent_message.tool_calls
    
    if not tool_calls:
        return {"messages": state["messages"]}

    tools = await get_all_langchain_tools(
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id')
    )
    tool_map = {tool.name: tool for tool in tools}

    # Redundancia eliminada
    tool_messages = []
    # Cargar las fuentes existentes del estado para poder añadir nuevas
    current_sources = state.get("sources") or []
    # Usar un set para evitar duplicados basados en la URL
    existing_urls = {s['url'] for s in current_sources if 'url' in s and s['url']}

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args")
        
        # Enviar evento tool_start
        target_account_id = "telegram_bot_service" if state.get('telegram_id') else state['account_id']
        conn_type = "chat" if state.get('telegram_id') else None
        logger.debug(f"DEBUG (agent.py): Enviando tool_start para taskId {state.get('task_id')}, tool {tool_name}")
        await send_personal_message(target_account_id, {
            "type": "tool_start",
            "taskId": state.get("task_id"),
            "toolName": tool_name,
        }, connection_type=conn_type)

        if tool_name not in tool_map:
            logger.error(f"Herramienta '{tool_name}' no encontrada.")
            tool_messages.append(ToolMessage(
                content=f"Error: Herramienta '{tool_name}' no encontrada.",
                tool_call_id=tool_call.get("id")
            ))
            # Enviar evento tool_end con error
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "toolName": tool_name,
                "result": f"Error: Herramienta '{tool_name}' no encontrada.",
                "error": True,
                "sources": []
            }, connection_type=conn_type)
            continue
            
        selected_tool = tool_map[tool_name]
        
        # --- INYECCIÓN DE ATRIBUTOS DE CONTEXTO ---
        selected_tool.account_id = state['account_id']  # type: ignore
        selected_tool.workspace_id = state.get('workspace_id')  # type: ignore
        selected_tool.telegram_id = state.get('telegram_id')  # type: ignore

        if hasattr(selected_tool, 'thread_id'):
            selected_tool.thread_id = state['messages'][-1].additional_kwargs.get('thread_id')  # type: ignore
        # --- FIN INYECCIÓN ---

        try:
            logger.info(f"Ejecutando herramienta '{tool_name}' con argumentos: {tool_args}")
            # La salida de la herramienta ahora siempre es un dict (model_dump de ToolOutputWithSources)
            output_dump = await selected_tool.ainvoke(tool_args)
            logger.info(f"Resultado de la herramienta '{tool_name}': {output_dump}")
            
            # Asegurar que tool_output siempre sea un objeto ToolOutputWithSources válido
            tool_output: ToolOutputWithSources
            context_content: str = ""
            sources_list = []

            if isinstance(output_dump, str):
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
                    # Caso 2: Salida estándar con 'context_for_llm'
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
                logger.info(f"La herramienta '{tool_name}' devolvió {len(tool_output.sources)} fuentes. Reemplazando fuentes existentes.")
                # Sobrescribe completamente las fuentes actuales con las de la herramienta
                current_sources = [s.dict() for s in tool_output.sources]
                # Asigna las mismas fuentes para el evento websocket
                tool_sources_to_add = current_sources
            else:
                # Si la herramienta no devuelve fuentes, nos aseguramos de que no se añada nada
                tool_sources_to_add = []
            
            tool_messages.append(ToolMessage(
                content=tool_content_for_llm,
                tool_call_id=tool_call.get("id")
            ))
            
            # Enviar evento tool_end con éxito
            logger.debug(f"DEBUG (agent.py): Enviando tool_end (success) para taskId {state.get('task_id')}, tool {tool_name}")
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "toolName": tool_name,
                "result": tool_content_for_llm,
                "sources": tool_sources_to_add, # Enviar solo las fuentes generadas por esta herramienta
            }, connection_type=conn_type)

        except Exception as e:
            logger.error(f"Error al ejecutar la herramienta {tool_name}: {e}", exc_info=True)
            tool_messages.append(ToolMessage(
                content=f"Error: {e}",
                tool_call_id=tool_call.get("id")
            ))
            # Enviar evento tool_end con error
            logger.debug(f"DEBUG (agent.py): Enviando tool_end (error) para taskId {state.get('task_id')}, tool {tool_name}")
            await send_personal_message(target_account_id, {
                "type": "tool_end",
                "taskId": state.get("task_id"),
                "toolName": tool_name,
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
    return {"messages": state["messages"] + tool_messages, "sources": final_sources_with_sequential_ids}

# --- 2. Enrutador ---

def should_continue(state: AgentState) -> str:
    """
    Decide si continuar con la ejecución de herramientas o finalizar.
    """
    logger.info("--- (Grafo) Nodo: Enrutamiento ---")
    last_message = state["messages"][-1]
    
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info("Decisión del enrutador: Llamar a herramienta.")
        return "continue"
    
    logger.info("Decisión del enrutador: Generar respuesta final.")
    return "generate_response"

# --- 3. Ensamblaje del Grafo ---

def create_langgraph_agent():
    """
    Crea y compila el StateGraph para el agente KAI.
    """
    workflow = StateGraph(AgentState)

    # Añadir los nodos al grafo
    workflow.add_node("agent", call_model_node)
    workflow.add_node("action", tool_node)
    workflow.add_node("generateResponse", generate_response_node) # El nombre coincide con lo que espera api/chat.py

    # Definir las aristas (el flujo de trabajo)
    workflow.set_entry_point("agent")
    
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
    # memory = MemorySaver() # Se añadirá cuando se integre el historial
    return workflow.compile()
