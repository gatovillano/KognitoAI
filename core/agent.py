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
from typing import Optional, List, Any
import uuid
import os

# --- Langchain Core ---
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models.base import BaseLanguageModel
from sqlalchemy import update

# --- Módulos del Proyecto ---
from telegram_client.tools import get_all_langchain_tools
from core.memory_manager import get_user_profile, get_relevant_memories
from core.database import SessionLocal, Account, ChatThread
from utils.db_session import DBSession
from utils.helpers import sanitize_html
from core.config import settings

# --- Claves para estado temporal ---
from utils.image_generation import GENERATED_IMAGE_KEY
from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select
from sqlalchemy.orm import selectinload
# --- Configuración del Logger ---
logger = logging.getLogger(__name__)

# --- Instancias Globales de LLM ---
# Se inicializan en `initialize_llms` al arrancar el servidor.
_main_agent_llm_instance: Optional[BaseLanguageModel] = None
_fast_task_llm_instance: Optional[BaseLanguageModel] = None

# ==============================================================================
# SECCIÓN 1: INICIALIZACIÓN DE MODELOS
# ==============================================================================

async def initialize_llms():
    """
    Inicializa las instancias globales de los LLMs (principal y de tareas rápidas).
    Esta función se llama una vez al arrancar el `web_server`.
    """
    global _main_agent_llm_instance, _fast_task_llm_instance
    
    if not settings.google_api_key:
        logger.error("¡ERROR FATAL! GOOGLE_API_KEY no está configurada. El agente no puede funcionar.")
        raise ValueError("No se ha configurado la API key de Google.")

    try:
        logger.info(f"🛠️ Inicializando LLM principal del agente (ChatGoogleGenerativeAI - {settings.google_main_model_name})...")
        main_llm = ChatGoogleGenerativeAI(
            model=settings.google_main_model_name,
            temperature=settings.llm_temperature,
            google_api_key=settings.google_api_key,
            streaming=True,  # Habilita streaming real
        )
        await main_llm.ainvoke("Test prompt")
        _main_agent_llm_instance = main_llm
        logger.info("✅ LLM principal del agente inicializado.")
    except Exception as e:
        logger.error(f"❌ FATAL: Fallo al inicializar el LLM principal: {e}", exc_info=True)
        raise

    try:
        logger.info(f"🛠️ Inicializando LLM para tareas rápidas (ChatGoogleGenerativeAI - {settings.google_summary_model_name})...")
        fast_llm = ChatGoogleGenerativeAI(
            model=settings.google_summary_model_name,
            temperature=0.0,
            google_api_key=settings.google_api_key,
            streaming=True,  # Habilita streaming real
        )
        await fast_llm.ainvoke("Test prompt")
        _fast_task_llm_instance = fast_llm
        logger.info("✅ LLM para tareas rápidas inicializado.")
    except Exception as e:
        logger.warning(f"⚠️ Fallo al inicializar el LLM para tareas rápidas. Se usará el principal como fallback: {e}")
        _fast_task_llm_instance = _main_agent_llm_instance

# ==============================================================================
# SECCIÓN 2: MANEJO DE CONTEXTO Y MEMORIA
# ==============================================================================

async def _get_user_context(account_id: str, user_message: str) -> str:
    """
    Recupera el perfil del usuario y las memorias relevantes para una consulta dada.

    Args:
        account_id: El ID universal de la cuenta del usuario.
        user_message: El mensaje actual del usuario para buscar memorias relevantes.

    Returns:
        Una cadena de texto formateada con el contexto del usuario.
    """
    try:
        profile = await get_user_profile(account_id)
        profile_info = []
        if profile:
            if profile.nombre: profile_info.append(f"- Nombre: {profile.nombre}")
            if profile.gustos: profile_info.append(f"- Gustos: {profile.gustos}")
            if profile.intereses: profile_info.append(f"- Intereses: {profile.intereses}")
            if profile.otros_datos: profile_info.append(f"- Otros datos: {profile.otros_datos}")

        user_context_parts = [
            "--- Información Relevante sobre el Usuario y su Contexto ---",
            "Información de Perfil del Usuario:",
            "\n".join(profile_info) if profile_info else "No hay información de perfil disponible."
        ]

        # Evitar búsqueda de memoria para mensajes muy cortos o saludos
        ignore_keywords = ['hola', 'hey', 'qué tal', 'cómo estás', 'gracias', 'ok', 'dale']
        if len(user_message.strip().split()) < 3 or any(kw in user_message.lower() for kw in ignore_keywords):
            relevant_memories = ""
        else:
            relevant_memories = await get_relevant_memories(account_id, user_message, k=5)

        if relevant_memories and "No se encontraron memorias relevantes" not in relevant_memories:
            user_context_parts.append("\nMemorias y Documentos Relevantes (Base de Conocimiento):")
            user_context_parts.append(relevant_memories)

        user_context_parts.append("---------------------------------------------------------")
        return "\n".join(user_context_parts)
    except Exception as e:
        logger.error(f"❌ Error recuperando el contexto para la cuenta {account_id}: {e}", exc_info=True)
        return "Error recuperando la información del usuario."

async def summarize_history_in_background(
    history_to_summarize: List[BaseMessage],
    chat_message_history: PostgresChatMessageHistory
):
    """
    Resume mensajes en segundo plano y añade un resumen al historial, pero NO borra los mensajes previos.
    El resumen se usará solo para el contexto del LLM, pero el historial completo se conserva para el frontend.
    """
    llm_for_summary = _fast_task_llm_instance or _main_agent_llm_instance
    if not llm_for_summary:
        logger.warning("⚠️ No hay LLM disponible para la sumarización en segundo plano.")
        return

    logger.info(f"Tarea en segundo plano: Resumiendo {len(history_to_summarize)} mensajes...")
    try:
        summarization_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="Tu tarea es crear un resumen conciso de la siguiente conversación para mantener el contexto. Captura los puntos clave, decisiones y el estado actual de cualquier discusión. Ignora saludos genéricos."),
            MessagesPlaceholder(variable_name="history"),
        ])
        summarization_chain = summarization_prompt | llm_for_summary
        messages_for_summarization_input = [msg for msg in history_to_summarize if not (hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary")]
        if not messages_for_summarization_input:
            return
        summary_response = await summarization_chain.ainvoke({"history": messages_for_summarization_input})
        summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        summary_message = HumanMessage(
            content=f"Resumen de la conversación anterior: {summary_content}",
            additional_kwargs={"role": "summary"}
        )
        # Guardar el resumen como un mensaje más, sin borrar el historial
        await chat_message_history.aadd_messages([summary_message])
        logger.info("✅ Sumarización en segundo plano completada y resumen añadido al historial.")
    except Exception as e:
        logger.error(f"❌ Error en la tarea de sumarización: {e}", exc_info=True)

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
        conversation_text = '\n'.join([m.content if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = f"Resume la conversación en un título breve y descriptivo (máx 8 palabras):\n{conversation_text}"
        llm = _fast_task_llm_instance or _main_agent_llm_instance
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

async def force_update_all_thread_titles():
    """
    Fuerza la actualización de títulos de todos los hilos de chat existentes usando el LLM de tareas rápidas.
    Si el hilo tiene más de 5 mensajes y el título es 'Nuevo Chat', o si tiene más de 20 y el título es distinto, se actualiza.
    """
    from core.database import SessionLocal, ChatThread
    logger.info("Forzando actualización de títulos de todos los hilos...")
    async with DBSession(SessionLocal) as db:
        threads = (await db.execute(select(ChatThread))).scalars().all()
        for thread in threads:
            session_id = str(thread.id)
            db_url = settings.database_url or os.getenv("DATABASE_URL")
            if not db_url:
                logger.error("DATABASE_URL no está configurada para el historial de chat.")
                continue
            db_sync_url = db_url.replace("+psycopg", "")
            from langchain_community.chat_message_histories import PostgresChatMessageHistory
            chat_message_history = PostgresChatMessageHistory(
                connection_string=db_sync_url,
                session_id=session_id,
                table_name="langchain_chat_history",
            )
            messages = await chat_message_history.aget_messages()
            await update_thread_title_if_needed(str(thread.id), messages)
    logger.info("Actualización de títulos completada.")

# ==============================================================================
# SECCIÓN 3: EJECUCIÓN PRINCIPAL DEL AGENTE
# ==============================================================================

async def create_and_run_agent(
    account_id: str,
    thread_id: str,
    telegram_id: Optional[int],
    user_message: str,
    image_base64: Optional[str] = None,
) -> str:
    """
    Crea y ejecuta el agente de Langchain con manejo explícito de memoria.
    """
    logger.info(f"--- Ejecutando agente para account_id: {account_id}, thread_id: {thread_id} (desde telegram_id: {telegram_id}) ---")
    # --- 1. Gestión del Historial de Chat ---
    session_id = thread_id  # Usar siempre el thread_id como session_id
    if not settings.database_url:
        raise ValueError("DATABASE_URL no está configurada para el historial de chat.")
    db_sync_url = settings.database_url.replace("+psycopg", "")
    chat_message_history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=session_id,
        table_name="langchain_chat_history",
    )
    full_history = await chat_message_history.aget_messages()

    # --- NUEVO: Si el historial es muy corto (nuevo hilo), sumarizar hilos previos y sumar últimos 4 mensajes globales ---
    if len(full_history) < 2:
        # Buscar todos los hilos previos del usuario
        from core.database import SessionLocal, ChatThread
        from utils.db_session import DBSession
        import uuid as uuidlib
        async with DBSession(SessionLocal) as db:
            threads = (await db.execute(select(ChatThread).where(ChatThread.account_id == uuidlib.UUID(account_id)).order_by(ChatThread.created_at.desc()))).scalars().all()
        # Excluir el hilo actual
        prev_threads = [t for t in threads if str(t.id) != thread_id]
        prev_messages = []
        for t in prev_threads:
            prev_hist = PostgresChatMessageHistory(
                connection_string=db_sync_url,
                session_id=str(t.id),
                table_name="langchain_chat_history",
            )
            msgs = await prev_hist.aget_messages()
            prev_messages.extend(msgs)
        # Sumarizar historial anterior si hay suficiente
        if prev_messages:
            
            from core.agent import summarize_history_in_background
            # Solo mensajes que no sean resumen
            msgs_for_sum = [m for m in prev_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            # Usar la función de sumarización ya implementada
            llm_for_summary = _fast_task_llm_instance or _main_agent_llm_instance
            summarization_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="Tu tarea es crear un resumen conciso de la siguiente conversación para mantener el contexto. Captura los puntos clave, decisiones y el estado actual de cualquier discusión. Ignora saludos genéricos."),
                MessagesPlaceholder(variable_name="history"),
            ])
            summarization_chain = summarization_prompt | llm_for_summary
            summary_response = await summarization_chain.ainvoke({"history": msgs_for_sum})
            summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            summary_string = f"Resumen de la conversación anterior: {summary_content}"
        else:
            summary_string = ""
        # Agregar los últimos 4 mensajes recientes (de cualquier hilo)
        last_msgs = [m for m in prev_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
        last_msgs = last_msgs[-4:] if len(last_msgs) >= 4 else last_msgs
        history_for_prompt = last_msgs.copy()
    else:
        # Extraer resumen y filtrar historial para el prompt (lógica original)
        summary_string = ""
        history_for_prompt = []
        for msg in full_history:
            if isinstance(msg, HumanMessage) and msg.additional_kwargs.get("role") == "summary":
                summary_string = str(msg.content)
            else:
                history_for_prompt.append(msg)

    # --- 2. Preparar el Mensaje Actual del Usuario ---
    account_name = "Usuario" # Valor por defecto
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, account_id)
        if account and account.name:
            account_name = account.name
            
    current_user_input_content: Any = user_message
    if image_base64:
        current_user_input_content = [
            {"type": "text", "text": user_message},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
    current_human_message = HumanMessage(content=current_user_input_content, additional_kwargs={"user_name": account_name})
    
    # Combinar historial filtrado con el mensaje actual para el prompt
    full_history_for_llm_prompt = history_for_prompt + [current_human_message]

    # --- 3. Construir el Prompt del Sistema Dinámicamente ---
    
    # ¡CORREGIDO! Llamamos a las funciones que sí existen en tu memory_manager.py
    
    # Obtener el perfil y las memorias
    user_profile = await get_user_profile(account_id)
    relevant_memories = await get_relevant_memories(account_id, user_message)

    # Construir la parte del perfil del prompt
    profile_info = []
    custom_prompt = None
    if user_profile:
        if user_profile.nombre: profile_info.append(f"- Nombre: {user_profile.nombre}")
        if user_profile.gustos: profile_info.append(f"- Gustos: {user_profile.gustos}")
        if user_profile.intereses: profile_info.append(f"- Intereses: {user_profile.intereses}")
        if user_profile.otros_datos: profile_info.append(f"- Otros datos: {user_profile.otros_datos}")
        # ¡CORREGIDO! Usamos el nombre correcto del atributo: system_prompt
        custom_prompt = user_profile.system_prompt
        
    user_context_parts = [
        "--- Información Relevante sobre el Usuario y su Contexto ---",
        "Información de Perfil del Usuario:",
        "\n".join(profile_info) if profile_info else "No hay información de perfil disponible."
    ]

    if relevant_memories and "No se encontraron memorias relevantes" not in relevant_memories:
        user_context_parts.append("\nMemorias y Documentos Relevantes (Base de Conocimiento):")
        user_context_parts.append(relevant_memories)

    user_context_parts.append("---------------------------------------------------------")
    user_context_string = "\n".join(user_context_parts)
    
    effective_system_prompt = custom_prompt or settings.default_system_prompt
    tools = get_all_langchain_tools()
    tool_descriptions = "\n".join([f"- `{tool.name}`: {tool.description}" for tool in tools])

    id_instructions = f"""
    <b>Instrucciones Críticas de Identificación de Usuario:</b>
    - Para CUALQUIER herramienta que requiera el argumento `account_id`, DEBES usar este valor exacto: <b>{account_id}</b>.
    - Para CUALQUIER herramienta que requiera el argumento `telegram_id`, DEBES usar este valor exacto: <b>{telegram_id}</b>.
    """
    system_prompt_content = f"""
{user_context_string}
{summary_string}
    <hr>
{effective_system_prompt}
    <hr>
<b>Instrucción crítica:</b> Si necesitas usar herramientas, hazlo de una en una. Nunca intentes usar más de una herramienta en una sola respuesta. Espera la siguiente interacción antes de usar otra herramienta.
    <hr>
{id_instructions}
    <hr>
    <b>Guía de Uso de Herramientas Obligatoria:</b>
    Debes analizar CADA petición del usuario para determinar si una de tus herramientas es la forma más apropiada de responder. Si una herramienta encaja, DEBES usarla.
{tool_descriptions}
    """

    # 4. --- Configurar y Ejecutar el Agente ---
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    if not _main_agent_llm_instance:
        raise RuntimeError("El LLM principal no está inicializado.")

    llm_with_tools = _main_agent_llm_instance.bind_tools(tools)

    # ¡CADENA CORREGIDA! La estructura es más estándar y clara.
    agent_chain = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_to_tool_messages(x.get("intermediate_steps", []))
        )
        | prompt_template
        | llm_with_tools
        | ToolsAgentOutputParser()
    )

    agent_executor = AgentExecutor(
        agent=agent_chain, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True
    )

    final_output = ""
    try:
        # ¡INVOCACIÓN CORREGIDA! El diccionario de entrada ahora es simple y directo.
        # Solo pasamos las variables que nuestra plantilla espera: `input` y `chat_history`.
        # `history_for_prompt` ya contiene los mensajes del historial en el formato correcto.
        input_data = {
            "input": user_message,
            "chat_history": history_for_prompt,
        }

        response = await agent_executor.ainvoke(
            input_data,
            config={"configurable": {"account_id": account_id, "telegram_id": telegram_id}}
        )
        final_output = response.get("output", "No pude procesar tu solicitud.")

    except Exception as e:
        logger.error(f"❌ FATAL: Error durante la ejecución del agente para la cuenta {account_id}: {e}", exc_info=True)
        final_output = "Lo siento, ocurrió un error inesperado al procesar tu solicitud. El error ha sido registrado."
    # 5. --- Guardar Historial y Sumarizar ---
    # Es importante añadir el `current_human_message` que creamos antes
    await chat_message_history.aadd_messages([current_human_message, AIMessage(content=final_output)])
    updated_full_history = await chat_message_history.aget_messages()
    # Sumarizar solo para el contexto, pero sin borrar historial
    if _main_agent_llm_instance.get_num_tokens_from_messages(updated_full_history) > 3000:
        asyncio.create_task(summarize_history_in_background(updated_full_history, chat_message_history))
    # Actualizar título si corresponde
    await update_thread_title_if_needed(session_id, updated_full_history)
    return sanitize_html(final_output)

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



