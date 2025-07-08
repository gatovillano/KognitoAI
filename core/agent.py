# core/agent.py

"""
Módulo del Agente de IA de LangChain (Versión ReAct Mejorada).

Este módulo implementa un agente avanzado usando el patrón ReAct (Reason and Act),
lo que le permite pensar paso a paso, manejar tareas complejas y corregir sus
propios errores. La arquitectura aprovecha la gran ventana de contexto de modelos
como Gemini, eliminando la necesidad de resumir el historial de chat
durante la conversación activa.

Arquitectura Clave:
1.  **Agente ReAct:** Se utiliza la función `create_react_agent` de LangChain y un
    prompt estándar de `LangChain Hub` para un razonamiento robusto.
2.  **Manejo de Memoria Simplificado:** Gracias a la gran ventana de contexto, se
    pasa el historial de chat completo al agente, asegurando que nunca "olvide"
    cómo usar las herramientas. La sumarización es ahora una tarea de
    mantenimiento en segundo plano, no una necesidad crítica.
3.  **Inyección de Contexto Dinámico:** El `build_system_prompt` sigue siendo crucial
    y su contenido (perfil, memorias, etc.) se inyecta directamente en el input
    del agente en cada turno.
"""

import logging
import asyncio
from typing import Optional, List, Any
import uuid
import os

# --- Langchain Core ---
from langchain.agents import AgentExecutor
# --- MEJORA ReAct: Nuevas importaciones para el agente ReAct ---
from langchain.agents import create_react_agent
from langchain import hub
# --- Fin de la mejora ---
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.language_models.base import BaseLanguageModel
from sqlalchemy import update
import json
import re

# --- Módulos del Proyecto ---
from core.tools import get_all_langchain_tools
from core.memory_manager import get_user_profile, get_relevant_memories
from core.database import SessionLocal, Account, ChatThread, Workspace
from utils.db_session import DBSession
from core.config import settings
from core.llm_manager import get_main_llm, get_fast_llm
from sqlalchemy import select

# --- Configuración del Logger ---
logger = logging.getLogger(__name__)

# --- Constante para el manejo de memoria ---
# Define cuántos mensajes de conversación recientes se mantendrán sin resumir.
# Las interacciones con herramientas no cuentan para este límite y siempre se conservan.
MAX_CONVERSATIONAL_MESSAGES_TO_KEEP = 10

# ==============================================================================
# SECCIÓN 2: CALLBACK PERSONALIZADO PARA LOGGING DETALLADO (SIN CAMBIOS)
# ==============================================================================

class DetailedLLMLoggingCallback(BaseCallbackHandler):
    """
    Callback personalizado para capturar toda la comunicación con el LLM de manera estructurada.
    Evita duplicación de logs y trunca contenido muy largo para mantener legibilidad.
    """
    def __init__(self, account_id: str, thread_id: str):
        self.account_id = account_id
        self.thread_id = thread_id
        self.session_id = f"{account_id}_{thread_id}"
        self.logger = logging.getLogger("LLMCallback")
        self._last_logged_messages = None

    def _truncate_content(self, content: str, max_length: int = 200) -> str:
        """Trunca contenido muy largo para mantener legibilidad."""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _format_messages(self, messages: list) -> str:
        """Formatea los mensajes para logging."""
        if not messages:
            return "No messages"
        
        formatted = []
        for msg_list in messages:
            if isinstance(msg_list, list):
                for msg in msg_list:
                    msg_type = type(msg).__name__
                    content = getattr(msg, 'content', str(msg))
                    truncated_content = self._truncate_content(str(content))
                    formatted.append(f"{msg_type}: {truncated_content}")
            else:
                msg_type = type(msg_list).__name__
                content = getattr(msg_list, 'content', str(msg_list))
                truncated_content = self._truncate_content(str(content))
                formatted.append(f"{msg_type}: {truncated_content}")

        return " | ".join(formatted)

    def on_chat_model_start(self, serialized: dict, messages: list, **kwargs):
        """Se ejecuta cuando el modelo de chat comienza."""
        messages_str = self._format_messages(messages)
        if self._last_logged_messages == messages_str:
            return
        
        self._last_logged_messages = messages_str
        
        model_name = serialized.get("name", "unknown")
        message_count = sum(len(msg_list) if isinstance(msg_list, list) else 1 for msg_list in messages)
        
        self.logger.info(f"💬 [CHAT START] Session: {self.session_id[:8]}...{self.session_id[-8:]} | Model: {model_name} | Messages: {message_count}")
        
        for msg_list in messages:
            if isinstance(msg_list, list):
                for msg in msg_list:
                    msg_type = type(msg).__name__
                    content = getattr(msg, 'content', str(msg))
                    truncated_content = self._truncate_content(str(content))
                    self.logger.info(f"📧 [USER INPUT] {msg_type}: {truncated_content}")
            else:
                msg_type = type(msg_list).__name__
                content = getattr(msg_list, 'content', str(msg_list))
                truncated_content = self._truncate_content(str(content))
                self.logger.info(f"📧 [USER INPUT] {msg_type}: {truncated_content}")

    def on_llm_end(self, response, **kwargs):
        """Se ejecuta cuando el LLM termina."""
        self.logger.info(f"✅ [LLM END] Session: {self.session_id[:8]}...{self.session_id[-8:]}")
        
        if hasattr(response, 'generations') and response.generations:
            for generation_list in response.generations:
                for generation in generation_list:
                    content = getattr(generation, 'text', str(generation))
                    truncated_content = self._truncate_content(str(content))
                    self.logger.info(f"📤 [LLM RESPONSE]: {truncated_content}")

        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            if token_usage:
                self.logger.info(f"🔧 [TOKENS]: {token_usage}")

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Se ejecuta cuando una herramienta comienza."""
        tool_name = serialized.get("name", "unknown")
        truncated_input = self._truncate_content(str(input_str))
        self.logger.info(f"🔧 [TOOL START] {tool_name}: {truncated_input}")

    def on_tool_end(self, output: str, **kwargs):
        """Se ejecuta cuando una herramienta termina."""
        truncated_output = self._truncate_content(str(output))
        self.logger.info(f"✅ [TOOL END]: {truncated_output}")

    def on_tool_error(self, error: BaseException, **kwargs):
        """Se ejecuta cuando una herramienta falla."""
        self.logger.error(f"❌ [TOOL ERROR]: {str(error)}")

    def on_llm_error(self, error: BaseException, **kwargs):
        """Se ejecuta cuando el LLM falla."""
        self.logger.error(f"❌ [LLM ERROR]: {str(error)}")


# ==============================================================================
# SECCIÓN 3: MANEJO DE CONTEXTO Y MEMORIA (SIN CAMBIOS EN LÓGICA, PERO EL USO CAMBIA)
# ==============================================================================

async def summarize_history_in_background(
    history_to_summarize: List[BaseMessage],
    chat_message_history: PostgresChatMessageHistory,
    account_id: str,
    workspace_id: Optional[str] = None
):
    """
    Resume mensajes en segundo plano. Ya no es crítico para el prompt inmediato,
    sino para el mantenimiento a largo plazo del historial en la base de datos.
    """
    llm_for_summary = get_fast_llm()
    if not llm_for_summary:
        logger.warning("⚠️ No hay LLM disponible para la sumarización en segundo plano.")
        return
    
    messages_for_summarization_input = [
        msg for msg in history_to_summarize if not (
            hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary"
        )
    ]
    if not messages_for_summarization_input:
        logger.info("No hay mensajes nuevos que requieran resumen.")
        return
    
    logger.info(f"Tarea en segundo plano: Resumiendo {len(messages_for_summarization_input)} mensajes...")
    try:
        summarization_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="Tu tarea es crear un resumen conciso y denso en información de la siguiente conversación para mantener el contexto en el futuro. Captura los puntos clave, decisiones, datos importantes y el estado actual de cualquier discusión. Ignora saludos genéricos y relleno."),
            MessagesPlaceholder(variable_name="history"),
        ])
        summarization_chain = summarization_prompt | llm_for_summary
        summary_response = await summarization_chain.ainvoke({"history": messages_for_summarization_input})
        summary_content = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        
        summary_message = HumanMessage(
            content=f"Resumen de la conversación anterior: {summary_content}",
            additional_kwargs={"role": "summary"}
        )
        
        await chat_message_history.aadd_messages([summary_message])
        logger.info(f"Resumen añadido al historial de chat para la sesión: {chat_message_history.session_id}")

    except Exception as e:
        logger.error(f"Error durante la sumarización en segundo plano: {e}", exc_info=True)


async def get_and_prepare_history_for_prompt(
    chat_message_history: PostgresChatMessageHistory
) -> List[BaseMessage]:
    """
    Obtiene el historial completo. Con una ventana de contexto grande como la de Gemini,
    esta función puede simplificarse para devolver simplemente todo el historial,
    pero la mantenemos por si se usan modelos con contextos más pequeños en el futuro.
    """
    full_history = await chat_message_history.aget_messages()
    
    # Con Gemini 1.5 Flash (1M tokens), podemos permitirnos enviar un historial mucho más grande.
    # La lógica de separación se mantiene como un "seguro" por si el historial crece demasiado
    # o si se cambia a un modelo con menor contexto.
    preserved_tool_interactions = []
    conversational_messages = []
    existing_summaries = []

    for msg in full_history:
        if (isinstance(msg, AIMessage) and msg.tool_calls) or isinstance(msg, ToolMessage):
            preserved_tool_interactions.append(msg)
        elif hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary":
            existing_summaries.append(msg)
        else:
            conversational_messages.append(msg)
            
    # Para Gemini, podemos aumentar este límite drásticamente o incluso eliminarlo si confiamos
    # en que no excederemos el millón de tokens. Lo mantenemos bajo por ahora por seguridad.
    recent_conversational = conversational_messages[-MAX_CONVERSATIONAL_MESSAGES_TO_KEEP:]
    
    prompt_history = existing_summaries + recent_conversational + preserved_tool_interactions
    
    logger.info(
        f"Historial preparado para prompt: {len(existing_summaries)} resúmenes, "
        f"{len(recent_conversational)} mensajes conversacionales, "
        f"{len(preserved_tool_interactions)} interacciones de herramientas."
    )
    
    return prompt_history


async def update_thread_title_if_needed(thread_id: str, messages: list):
    """
    Genera o actualiza el título del hilo. (SIN CAMBIOS)
    """
    if not messages:
        logger.info(f"[TÍTULO] No hay mensajes para el hilo {thread_id}, no se genera título.")
        return
    async with DBSession(SessionLocal) as db:
        thread = await db.get(ChatThread, uuid.UUID(thread_id))
        current_title = thread.title if thread else None

    logger.info(f"[TÍTULO][DEBUG] Hilo {thread_id} - Título actual: '{current_title}' - Mensajes reales: {len(messages)}")

    if (current_title == "Nuevo Chat" and len(messages) >= 5) or (current_title != "Nuevo Chat" and len(messages) >= 20 and len(messages) % 20 == 0):
        conversation_text = '\n'.join([extract_text_content(m.content) for m in messages[-20:]])
        prompt = f"Resume la conversación en un título breve y descriptivo (máx 8 palabras):\n{conversation_text}"
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


def extract_text_content(content):
    """Extrae el contenido de texto. (SIN CAMBIOS)"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                return item.get('text', '')
    return str(content) if content else ""


async def force_update_thread_title(thread_id: str):
    """Fuerza la actualización del título. (SIN CAMBIOS)"""
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
        
    conversation_text = '\n'.join([extract_text_content(m.content) for m in messages[-20:]])
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
        async with DBSession(SessionLocal) as db:
            await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(title=new_title))
            await db.commit()
    except Exception as e:
        logger.error(f"Error al forzar la actualización del título del hilo {thread_id}: {e}")


async def force_update_all_thread_titles():
    """Fuerza la actualización de todos los títulos. (SIN CAMBIOS)"""
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
# SECCIÓN 4: LÓGICA PRINCIPAL DEL AGENTE (REFACTORIZADA PARA ReAct)
# ==============================================================================

async def build_system_prompt(account_id: str, workspace_id: Optional[str] = None) -> str:
    """
    Construye el prompt del sistema. (SIN CAMBIOS, PERO SU USO ES DIFERENTE)
    """
    user_profile = await get_user_profile(account_id)
    relevant_memories = await get_relevant_memories(account_id, "contexto general", k=5, workspace_id=workspace_id)
    
    profile_info = []
    custom_prompt = None
    if user_profile:
        if user_profile.nombre: profile_info.append(f"- Nombre: {user_profile.nombre}")
        if user_profile.gustos: profile_info.append(f"- Gustos: {user_profile.gustos}")
        if user_profile.intereses: profile_info.append(f"- Intereses: {user_profile.intereses}")
        if user_profile.otros_datos: profile_info.append(f"- Otros datos: {user_profile.otros_datos}")
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
    
    if workspace_id:
        async with DBSession(SessionLocal) as db:
            workspace = await db.get(Workspace, uuid.UUID(workspace_id))
            if workspace and workspace.system_prompt:
                effective_system_prompt = workspace.system_prompt
                logger.info(f"Usando prompt de sistema de workspace {workspace_id}.")
                
    # --- MEJORA ReAct: Prompt más orientado al razonamiento ---
    system_prompt_parts = [
        user_context_string,
        "<hr>",
        effective_system_prompt,
        "<hr>",
        "<b>Proceso de Razonamiento Obligatorio (Thought Process):</b>",
        "Antes de actuar, debes pensar paso a paso qué necesitas hacer para responder a la consulta del usuario. Considera si necesitas usar una herramienta y cuál es la más adecuada.",
    ]
    
    return "\n".join(system_prompt_parts)


# --- MEJORA ReAct: La planificación explícita ya no es necesaria ---
# La lógica ReAct se encarga de la planificación paso a paso.
# Mantenemos las funciones por si se quieren reutilizar, pero no se llamarán.
async def create_execution_plan(user_query: str, context: str = "", available_tools: Optional[List[Any]] = None) -> dict:
    """[NO USADO EN ReAct] Crea un plan de ejecución para la consulta del usuario."""
    logger.info(f"🧠 [NO USADO EN ReAct] Creando plan de ejecución para: '{user_query[:100]}...'")
    return _create_basic_plan(user_query)

def _create_basic_plan(user_query: str) -> dict:
    """[NO USADO EN ReAct] Plan básico cuando falla la planificación automática."""
    return {}


# --- MEJORA ReAct: Se reemplaza la función de creación de agente manual ---
def create_agent(llm: BaseLanguageModel, tools: List, prompt):
    """
    Crea un agente ReAct a partir de un LLM, herramientas y un prompt.
    """
    return create_react_agent(llm, tools, prompt)


# ==============================================================================
# SECCIÓN 5: EJECUCIÓN PRINCIPAL DEL AGENTE (NUEVA VERSIÓN ReAct)
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
    workspace_id: Optional[str] = None,
    k: int = 5
) -> str:
    """
    Crea y ejecuta un agente ReAct, aprovechando un gran contexto y un razonamiento
    paso a paso para el uso de herramientas.
    """
    logger.info(f"--- Ejecutando agente ReAct para account_id: {account_id}, thread_id: {thread_id} ---")

    # --- 1. Obtener Workspace ID ---
    if workspace_id is None:
        async with DBSession(SessionLocal) as db:
            thread = await db.get(ChatThread, uuid.UUID(thread_id))
            if thread and thread.workspace_id:
                workspace_id = str(thread.workspace_id)
                logger.info(f"Recuperado workspace_id {workspace_id} del ChatThread.")

    # --- 2. Gestión del Historial de Chat ---
    session_id = thread_id
    if not settings.database_url:
        raise ValueError("DATABASE_URL no está configurada para el historial de chat.")
    db_sync_url = settings.database_url.replace("+psycopg", "")
    chat_message_history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=session_id,
        table_name="langchain_chat_history",
    )
    # Con un contexto grande, podemos permitirnos cargar el historial completo.
    processed_history_for_prompt = await chat_message_history.aget_messages()
    logger.info(f"Cargados {len(processed_history_for_prompt)} mensajes del historial para el prompt ReAct.")

    # --- 3. Preparar el Mensaje Actual del Usuario ---
    account_name = "Usuario"
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, uuid.UUID(account_id))
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
        
    current_human_message = HumanMessage(content=current_user_input_content, name=account_name)

    # --- 4. Construir el Input para el Agente ReAct ---
    system_prompt_content = await build_system_prompt(account_id, workspace_id)
    
    # El prompt de ReAct espera un 'input' que contenga toda la información contextual.
    final_input = f"""{system_prompt_content}

--- Consulta Actual del Usuario ---
{user_message}
"""
    
    # --- 5. Configurar Herramientas y LLM ---
    all_tools = get_all_langchain_tools(account_id=account_id, telegram_id=str(telegram_id) if telegram_id else "")
    tools = all_tools

    # Modos especiales para forzar herramientas (se mantiene la lógica)
    if mode == 'knowledgeAnalysis':
        logger.info("Modo ReAct: Forzando 'knowledge_base_analyzer'")
        tools = [t for t in all_tools if t.name == 'knowledge_base_analyzer']
    elif mode == 'webSearch':
        logger.info("Modo ReAct: Forzando 'web_search'")
        tools = [t for t in all_tools if t.name == 'web_search']
    elif mode == 'comprehensiveAnalysis':
        logger.info("Modo ReAct: Forzando 'comprehensive_web_analyzer'")
        tools = [t for t in all_tools if t.name == 'comprehensive_web_analyzer']

    main_llm = get_main_llm()
    if not main_llm:
        raise RuntimeError("El LLM principal (main_llm) no está inicializado.")

    # --- 6. Crear y Ejecutar el Agente ReAct ---
    # Usamos un prompt ReAct personalizado compatible con nuestras variables
    from langchain_core.prompts import PromptTemplate

    # Insertamos las instrucciones de ID y workspace en el prompt de ReAct
    id_instructions = (
        f"<b>Instrucciones Críticas de Identificación:</b>\n"
        f"- Para CUALQUIER herramienta que requiera `account_id`, DEBES usar: <b>{account_id}</b>.\n"
        f"- Para CUALQUIER herramienta que requiera `telegram_id`, DEBES usar: <b>{telegram_id}</b>.\n"
        f"\n<b>Instrucciones CRÍTICAS para el uso de herramientas:</b>\n"
        f"- NUNCA incluyas 'query=' o 'account_id=' en el parámetro de consulta\n"
        f"- Para comprehensive_web_analyzer: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
        f"- Para web_search_tool: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
        f"- Para multi_query_search: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
        f"- CORRECTO: Action Input: modelos ligeros de reconocimiento de entidades\n"
        f"- INCORRECTO: Action Input: query='modelos ligeros de reconocimiento de entidades', account_id='...'\n"
        f"- Los parámetros account_id, workspace_id, etc. se pasan automáticamente por el sistema\n"
    )
    if workspace_id:
        id_instructions += f"- Para CUALQUIER herramienta que requiera `workspace_id`, DEBES usar: <b>{workspace_id}</b>.\n"

    # Crear un prompt template personalizado compatible con nuestras variables
    react_template = """Responde las siguientes preguntas lo mejor que puedas. Tienes acceso a las siguientes herramientas:

{tools}

DEBES seguir EXACTAMENTE este formato (es OBLIGATORIO):

Question: la pregunta que debes responder
Thought: piensa paso a paso qué necesitas hacer
Action: la acción a tomar, debe ser una de [{tool_names}]
Action Input: la entrada para la acción
Observation: el resultado de la acción
... (este ciclo Thought/Action/Action Input/Observation puede repetirse N veces)
Thought: ahora conozco la respuesta final
Final Answer: la respuesta final a la pregunta original

IMPORTANTE: Después de cada "Thought:" SIEMPRE debe seguir "Action:" o "Final Answer:"

{id_instructions}

CRITICAL RULE FOR ACTION INPUT:
When using search tools (comprehensive_web_analyzer, web_search_tool, multi_query_search),
the Action Input must be ONLY the search text, never JSON or key-value pairs.

EXAMPLES:
If user asks: "busca información sobre modelos ligeros de reconocimiento de entidades"
- CORRECT Action Input: modelos ligeros de reconocimiento de entidades
- WRONG Action Input: {{"query": "modelos ligeros de reconocimiento de entidades", "account_id": "..."}}
- WRONG Action Input: query='modelos ligeros de reconocimiento de entidades', account_id='...'

If user asks: "find information about machine learning"
- CORRECT Action Input: machine learning
- WRONG Action Input: {{"query": "machine learning"}}

Remember: Extract ONLY the search terms from the user's question for search tools.

FORMATO OBLIGATORIO - EJEMPLO COMPLETO:
Question: busca información sobre IA
Thought: El usuario quiere información sobre inteligencia artificial. Necesito usar la herramienta de búsqueda web.
Action: comprehensive_web_analyzer
Action Input: inteligencia artificial
Observation: [resultado de la búsqueda]
Thought: Ahora tengo información suficiente para responder al usuario.
Final Answer: [respuesta basada en la información encontrada]

Begin!

{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""

    react_prompt = PromptTemplate(
        template=react_template,
        input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names", "id_instructions"]
    )

    # Preparar las variables del prompt
    tool_names = [tool.name for tool in tools]
    tools_description = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

    # Crear el prompt con las variables necesarias
    formatted_prompt = react_prompt.partial(
        tools=tools_description,
        tool_names=", ".join(tool_names),
        id_instructions=id_instructions
    )

    agent = create_agent(main_llm, tools, formatted_prompt)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,  # Activar manejo de errores para que el agente pueda continuar
        max_iterations=10, # Permitir más iteraciones para que el agente complete su razonamiento
    )

    # --- 7. Invocar y Gestionar Historial ---
    final_output = ""
    try:
        # Guardar el mensaje del usuario antes de la ejecución
        await chat_message_history.aadd_messages([current_human_message])
        
        config_data = {"account_id": account_id, "telegram_id": telegram_id}
        if workspace_id:
            config_data["workspace_id"] = workspace_id

        response = await agent_executor.ainvoke(
            {
                "input": final_input,
                "chat_history": processed_history_for_prompt
            },
            config={"configurable": config_data}
        )
        final_output = response.get("output", "No pude procesar tu solicitud.")

    except Exception as e:
        logger.error(f"❌ FATAL: Error durante la ejecución del agente ReAct para la cuenta {account_id}: {e}", exc_info=True)
        final_output = "Lo siento, ocurrió un error inesperado al procesar tu solicitud. El error ha sido registrado."

    # Guardar la respuesta final del agente
    await chat_message_history.aadd_messages([AIMessage(content=final_output)])
    
    # --- 8. Tareas en Segundo Plano (Mantenimiento) ---
    full_history_after_run = await chat_message_history.aget_messages()
    
    # La sumarización ahora es una tarea de mantenimiento para historiales muy largos
    if len(full_history_after_run) > 50: # Un umbral mucho más alto
        asyncio.create_task(
            summarize_history_in_background(
                full_history_after_run, chat_message_history, account_id, workspace_id
            )
        )
        
    await update_thread_title_if_needed(session_id, full_history_after_run)
    
    return final_output

async def create_thread_for_account(account_id: str, title: str = "Nuevo Chat", platform: str = "web") -> str:
    """
    Crea un nuevo hilo de chat para la cuenta dada. (SIN CAMBIOS)
    """
    async with DBSession(SessionLocal) as db:
        account = await db.get(Account, uuid.UUID(account_id))
        if not account:
            raise ValueError(f"No existe la cuenta {account_id}")
        new_thread = ChatThread(account_id=account.id, title=title, platform=platform)
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
    return str(new_thread.id)