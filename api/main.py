# api/main.py

import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.auth import router as auth_router
from api.users import router as users_router
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.notes import router as notes_router
from api.agenda import router as agenda_router
from api.teams import router as teams_router
from api.knowledge_graph import router as knowledge_graph_router
from api.search import router as search_router
from core.config import settings
from core.database import create_tables
from core.llm_manager import initialize_llms
from core.websocket_manager import connect_websocket, disconnect_websocket
from utils.security import decode_access_token
from utils.embeddings import initialize_embeddings
from utils.ascii_logo import print_startup_logo

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.propagate = False # Evitar la duplicación de logs del logger principal

# Configurar logging detallado para LangChain y componentes del LLM
from utils.llm_logging_config import setup_llm_detailed_logging, create_llm_log_filename, enable_verbose_langchain_logging, disable_noisy_loggers

# Configurar logging detallado del LLM
setup_llm_detailed_logging(
    log_level="DEBUG",
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

# Configuración de CORS
origins = [
    "http://localhost:8880",
    "http://localhost:8000",
    "https://kognito.gatoslibres.art",
    "http://192.168.100.106:8880",
    "http://192.168.100.106:8000",
    "https://api.telegram.org",
    "https://web.telegram.org",
    "https://t.me",
    "https://kognito.gatoslibres.art",
    "https://apibase.gatoslibres.art",
    "http://localhost:8880",
    "http://192.168.100.106:8880",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar la carpeta 'telegram_panel' para servir archivos estáticos
app.mount("/telegram_panel", StaticFiles(directory="telegram_panel"), name="telegram_panel")


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
        logger.info("Servidor listo para aceptar peticiones.")
    except Exception as e:
        logger.error(f"ERROR FATAL DURANTE EL ARRANQUE: {e}", exc_info=True)
        raise

# Middleware para registrar solicitudes que resultan en error 405
@app.middleware("http")
async def log_405_errors(request, call_next):
    response = await call_next(request)
    if response.status_code == 405:
        logger.warning(f"Method Not Allowed (405) for request: {request.method} {request.url}")
    return response


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Endpoint para manejar conexiones WebSocket."""
    account_id = user_id
    if not account_id:
        await websocket.close(code=1008)
        logger.warning("Intento de conexión WebSocket sin user_id.")
        return

    await connect_websocket(account_id, websocket)
    try:
        while True:
            # Mantenemos la conexión abierta. El cliente no necesita enviar datos.
            # El servidor enviará datos cuando sea necesario.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Cliente WebSocket desconectado (de forma limpia): {account_id}")
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket para la cuenta {account_id}: {e}", exc_info=True)
    finally:
        await disconnect_websocket(account_id)

@app.get("/", include_in_schema=False)
async def serve_telegram_panel():
    """Sirve el archivo HTML del panel de control de Telegram WebApp."""
    panel_path = os.path.join("telegram_panel", "index.html")
    if not os.path.exists(panel_path):
        raise HTTPException(status_code=404, detail="Panel de control no encontrado.")
    return FileResponse(panel_path)

# Incluir routers de los módulos
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(documents_router, prefix="/api", tags=["documents"])
app.include_router(notes_router, prefix="/api", tags=["notes"])
app.include_router(agenda_router, prefix="/api", tags=["agenda"])
from api.workspaces import router as workspaces_router

app.include_router(teams_router, prefix="/api", tags=["teams"])
app.include_router(workspaces_router, prefix="/api", tags=["workspaces"])
from api.analysis import router as analysis_router
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
from api.github import router as github_router
from api.telegram import router as telegram_router
from api.logs import router as logs_router
from api.scheduled_tools import router as scheduled_tools_router

app.include_router(github_router, prefix="/api/github", tags=["github"])
app.include_router(telegram_router, prefix="", tags=["telegram"])
app.include_router(logs_router, prefix="/api", tags=["logs"])
app.include_router(scheduled_tools_router, prefix="/api", tags=["scheduled-tools"])
app.include_router(knowledge_graph_router, prefix="/api", tags=["knowledge-graph"])
app.include_router(search_router, prefix="/api", tags=["search"])
from api.deep_research import router as deep_research_router
app.include_router(deep_research_router, prefix="/api", tags=["deep-research"])

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor API en modo de desarrollo local (host 0.0.0.0, port 8000)...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
