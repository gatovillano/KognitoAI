# api/chat.py

import logging
import uuid
import re
import json
import asyncio
import os
from typing import Optional, AsyncGenerator, Any, List, Dict
from io import BytesIO
import httpx
from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

from sqlalchemy import update, Integer, cast # Added cast # Added Integer


from utils.audio_transcriber import transcribe_audio_file
from utils.security import get_current_account_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import SessionLocal, ChatThread, settings, Workspace
from core.llm_manager import get_main_llm
from tools.deep_research_tool import DeepResearchTool
from tools.add_web_to_rag_tool import AddWebToRAGTool
from tools.ddg_search_tool import create_ddg_search_tool

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
    rag_context: Optional[List[Dict[str, str]]] = None # Contexto RAG: [{'type': 'document', 'id': '...'}, {'type': 'collection', 'id': '...'}]

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
    rag_context: Optional[List[Dict[str, str]]] = None

class TextToSpeechRequest(BaseModel):
    """Define la estructura de datos para una solicitud de conversión de texto a voz."""
    text: str
    voice: Optional[str] = None  # Voz opcional para la conversión

class PinThreadRequest(BaseModel):
    """Define la estructura de datos para una solicitud de fijar/desfijar un hilo de chat."""
    isPinned: bool

class Message(BaseModel):
    text: str
    sender: str
    created_at: str

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
    # text_to_speak = re.sub(r'`[^`]*`', '', text_to_speak)
    # 3. Eliminar caracteres de puntuación que no se quieren leer
    # text_to_speak = re.sub(r'[\[\]{}()#*_]', '', text_to_speak)
    # 4. Limpiar espacios en blanco múltiples
    text_to_speak = re.sub(r'\s+', ' ', text_to_speak).strip()

    if not text_to_speak:
        return StreamingResponse(BytesIO(), media_type="audio/wav")

    # Parámetros para open-edgetts.
    tts_payload = {
        'input': text_to_speak,
        'voice': request.voice if request.voice else 'es-MX-JorgeNeural',
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
async def handle_chat(
    background_tasks: BackgroundTasks,
    thread_id: str = Form(...),
    account_id: str = Form(...),
    user_message: str = Form(...),
    telegram_id: Optional[int] = Form(None),
    image_base64: Optional[str] = Form(None),
    document_url: Optional[str] = Form(None),
    mode: Optional[str] = Form(None),
    rag_context: Optional[str] = Form(None), # Received as JSON string
    file: Optional[UploadFile] = File(None), # New parameter for file upload
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
    # Parse rag_context if provided
    parsed_rag_context = None
    if rag_context:
        try:
            parsed_rag_context = json.loads(rag_context)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON for rag_context: {rag_context}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El formato de rag_context es inválido.")

    try:
        account_id_uuid = uuid.UUID(account_id)
        if str(account_id_uuid) != current_account_id:  # Validar que el account_id coincida con el del token
            logger.error(f"El account_id proporcionado ({account_id}) no coincide con el token de autenticación ({current_account_id})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El account_id proporcionado no coincide con el token de autenticación.")
    except ValueError:
        logger.error(f"El account_id proporcionado no es un UUID válido: {account_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El account_id proporcionado no tiene un formato válido.")

    logger.info(f"Petición de chat recibida de la cuenta: {account_id} con modo: {mode}")
    
    # Obtener el workspace_id del ChatThread asociado
    workspace_id = None
    
    # Logs de depuración para verificar thread_id y account_id
    logger.info(f"DEBUG: Intentando recuperar ChatThread con thread_id: {thread_id} y account_id: {current_account_id}")
    
    thread = await db.scalar(select(ChatThread).where(  # type: ignore[arg-type]
        ChatThread.id == uuid.UUID(thread_id),
        ChatThread.account_id == uuid.UUID(current_account_id)
    ))
    if not thread:
        logger.warning(f"No se encontró el hilo {thread_id} para la cuenta {current_account_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hilo de chat con id {thread_id} no encontrado.")

    if thread.workspace_id:
        workspace_id = str(thread.workspace_id)
        logger.info(f"Recuperado workspace_id {workspace_id} para el hilo {thread_id}.")
    else:
        logger.info(f"El hilo {thread_id} no tiene un workspace_id asociado (opcional).")

    # --- Manejo de archivos adjuntos ---
    processed_file_content = None
    if file:
        logger.info(f"Archivo recibido: {file.filename}, Content-Type: {file.content_type}")
        try:
            # Aquí iría la lógica para procesar el archivo (ej. extraer texto)
            # Por ahora, solo leeremos el contenido como bytes y lo codificaremos si es necesario
            # En una implementación real, se usaría una librería para extraer texto de PDFs, DOCX, etc.
            file_bytes = await file.read()
            # Ejemplo muy básico: si es texto, leerlo; si no, indicar que es un archivo binario
            if file.content_type and "text" in file.content_type:
                processed_file_content = file_bytes.decode('utf-8')
            elif file.content_type and "pdf" in file.content_type:
                # Placeholder para procesamiento de PDF
                processed_file_content = f"Contenido de PDF adjunto (procesamiento pendiente): {file.filename}"
            else:
                processed_file_content = f"Archivo adjunto (tipo no procesado para texto): {file.filename}"
            
            # Añadir el contenido del archivo al user_message para que el LLM lo vea
            user_message = f"{user_message}\n\n--- Contenido del archivo adjunto: {file.filename} ---\n{processed_file_content}\n--- Fin del contenido del archivo adjunto ---" 
            logger.info(f"Contenido del archivo {file.filename} añadido al user_message.")

        except Exception as e:
            logger.error(f"Error al procesar el archivo {file.filename}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar el archivo: {e}")
    # --- Fin manejo de archivos adjuntos ---

    # Implementar la lógica principal del agente aquí y devolver la respuesta real
    # La lógica de streaming ahora se maneja dentro de create_and_run_agent_streaming
    # y solo el "Final Answer" se propaga como contenido.
    # Los pasos intermedios (actions, observations) no deben ser parte del content.
    # Por lo tanto, simplemente consumimos el generador y obtenemos la respuesta final.
    final_agent_response = ""
    final_tool_code = None
    final_sources = []

    async for chunk_str in create_and_run_agent_streaming(
        account_id=account_id,
        thread_id=thread_id,
        telegram_id=telegram_id,
        user_message=user_message,
        image_base64=image_base64,
        document_url=document_url,
        mode=mode,
        rag_context=parsed_rag_context, # Use parsed rag_context
        background_tasks=background_tasks,
        workspace_id=workspace_id
    ):
        chunk_data = json.loads(chunk_str.replace("data: ", ""))
        if chunk_data["type"] == "chunk":
            final_agent_response += chunk_data.get("content", "")
        elif chunk_data["type"] == "done":
            # El mensaje final del tipo "done" puede contener la respuesta completa o un resumen
            # Si ya hemos acumulado chunks, el mensaje del "done" es solo una confirmación.
            # Si no hubo chunks (ej. respuesta corta), el mensaje del "done" es la respuesta.
            if not final_agent_response:
                final_agent_response = chunk_data.get("message", "")
            final_tool_code = chunk_data.get("tool_code")
            final_sources = chunk_data.get("sources", [])
            logger.info(f"DEBUG (handle_chat): Recibido chunk 'done'. final_tool_code: {final_tool_code}, final_sources: {final_sources}")
        elif chunk_data["type"] == "error":
            logger.error(f"Error recibido del agente de streaming: {chunk_data['message']}")
            raise HTTPException(status_code=500, detail=f"Error en el agente de IA: {chunk_data['message']}")

    logger.info(f"DEBUG (handle_chat): Retornando ChatResponse con response_text: {final_agent_response[:100]}..., tool_code: {final_tool_code}, sources: {final_sources}")
    return ChatResponse(response_text=final_agent_response, tool_code=final_tool_code, sources=final_sources)


async def create_and_run_agent_streaming(
    account_id: str,
    thread_id: str,
    telegram_id: Optional[int],
    user_message: str,
    image_base64: Optional[str] = None,
    document_url: Optional[str] = None,
    mode: Optional[str] = None,
    rag_context: Optional[List[Dict[str, str]]] = None,
    background_tasks: Optional[Any] = None,
    workspace_id: Optional[str] = None,
    k: int = 5
) -> AsyncGenerator[str, None]:
    """
    Ejecuta el agente LangGraph y transmite los resultados en dos fases:
    1.  Fase de Proceso: Envía el estado actual del grafo (ej. "Reflexionando...").
    2.  Fase de Tokens: Transmite la respuesta final token por token.
    """
    from core.agent import create_langgraph_agent, AgentState # Importar AgentState
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage # Importar ToolMessage
    from langchain_community.chat_message_histories import PostgresChatMessageHistory
    from core.config import settings
    from core.database import LangchainPgEmbedding # Importar el modelo correcto
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    # from sqlalchemy import Integer # Importar Integer - MOVED


    logger.info(f"--- Iniciando agente LangGraph para account_id: {account_id}, thread_id: {thread_id} ---")

    try:
        # --- Preparación del Contexto RAG ---
        context_text = ""
        if rag_context:
            logger.info(f"Enriqueciendo contexto con {len(rag_context)} item(s) de RAG.")
            document_ids_to_fetch = [item['id'] for item in rag_context if item.get('type') == 'document']
            
            if document_ids_to_fetch:
                async with SessionLocal() as session:
                    # 1. Obtener todos los chunks para los documentos solicitados
                    stmt = (
                        select(LangchainPgEmbedding)
                        .filter(LangchainPgEmbedding.cmetadata['document_id'].astext.in_(document_ids_to_fetch))
                        .order_by(cast(LangchainPgEmbedding.cmetadata['chunk_index'].astext, Integer))\
                    )
                    result = await session.execute(stmt)
                    all_chunks = result.scalars().all()

                    # 2. Agrupar chunks por document_id
                    docs_content = {}
                    for chunk in all_chunks:
                        doc_id = chunk.cmetadata.get('document_id')
                        if doc_id not in docs_content:
                            docs_content[doc_id] = {
                                'title': chunk.cmetadata.get('title', chunk.cmetadata.get('file_name')),
                                'chunks': []
                            }
                        docs_content[doc_id]['chunks'].append(chunk.document)

                    # 3. Construir el texto del contexto
                    for doc_id, data in docs_content.items():
                        full_content = "".join(data['chunks'])
                        context_text += f"\n\n--- Contexto del Documento: {data['title']} ---\n"
                        context_text += f"Contenido: {full_content}\n"
                        context_text += "--- Fin del Contexto del Documento ---"

        if context_text:
            # No modificar user_message aquí, solo usar context_text para el LLM
            # El contexto se pasará al LLM a través de un prompt específico o como parte de las herramientas
            logger.info("Contexto RAG preparado para el LLM.")

        # --- Preparación Inicial ---
        agent_app = create_langgraph_agent()
        db_sync_url = settings.database_url.replace("+psycopg", "")
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )
        history_messages = await chat_message_history.aget_messages()

        # Crear el HumanMessage con el rag_context en additional_kwargs
        user_message_with_rag_context = HumanMessage(
            content=user_message,
            additional_kwargs={'rag_context': rag_context} if rag_context else {}
        )

        # --- Fase 1: Streaming del Proceso con LangGraph ---
        initial_state = {
            "messages": history_messages + [HumanMessage(content=user_message)],
            "account_id": account_id,
            "telegram_id": telegram_id,
            "workspace_id": workspace_id,
            "rag_context": rag_context,  # <-- AÑADIDO
            "sources": [],  # Inicializar lista de fuentes
        }

        config = {"configurable": {"thread_id": thread_id}}
        final_state = None

        async for chunk in agent_app.astream(initial_state, config=config):
            if "getContext" in chunk:
                yield "data: " + json.dumps({"type": "status", "message": "Analizando contexto... 🧠"}) + "\n\n"
            elif "callTool" in chunk:
                yield "data: " + json.dumps({"type": "status", "message": "Consultando mis herramientas... 🛠️"}) + "\n\n"
            elif "reflect" in chunk:
                yield "data: " + json.dumps({"type": "status", "message": "Reflexionando sobre la información... 🤔"}) + "\n\n"
            elif "generateResponse" in chunk:
                yield "data: " + json.dumps({"type": "status", "message": "Generando respuesta... ✍️"}) + "\n\n"
                final_state = chunk["generateResponse"]
        
        if not final_state or not final_state.get("messages"):
            logger.warning("El grafo finalizó sin un nodo 'generateResponse' explícito. Se intentará recuperar del último chunk.")
            # Si el bucle termina sin un nodo 'generateResponse', el último chunk
            # puede contener el estado final completo del último nodo ejecutado.
            if chunk and "agent" in chunk:
                final_state = chunk["agent"]
                logger.info("Estado final recuperado del último nodo 'agent' en el chunk.")
            else:
                # Si aún no hay estado, el grafo realmente falló.
                logger.error("No se pudo recuperar un estado final válido del grafo.")
                raise ValueError("El grafo no produjo un estado final válido y el último chunk no contenía un estado recuperable.")

        # --- Fase 2: Streaming de Tokens de la Respuesta Final ---
        final_response_message = final_state["messages"][-1]
        full_response_content = ""

        # Simulamos el streaming de tokens para la respuesta ya generada
        # En una implementación real con un LLM que soporte streaming, aquí se usaría `llm.astream()`
        for char in final_response_message.content:
            full_response_content += char
            yield "data: " + json.dumps({"type": "chunk", "content": char}) + "\n\n"

        # Guardar el historial completo (incluyendo la respuesta final)
        await chat_message_history.aadd_messages([HumanMessage(content=user_message), AIMessage(content=full_response_content)])

        # --- NOMBRAMIENTO AUTOMÁTICO DE HILOS ---
        if background_tasks:
            # Obtener el historial actualizado para el conteo
            updated_history = await chat_message_history.aget_messages()
            # Filtrar mensajes que no sean de resumen para un conteo preciso
            real_messages = [m for m in updated_history if not (hasattr(m, 'additional_kwargs') and m.additional_kwargs.get("role") == "summary")]
            message_count = len(real_messages)

            async with SessionLocal() as db:
                thread = await db.get(ChatThread, uuid.UUID(thread_id))
                current_title = thread.title if thread else ""

            # Condición para nombrar/renombrar
            should_rename = (
                (current_title == "Nuevo Chat" and message_count >= 3) or
                (message_count >= 10 and message_count % 10 == 0) # Renombrar cada 10 mensajes después de los 10 iniciales
            )

            if should_rename:
                from core.agent import force_update_thread_title
                logger.info(f"[AUTO-TÍTULO] Hilo {thread_id} cumple condición para nombrar/renombrar con {message_count} mensajes. Título actual: '{current_title}'")
                background_tasks.add_task(force_update_thread_title, thread_id)
        # --- FIN NOMBRAMIENTO AUTOMÁTICO ---
        
        # Extraer tool_code de los mensajes del estado final, si existe
        # Asumimos que si hay tool_code, debería estar en el último mensaje de herramienta o en el último mensaje del AI
        tool_code_to_send = None
        sources_to_send = []

        # Buscar tool_code en los mensajes del estado final
        for msg in final_state["messages"]:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                # Si el LLM emitió tool_calls, las convertimos a una representación de tool_code
                # Esto es una simplificación; en un sistema real, el tool_code sería el JSON de la llamada a la herramienta
                tool_code_to_send = json.dumps([
                    {
                        "name": tc["name"],
                        "arguments": tc["args"],
                    }
                    for tc in msg.tool_calls
                ])
                logger.info(f"DEBUG (create_and_run_agent_streaming): Encontrado tool_code en AIMessage: {tool_code_to_send}")
                break # Solo tomamos el primero
            elif isinstance(msg, ToolMessage) and msg.content:
                # Si hay un ToolMessage, su contenido podría ser el resultado de la herramienta, no el código de la herramienta en sí.
                # Necesitamos ser más específicos sobre cómo se representa el "tool_code" que el frontend espera ejecutar.
                # Por ahora, si el LLM lo "imprime" como parte de su respuesta, es el problema principal.
                logger.info(f"DEBUG (create_and_run_agent_streaming): Encontrado ToolMessage con contenido: {msg.content[:100]}...")
                # Aquí, si el frontend espera un JSON específico para ejecutar, deberíamos construirlo.
                # Por el momento, este log nos ayudará a ver si el ToolMessage se está generando.
                pass # No se hace nada aquí, ya que el tool_code es lo que el frontend espera ejecutar.

        # También podríamos querer extraer fuentes si el LLM las proporciona en algún formato específico
        # Por ahora, este ejemplo no las maneja explícitamente en el estado del grafo, pero es un punto de extensión.

        yield "data: " + json.dumps({
            "type": "done",
            "message": "Respuesta completada",
            "tool_code": tool_code_to_send, # Enviar el tool_code si se encontró
            "sources": sources_to_send # Enviar las fuentes si se encontraron
        }) + "\n\n"

    except Exception as e:
        logger.error(f"Error en streaming agent LangGraph: {e}", exc_info=True)
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
            if request.mode == "deepResearch":
                logger.info(f"Iniciando Deep Research para: {request.user_message}")
                llm_instance = get_main_llm()
                if not llm_instance:
                    raise HTTPException(status_code=500, detail="LLM no inicializado para Deep Research.")

                ddg_search_tool_instance = create_ddg_search_tool(account_id=request.account_id)
                add_web_to_rag_tool_instance = AddWebToRAGTool()

                deep_research_tool = DeepResearchTool(
                    llm_instance=llm_instance,
                    ddg_search_tool=ddg_search_tool_instance,
                    add_web_to_rag_tool=add_web_to_rag_tool_instance
                )

                research_report = await deep_research_tool._run(request.user_message)
                
                yield "data: " + json.dumps({"type": "chunk", "content": "**Informe de Investigación Profunda:**\n\n"}) + "\n\n"
                for char in research_report:
                    yield "data: " + json.dumps({"type": "chunk", "content": char}) + "\n\n"
                yield "data: " + json.dumps({"type": "done", "message": "Investigación profunda completada."}) + "\n\n"

            else:
                async for chunk in create_and_run_agent_streaming(
                    account_id=request.account_id,
                    thread_id=request.thread_id,
                    telegram_id=request.telegram_id,
                    user_message=request.user_message,
                    image_base64=request.image_base64,
                    document_url=request.document_url,
                    mode=request.mode,
                    rag_context=request.rag_context,
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
        # MODIFICADO: Añadido .order_by() para ordenar por fecha de creación descendente
        threads = await db.execute(
            select(ChatThread)
            .where(ChatThread.account_id == uuid.UUID(current_account_id))
            .order_by(ChatThread.created_at.desc())
        )
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

@router.get("/threads/{thread_id}/messages", summary="Obtener mensajes de un hilo de chat")
async def get_thread_messages(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener los mensajes de un hilo de chat específico.
    """
    try:
        logger.info(f"DEBUG: Intentando obtener mensajes para Thread ID: {thread_id}, Account ID: {current_account_id}") # Added logging
        # Verificar que el hilo pertenece al usuario
        thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
        if not thread:
            logger.warning(f"DEBUG: Hilo {thread_id} no encontrado para Account ID: {current_account_id}") # Added logging
            raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")

        # Recuperar historial de mensajes de Langchain
        if not settings.database_url:
            raise Exception("DATABASE_URL no está configurada para el historial de chat.")
        db_sync_url = settings.database_url.replace("+psycopg", "")
        
        chat_message_history = PostgresChatMessageHistory(
            connection_string=db_sync_url,
            session_id=thread_id,
            table_name="langchain_chat_history",
        )

        history_messages = await chat_message_history.aget_messages()
        
        # Formatear mensajes para el frontend
        formatted_messages = []
        for msg in history_messages:
            sender = "unknown"
            if isinstance(msg, HumanMessage):
                sender = "user"
            elif isinstance(msg, AIMessage):
                sender = "ai"
            
            # Asegurarse de que el contenido es un string
            content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)

            formatted_messages.append({
                "text": content,
                "sender": sender,
                "created_at": msg.additional_kwargs.get('timestamp', ''),
                "ragContext": msg.additional_kwargs.get('rag_context', []) # Extraer rag_context
            })

        return formatted_messages

    except ValueError:
        logger.error(f"El thread_id proporcionado no es un UUID válido: {thread_id}")
        raise HTTPException(status_code=400, detail="El thread_id proporcionado no tiene un formato válido.")
    except Exception as e:
        logger.error(f"Error al obtener mensajes del hilo {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error al obtener los mensajes del hilo de chat.")



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

