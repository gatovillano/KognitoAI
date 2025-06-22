# run_api.py

import logging
import asyncio
import os
import json
import hmac
import hashlib
import time
import random
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import unquote, parse_qs
import uuid

from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, Query, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
import httpx

from core.config import settings
from core.database import (
    create_tables, SessionLocal, Account, PlatformIdentity, Perfil,
    get_or_create_account_from_platform_id, get_account_by_telegram_id,
    find_telegram_identity, ChatThread
)
from core.agent import initialize_llms, create_and_run_agent, create_thread_for_account
from utils.db_session import DBSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, delete_document_chunks, get_full_document_content, update_document_metadata
from core.notes_manager import get_notes, add_note, update_note, delete_note
from core.agenda_manager import get_events_as_dicts, schedule_event, cancel_event, get_agenda_for_day
from telegram_client.bot_manager import bot_manager
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

from utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_account_id,
)
from fastapi.security import APIKeyHeader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kognito AI System - API Central",
    description="Procesa la lógica de la IA, sirve el panel de Telegram y gestiona la autenticación universal.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Se ejecuta una vez al arrancar el servidor. Inicializa recursos críticos."""
    logger.info("El servidor central está arrancando...")
    if not settings.jwt_secret_key:
        logger.error("ERROR FATAL: JWT_SECRET_KEY no está configurada. El servicio de autenticación no funcionará.")
    try:
        await create_tables()
        logger.info("Tablas de la base de datos verificadas/creadas.")
        await initialize_llms()
        logger.info("Modelos de Lenguaje (LLMs) inicializados.")
        logger.info("Servidor listo para aceptar peticiones.")
    except Exception as e:
        logger.error(f"ERROR FATAL DURANTE EL ARRANQUE: {e}", exc_info=True)
        raise

origins = [
    "http://localhost:8880",
    "http://localhost:8000",
    "https://kognito.gatoslibres.art",
    "http://192.168.100.106:8880",
    "http://192.168.100.106:8000",
    "https://api.telegram.org",
    "https://web.telegram.org",
    "https://t.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db() -> AsyncSession:
    """Dependencia de FastAPI que crea y limpia una sesión de base de datos por petición."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)

async def get_internal_api_key(
    x_internal_api_key: Optional[str] = Depends(api_key_header)
) -> str:
    """
    Dependencia para validar una clave API interna para comunicación entre servicios.
    Requiere que la clave 'X-Internal-API-Key' coincida con 'settings.internal_api_key_for_bot'.
    """
    if x_internal_api_key and x_internal_api_key == settings.internal_api_key_for_bot:
        return x_internal_api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Clave API Interna inválida o ausente."
    )

def _validate_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """Valida los datos de inicialización de una Telegram WebApp."""
    if not settings.telegram_bot_token: return None
    try:
        decoded_data = unquote(init_data)
        parsed_data = parse_qs(decoded_data)
        if "hash" not in parsed_data: return None

        data_check_string_parts = []
        for key, value in sorted(parsed_data.items()):
            if key != "hash":
                data_check_string_parts.append(f"{key}={value[0]}")
        data_check_string = "\n".join(data_check_string_parts)

        secret_key = hmac.new("WebAppData".encode(), settings.telegram_bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hmac.compare_digest(calculated_hash, parsed_data["hash"][0]):
            user_str = parsed_data.get("user", [None])[0]
            if user_str:
                return json.loads(user_str)
        return None
    except Exception as e:
        logger.error(f"Error validando initData: {e}")
        return None

async def get_validated_user_id(initData: str = Form(...)) -> int:
    """Dependencia para obtener el ID de usuario de Telegram validado desde `initData`."""
    user_data = _validate_telegram_init_data(initData)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Datos de inicialización inválidos o ausentes.")
    return int(user_data["id"])

class RegisterRequest(BaseModel):
    """Define la estructura de datos para una solicitud de registro."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = None

class LoginRequest(BaseModel):
    """Define la estructura de datos para una solicitud de inicio de sesión."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Define la estructura de datos para la respuesta del token de autenticación."""
    access_token: str
    token_type: str = "bearer"

class TelegramLoginRequest(BaseModel):
    """Define la estructura de datos para una solicitud de login de Telegram."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

# --- Endpoints de Email/Pass y Social Login ---

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Registrar con email/pass")
async def register_user(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registra una nueva cuenta de usuario con email y contraseña."""
    existing_account_result = await db.execute(select(Account).where(Account.email == request.email))
    if existing_account_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con este correo electrónico.")

    new_account = Account(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        name=request.name or request.email.split('@')[0]
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    access_token = create_access_token(data={"sub": str(new_account.id)})
    return TokenResponse(access_token=access_token)

@app.post("/api/auth/login", response_model=TokenResponse, summary="Iniciar sesión con email/pass")
async def login_for_access_token(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Inicia sesión con email y contraseña y devuelve un token de acceso JWT."""
    account_result = await db.execute(select(Account).where(Account.email == request.email))
    account = account_result.scalars().first()
    if not account or not account.hashed_password or not verify_password(request.password, account.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos.")

    access_token = create_access_token(data={"sub": str(account.id)})
    return TokenResponse(access_token=access_token)

def verify_telegram_hash(data: TelegramLoginRequest, bot_token: str) -> bool:
    """Verifica el hash de los datos de login de Telegram (método oficial)."""
    data_dict = data.dict(exclude={'hash'})
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()) if v is not None)
    # CORRECT: secret key is SHA256 of the bot token (not HMAC)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_hash, data.hash)

@app.post("/api/auth/telegram/callback", response_model=TokenResponse, summary="Callback de Login Social de Telegram")
async def handle_telegram_login(login_data: TelegramLoginRequest, db: AsyncSession = Depends(get_db)):
    """Maneja el callback de autenticación social de Telegram, crea o vincula la cuenta y devuelve un token."""
    if not settings.telegram_bot_token: raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Autenticación de Telegram no configurada.")

    # DEBUG: Log incoming data and calculated hash for troubleshooting
    import logging
    logger = logging.getLogger("telegram_auth")
    logger.warning(f"Incoming Telegram login data: {login_data}")
    data_dict = login_data.dict(exclude={'hash'})
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()) if v is not None)
    secret_key = hmac.new("WebAppData".encode(), settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    logger.warning(f"Calculated hash: {calculated_hash}, Provided hash: {login_data.hash}")

    if not verify_telegram_hash(login_data, settings.telegram_bot_token): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hash de Telegram inválido.")
    if time.time() - login_data.auth_date > 300: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Datos de autenticación expirados.")

    identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(login_data.id)))
    identity = identity_result.scalars().first()

    if identity:
        account = await db.get(Account, identity.account_id)
        if not account:
             raise HTTPException(status_code=500, detail="Error de consistencia de datos.")
    else:
        account = Account(name=login_data.first_name, username=login_data.username)
        db.add(account)
        await db.flush()
        new_identity = PlatformIdentity(account_id=account.id, platform='telegram', platform_user_id=str(login_data.id))
        db.add(new_identity)
        await db.commit()
        await db.refresh(account)

    access_token = create_access_token(data={"sub": str(account.id)})
    return TokenResponse(access_token=access_token)

# --- Endpoints de Login con Código (Legado y Específico de Telegram) ---
verification_codes: Dict[str, Dict[str, Any]] = {} # Almacenamiento temporal en memoria

class AuthRequestCode(BaseModel):
    """Define la estructura para solicitar un código de verificación."""
    identifier: str

class AuthVerifyCode(BaseModel):
    """Define la estructura para verificar un código y obtener un token."""
    identifier: str
    code: str

@app.post("/api/auth/request-code", summary="Solicitar código de verificación (legado)")
async def request_verification_code(request_data: AuthRequestCode):
    """Solicita un código de verificación para Telegram y lo envía al chat del usuario."""
    async with DBSession(SessionLocal) as db:
        identity = await find_telegram_identity(db, request_data.identifier)
        if not identity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró usuario con identificador '{request_data.identifier}'.")
        telegram_id = int(identity.platform_user_id)

    code = str(random.randint(100000, 999999))
    verification_codes[request_data.identifier.lower()] = {"code": code, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}

    try:
        # Aquí se llama al servicio del bot de Telegram para enviar el mensaje.
        # Hardcodeado para Docker Compose, se podría externalizar en settings.
        async with httpx.AsyncClient() as client:
            await client.post("http://telegram_client:9090/internal/send-message", json={"chat_id": telegram_id, "text": f"Tu código de Kognito AI es: <b>{code}</b>"})
        return {"message": "Código de verificación enviado a tu chat de Telegram."}
    except Exception as e:
        logger.error(f"Error al enviar código a {telegram_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo contactar al servicio de mensajería.")

@app.post("/api/auth/verify-code", response_model=TokenResponse, summary="Verificar código (legado)")
async def verify_code_and_get_token(request_data: AuthVerifyCode):
    """Verifica un código de verificación y devuelve un token de acceso si es válido."""
    identifier = request_data.identifier.lower()
    stored_code = verification_codes.get(identifier)
    if not stored_code or stored_code["code"] != request_data.code or datetime.now(timezone.utc) > stored_code["exp"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorrecto o expirado.")

    async with DBSession(SessionLocal) as db:
        identity = await find_telegram_identity(db, identifier)
        if not identity:
            raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta asociada.")

    if identifier in verification_codes:
        del verification_codes[identifier]

    access_token = create_access_token(data={"sub": str(identity.account_id)})
    return TokenResponse(access_token=access_token)

# ==============================================================================
# SECCIÓN 4: API DEL AGENTE Y ENDPOINTS PROTEGIDOS
# ==============================================================================

# --- Modelo de Respuesta para el Perfil de Usuario ---
class UserProfileResponse(BaseModel):
    """Define la estructura de datos para la respuesta del perfil de usuario."""
    id: str
    name: Optional[str]
    email: Optional[EmailStr]
    username: Optional[str]
    telegram_id: Optional[int] = None # Añadimos para el frontend

    class Config:
        orm_mode = True # Habilita compatibilidad con ORM de SQLAlchemy

@app.get("/api/users/me", response_model=UserProfileResponse, summary="Obtener perfil del usuario actual (protegido)")
async def read_users_me(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Devuelve los datos públicos del usuario actualmente autenticado a través del token JWT.
    """
    account = await db.get(Account, uuid.UUID(current_account_id)) # Asegúrate de que el ID sea un UUID
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Intentar obtener el telegram_id si existe
    telegram_identity = await db.execute(
        select(PlatformIdentity).where(
            PlatformIdentity.account_id == uuid.UUID(current_account_id),
            PlatformIdentity.platform == 'telegram'
        )
    )
    telegram_id = None
    identity_obj = telegram_identity.scalars().first()
    if identity_obj and identity_obj.platform_user_id:
        try:
            telegram_id = int(identity_obj.platform_user_id)
        except ValueError:
            logger.warning(f"platform_user_id '{identity_obj.platform_user_id}' no es un entero para telegram_id.")


    return UserProfileResponse(
        id=str(account.id),
        name=account.name,
        email=account.email,
        username=account.username,
        telegram_id=telegram_id
    )

# --- Modelos para el Chat ---
class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None

class ChatResponse(BaseModel):
    """Define la estructura de datos para la respuesta del agente de chat."""
    response_text: str

@app.post("/api/chat", response_model=ChatResponse, summary="Procesar Mensaje de Chat")
async def handle_chat(request: ChatRequest, current_account_id: str = Depends(get_current_account_id)) -> ChatResponse:
    """
    Endpoint principal para procesar mensajes de chat con el agente de IA.
    Requiere autenticación JWT.
    """
    if str(uuid.UUID(request.account_id)) != current_account_id: # Validar que el account_id coincida con el del token
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El account_id proporcionado no coincide con el token de autenticación.")

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id}")
    try:
        final_response_text = await create_and_run_agent(
            account_id=request.account_id,
            thread_id=request.thread_id,
            telegram_id=request.telegram_id, # telegram_id ahora es Optional[int]
            user_message=request.user_message,
            image_base64=request.image_base64
        )
        return ChatResponse(response_text=final_response_text)
    except Exception as e:
        logger.error(f"Error al procesar petición de la cuenta {request.account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error interno al procesar tu solicitud.")

@app.post("/api/chat/stream", summary="Chat streaming con Gemini")
async def chat_stream(request: Request, current_account_id: str = Depends(get_current_account_id)):
    body = await request.json()
    user_message = body.get("user_message")
    thread_id = body.get("thread_id")
    # Aquí puedes obtener el historial y contexto igual que en create_and_run_agent
    # ...preparar prompt/contexto...
    from core.agent import _main_agent_llm_instance
    async def gemini_stream_async():
        llm = _main_agent_llm_instance
        if not llm:
            yield "[ERROR: LLM no inicializado]"
            return
        # El método correcto para streaming es astream (async generator)
        async for chunk in llm.astream(user_message):
            # chunk puede ser un objeto con .content o un string
            text = getattr(chunk, 'content', None) or str(chunk)
            yield text
    return StreamingResponse(gemini_stream_async(), media_type="text/plain")

# ==============================================================================
# SECCIÓN 5: API PARA EL PANEL DE CONTROL DE TELEGRAM (Protegida por initData)
# ==============================================================================

@app.get("/", include_in_schema=False)
async def serve_telegram_panel():
    """Sirve el archivo HTML del panel de control de Telegram WebApp."""
    panel_path = os.path.join("telegram_panel", "index.html")
    if not os.path.exists(panel_path):
        raise HTTPException(status_code=404, detail="Panel de control no encontrado.")
    return FileResponse(panel_path)

# Monta la carpeta 'telegram_panel' para servir archivos estáticos.
app.mount("/telegram_panel", StaticFiles(directory="telegram_panel"), name="telegram_panel")

@app.post("/api/get-system-prompt")
async def get_system_prompt(user_id: int = Depends(get_validated_user_id), db: AsyncSession = Depends(get_db)):
    """
    Obtiene el prompt de sistema personalizado para un usuario de Telegram.
    Protegido por `initData` de Telegram.
    """
    account = await get_account_by_telegram_id(db, user_id)
    if not account:
        return {"prompt": settings.default_system_prompt, "is_custom": False}

    # Asumimos que profile está cargado o accedemos directamente al atributo.
    # El atributo custom_system_prompt ahora está directamente en el modelo Account
    prompt = account.custom_system_prompt if account.custom_system_prompt else settings.default_system_prompt
    is_custom = account.custom_system_prompt is not None

    return {"prompt": prompt, "is_custom": is_custom}

@app.post("/api/save-system-prompt")
async def save_system_prompt(user_id: int = Depends(get_validated_user_id), system_prompt: str = Form(""), db: AsyncSession = Depends(get_db)):
    """
    Guarda el prompt de sistema personalizado para un usuario de Telegram.
    Protegido por `initData` de Telegram.
    """
    account = await get_account_by_telegram_id(db, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta para guardar el prompt.")

    account.custom_system_prompt = system_prompt.strip() if system_prompt.strip() else None
    await db.commit()
    return {"message": "Prompt del sistema actualizado."}

@app.post("/api/upload-document")
async def upload_document_endpoint(
    current_account_id: str = Depends(get_current_account_id), # Protegido por JWT para el frontend web
    files: List[UploadFile] = File(...),
    topic: str = Form(...)
):
    """
    Sube y procesa documentos para la base de conocimiento de un usuario.
    Protegido por JWT (para frontend web) o `initData` de Telegram (para panel Telegram WebApp, si se llama así).
    Nota: Para `initData`, el `user_id` se extrae de `get_validated_user_id`
          y luego se busca el `account_id` asociado. Aquí usamos JWT directamente.
          Si quieres que este endpoint sea llamado por initData, necesitas otro endpoint
          o un middleware que maneje ambas autenticaciones.
          Por ahora, este está con JWT para el frontend general.
    """
    account_id_uuid = uuid.UUID(current_account_id) # Convertir a UUID
    processed_files = 0
    for file in files:
        try:
            content_bytes = await file.read()
            extracted_text, metadata = extract_text_and_metadata_from_document(file.filename, content_bytes)
            if not extracted_text:
                logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                continue
            metadata.update({"file_name": file.filename, "topic": topic})
            await process_document_for_rag(account_id=str(account_id_uuid), file_name=file.filename, extracted_text=extracted_text, metadata=metadata)
            processed_files += 1
        except Exception as e:
            logger.error(f"Fallo al procesar el archivo {file.filename} para la cuenta {account_id_uuid}: {e}", exc_info=True)

    if processed_files == 0 and files:
        raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
    return {"message": f"{processed_files}/{len(files)} archivo(s) procesado(s) y añadido(s) a tu base de conocimiento."}

@app.post("/api/list-documents") # Cambiado a POST porque el frontend web lo usa con FormData
async def list_documents_endpoint(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """Lista los documentos subidos por el usuario. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    return await list_user_documents(str(account_id_uuid))

@app.post("/api/delete-document") # Cambiado a POST porque el frontend web lo usa con FormData
async def delete_document_endpoint(current_account_id: str = Depends(get_current_account_id), file_name: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Elimina documentos de la base de conocimiento del usuario. Protegido por JWT."""
    account_id_uuid = uuid.UUID(current_account_id)
    success = await delete_document_chunks(str(account_id_uuid), file_name)
    if not success: raise HTTPException(status_code=404, detail="Documento no encontrado o ya eliminado.")
    return {"message": f"El documento '{file_name}' ha sido eliminado."}

@app.post("/api/list-notes") # Cambiado a POST
async def list_notes_endpoint(current_account_id: str = Depends(get_current_account_id), search_term: Optional[str] = Form(None), db: AsyncSession = Depends(get_db)):
    """Lista las notas de un usuario. Protegido por JWT."""
    return await get_notes(current_account_id, search_query=search_term)

@app.post("/api/add-note") # Cambiado a POST
async def add_note_endpoint(current_account_id: str = Depends(get_current_account_id), title: Optional[str] = Form(None), content: str = Form(...), category: Optional[str] = Form(None), db: AsyncSession = Depends(get_db)):
    """Añade una nueva nota para el usuario. Protegido por JWT."""
    result_message = await add_note(current_account_id, content, title, category)
    return {"message": result_message}

@app.post("/api/update-note") # Cambiado a POST
async def update_note_endpoint(current_account_id: str = Depends(get_current_account_id), note_id: int = Form(...), content: str = Form(...), title: Optional[str] = Form(None), category: Optional[str] = Form(None), db: AsyncSession = Depends(get_db)):
    """Actualiza una nota existente del usuario. Protegido por JWT."""
    result_message = await update_note(current_account_id, note_id, content, title, category)
    return {"message": result_message}

@app.post("/api/delete-note") # Cambiado a POST
async def delete_note_endpoint(current_account_id: str = Depends(get_current_account_id), note_id: int = Form(...), db: AsyncSession = Depends(get_db)):
    """Elimina una nota del usuario. Protegido por JWT."""
    result_message = await delete_note(current_account_id, note_id)
    return {"message": result_message}

@app.post("/api/list-events") # Cambiado a POST
async def list_events_endpoint(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """Lista los eventos de la agenda del usuario. Protegido por JWT."""
    return await get_events_as_dicts(current_account_id)

@app.post("/api/add-event") # Cambiado a POST
async def add_event_endpoint(current_account_id: str = Depends(get_current_account_id), description: str = Form(...), event_datetime: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event = await schedule_event(
        account_id=current_account_id,
        description=description,
        natural_language_datetime=event_datetime
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    # Aquí podríamos programar la notificación de Telegram si tuviéramos el telegram_id
    return {"message": message}

@app.post("/api/cancel-event") # Cambiado a POST
async def cancel_event_endpoint(current_account_id: str = Depends(get_current_account_id), event_id: int = Form(...), db: AsyncSession = Depends(get_db)):
    """Cancela un evento de la agenda del usuario. Protegido por JWT."""
    success, message = await cancel_event(current_account_id, event_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    # Aquí también se cancelaría el job de notificación de Telegram si existiera.
    return {"message": message}

@app.post("/api/update-document-metadata")
async def update_document_metadata_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    file_name: str = Form(...),
    new_title: Optional[str] = Form(None),
    new_topic: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el título y/o la categoría de un documento del usuario."""
    account_id_uuid = uuid.UUID(current_account_id)
    success = await update_document_metadata(str(account_id_uuid), file_name, new_title, new_topic)
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado o no actualizado.")
    return {"message": "Metadatos actualizados correctamente."}

# ==============================================================================
# SECCIÓN 6: ENDPOINTS PARA INTERFAZ WEB
# ==============================================================================

# --- Modelos Pydantic para Hilos de Chat ---
class ThreadResponse(BaseModel):
    """Define la estructura de datos para la respuesta de un hilo de chat."""
    id: str
    title: str
    created_at: datetime

class MessageResponse(BaseModel):
    """Define la estructura de datos para un mensaje individual en el chat."""
    text: str  # antes 'content'
    sender: str  # antes 'type', valores: 'human' o 'ai'
    created_at: datetime

@app.get("/api/threads", response_model=List[ThreadResponse], summary="Listar hilos de chat del usuario")
async def list_chat_threads(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los hilos de chat de un usuario autenticado, ordenados por fecha de creación descendente.
    """
    logger.info(f"Listando hilos de chat para la cuenta: {current_account_id}")
    stmt = select(ChatThread).where(ChatThread.account_id == uuid.UUID(current_account_id)).order_by(ChatThread.created_at.desc())
    result = await db.execute(stmt)
    threads = result.scalars().all()
    return [ThreadResponse(id=str(t.id), title=t.title, created_at=t.created_at) for t in threads]

@app.post("/api/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo hilo de chat")
async def create_new_thread(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Crea un nuevo hilo de chat para el usuario autenticado.
    """
    logger.info(f"Creando nuevo hilo de chat para la cuenta: {current_account_id}")
    new_thread = ChatThread(account_id=uuid.UUID(current_account_id))
    db.add(new_thread)
    await db.commit()
    await db.refresh(new_thread)
    return ThreadResponse(id=str(new_thread.id), title=new_thread.title, created_at=new_thread.created_at)

@app.get("/api/threads/{thread_id}/messages", response_model=List[MessageResponse], summary="Obtener mensajes de un hilo de chat")
async def get_thread_messages(
    thread_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial de mensajes para un hilo de chat específico.
    """
    logger.info(f"Obteniendo mensajes para el hilo: {thread_id} de la cuenta: {current_account_id}")

    # Verificar que el hilo pertenzca a la cuenta actual
    thread_exists = await db.scalar(
        select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id))
    )
    if not thread_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hilo de chat no encontrado o no pertenece al usuario.")

    # Asegurarse de que database_url no es None antes de usar .replace()
    if settings.database_url is None:
        raise HTTPException(status_code=500, detail="Configuración de base de datos faltante.")

    db_sync_url = settings.database_url.replace("+psycopg", "")
    history = PostgresChatMessageHistory(
        connection_string=db_sync_url,
        session_id=thread_id, # El session_id para LangChain es el thread_id
        table_name="langchain_chat_history",
    )

    try:
        # ¡CORRECCIÓN CLAVE! Usar aget_messages() y esperar directamente
        messages = await history.aget_messages()
        # Filtrar mensajes de resumen si los hay y mapear a MessageResponse
        response_messages = []
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get("role") == "summary":
                continue # Ignorar mensajes de resumen internos

            msg_content = msg.content if hasattr(msg, 'content') else str(msg)
            # Determinar el sender de forma robusta
            if isinstance(msg, HumanMessage):
                sender = "user"
            elif isinstance(msg, AIMessage):
                sender = "ai"
            else:
                sender = "ai" # fallback seguro
            msg_created_at = datetime.now(timezone.utc) # Placeholder si no hay un 'created_at' en BaseMessage

            response_messages.append(MessageResponse(
                text=msg_content,
                sender=sender,
                created_at=msg_created_at
            ))
        logger.info(f"Mensajes recuperados para el hilo {thread_id}.")
        return response_messages
    except Exception as e:
        logger.error(f"Error al obtener historial de chat para el hilo {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener mensajes del hilo: {e}")

@app.delete("/api/threads/{thread_id}", status_code=204, summary="Eliminar un hilo de chat")
async def delete_chat_thread(
    thread_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un hilo de chat si pertenece al usuario autenticado.
    """
    thread = await db.scalar(
        select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id))
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")
    await db.delete(thread)
    await db.commit()
    return JSONResponse(status_code=204, content=None)

@app.get("/api/threads/{thread_id}", response_model=ThreadResponse, summary="Obtener un hilo de chat por ID")
async def get_thread_by_id(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")
    return ThreadResponse(id=str(thread.id), title=thread.title, created_at=thread.created_at)

@app.post("/internal/bot-create-thread")
async def bot_create_thread(account_id: str = Form(...), title: str = Form("Nuevo Chat")):
    """Permite al bot de Telegram crear un hilo de chat para una cuenta dada."""
    try:
        thread_id = await create_thread_for_account(account_id, title)
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"Error creando hilo para la cuenta {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe-audio", summary="Transcribe un audio usando Faster Whisper")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    from telegram_client.handlers.message_handlers import get_whisper_model
    import io
    audio_bytes = await file.read()
    audio_io = io.BytesIO(audio_bytes)
    model = await get_whisper_model()
    if not model:
        return JSONResponse(content={"error": "El servicio de transcripción no está disponible."}, status_code=503)
    segments, info = model.transcribe(audio_io)
    transcribed_text = " ".join([segment.text for segment in segments])
    return {"transcription": transcribed_text}

# ==============================================================================
# SECCIÓN 7: Bloque de Ejecución para Desarrollo Local
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor API en modo de desarrollo local (host 0.0.0.0, port 8000)...")
    uvicorn.run("run_api:app", host="0.0.0.0", port=8000, reload=True)