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
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.runnables import RunnablePassthrough
from sqlalchemy import update

# --- Módulos del Proyecto ---
from core.tools import get_all_langchain_tools
from core.memory_manager import get_user_profile, get_relevant_memories
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession
from core.config import settings
from core.llm_manager import get_main_llm, get_fast_llm, initialize_llms

# --- Claves para estado temporal ---
from utils.image_generation import GENERATED_IMAGE_KEY
from tools.get_document_content_tool import DOCUMENT_NAME_KEY
from sqlalchemy import select
from sqlalchemy.orm import selectinload
# --- Configuración del Logger ---
logger = logging.getLogger(__name__)

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
    llm_for_summary = get_fast_llm()
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
        # Manejar contenido de mensajes que puede ser una lista o una cadena
        def extract_text_content(content):
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        return item.get('text', '')
            return str(content)
        
        conversation_text = '\n'.join([extract_text_content(m.content) if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = f"Resume la conversación en un título breve y descriptivo (máx 8 palabras):\n{conversation_text}"
        llm = get_fast_llm()
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

        conversation_text = '\n'.join([m.content if hasattr(m, 'content') else str(m) for m in messages[-20:]])
        prompt = f"Resume la conversación en un título breve y descriptivo (máx 8 palabras):\n{conversation_text}"
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
    document_url: Optional[str] = None,
    mode: Optional[str] = None,
    background_tasks: Optional[Any] = None,
    workspace_id: Optional[str] = None
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

    # --- NUEVO: Si el historial es muy corto (nuevo hilo), sumarizar SOLO el hilo anterior y sumar últimos 4 mensajes de ese hilo ---
    if len(full_history) < 2:
        import uuid as uuidlib
        async with DBSession(SessionLocal) as db:
            threads = (await db.execute(select(ChatThread).where(ChatThread.account_id == uuidlib.UUID(account_id)).order_by(ChatThread.created_at.desc()))).scalars().all()
        # Excluir el hilo actual
        prev_threads = [t for t in threads if str(t.id) != thread_id]
        if prev_threads:
            last_thread = prev_threads[0]
            prev_hist = PostgresChatMessageHistory(
                connection_string=db_sync_url,
                session_id=str(last_thread.id),
                table_name="langchain_chat_history",
            )
            prev_messages = await prev_hist.aget_messages()
            # Sumarizar historial anterior si hay suficiente
            if prev_messages:
                msgs_for_sum = [m for m in prev_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
                llm_for_summary = get_fast_llm()
                summarization_prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content="Tu tarea es crear un resumen conciso de la siguiente conversación para mantener el contexto. Captura los puntos clave, decisiones y el estado actual de cualquier discusión. Ignora saludos genéricos."),
                    MessagesPlaceholder(variable_name="history"),
                ])
                summarization_chain = summarization_prompt | llm_for_summary
                summary_response = await summarization_chain.ainvoke({"history": msgs_for_sum})
                summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
                summary_string = f"Resumen de la conversación anterior: {summary_content}"
                # --- GUARDAR EN MEMORIA VECTORIAL ---
                try:
                    from core.memory_manager import add_memory_to_vector_db
                    # Guardar el embedding del resumen con metadata de tipo y categoría
                    await add_memory_to_vector_db(
                        account_id=account_id,
                        content=summary_content,
                        type="thread_summary"
                    )
                    logger.info(f"✅ Resumen del hilo {last_thread.id} guardado en memoria vectorial como 'thread_summary'.")
                except Exception as e:
                    logger.error(f"❌ Error al guardar el resumen del hilo {last_thread.id} en la memoria vectorial: {e}")
            else:
                summary_string = ""
            # Agregar los últimos 4 mensajes recientes (de ese hilo)
            last_msgs = [m for m in prev_messages if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            last_msgs = last_msgs[-4:] if len(last_msgs) >= 4 else last_msgs
            # --- AGREGADO: incluir el mensaje actual del usuario como el último ---
            history_for_prompt = last_msgs.copy()
        else:
            summary_string = ""
            history_for_prompt = []
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
    elif document_url:
        current_user_input_content = f"{user_message}\n\nDocumento adjunto: {document_url}"
    current_human_message = HumanMessage(content=current_user_input_content, additional_kwargs={"user_name": account_name})

    # --- CORRECCIÓN: Siempre agregar el mensaje actual al final del historial para el modelo ---
    full_history_for_llm_prompt = history_for_prompt + [current_human_message]

    # --- 3. Construir el Prompt del Sistema Dinámicamente ---
    
    # ¡CORREGIDO! Llamamos a las funciones que sí existen en tu memory_manager.py
    
    # Obtener el perfil y las memorias
    user_profile = await get_user_profile(account_id)
    relevant_memories = await get_relevant_memories(account_id, user_message)

    # Construir la parte del perfil del prompt
    profile_info = []
    custom_prompt = None
    async with DBSession(SessionLocal) as db:
        thread = await db.scalar(select(ChatThread).options(selectinload(ChatThread.workspace)).where(ChatThread.id == uuid.UUID(thread_id)))
        if thread and thread.workspace and thread.workspace.system_prompt:
            custom_prompt = thread.workspace.system_prompt
        elif user_profile:
            # ¡CORREGIDO! Usamos el nombre correcto del atributo: system_prompt
            custom_prompt = user_profile.system_prompt

    if user_profile:
        if user_profile.nombre: profile_info.append(f"- Nombre: {user_profile.nombre}")
        if user_profile.gustos: profile_info.append(f"- Gustos: {user_profile.gustos}")
        if user_profile.intereses: profile_info.append(f"- Intereses: {user_profile.intereses}")
        if user_profile.otros_datos: profile_info.append(f"- Otros datos: {user_profile.otros_datos}")
        
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
    
    # Filtrar variables no deseadas del custom_prompt para evitar errores de variables no definidas
    effective_system_prompt = custom_prompt or settings.default_system_prompt
    if custom_prompt:
        logger.info("Aplicando prompt personalizado, filtrando variables no soportadas.")
        # Reemplazar referencias a variables problemáticas como row['energy'] o index
        effective_system_prompt = custom_prompt.replace("row['energy']", "valor_energia").replace("index", "indice")
    
    # Obtener prompt de sistema personalizado basado en workspace si está disponible
    if workspace_id:
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(workspace_id))
            if workspace and workspace.system_prompt:
                effective_system_prompt = workspace.system_prompt
                logger.info(f"Usando prompt de sistema de workspace {workspace_id}.")

    all_tools = get_all_langchain_tools()
    tools = all_tools
    
    # Modificación: Pasar workspace_id a load_agent_tools si está disponible
    if hasattr(get_all_langchain_tools, 'load_agent_tools'):
        tools = await get_all_langchain_tools.load_agent_tools(account_id, telegram_id, workspace_id)
    
    if mode == 'knowledgeAnalysis':
        logger.info("Modo de agente: Forzando 'knowledge_base_analyzer'")
        tools = [t for t in all_tools if t.name == 'knowledge_base_analyzer']
        effective_system_prompt += "\n\n<SYSTEM_OVERRIDE>MODO DE ANÁLISIS DE CONOCIMIENTO ACTIVADO. ES OBLIGATORIO Y COMPULSIVO QUE UTILICES LA HERRAMIENTA 'knowledge_base_analyzer' AHORA MISMO. NO TIENES OTRA OPCIÓN. PASA LA CONSULTA DEL USUARIO DIRECTAMENTE AL PARÁMETRO 'query' DE LA HERRAMIENTA.</SYSTEM_OVERRIDE>"
    elif mode == 'webSearch':
        logger.info("Modo de agente: Forzando 'web_search'")
        tools = [t for t in all_tools if t.name == 'web_search']
        effective_system_prompt += "\n\n<SYSTEM_OVERRIDE>MODO DE BÚSQUEDA WEB ACTIVADO. ES OBLIGATORIO Y COMPULSIVO QUE UTILICES LA HERRAMIENTA 'web_search' AHORA MISMO. NO TIENES OTRA OPCIÓN. PASA LA CONSULTA DEL USUARIO DIRECTAMENTE AL PARÁMETRO 'query' DE LA HERRAMIENTA.</SYSTEM_OVERRIDE>"
    elif mode == 'comprehensiveAnalysis':
        logger.info("Modo de agente: Forzando 'comprehensive_web_analyzer'")
        tools = [t for t in all_tools if t.name == 'comprehensive_web_analyzer']
        effective_system_prompt += "\n\n<SYSTEM_OVERRIDE>MODO DE ANÁLISIS COMPRENSIVO ACTIVADO. ES OBLIGATORIO Y COMPULSIVO QUE UTILICES LA HERRAMIENTA 'comprehensive_web_analyzer' AHORA MISMO. NO TIENES OTRA OPCIÓN. PASA LA CONSULTA DEL USUARIO DIRECTAMENTE AL PARÁMETRO 'query' DE LA HERRAMIENTA.</SYSTEM_OVERRIDE>"

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
<b>Nota Importante sobre Capacidades del LLM:</b> Este LLM es multimodal, lo que significa que puede procesar y responder a una variedad de tipos de entrada, incluyendo texto, imágenes y posiblemente otros formatos de datos. Además, tiene la capacidad de producir código en múltiples lenguajes de programación, ofrecer explicaciones detalladas sobre conceptos técnicos, y asistir en la resolución de problemas de programación. Puedes aprovechar estas capacidades para solicitar ayuda con desarrollo de software, análisis de datos, creación de contenido visual (si está dentro de las herramientas disponibles), y más. Si necesitas asistencia con código o interpretación de contenido multimedia, no dudes en pedírmelo, y utilizaré mis habilidades para proporcionarte soluciones precisas y útiles.
    <hr>
<b>Instrucción crítica:</b> Si necesitas usar herramientas, hazlo de una en una. Nunca intentes usar más de una herramienta en una sola respuesta. Espera la siguiente interacción antes de usar otra herramienta.
    <hr>
<b>Instrucción de Memoria Importante:</b> Es muy importante que analices cada mensaje del usuario para identificar información relevante que deba ser guardada automáticamente en la memoria. Esto incluye datos personales, preferencias, eventos importantes, o cualquier detalle que pueda ser útil para futuras interacciones. Utiliza la herramienta adecuada para almacenar esta información cuando la detectes.
    <hr>
{id_instructions}
    <hr>
    <b>Guía de Uso de Herramientas Obligatoria:</b>
    Debes analizar CADA petición del usuario para determinar si una de tus herramientas es la forma más apropiada de responder. Si una herramienta encaja, DEBES usarla.
{tool_descriptions}
    """

    # --- NUEVO: Instrucciones de formato MarkdownV2 para Telegram ---
    # markdownv2_format_rules = (
    #     "\n[Reglas de formato MarkdownV2 para Telegram]\n"
    #     "Responde SIEMPRE usando solo MarkdownV2 de Telegram:\n"
    #     "- Usa *texto* para negrita, _texto_ para cursiva, `texto` para código, [texto](url) para enlaces.\n"
    #     "- Usa • para listas.\n"
    #     "- Escapa todos los caracteres reservados de MarkdownV2 (_ * [ ] ( ) ~ ` > # + - = | {{ }} . !) con una barra invertida (\\) cuando no formen parte de la sintaxis.\n"
    #     "- No uses HTML, encabezados, tablas, imágenes ni emojis.\n"
    #     "- Un solo salto de línea por párrafo.\n"
    #     "Ejemplo:\n*Texto en negrita*\\n_Ejemplo en cursiva_\\n`Código`\\n[Enlace](https://ejemplo.com)\\n• Lista uno\\n• Lista dos\n"
    # )
    # system_prompt_content += markdownv2_format_rules

    # 4. --- Configurar y Ejecutar el Agente ---
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    main_llm = get_main_llm()
    if not main_llm:
        raise RuntimeError("El LLM principal no está inicializado.")

    llm_with_tools = main_llm.bind_tools(tools)

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
        handle_parsing_errors=True,
        max_iterations=5  # Aumentar a 5 iteraciones para permitir más ciclos de búsqueda y síntesis
    )

    final_output = ""
    try:
        # ¡INVOCACIÓN CORREGIDA! El diccionario de entrada ahora es simple y directo.
        # Solo pasamos las variables que nuestra plantilla espera: `input` y `chat_history`.
        # `history_for_prompt` ya contiene los mensajes del historial en el formato correcto.
        input_data = {
            "input": user_message,
            "chat_history": full_history_for_llm_prompt,
        }
        logger.info(f"Datos de entrada pasados al agente: {input_data.keys()}")

        response = await agent_executor.ainvoke(
            input_data,
            config={"configurable": {"account_id": account_id, "telegram_id": telegram_id, "thread_id": thread_id, "background_tasks": background_tasks}}
        )
        final_output = response.get("output", "No pude procesar tu solicitud.")

    except AssertionError as ae:
        logger.warning(f"⚠️ Error de aserción durante la ejecución del agente para la cuenta {account_id},可能是由于streaming. Intentando sin streaming: {ae}", exc_info=True)
        # Reintentar sin streaming
        main_llm = get_main_llm()
        if main_llm:
            main_llm.streaming = False
            llm_with_tools = main_llm.bind_tools(tools)
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
                handle_parsing_errors=True,
                max_iterations=5
            )
            try:
                response = await agent_executor.ainvoke(
                    input_data,
                    config={"configurable": {"account_id": account_id, "telegram_id": telegram_id, "thread_id": thread_id, "background_tasks": background_tasks}}
                )
                final_output = response.get("output", "No pude procesar tu solicitud.")
            except Exception as e2:
                logger.error(f"❌ FATAL: Error durante el reintento sin streaming para la cuenta {account_id}: {e2}", exc_info=True)
                final_output = "Lo siento, ocurrió un error inesperado al procesar tu solicitud. El error ha sido registrado."
        else:
            logger.error(f"❌ FATAL: No se pudo obtener el LLM principal para reintento sin streaming para la cuenta {account_id}")
            final_output = "Lo siento, ocurrió un error inesperado al procesar tu solicitud. El error ha sido registrado."
    except Exception as e:
        logger.error(f"❌ FATAL: Error durante la ejecución del agente para la cuenta {account_id}: {e}", exc_info=True)
        final_output = "Lo siento, ocurrió un error inesperado al procesar tu solicitud. El error ha sido registrado."
    # 5. --- Guardar Historial y Sumarizar ---
    # Es importante añadir el `current_human_message` que creamos antes
    await chat_message_history.aadd_messages([current_human_message, AIMessage(content=final_output)])
    updated_full_history = await chat_message_history.aget_messages()
    main_llm = get_main_llm()
    # Sumarizar solo para el contexto, pero sin borrar historial
    if main_llm and main_llm.get_num_tokens_from_messages(updated_full_history) > 3000:
        asyncio.create_task(summarize_history_in_background(updated_full_history, chat_message_history))
    # Actualizar título si corresponde
    await update_thread_title_if_needed(session_id, updated_full_history)
    return (final_output)

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
