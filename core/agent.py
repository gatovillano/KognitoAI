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
from core.memory_manager import get_user_profile, get_relevant_memories, add_memory_to_vector_db
from core.context_cache import get_cached_context, cache_context
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession
#from utils.helpers import sanitize_html
from core.config import settings
from core.llm_manager import get_main_llm, get_fast_llm
from core.prompts import SUMMARIZATION_PROMPT, THREAD_TITLE_PROMPT
# --- Claves para estado temporal ---
from utils.image_generation import GENERATED_IMAGE_KEY
# from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
        await chat_message_history.aadd_messages([summary_message])
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
            await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(title=new_title))
            await db.commit()
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
    relevant_memories = await get_relevant_memories(
        state['account_id'],
        user_message,
        k=5,
        workspace_id=state.get('workspace_id')
    )
    
    from core.prompt_manager import PromptManager
    prompt_manager = PromptManager(settings={"default_system_prompt": settings.default_system_prompt})
    
    tools = get_all_langchain_tools(
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id')
    )
    
    workspace_prompt = None
    if state.get('workspace_id'):
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(state.get('workspace_id')))
            if workspace and workspace.system_prompt:
                workspace_prompt = str(workspace.system_prompt)

    system_prompt_content = prompt_manager.build_system_prompt(
        user_profile=user_profile,
        relevant_memories=relevant_memories,
        summary_string="",
        custom_prompt_from_profile=str(user_profile.system_prompt) if user_profile and user_profile.system_prompt else None,
        workspace_prompt=workspace_prompt,
        tools=tools,
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id'),
        user_message=user_message
    )
    
    # 2. Preparar el LLM con herramientas
    llm = get_main_llm()
    if not llm:
        raise ValueError("El LLM principal no está disponible.")
        
    llm_with_tools = cast(ChatGoogleGenerativeAI, llm).bind_tools(tools)
    
    # 3. Construir el prompt y la cadena de ejecución
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_content),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    chain = prompt | llm_with_tools
    
    # 4. Invocar la cadena y añadir la respuesta al estado
    response = await chain.ainvoke({"messages": state["messages"]})
    
    return {"messages": state["messages"] + [response]}

async def generate_response_node(state: AgentState):
    """
    Nodo final que simplemente pasa el estado para que el consumidor lo reciba.
    Actúa como un punto de salida nombrado que 'api/chat.py' puede escuchar.
    """
    logger.info("--- (Grafo) Nodo: Generar Respuesta ---")
    return {"messages": state["messages"]}

async def tool_node(state: AgentState):
    """
    Ejecuta las herramientas llamadas por el agente y añade los resultados al estado.
    """
    logger.info("--- (Grafo) Nodo: Llamar Herramienta ---")
    if not isinstance(state["messages"][-1], AIMessage):
        return {"messages": state["messages"]}

    agent_message = state["messages"][-1]
    tool_calls = agent_message.tool_calls
    
    if not tool_calls:
        return {"messages": state["messages"]}

    tools = get_all_langchain_tools(
        account_id=state['account_id'],
        telegram_id=state.get('telegram_id')
    )
    tool_map = {tool.name: tool for tool in tools}

    tool_messages = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args")
        
        if tool_name not in tool_map:
            logger.error(f"Herramienta '{tool_name}' no encontrada.")
            tool_messages.append(ToolMessage(
                content=f"Error: Herramienta '{tool_name}' no encontrada.",
                tool_call_id=tool_call.get("id")
            ))
            continue
            
        selected_tool = tool_map[tool_name]
        
        # --- INYECCIÓN DE ATRIBUTOS DE CONTEXTO ---
        # Asegurarse de que los IDs de contexto se pasen como atributos de la instancia de la herramienta
        # Esto es crucial para la estandarización que ya tienes definida.
        selected_tool.account_id = state['account_id']
        selected_tool.workspace_id = state.get('workspace_id')
        selected_tool.telegram_id = state.get('telegram_id')
        # Asumiendo que thread_id está en additional_kwargs del último mensaje
        selected_tool.thread_id = state['messages'][-1].additional_kwargs.get('thread_id') 
        # --- FIN INYECCIÓN ---

        try:
            logger.info(f"Ejecutando herramienta '{tool_name}' con argumentos: {tool_args}")
            output = await selected_tool.ainvoke(tool_args)
            logger.info(f"Resultado de la herramienta '{tool_name}': {output}")
            
            # Asegurarse de que la salida sea un string
            if not isinstance(output, str):
                output = json.dumps(output, ensure_ascii=False)

            tool_messages.append(ToolMessage(
                content=output,
                tool_call_id=tool_call.get("id")
            ))
        except Exception as e:
            logger.error(f"Error al ejecutar la herramienta {tool_name}: {e}", exc_info=True)
            tool_messages.append(ToolMessage(
                content=f"Error: {e}",
                tool_call_id=tool_call.get("id")
            ))
            
    return {"messages": state["messages"] + tool_messages}

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
