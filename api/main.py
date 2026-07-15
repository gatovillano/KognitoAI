import logging
import asyncio # Added
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, status, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.middleware.audit import AuditMiddleware
import json
import os
import uuid
from utils.patches import apply_patches
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from utils.limiter import limiter

# Aplicar parches de estabilidad antes de cualquier otra cosa
apply_patches()


from api.auth import router as auth_router
from api.users import router as users_router
from api.chat import router as chat_router
from api.chat_share import router as chat_share_router
from api.documents import router as documents_router
from api.notes import router as notes_router
from api.agenda import router as agenda_router
from api.knowledge_graph import router as knowledge_graph_router
from api.search import router as search_router
from api.forms import router as forms_router
from api.collections import router as collections_router # Importar el router de collections
from api.universal_search import router as universal_search_router # Importar el router de búsqueda universal
from api.collection_search import router as collection_search_router # Importar el router de búsqueda en colecciones
from api.note_search import router as note_search_router # Importar el router de búsqueda en notas
from api.tables import router as tables_router
from core.config import settings
from core.database import create_tables, Account
from core.llm_manager import initialize_llms
from core.websocket_manager import manager as websocket_manager, startup_event as ws_startup, shutdown_event as ws_shutdown
from utils.security import decode_access_token
from utils.embeddings import initialize_embeddings
from utils.audio_transcriber import load_whisper_model
from utils.ascii_logo import print_startup_logo
from api.users import get_current_admin_account # Importar dependencias de users
from core.dependencies import get_db_session # Importar get_db_session
from utils.tool_scheduler import tool_scheduler # Importar tool_scheduler
from utils.scheduled_tools_manager import scheduled_tools_manager # Importar scheduled_tools_manager
from core.reminders_manager import reschedule_simple_reminders # Importar reschedule_simple_reminders
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import select, func # Importar func
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.propagate = False # Evitar la duplicación de logs del logger principal

# Configurar niveles de logging específicos para módulos ruidosos
logging.getLogger('knowledge_graph.graph_database').setLevel(logging.WARNING)
logging.getLogger('api.knowledge_graph').setLevel(logging.WARNING)
logging.getLogger('utils.security').setLevel(logging.WARNING) # Silenciar logs de seguridad
logging.getLogger('uvicorn.access').setLevel(logging.WARNING) # Silenciar logs de acceso de uvicorn
logging.getLogger('uvicorn.error').setLevel(logging.WARNING) # Silenciar logs de error de uvicorn
logging.getLogger('watchfiles.main').setLevel(logging.WARNING) # Silenciar watchfiles (reload)
logging.getLogger('apscheduler').setLevel(logging.WARNING) # Silenciar scheduler

# Configurar logging detallado para LangChain y componentes del LLM
from utils.llm_logging_config import setup_llm_detailed_logging, create_llm_log_filename, enable_verbose_langchain_logging, disable_noisy_loggers

# Configurar logging detallado del LLM
setup_llm_detailed_logging(
    log_level="INFO",
    log_file=create_llm_log_filename()
)

# Habilitar logging verbose para debugging completo
enable_verbose_langchain_logging()

# Silenciar loggers ruidosos
disable_noisy_loggers()

app = FastAPI(
    title="Kognito AI System - API Central",
    description="Procesa la lógica de la IA, sirve el panel de Telegram y gestiona la autenticación universal.",
    version="1.0.0"
)

# Configurar Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Loguear siempre el error completo en el servidor para debugging
    logger.error(f"Request validation error for {request.method} {request.url}: {json.dumps(jsonable_encoder(exc.errors()), indent=2)}")
    
    # En producción (DEBUG_MODE=False), ocultar los detalles exactos de la falla
    detail = exc.errors() if settings.debug_mode else "Error de validación en la solicitud. Verifique los campos enviados."
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": detail}),
    )

# Agregar middleware de auditoría
app.add_middleware(AuditMiddleware)

# Configuración de CORS
# Permite: localhost, la IP local y los dominios de producción desde settings.
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://192.168.1.7:3000",
    "http://192.168.1.7:3001",
    "https://kognito.gatoslibres.art",
    "https://apibase.gatoslibres.art",
    "https://apibase.cuerpolibre.cl",
    "https://kognitoai.digital",
    "https://kognitoai.cloud",
    "http://localhost:8081",
]

# Incorporar orígenes desde el .env si existen
if hasattr(settings, 'cors_allowed_origins') and settings.cors_allowed_origins:
    if isinstance(settings.cors_allowed_origins, str):
        extra_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
        for origin in extra_origins:
            if origin not in allowed_origins:
                allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)


from api.galleries import router as galleries_router, MEDIA_ROOT, THUMBNAIL_ROOT

app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

app.mount("/thumbnails", StaticFiles(directory=THUMBNAIL_ROOT), name="thumbnails")

# Montar la carpeta de imágenes temporales de Pollinations
os.makedirs("/tmp/pollinations_images", exist_ok=True)
app.mount("/tmp/pollinations_images", StaticFiles(directory="/tmp/pollinations_images"), name="tmp_pollinations_images")


@app.on_event("startup")
async def startup_event():
    """Se ejecuta una vez al arrancar el servidor. Inicializa recursos críticos."""
    print_startup_logo("1.0.0")
    logger.info("El servidor central está arrancando...")
    if not settings.jwt_secret_key:
        logger.error("ERROR FATAL: JWT_SECRET_KEY no está configurada. El servicio de autenticación no funcionará.")
        raise RuntimeError("JWT_SECRET_KEY no está configurada")
    try:
        await create_tables()
        logger.info("Metadatos de tablas de LangChain inicializados.")
        await initialize_llms()
        logger.info("Modelos de Lenguaje (LLMs) inicializados.")
        await initialize_embeddings()
        logger.info("Modelo de embeddings inicializado.")
        load_whisper_model()
        await ws_startup()
        await scheduled_tools_manager.initialize_scheduled_tools() # Inicializar el programador de herramientas
        tool_scheduler.start() # Iniciar el nuevo scheduler de APScheduler
        await reschedule_simple_reminders() # Re-programar recordatorios simples en APScheduler

        
        # 🧹 Limpieza de archivos generados al arrancar
        try:
            from utils.file_cleanup import cleanup_old_generated_files
            cleanup_old_generated_files()
        except Exception as e:
            logger.error(f"Error en la limpieza inicial de archivos: {e}")
            
        logger.info("Servidor listo para aceptar peticiones.")
    except Exception as e:
        logger.error(f"ERROR FATAL DURANTE EL ARRANQUE: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al apagar el servidor."""
    await ws_shutdown()
    tool_scheduler.shutdown() # Detener el scheduler de APScheduler

# Middleware para registrar solicitudes que resultan en error 405
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    if response.status_code == 405:
        logger.warning(f"Method Not Allowed (405) for request: {request.method} {request.url}")
    return response


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Endpoint para manejar conexiones WebSocket con autenticación."""
    token = websocket.query_params.get('token')

    if not token:
        logger.warning(f"Intento de conexión WebSocket sin token para el usuario {user_id}.")
        await websocket.close(code=1008, reason="Token no proporcionado")
        return

    try:
        payload = decode_access_token(token)
        if not payload:
            logger.warning(f"Token inválido o expirado en WebSocket para el usuario {user_id}.")
            await websocket.close(code=1008, reason="Token inválido o expirado")
            return
            
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            logger.warning(f"Conflicto de ID de usuario en WebSocket. Token ID: {token_user_id}, Path ID: {user_id}")
            await websocket.close(code=1008, reason="Conflicto de ID de usuario")
            return
    except HTTPException as e:
        logger.error(f"Error de autenticación de token en WebSocket para el usuario {user_id}: {e.detail}")
        await websocket.close(code=1008, reason=f"Token inválido: {e.detail}")
        return
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token en WebSocket para el usuario {user_id}: {e}", exc_info=True)
        await websocket.close(code=1008, reason="Error de token")
        return

    account_id = user_id
    await websocket.accept() # Aceptar la conexión WebSocket
    await websocket_manager.connect(websocket, account_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Cliente WebSocket desconectado (de forma limpia): {account_id}")
        websocket_manager.disconnect(websocket, account_id)
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket para la cuenta {account_id}: {e}", exc_info=True)
        websocket_manager.disconnect(websocket, account_id)


from utils.audio_transcriber import StreamingTranscriber, get_whisper_model # Importar aquí

@app.websocket("/ws/audio/transcribe/{account_id}")
async def websocket_transcribe(websocket: WebSocket, account_id: str):
    """Endpoint para manejar conexiones WebSocket de transcripción con autenticación."""
    await websocket.accept()
    
    token = websocket.query_params.get('token')
    if not token:
        logger.warning(f"Intento de conexión WebSocket de transcripción sin token para el usuario {account_id}.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token no proporcionado")
        return

    try:
        payload = decode_access_token(token)
        if not payload:
            logger.warning(f"Token inválido o expirado en WebSocket de transcripción para el usuario {account_id}.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido o expirado")
            return
            
        token_account_id = payload.get("sub")
        if token_account_id != account_id:
            logger.warning(f"Conflicto de ID de usuario en WebSocket de transcripción. Token ID: {token_account_id}, Path ID: {account_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Conflicto de ID de usuario")
            return
    except HTTPException as e:
        logger.error(f"Error de autenticación de token en WebSocket de transcripción para el usuario {account_id}: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Token inválido: {e.detail}")
        return
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token en WebSocket de transcripción para el usuario {account_id}: {e}", exc_info=True)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Error de token")
        return

    logger.info(f"WebSocket de transcripción conectado y autenticado para la cuenta: {account_id}")

    whisper_model = await get_whisper_model()
    if not whisper_model:
        logger.error("Modelo de Whisper no disponible para transcripción en streaming.")
        await websocket.send_json({"type": "error", "message": "Modelo de transcripción no disponible."})
        return

    transcriber = StreamingTranscriber(whisper_model)
    try:
        await transcriber.start_transcription_session(websocket)
    except Exception as e:
        logger.error(f"Error en la sesión de transcripción para la cuenta {account_id}: {e}", exc_info=True)
    finally:
        logger.info(f"Conexión WebSocket de transcripción cerrada para {account_id}")


@app.get("/", include_in_schema=False)
async def root_status():
    """Retorna el estado del servidor central."""
    return {"status": "running", "service": "Kognito AI Central API"}


@app.api_route("/.well-known/caldav", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PROPFIND", "PROPPATCH", "REPORT"], include_in_schema=False)
async def well_known_caldav(request: Request):
    """Redirección estándar para descubrimiento automático de CalDAV."""
    return RedirectResponse(url="/api/caldav/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.api_route("/.well-known/carddav", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PROPFIND", "PROPPATCH", "REPORT"], include_in_schema=False)
async def well_known_carddav(request: Request):
    """Redirección estándar para descubrimiento automático de CardDAV (opcional, redirigido a CalDAV por ahora)."""
    return RedirectResponse(url="/api/caldav/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# Incluir routers de los módulos
# Incluir routers de los módulos
app.include_router(chat_router, prefix="/api", tags=["chat"]) # Mover arriba para dar prioridad a las rutas de chat
app.include_router(chat_share_router, prefix="/api/chat/share", tags=["chat-share"])

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(note_search_router, prefix="/api", tags=["note-search"]) # Mover arriba para prioridad sobre {note_id}
app.include_router(notes_router, prefix="/api", tags=["notes"])
app.include_router(agenda_router, prefix="/api", tags=["agenda"])
from api.workspaces import router as workspaces_router
from api.contact_profiles import router as contact_profiles_router

app.include_router(workspaces_router, prefix="/api", tags=["workspaces"])
app.include_router(contact_profiles_router, prefix="/api", tags=["contact-profiles"])
from api.analysis import router as analysis_router
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
from api.analysis_share import router as analysis_share_router
app.include_router(analysis_share_router, prefix="/api/analysis/share", tags=["analysis-share"])
from api.github import router as github_router
from api.slack import router as slack_router # NUEVO: Importar router de Slack
from api.notion import router as notion_router # NUEVO: Importar router de Notion
from api.local_files import router as local_files_router # NUEVO: Importar router de archivos locales
from api.telegram import router as telegram_router
from api.logs import router as logs_router
from api.analytics import router as analytics_router
from api.scheduled_tools import router as scheduled_tools_router
from api.tasks import router as tasks_router # Importar el router de tasks
from api.caldav import router as caldav_router # Importar el router de caldav
from api.llm import router as llm_router # Importar el router de llm
from api.admin_llm import router as admin_llm_router
from api.admin_pipeline import router as admin_pipeline_router

from api.galleries import router as galleries_router, MEDIA_ROOT
from api.graph import router as graph_router
from api.memory import router as memory_router # NUEVO: Importar el router de memory
from api.routers.mcp import router as mcp_router # NUEVO: Importar router de MCP

app.include_router(github_router, prefix="/api/github", tags=["github"])
app.include_router(slack_router, prefix="/api/slack", tags=["slack"]) # NUEVO: Incluir router de Slack
app.include_router(notion_router, prefix="/api/notion", tags=["notion"]) # NUEVO: Incluir router de Notion
app.include_router(local_files_router, prefix="/api/files", tags=["local-files"]) # NUEVO: Incluir router de archivos locales
app.include_router(telegram_router, prefix="", tags=["telegram"])
app.include_router(logs_router, prefix="/api", tags=["logs"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(scheduled_tools_router, prefix="/api", tags=["scheduled-tools"])
app.include_router(tasks_router, prefix="/api", tags=["tasks"]) # Incluir el router de tasks
app.include_router(caldav_router, prefix="/api", tags=["caldav"]) # Incluir el router de caldav
app.include_router(llm_router, prefix="/api", tags=["llm"]) # Incluir el router de llm
app.include_router(admin_llm_router, prefix="/api", tags=["admin-llm"])
app.include_router(admin_pipeline_router, prefix="/api", tags=["admin-pipeline"])
app.include_router(knowledge_graph_router, prefix="/api/knowledge-graph", tags=["knowledge-graph"])
app.include_router(graph_router, prefix="/api", tags=["graph"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(galleries_router, prefix="/api/galleries", tags=["galleries"])
app.include_router(forms_router, prefix="/api", tags=["forms"])
app.include_router(collections_router, prefix="/api", tags=["collections"])
app.include_router(universal_search_router, prefix="/api", tags=["universal-search"])
app.include_router(collection_search_router, prefix="/api", tags=["collection-search"])
app.include_router(memory_router, prefix="/api", tags=["memory"]) # NUEVO: Incluir el router de memory
app.include_router(mcp_router) # NUEVO: Incluir el router de MCP
app.include_router(tables_router, prefix="/api/tables", tags=["tables"])

from api.email import router as email_router # Importar el router de email

app.include_router(email_router, prefix="/api", tags=["email"]) # Incluir el router de email

from api.terminal import router as terminal_router  # PTY terminal interactiva
from api.skills import router as skills_router
from api.deep_research import router as deep_research_router
from api.gap_development import router as gap_development_router
from api.mfa import router as mfa_router # Importar el router de MFA
from api.onlyoffice import router as onlyoffice_router # IMPORTAR ONLYOFFICE
from api.openai import router as openai_router # IMPORTAR OPENAI COMPATIVEL (legacy)
from api.public_api import router as public_api_router # IMPORTAR API PÚBLICA NUEVA
from skills.media_and_generation_skill.scripts.html_generator_tool import HTMLGeneratorTool # Importar la herramienta HTMLGeneratorTool desde skills
from utils.security import get_current_account_id # Importar get_current_account_id

app.include_router(terminal_router, tags=["terminal"])  # PTY terminal interactiva (WS)
app.include_router(skills_router, prefix="/api/skills", tags=["skills"])
app.include_router(skills_router, prefix="/api/tools", tags=["skills"]) # Alias para retrocompatibilidad
app.include_router(onlyoffice_router, prefix="/api/onlyoffice", tags=["onlyoffice"]) # INCLUIR ONLYOFFICE
app.include_router(deep_research_router, prefix="/api", tags=["deep-research"])
app.include_router(gap_development_router, prefix="/api", tags=["gap-development"])
app.include_router(mfa_router, prefix="/api", tags=["mfa"])
# Incluir API pública nueva (reemplaza openai_router)
app.include_router(public_api_router, prefix="", tags=["openai-compatible"])

class GenerateHTMLRequest(BaseModel):
    content: str = Field(..., description="El contenido en formato Markdown o texto plano.")
    title: Optional[str] = Field("Documento Generado", description="El título del documento HTML.")
    include_css: bool = Field(True, description="Si se debe incluir un CSS básico para mejorar la presentación.")

@app.post("/api/generate-html", summary="Generar y descargar un archivo HTML", response_class=FileResponse)
async def generate_html_file(
    request_data: GenerateHTMLRequest,
    account_id: str = Depends(get_current_account_id) # Usar get_current_account_id para autenticación
):
    """
    Genera un archivo HTML a partir del contenido proporcionado (Markdown o texto plano)
    y lo devuelve para su descarga.
    """
    try:
        # Instanciar la herramienta HTMLGeneratorTool
        html_generator = HTMLGeneratorTool(account_id=account_id) # Pasar account_id si la herramienta lo necesita
        
        # Ejecutar la herramienta para obtener el contenido HTML
        html_content = await html_generator._arun(
            content=request_data.content,
            title=request_data.title,
            include_css=request_data.include_css
        )

        # Usar un nombre de archivo más robusto y seguro
        safe_title = "".join(c for c in request_data.title if c.isalnum() or c in (' ', '.', '_')).rstrip()
        file_name = f"{safe_title.replace(' ', '_').lower()}_{uuid.uuid4().hex[:6]}.html"
        
        # Definir el directorio de salida dentro de 'media' usando MEDIA_ROOT absoluto
        output_dir = os.path.join(MEDIA_ROOT, "generated_html")
        os.makedirs(output_dir, exist_ok=True) # Asegurarse de que el directorio exista
        
        temp_file_path = os.path.join(output_dir, file_name) # Guardar en el directorio 'media/generated_html'

        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Devolver el archivo para descarga
        return FileResponse(
            path=temp_file_path,
            media_type="text/html",
            filename=file_name,
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except Exception as e:
        logger.error(f"Error al generar archivo HTML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar archivo HTML: {e}")

class AdminMetricsResponse(BaseModel):
    total_users: int
    total_scheduled_tools: int
    active_scheduled_tools: int

@app.get("/api/admin/metrics", response_model=AdminMetricsResponse, summary="Obtener métricas del sistema (solo admin)")
async def get_admin_metrics(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene métricas clave del sistema para el panel de administración.
    Requiere privilegios de administrador.
    """
    logger.info(f"Admin {admin_account.id} solicitando métricas del sistema.")

    # Total de usuarios
    total_users_count = await db.scalar(select(func.count(Account.id)))

    # Total y activas herramientas programadas
    total_scheduled = len(tool_scheduler.scheduled_jobs)
    active_jobs = sum(1 for job in tool_scheduler.scheduled_jobs.values()
                         if getattr(job, 'enabled', True))

    return AdminMetricsResponse(
        total_users=total_users_count,
        total_scheduled_tools=total_scheduled,
        active_scheduled_tools=active_jobs
    )

@app.post("/api/admin/cleanup-files", summary="Ejecutar limpieza manual de archivos (solo admin)")
async def manual_cleanup_files(
    admin_account: Account = Depends(get_current_admin_account)
):
    """
    Ejecuta manualmente la limpieza de archivos generados con más de 24 horas.
    Requiere privilegios de administrador.
    """
    logger.info(f"Admin {admin_account.id} solicitando limpieza manual de archivos.")
    try:
        from utils.file_cleanup import cleanup_old_generated_files
        files_deleted = cleanup_old_generated_files()
        return {"message": "Limpieza completada", "files_deleted": files_deleted}
    except Exception as e:
        logger.error(f"Error en limpieza manual: {e}")
        raise HTTPException(status_code=500, detail=f"Error en limpieza manual: {e}")

@app.get("/test-connection")
async def test_connection():
    return {"message": "Connection successful!"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor API en modo de desarrollo local (host 0.0.0.0, port 8000)...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)