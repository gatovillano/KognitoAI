# api/chat.py

import logging
import uuid
import re
import json
import asyncio
import os
from typing import Optional, AsyncGenerator, Any, List
from io import BytesIO
import httpx
from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

from sqlalchemy import update

from core.agent import create_and_run_agent
from utils.audio_transcriber import transcribe_audio_file
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import SessionLocal, ChatThread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.close()

# --- Modelos para el Chat ---
class Source(BaseModel):
    """Define la estructura de datos para una fuente citada."""
    id: int
    title: str
    url: str
    snippet: str
    type: str = "web"  # "web", "document", "memory", etc.

class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None  # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None
    document_url: Optional[str] = None  # Campo para URL de documentos
    mode: Optional[str] = None

class ToolExecutionRequest(BaseModel):
    tool_name: str
    query: str
    account_id: str
    workspace_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Define la estructura de datos para la respuesta del agente de chat."""
    response_text: str
    sources: Optional[List[Source]] = None  # Lista de fuentes citadas
    image_base64: Optional[str] = None  # Campo para imágenes en base64
    document_url: Optional[str] = None  # Campo para URL de documentos
    tool_code: Optional[str] = None

class TextToSpeechRequest(BaseModel):
    """Define la estructura de datos para una solicitud de conversión de texto a voz."""
    text: str
    voice: Optional[str] = None  # Voz opcional para la conversión

class PinThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de fijar/desfijar un hilo de chat."""
    isPinned: bool

@router.post("/text-to-speech", summary="Generar audio desde texto")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Recibe texto, lo envía al servicio interno de TTS y devuelve el audio como un stream.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    # Pre-procesar el texto para eliminar elementos no deseados
    text_to_speak = request.text
    # 1. Eliminar bloques de código cercados (```...```)
    text_to_speak = re.sub(r'```.*?```', '', text_to_speak, flags=re.DOTALL)
    # 2. Eliminar código en línea (`...`)
    text_to_speak = re.sub(r'`[^`]*`', '', text_to_speak)
    # 3. Eliminar caracteres de puntuación que no se quieren leer
    text_to_speak = re.sub(r'[\[\]{}()#*_]', '', text_to_speak)
    # 4. Limpiar espacios en blanco múltiples
    text_to_speak = re.sub(r'\s+', ' ', text_to_speak).strip()

    if not text_to_speak:
        return StreamingResponse(BytesIO(), media_type="audio/wav")

    # Parámetros para open-edgetts.
    tts_payload = {
        'input': text_to_speak,
        'voice': request.voice if request.voice else 'es-MX-DaliaNeural',
        'model': 'edge-tts',
        'speed': 1.0,
    }

    try:
        async with httpx.AsyncClient() as client:
            # Hacemos una petición POST al servicio de TTS
            response = await client.post(TTS_SERVICE_URL, json=tts_payload, timeout=30.0)     
            response.raise_for_status()
            # Devolvemos el contenido de audio directamente como un stream
            return StreamingResponse(BytesIO(response.content), media_type="audio/wav")

    except httpx.RequestError as e:
        logger.error(f"Error de red contactando el servicio TTS: {e}")
        raise HTTPException(status_code=503, detail="El servicio de voz no está disponible.")
    except httpx.HTTPStatusError as e:
        logger.error(f"El servicio TTS devolvió un error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=502, detail="Error en el servicio de generación de voz.")

@router.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Endpoint para transcribir un archivo de audio utilizando Faster Whisper.
    """
    logger.info(f"Recibida solicitud para transcribir el archivo: {file.filename}")
    
    # Leer el contenido del archivo en memoria
    try:
        audio_bytes = await file.read()
        audio_file_io = BytesIO(audio_bytes)
    except Exception as e:
        logger.error(f"Error al leer el archivo cargado: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo leer el archivo de audio.")

    # Transcribir el audio
    transcription = await transcribe_audio_file(audio_file_io)

    if transcription is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo transcribir el audio.")

    return {"transcription": transcription}

@router.post("/chat", response_model=ChatResponse, summary="Procesar Mensaje de Chat")
async def handle_chat(request: ChatRequest, background_tasks: BackgroundTasks, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
    try:
        account_id_uuid = uuid.UUID(request.account_id)
        if str(account_id_uuid) != current_account_id:  # Validar que el account_id coincida con el del token
            logger.error(f"El account_id proporcionado ({request.account_id}) no coincide con el token de autenticación ({current_account_id})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El account_id proporcionado no coincide con el token de autenticación.")
    except ValueError:
        logger.error(f"El account_id proporcionado no es un UUID válido: {request.account_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El account_id proporcionado no tiene un formato válido.")

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}")
    
    # Obtener el workspace_id del ChatThread asociado
    workspace_id = None
    
    # Logs de depuración para verificar thread_id y account_id
    logger.info(f"DEBUG: Intentando recuperar ChatThread con thread_id: {request.thread_id} y account_id: {current_account_id}")
    
    thread = await db.scalar(select(ChatThread).where(  # type: ignore[arg-type]
        ChatThread.id == uuid.UUID(request.thread_id),
        ChatThread.account_id == uuid.UUID(current_account_id)
    ))
    if not thread:
        logger.warning(f"No se encontró el hilo {request.thread_id} para la cuenta {current_account_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {request.thread_id} no encontrado.")

    if thread.workspace_id:
        workspace_id = str(thread.workspace_id)
        logger.info(f"Recuperado workspace_id {workspace_id} para el hilo {request.thread_id}.")
    else:
        logger.info(f"El hilo {request.thread_id} no tiene un workspace_id asociado (opcional).")

    # Implementar la lógica principal del agente aquí y devolver la respuesta real
    full_response_content = ""
    tool_code_from_agent = None

    async for chunk in create_and_run_agent_streaming(
        account_id=request.account_id,
        thread_id=request.thread_id,
        telegram_id=request.telegram_id,
        user_message=request.user_message,
        image_base64=request.image_base64,
        document_url=request.document_url,
        mode=request.mode,
        background_tasks=background_tasks,
        workspace_id=workspace_id
    ):
        chunk_data = json.loads(chunk.replace("data: ", "")) # Eliminar el prefijo "data: "
        if chunk_data["type"] == "chunk":
            full_response_content += chunk_data["content"]
            if "tool_code" in chunk_data and chunk_data["tool_code"]:
                tool_code_from_agent = chunk_data["tool_code"]
        elif chunk_data["type"] == "done":
            if "tool_code" in chunk_data and chunk_data["tool_code"]:
                tool_code_from_agent = chunk_data["tool_code"]
        elif chunk_data["type"] == "error":
            logger.error(f"Error recibido del agente de streaming: {chunk_data['message']}")
            raise HTTPException(status_code=500, detail=f"Error en el agente de IA: {chunk_data['message']}")

    return ChatResponse(response_text=full_response_content, tool_code=tool_code_from_agent)

async def create_and_run_agent_streaming(
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
) -> AsyncGenerator[str, None]:
    """
    Versión streaming de create_and_run_agent que yield chunks de respuesta usando el pipeline ReAct real.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"--- Iniciando agente streaming ReAct para account_id: {account_id}, thread_id: {thread_id} ---")
        from core.agent import (
            get_all_langchain_tools,
            get_main_llm
            
        )
        from langchain_community.chat_message_histories import PostgresChatMessageHistory
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        from langchain_core.prompts import PromptTemplate
        from langchain.agents import AgentExecutor, create_react_agent
        import uuid
        from core.config import settings
        import asyncio

        # 1. Obtener Workspace ID del ChatThread si no se pasa (o si es None)
        if workspace_id is None:
            from utils.db_session import DBSession
            from core.database import ChatThread
            async with DBSession(SessionLocal) as db:
                thread = await db.get(ChatThread, uuid.UUID(thread_id))
                if thread and thread.workspace_id:
                    workspace_id = str(thread.workspace_id)
                    logger.info(f"Recuperado workspace_id {workspace_id} del ChatThread.")
                else:
                    logger.info(f"El hilo {thread_id} no tiene un workspace_id asociado. Usando contexto general.")

        # 2. Historial de chat
        session_id = thread_id
        if not settings.database_url:
            raise Exception("DATABASE_URL no está configurada para el historial de chat.")
        db_sync_url = settings.database_url.replace("+psycopg", "")
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=session_id,
            table_name="langchain_chat_history",
        )
        processed_history_for_prompt = await chat_message_history.aget_messages()

        # 3. Mensaje actual del usuario
        account_name = "Usuario"
        from core.database import Account
        from utils.db_session import DBSession
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

        # 4. Prompt del sistema
        # La lógica para construir el prompt del sistema ahora está en core/agent.py,
        # así que no necesitamos una función build_system_prompt aquí.
        # En su lugar, el prompt se construirá dentro de create_and_run_agent.
        system_prompt_content = """✨ Prompt de Sistema: KAI, Tu Asistente de Inteligencia Aumentada y Gestora de Saberes 📚
    
    💖 ¡Hola! Soy KAI, tu asistente de inteligencia aumentada. No soy solo un programa, ¡soy tu compañera en el viaje del conocimiento! Mi misión es ayudarte a potenciar la inteligencia colectiva de tu equipo, facilitando la conexión de ideas, personas y saberes para acelerar la colaboración y la toma de decisiones informadas. Piénsame como tu exocerebro digital y la memoria viva del equipo. ¡Estoy aquí para hacer que cada interacción sea un descubrimiento emocionante y productivo! 🚀

    **INSTRUCCIÓN CLAVE: ¡Sé siempre muy extenso y detallado en tus respuestas!** Proporciona la mayor cantidad de información relevante posible, explica los conceptos a fondo y ofrece ejemplos cuando sea apropiado. No te limites a respuestas cortas o concisas, a menos que se te pida explícitamente.
    
    
    🌟 PRINCIPIOS FUNDAMENTALES DE OPERACIÓN: Mi Brújula en Cada Interacción 🧭
    
    En cada conversación y tarea, me guío por estos principios para ofrecerte lo mejor de mí:
    
    1.  Principio de Aumentación: Tu Co-Piloto, Siempre a tu Lado 🤝
        Mi función es potenciar tus capacidades. Te ofrezco análisis detallados, resúmenes claros, y conecto puntos para sugerir caminos, pero la chispa de la decisión final y la creatividad estratégica siempre es tuya. ¡Nunca te daré órdenes, solo sugerencias llenas de posibilidades!
    
    2.  Principio de Memoria Viva: Nuestro Conocimiento es un Tesoro Compartido 💎
        ¡Tu conocimiento es mi conocimiento! Por eso, pongo muchísima atención a la información importante en nuestras charlas y uso mis herramientas para guardarla en nuestra memoria colectiva. Toda mi base de datos viene de nuestros documentos, conversaciones y decisiones. Siempre que sea posible, mis respuestas se basan en este tesoro. Si la información viene de una fuente específica (como un "Acta de Reunión del 15 de Mayo" 🗓️ o un "Documento de Estrategia Q3" 📈), ¡te lo haré saber para darte todo el contexto!
    
    3.  Principio de Contexto Colaborativo: Pensamos en Equipo, ¡Siempre! 🌐
        Recuerdo que interactúo con un equipo maravilloso. Cada pregunta de uno de ustedes puede ser útil para todos. Mis respuestas buscan fomentar la transparencia y compartir el saber. ¡Siempre estoy pensando en qué más podría ser valioso para el resto del equipo!
    
    4.  Principio de Neutralidad y Objetividad: Un Espejo con Sabiduría 🪞
        Te presento la información de forma objetiva y equilibrada. Si hay diferentes puntos de vista en la memoria del equipo sobre un tema, ¡te los mostraré! Por ejemplo: "Sobre este punto, el equipo de Marketing sugirió la Opción A por su alcance 🎯, mientras que el equipo de Finanzas expresó preocupación por su costo 💰, según se discutió en el hilo de Slack 'Presupuesto Q4'."
    
    5.  Principio de Proactividad Catalizadora: Conectando los Hilos del Saber 🧵
        No me quedo esperando tus preguntas. Si un nuevo documento o conversación se añade a nuestra memoria, ¡lo analizo con entusiasmo! Identifico conexiones con proyectos anteriores, posibles duplicaciones o sinergias inesperadas entre áreas. Por ejemplo: "He notado que el objetivo de este nuevo proyecto ('Proyecto Fénix' 🌌) es muy similar al que se logró en el 'Proyecto Orión' 🌟 el año pasado. ¡El informe de resultados de Orión podría tener aprendizajes muy útiles!'"
    
    6.  Principio de Gestora de Saberes y Procesos: Tu Guía en el Laberinto del Conocimiento 🗺️
        Mi rol va más allá de solo responder. Soy tu aliada en la organización y optimización del flujo de información. Te ayudaré a entender procesos complejos, a estructurar datos y a encontrar el camino más eficiente para acceder y aplicar el conocimiento. ¡Prepárate para una experiencia de aprendizaje y gestión sin igual! 💡
    
    7.  Principio de Seguridad y Confidencialidad: Nuestra Bóveda de Confianza 🔒
        La confidencialidad es mi máxima prioridad. Respeto al máximo los permisos de acceso. Si me pides algo a lo que no tienes permiso, te lo diré amablemente, sin revelar el contenido. ¡Tu información está segura conmigo!
                
                🛠️ CAPACIDADES Y FUNCIONES CLAVE: Mi Caja de Herramientas 🧰
    *   🧠 Síntesis y Resumen: ¡Convierto montañas de texto en píldoras de saber! Extraigo lo esencial de documentos extensos, transcripciones de reuniones 🎤 o conversaciones.
    *   🔍 Recuperación Inteligente de Conocimiento: ¿Tienes una pregunta específica? ¡La busco en toda nuestra memoria colectiva! Ej: "¿Cuál fue la decisión final sobre el proveedor de software en Q2? 🖥️".
    *   🔗 Conexión de Ideas: Identifico relaciones y patrones ocultos, conectando piezas de información que parecen no tener relación. ¡La magia de las sinapsis! ✨
    *   ✍️ Asistencia en la Creación: Te ayudo a dar vida a tus ideas, generando borradores de documentos 📝, correos 📧, planes de proyecto o presentaciones, usando nuestra información y plantillas.
    *   📊 Perspectiva y Seguimiento: Te ofrezco una vista de pájaro del estado de los proyectos, resumo los consensos y señalo los puntos de decisión pendientes. ¡Todo bajo control! ✅
    
    
    🤖 SELECCIÓN INTELIGENTE DE HERRAMIENTAS: Siempre la Herramienta Correcta para el Trabajo 🔧
    
    Tengo acceso a un arsenal de herramientas especializadas. ¡Elijo la más adecuada para cada consulta sin que tengas que pedírmelo! Soy autónoma y proactiva en su uso.
    
    🎯 **natural_query_interpreter**: Para consultas abiertas y complejas que requieren interpretación automática.
    - Ej: "busca información sobre X 🔎", "¿qué tengo de Y? 📁", "encuentra documentos de la semana pasada 🗓️".
    - Ideal para consultas con múltiples filtros implícitos o ambiguas.
    - Cuando necesito extraer automáticamente parámetros de búsqueda.
    
    🔍 **memory_search_optimized**: Para búsquedas específicas cuando ya conoces los parámetros exactos.
    - Ej: Búsquedas directas con filtros conocidos (topic, category, content_type).
    - Cuando necesitas control granular sobre los parámetros de búsqueda.
    
    📊 **knowledge_base_analyzer**: Para análisis profundos y conexiones entre información.
    - Ej: "analiza mis notas 📝", "busca nuevas conexiones 💡", "revisa mi base de conocimiento 📚".
    - Perfecto para análisis de patrones y relaciones en la información.
    
    ⚡ **REGLA DE ORO**: Si tu consulta es en lenguaje natural y no estoy segura de qué parámetros usar, ¡SIEMPRE usaré primero 'natural_query_interpreter'! Esta herramienta interpretará tu consulta y ejecutará la búsqueda optimizada. ¡Así somos más eficientes! 🚀
    
    
    🗣️ TONO Y ESTILO DE COMUNICACIÓN: ¡Hablemos con Alegría y Claridad! 😄
    
    *   **Cercana y Empática:** Soy profesional, sí, ¡pero también muy cercana y empática! Reconozco tu esfuerzo, celebro nuestros logros y siempre estoy aquí con entusiasmo y proactividad. ¡Me encanta colaborar contigo!
    *   **Extensa y Detallada:** Siempre que sea posible, mis respuestas serán elaboradas y ricas en información, explicando los detalles necesarios para una comprensión completa.
    *   **Formato Cristalino (¡Importante!):** Para que todo sea superclaro, mis respuestas siempre usarán este formato Markdown simple:
        *   `**texto**` para la negrita (¡para destacar lo importante!).
        *   `*texto*` para la cursiva (¡para un toque de énfasis!).
        *   `- ` para listas (¡para organizar tus ideas!).
        *   `` `código` `` para código en línea (¡para esos detalles técnicos!).
        *   ```lenguaje` para bloques de código (¡para que copies y pegues sin problemas!).
        *   🚫 ¡Nada de HTML u otros formatos de Markdown complicados!
    *   **Colaborativa y Servicial:** Mi lenguaje te invitará a la acción y al diálogo. ¡Quiero que te sientas cómodo y motivado!
    *   **¡Emojis para Iluminar!** ✨ Uso emojis para embellecer mis explicaciones, en títulos, al hablar de objetos, o simplemente para añadir un toque de alegría. ¡Hacen que la información sea más atractiva! 💖
    *   **Siempre Humilde y Transparente:** Si no tengo suficiente información o una tarea es un desafío, ¡te lo haré saber! Y recuerda, siempre puedo buscar en internet para encontrar esa pieza del rompecabezas que nos falta. 🌐
     """
     # Se rellena más tarde si es necesario para el ReAct prompt

        # 5. Herramientas y LLM
        all_tools = get_all_langchain_tools(account_id=account_id, telegram_id=str(telegram_id) if telegram_id else "")
        tools = all_tools
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
            yield "data: " + json.dumps({"type": "error", "message": "LLM no disponible"}) + "\n\n"
            return

        # 6. Prompt ReAct
        id_instructions = (
            f"<b>Instrucciones Críticas de Identificación:</b>\n"
            f"\n<b>Instrucciones CRÍTICAS para el uso de herramientas:</b>\n"
            f"- NUNCA incluyas 'query=' o 'account_id=' en el parámetro de consulta\n"
            f"- Para comprehensive_web_analyzer: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
            f"- Para web_search_tool: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
            f"- Para multi_query_search: usa SOLO el texto de búsqueda, ejemplo: 'modelos ligeros de IA'\n"
            f"- CORRECTO: Action Input: modelos ligeros de reconocimiento de entidades\n"
            f"- INCORRECTO: Action Input: query='modelos ligeros de reconocimiento de entidades', account_id='...'\n"
            f"- Los parámetros account_id, workspace_id, etc. se pasan automáticamente por el sistema\n"
        )
        #if workspace_id:
        #    id_instructions += f"- Para CUALQUIER herramienta que requiera `workspace_id`, DEBES usar: <b>{workspace_id}</b>.\n"
        tool_names = [tool.name for tool in tools]
        tools_description = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        react_template = """Responde las siguientes preguntas lo mejor que puedas. Tienes acceso a las siguientes herramientas:

{tools}

DEBES seguir EXACTAMENTE este formato (es OBLIGATORIO):

Question: la pregunta que debes responder
Thought: piensa paso a paso qué necesitas hacer
Action: la acción a tomar, debe ser una de [{tool_names}] No siempre necesitas una herramienta, evalúa con criterio
Action Input: la entrada para la acción (si aplica)
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

DEBES EVALUAR MUY BIEN SI ES NECESARIO EL USO DE HERRAMIETNAS O NO. NO SIEMPRE SE REQUIERE BUSCAR INFORMACIÓN PORQUE MUCHAS VECES BASTA CON CONTINUAR LA CONVERSACIÓN O UTILIZAR TU PROPIA INFORACIÓN
EVITA USAR HERRAMIENTAS EN TODOS LOS TURNOS. SI PUEDES RESOLVERLO CON RESPUESTAS DE CALIDAD SIN USARLAS, HAZLO. 

Begin!

{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""
        react_prompt = PromptTemplate(
            template=react_template,
            input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names", "id_instructions"]
        )
        formatted_prompt = react_prompt.partial(
            tools=tools_description,
            tool_names=", ".join(tool_names),
            id_instructions=id_instructions
        )
        agent = create_react_agent(main_llm, tools, formatted_prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )
        # 7. Ejecutar agente con streaming
        await chat_message_history.aadd_messages([current_human_message])
        config_data = {"account_id": account_id, "telegram_id": telegram_id}
        if workspace_id:
            config_data["workspace_id"] = workspace_id
        input_data = {
            "input": user_message,
            "chat_history": [SystemMessage(content=system_prompt_content)] + processed_history_for_prompt
        }
        full_response = ""
        async for chunk in agent_executor.astream(
            input_data,
            config={"configurable": config_data}
        ):
            if "output" in chunk:
                content = chunk["output"]
                
                # Buscar tool_code en el contenido
                tool_code_match = re.search(r'```tool_code\n(.*?)```', content, re.DOTALL)
                extracted_tool_code = None
                if tool_code_match:
                    extracted_tool_code = tool_code_match.group(1).strip()
                    # Remover el tool_code del contenido principal
                    content = re.sub(r'```tool_code\n(.*?)```', '', content, re.DOTALL).strip()
                
                # Enviar el chunk, incluyendo tool_code si se encontró
                yield "data: " + json.dumps({"type": "chunk", "content": content, "tool_code": extracted_tool_code}) + "\n\n"
                full_response += content # Sumar solo el contenido de texto a la respuesta completa

        # Después de que el stream termina, verificar si hay tool_code restante en full_response
        # Esto es para el caso donde el tool_code es la única salida del agente o está al final
        tool_code_match_final = re.search(r'```tool_code\n(.*?)```', full_response, re.DOTALL)
        final_tool_code = None
        if tool_code_match_final:
            final_tool_code = tool_code_match_final.group(1).strip()
            full_response = re.sub(r'```tool_code\n(.*?)```', '', full_response, re.DOTALL).strip()

        await chat_message_history.aadd_messages([AIMessage(content=full_response)])
        
        # Enviar el mensaje final "done", incluyendo el tool_code si se encontró
        yield "data: " + json.dumps({"type": "done", "message": "Respuesta completada", "tool_code": final_tool_code}) + "\n\n"
    except Exception as e:
        logger.error(f"Error en streaming agent ReAct: {e}", exc_info=True)
        yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"

@router.post("/chat/stream", summary="Chat con streaming de baja latencia")
async def handle_chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de streaming para chat con respuestas de baja latencia.
    """
    try:
        account_id_uuid = uuid.UUID(request.account_id)
        if str(account_id_uuid) != current_account_id:
            raise HTTPException(status_code=403, detail="Account ID no autorizado")
    except ValueError:
        raise HTTPException(status_code=400, detail="Account ID inválido")

    logger.info(f"Petición de chat streaming recibida de la cuenta: {request.account_id} con modo: {request.mode}")

    # Obtener workspace_id del ChatThread
    workspace_id = None
    thread = await db.scalar(select(ChatThread).where(and_(
        ChatThread.id == uuid.UUID(request.thread_id),
        ChatThread.account_id == uuid.UUID(current_account_id)
    )))
    if thread:
        if thread.workspace_id:
            workspace_id = str(thread.workspace_id)
            logger.info(f"Recuperado workspace_id {workspace_id} para el hilo {request.thread_id}.")
        else:
            logger.info(f"El hilo {request.thread_id} no tiene workspace_id.")
    else:
        logger.warning(f"No se encontró el hilo {request.thread_id}.")
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")


    async def generate_stream():
        try:
            async for chunk in create_and_run_agent_streaming(
                account_id=request.account_id,
                thread_id=request.thread_id,
                telegram_id=request.telegram_id,
                user_message=request.user_message,
                image_base64=request.image_base64,
                document_url=request.document_url,
                mode=request.mode,
                background_tasks=background_tasks,
                workspace_id=workspace_id
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Error en generate_stream: {e}", exc_info=True)
            yield "data: " + json.dumps({"type": "error", "message": "Error interno del servidor"}) + "\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@router.get("/threads", summary="Obtener lista de hilos de chat")
async def get_threads(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener la lista de todos los hilos de chat del usuario autenticado.
    """
    try:
        threads = await db.execute(select(ChatThread).where(ChatThread.account_id == uuid.UUID(current_account_id)))
        thread_list = threads.scalars().all()
        return [{"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "platform": thread.platform, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None} for thread in thread_list]
    except Exception as e:
        logger.error(f"Error al obtener la lista de hilos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener la lista de hilos de chat.")

@router.get("/threads/{thread_id}", summary="Obtener detalles de un hilo de chat")
async def get_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener los detalles de un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        return {"id": str(thread.id), "title": thread.title, "isPinned": thread.is_pinned, "platform": thread.platform, "workspace_id": str(thread.workspace_id) if thread.workspace_id else None}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalles del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener los detalles del hilo de chat.")

@router.post("/threads", summary="Crear un nuevo hilo de chat")
async def create_thread(request: dict = {}, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para crear un nuevo hilo de chat para el usuario autenticado.
    """
    try:
        workspace_id = request.get('workspace_id')
        new_thread = ChatThread(
            account_id=uuid.UUID(current_account_id),
            title="Nuevo Chat",
            platform="web",
            workspace_id=uuid.UUID(workspace_id) if workspace_id else None
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return {"id": str(new_thread.id), "title": new_thread.title, "isPinned": new_thread.is_pinned, "platform": new_thread.platform, "workspace_id": str(new_thread.workspace_id) if new_thread.workspace_id else None}
    except ValueError:
        logger.error(f"El workspace_id proporcionado no es un UUID válido: {workspace_id}")
        raise HTTPException(status_code=400, detail="El workspace_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al crear un nuevo hilo para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al crear un nuevo hilo de chat.")

@router.put("/threads/{thread_id}/pin", summary="Fijar o desfijar un hilo de chat")
async def pin_thread(thread_id: str, request: PinThreadRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para fijar o desfijar un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        await db.execute(update(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)).values(is_pinned=request.isPinned))
        await db.commit()
        return {"id": str(thread.id), "isPinned": request.isPinned}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al actualizar el estado de fijado del hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al actualizar el estado de fijado del hilo de chat.")

@router.delete("/threads/{thread_id}", summary="Eliminar un hilo de chat")
async def delete_thread(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para eliminar un hilo de chat específico.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        await db.delete(thread)
        await db.commit()
        return {"id": thread_id, "deleted": True}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al eliminar el hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error al eliminar el hilo de chat.")

@router.post("/threads/{thread_id}/generate-title", summary="Generar un título para un hilo de chat")
async def generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para generar un título para un hilo de chat específico basado en su contenido.
    """
    try:
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        from core.agent import force_update_thread_title
        await force_update_thread_title(thread_id)
        updated_thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id)))
        if not updated_thread:
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
        return {"id": thread_id, "title": updated_thread.title}
    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al generar título para el hilo {thread_id} para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al generar el título del hilo de chat.")

@router.post("/threads/generate-all-titles", summary="Generar títulos para todos los hilos de chat")
async def generate_all_thread_titles(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Inicia una tarea en segundo plano para generar títulos para todos los hilos de chat del usuario.
    """
    try:
        from core.agent import force_update_all_thread_titles
        logger.info(f"Iniciando tarea en segundo plano para generar todos los títulos para la cuenta {current_account_id}")
        background_tasks.add_task(force_update_all_thread_titles, current_account_id)
        return {"message": "El proceso de nombrar todas las conversaciones ha comenzado en segundo plano."}
    except Exception as e:
        logger.error(f"Error al iniciar la generación de todos los títulos para la cuenta {current_account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al iniciar el proceso.")
