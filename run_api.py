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

from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, Query, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
import httpx

from core.config import settings
from core.database import (
    create_tables, SessionLocal, Account, PlatformIdentity, Perfil,
    get_or_create_account_from_platform_id, get_account_by_telegram_id,
    find_telegram_identity, ChatThread, VerificationCode, AnalysisTask,
    Memory, AgendaEvent, Nota, Team, MindmapTask
)
from datetime import datetime, timedelta, timezone
from core.llm_manager import initialize_llms
from core.agent import create_and_run_agent, create_thread_for_account, force_update_thread_title
from utils.db_session import DBSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, delete_document_chunks, get_full_document_content, update_document_metadata, list_user_collections
from core.notes_manager import get_notes, add_note, update_note, delete_note, get_notes_as_dicts
from core.agenda_manager import get_events_as_dicts, schedule_event, cancel_event, get_agenda_for_day
from telegram_client.bot_manager import bot_manager
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from collections import Counter
from sqlalchemy import update, select, desc 
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import or_
from utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_account_id,
)
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
import httpx
import io

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


# Tu CORSMiddleware existente
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
    "http://192.168.100.106:8880", # La IP desde la que pruebas
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

class AuthRequestCode(BaseModel):
    """Define la estructura para solicitar un código de verificación."""
    identifier: str

class AuthVerifyCode(BaseModel):
    """Define la estructura para verificar un código y obtener un token."""
    identifier: str
    code: str

@app.options("/api/auth/request-code", summary=" Manejar preflight para solicitar código de verificación")
async def request_verification_code_options():
    """Responde a las solicitudes OPTIONS para el endpoint de solicitud de código."""
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/api/auth/request-code", summary="Solicitar código de verificación")
async def request_verification_code(request_data: AuthRequestCode, db: AsyncSession = Depends(get_db)):
    """Busca al usuario, genera un código, lo guarda en la BD y lo envía a Telegram vía HTTP."""
    identity = await find_telegram_identity(db, request_data.identifier)
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontró usuario con identificador '{request_data.identifier}'.")
    
    telegram_id = int(identity.platform_user_id)
    account_id = identity.account_id

    # Genera el código y la fecha de expiración
    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Guarda el código en la base de datos primero
    new_code = VerificationCode(account_id=account_id, code=code, expires_at=expires_at)
    db.add(new_code)
    await db.commit()

    # Ahora, intenta enviar el mensaje haciendo una llamada HTTP al servicio del bot
    telegram_service_url = "http://kognito_telegram_client:9090/internal/send-message"
    message_payload = {
        "chat_id": telegram_id,
        "text": f"Tu código de acceso para Kognito es: <b>{code}</b>"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_service_url, json=message_payload, timeout=10)
            response.raise_for_status() # Lanza un error para respuestas 4xx o 5xx
        
        logger.info(f"Petición de envío de código a {telegram_service_url} exitosa para chat_id {telegram_id}")
        return {"message": "Código de verificación enviado a tu chat de Telegram."}
    
    except httpx.RequestError as e:
        logger.error(f"Error de red al contactar el servicio de Telegram en '{telegram_service_url}': {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Servicio de mensajería no disponible.")
    except httpx.HTTPStatusError as e:
        logger.error(f"El servicio de Telegram devolvió un error {e.response.status_code}: {e.response.text}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fallo al enviar el mensaje a través del servicio interno.")

@app.post("/api/auth/verify-code", response_model=TokenResponse, summary="Verificar código")
async def verify_code_and_get_token(request_data: AuthVerifyCode, db: AsyncSession = Depends(get_db)):
    """Verifica un código contra la BD y devuelve un token si es válido."""
    identity = await find_telegram_identity(db, request_data.identifier)
    if not identity:
        raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta asociada.")

    # Busca el código en la base de datos
    stmt = select(VerificationCode).where(
        VerificationCode.account_id == identity.account_id,
        VerificationCode.code == request_data.code,
        VerificationCode.expires_at > datetime.now(timezone.utc)
    ).order_by(VerificationCode.created_at.desc())
    
    result = await db.execute(stmt)
    valid_code = result.scalars().first()

    if not valid_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorrecto o expirado.")

    # Si el código es válido, lo eliminamos para que no se pueda reusar
    await db.delete(valid_code)
    await db.commit()

    # Creamos el token de acceso
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

@app.get("/api/users/search", summary="Buscar usuario por email o nombre de usuario")
async def search_user(identifier: str = Query(...), current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Busca un usuario por email o nombre de usuario de Telegram. Devuelve el account_id si se encuentra.
    Solo accesible para usuarios autenticados.
    """
    logger.info(f"Buscando usuario con identificador: {identifier} por la cuenta: {current_account_id}")
    
    # Buscar por email
    account_by_email = await db.scalar(select(Account).where(Account.email == identifier))
    if account_by_email:
        return {"account_id": str(account_by_email.id)}
    
    # Buscar por username
    account_by_username = await db.scalar(select(Account).where(Account.username == identifier))
    if account_by_username:
        return {"account_id": str(account_by_username.id)}
    
    # Buscar por platform_user_id en PlatformIdentity si es un ID de Telegram
    try:
        telegram_id = int(identifier)
        identity = await db.scalar(select(PlatformIdentity).where(
            PlatformIdentity.platform == 'telegram',
            PlatformIdentity.platform_user_id == str(telegram_id)
        ))
        if identity:
            return {"account_id": str(identity.account_id)}
    except ValueError:
        pass  # No es un ID numérico, ignorar esta búsqueda
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado con el identificador proporcionado.")

# --- Modelos para el Chat ---
class ChatRequest(BaseModel):
    """Define la estructura de datos para una solicitud de mensaje de chat al agente."""
    thread_id: str
    account_id: str
    telegram_id: Optional[int] = None # Hacemos telegram_id opcional
    user_message: str
    image_base64: Optional[str] = None
    mode: Optional[str] = None

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

    logger.info(f"Petición de chat recibida de la cuenta: {request.account_id} con modo: {request.mode}")
    try:
        final_response_text = await create_and_run_agent(
            account_id=request.account_id,
            thread_id=request.thread_id,
            telegram_id=request.telegram_id, # telegram_id ahora es Optional[int]
            user_message=request.user_message,
            image_base64=request.image_base64,
            mode=request.mode
        )
        return ChatResponse(response_text=final_response_text)
    except Exception as e:
        logger.error(f"Error al procesar petición de la cuenta {request.account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error interno al procesar tu solicitud.")


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
    current_account_id: str = Depends(get_current_account_id),
    files: List[UploadFile] = File(...),
    topic: str = Form(...) # El topic se recibe correctamente aquí
):
    account_id_uuid = uuid.UUID(current_account_id)
    processed_files = 0
    for file in files:
        try:
            content_bytes = await file.read()
            extracted_text, metadata = extract_text_and_metadata_from_document(file.filename, content_bytes)
            if not extracted_text:
                logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                continue

            # --- LA LÍNEA DEL PROBLEMA ESTABA AQUÍ ---
            # Antes, 'metadata' no contenía el topic de forma explícita para la función de abajo.
            # Ahora, pasamos el 'topic' directamente a la función de lógica.
            
            await process_document_for_rag(
                account_id=str(account_id_uuid),
                file_name=file.filename,
                extracted_text=extracted_text,
                topic=topic,  # <-- ¡AQUÍ ESTÁ LA CORRECCIÓN!
                metadata={"original_filename": file.filename} # Pasamos otros metadatos si es necesario
            )
            processed_files += 1
        except Exception as e:
            logger.error(f"Fallo al procesar el archivo {file.filename} para la cuenta {account_id_uuid}: {e}", exc_info=True)

    if processed_files == 0 and files:
        raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
    return {"message": f"{processed_files}/{len(files)} archivo(s) procesado(s) y añadido(s) a tu base de conocimiento en la categoría '{topic}'."}

@app.post("/api/upload-chat-file")
async def upload_chat_file_endpoint(
    current_account_id: str = Depends(get_current_account_id),
    files: List[UploadFile] = File(...),
    thread_id: str = Form(...)
):
    """
    Endpoint para subir archivos al contexto de un hilo de chat específico.
    """
    account_id_uuid = uuid.UUID(current_account_id)
    processed_files = 0
    for file in files:
        try:
            content_bytes = await file.read()
            # Aquí puedes procesar el archivo según sea necesario para el contexto del chat
            # Por ahora, simplemente registramos que se ha subido el archivo
            logger.info(f"Archivo {file.filename} subido al hilo {thread_id} por la cuenta {account_id_uuid}")
            processed_files += 1
        except Exception as e:
            logger.error(f"Fallo al procesar el archivo {file.filename} para el hilo {thread_id} de la cuenta {account_id_uuid}: {e}", exc_info=True)

    if processed_files == 0 and files:
        raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
    return {"message": f"{processed_files}/{len(files)} archivo(s) subido(s) al contexto del hilo {thread_id}."}
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

class ListNotesRequest(BaseModel):
    search_term: Optional[str] = None

# --- ENDPOINT DE NOTAS ACTUALIZADO ---
# Cambiamos el nombre del endpoint para que sea más claro
@app.post("/api/list-notes")
async def list_notes_endpoint(
    request: ListNotesRequest, # Usamos el modelo
    current_account_id: str = Depends(get_current_account_id)
):
    """Devuelve las notas de un usuario como una lista de objetos JSON."""
    notes_list = await get_notes_as_dicts(
        account_id=current_account_id, 
        search_query=request.search_term
    )
    return notes_list
# --- MODELOS PYDANTIC PARA NOTAS ---
class NoteRequest(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = None

@app.post("/api/add-note")
async def add_note_endpoint(note: NoteRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade una nueva nota para el usuario. Protegido por JWT."""
    new_note = await add_note(current_account_id, note.title or "", note.content, note.category or "")
    # Devolvemos la nota creada para poder añadirla al estado del frontend sin re-fetchear
    return new_note 

class NoteUpdateRequest(NoteRequest):
    note_id: int

@app.post("/api/update-note")
async def update_note_endpoint(note: NoteUpdateRequest, current_account_id: str = Depends(get_current_account_id)):
    """Actualiza una nota existente del usuario. Protegido por JWT."""
    result_message = await update_note(current_account_id, note.note_id, note.title, note.content, note.category)
    return {"message": result_message}

class NoteDeleteRequest(BaseModel):
    note_id: int

@app.post("/api/delete-note")
async def delete_note_endpoint(note: NoteDeleteRequest, current_account_id: str = Depends(get_current_account_id)):
    """Elimina una nota del usuario. Protegido por JWT."""
    result_message = await delete_note(current_account_id, note.note_id)
    return {"message": result_message}

@app.post("/api/list-events") # Cambiado a POST
async def list_events_endpoint(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """Lista los eventos de la agenda del usuario. Protegido por JWT."""
    return await get_events_as_dicts(current_account_id)

# --- MODELOS PYDANTIC PARA AGENDA ---
class EventRequest(BaseModel):
    description: str
    event_datetime: str # "mañana a las 3pm"

@app.post("/api/add-event")
async def add_event_endpoint(event: EventRequest, current_account_id: str = Depends(get_current_account_id)):
    """Añade un nuevo evento a la agenda del usuario. Protegido por JWT."""
    success, message, new_event = await schedule_event(
        account_id=current_account_id,
        description=event.description,
        natural_language_datetime=event.event_datetime
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    # Devolvemos el evento creado para añadirlo al estado del frontend
    return new_event.to_dict() if new_event else {}

class EventCancelRequest(BaseModel):
    event_id: int

@app.post("/api/cancel-event")
async def cancel_event_endpoint(event: EventCancelRequest, current_account_id: str = Depends(get_current_account_id)):
    """Cancela un evento de la agenda del usuario. Protegido por JWT."""
    success, message = await cancel_event(current_account_id, event.event_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}

class UpdateMetadataRequest(BaseModel):
    """Define la estructura de datos para actualizar los metadatos de un documento."""
    file_name: str
    new_title: Optional[str] = None
    new_topic: Optional[str] = None

@app.post("/api/update-document-metadata")
async def update_document_metadata_endpoint(
    request: UpdateMetadataRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza el título y/o la categoría de un documento del usuario."""
    account_id_uuid = uuid.UUID(current_account_id)
    # Usa los datos del objeto 'request'
    success = await update_document_metadata(
        str(account_id_uuid), 
        request.file_name, 
        request.new_title, 
        request.new_topic
    )
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado o no actualizado.")
    return {"message": "Metadatos actualizados correctamente."}
class DocumentContentRequest(BaseModel):
    file_name: str

@app.post("/api/get-document-content", summary="Obtener el contenido de un documento")
async def get_document_content_endpoint(
    request: DocumentContentRequest,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Recupera el contenido textual completo de un documento específico.
    """
    content = await get_full_document_content(
        account_id=current_account_id,
        file_name=request.file_name
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado o sin contenido.")
    
    return {"content": content}

from fastapi import BackgroundTasks
from core.memory_manager import get_full_document_content
from utils.advanced_text_analyzer import text_analyzer
from core.database import ProactiveInsight

# Modelo para la petición
class AnalyzeDocumentRequest(BaseModel):
    file_name: str

# Esta función se ejecutará en segundo plano
async def run_document_analysis_and_save(task_id: str, account_id: str, file_name: str):
    """Función pesada que se ejecuta en segundo plano."""
    async with SessionLocal() as db_session:
        try:
            # 1. Marcar la tarea como 'processing'
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            
            logger.info(f"Iniciando análisis para tarea {task_id}...")
            text_content = await get_full_document_content(account_id, file_name)
            if not text_content: raise ValueError("Contenido del documento no encontrado.")

            # 2. Realizar el análisis pesado
            analysis_result = await text_analyzer.analyze_single_text(text_content)

            # 3. Guardar el resultado y marcar como 'completed'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload=analysis_result.dict())
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis para tarea {task_id} completado.")

        except Exception as e:
            logger.error(f"Fallo en tarea de análisis {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()

@app.post("/api/start-document-analysis", status_code=202)
async def start_document_analysis_endpoint(
    req: AnalyzeDocumentRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Inicia una tarea de análisis de documento y devuelve un ID de tarea."""
    # Verificar que el documento existe antes de crear la tarea
    content_check = await get_full_document_content(current_account_id, req.file_name)
    if content_check is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        file_name=req.file_name,
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_document_analysis_and_save, str(new_task.id), current_account_id, req.file_name)
    
    return {"task_id": str(new_task.id)}


@app.get("/api/get-analysis-result/{task_id}")
async def get_analysis_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Consulta el estado y el resultado de una tarea de análisis."""
    task = await db.get(AnalysisTask, uuid.UUID(task_id))
    if not task or str(task.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")
    return {"status": task.status, "result": task.result_payload, "error": task.error_message}

@app.get("/api/get-mindmap-result/{task_id}")
async def get_mindmap_result_endpoint(
    task_id: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Consulta el estado y el resultado de una tarea de mapa mental, incluyendo la imagen Base64 si está disponible."""
    task = await db.get(MindmapTask, uuid.UUID(task_id))
    if not task or str(task.account_id) != current_account_id:
        raise HTTPException(status_code=404, detail="Tarea de mapa mental no encontrada.")
    return {
        "status": task.status,
        "result": task.result_payload if task.result_payload else {},
        "topic": task.topic,
        "created_at": task.created_at.isoformat()
    }



@app.post("/api/list-collections", summary="Listar las colecciones de conocimiento")
async def list_collections_endpoint(current_account_id: str = Depends(get_current_account_id)):
    """
    Devuelve una lista de todas las colecciones (temas) únicas de un usuario
    y el número de documentos en cada una.
    """
    collections = await list_user_collections(current_account_id)
    return collections

from utils.advanced_text_analyzer import CollectionAnalysis, AdvancedTextAnalyzer  # Importar la nueva función

# --- Modelo para la petición de análisis de colección ---
class AnalyzeCollectionRequest(BaseModel):
    topic: str

# --- Nueva función que se ejecutará en segundo plano ---
async def run_collection_analysis_and_save(task_id: str, account_id: str, topic: str):
    """
    Obtiene todos los documentos de una colección, los analiza y guarda el resultado.
    """
    db_session = SessionLocal()
    try:
        # Marcar la tarea como 'processing'
        await db_session.execute(update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing"))
        await db_session.commit()
        
        logger.info(f"Iniciando análisis de colección para tarea {task_id} (tema: {topic})")

        # 1. Obtener todos los documentos de la colección
        all_docs_in_topic = []
        # (Aquí usamos la lógica de list_user_documents, pero necesitamos el contenido)
        from core.memory_manager import list_user_documents, get_full_document_content
        doc_list = await list_user_documents(account_id)
        filtered_doc_list = [doc for doc in doc_list if doc.get('topic') == topic]
        
        for doc_meta in filtered_doc_list:
            content = await get_full_document_content(account_id, doc_meta['file_name'])
            if content:
                all_docs_in_topic.append({
                    "title": doc_meta.get('title', doc_meta['file_name']),
                    "content": content
                })

        if not all_docs_in_topic:
            raise ValueError(f"No se encontraron documentos con contenido en la colección '{topic}'.")

        # 2. Realizar el análisis de la colección
        analysis_result = await text_analyzer.analyze_collection(all_docs_in_topic)
        logger.info(f"Collection analysis result generated for topic '{topic}': {analysis_result.dict()}")
        
        # 3. Guardar el resultado y marcar como 'completed'
        stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
            status="completed", result_payload=analysis_result.dict())
        await db_session.execute(stmt_completed)
        await db_session.commit()
        logger.info(f"Análisis de colección para tarea {task_id} completado.")

    except Exception as e:
        logger.error(f"Fallo en tarea de análisis de colección {task_id}: {e}", exc_info=True)
        stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
            status="failed", error_message=str(e))
        await db_session.execute(stmt_failed)
        await db_session.commit()
    finally:
        await db_session.close()

# --- ENDPOINT PARA INICIAR EL ANÁLISIS DE COLECCIÓN ---
@app.post("/api/start-collection-analysis", status_code=202)
async def start_collection_analysis_endpoint(
    req: AnalyzeCollectionRequest,
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """Inicia un análisis de una colección completa y devuelve un ID de tarea."""
    new_task = AnalysisTask(
        account_id=uuid.UUID(current_account_id),
        # Usamos el nombre del topic como referencia en lugar de un file_name
        file_name=f"Colección: {req.topic}",
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    background_tasks.add_task(run_collection_analysis_and_save, str(new_task.id), current_account_id, req.topic)
    
    return {"task_id": str(new_task.id)}

class GetSavedAnalysesRequest(BaseModel):
    topic: Optional[str] = None # Para filtrar por colección
    all: bool = False # Para obtener todos los análisis sin filtrar por colección

@app.post("/api/get-saved-analyses")
async def get_saved_analyses_endpoint(
    req: GetSavedAnalysesRequest,
    current_account_id: str = Depends(get_current_account_id), 
    db: AsyncSession = Depends(get_db)
):
    """
    Recupera la lista de análisis completados.
    Si se proporciona un 'topic', devuelve los análisis de esa colección Y de sus documentos.
    Si 'all' es True, devuelve todos los análisis.
    Si no, devuelve solo los análisis de documentos individuales.
    """
    account_uuid = uuid.UUID(current_account_id)
    
    # Construimos la consulta base
    base_stmt = select(AnalysisTask).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed"
    )

    if req.topic:
        # --- LÓGICA MEJORADA PARA COLECCIONES ---
        
        # 1. Obtenemos los nombres de los archivos que pertenecen a este topic.
        #    (Reutilizamos la lógica de list_user_documents)
        all_user_docs = await list_user_documents(current_account_id)
        files_in_topic = [
            doc['file_name'] for doc in all_user_docs if doc.get('topic') == req.topic
        ]
        
        # 2. Construimos la condición del WHERE
        #    Queremos análisis cuyo 'file_name' sea uno de los archivos de la colección,
        #    O que sea el análisis de la propia colección.
        collection_reference_name = f"Colección: {req.topic}"
        
        # Usamos or_() para combinar las condiciones
        final_stmt = base_stmt.where(
            or_(
                AnalysisTask.file_name.in_(files_in_topic),
                AnalysisTask.file_name == collection_reference_name
            )
        )
    elif req.all:
        # Si se pide 'all', no aplicamos más filtros.
        final_stmt = base_stmt
    else:
        # Comportamiento por defecto: devolver todos los análisis completados si no se especifica un 'topic'.
        final_stmt = base_stmt

    # Ordenamos y limitamos la consulta final
    final_stmt = final_stmt.order_by(desc(AnalysisTask.created_at)).limit(50)
    
    results = await db.execute(final_stmt)
    return results.scalars().all()

class DeleteAnalysisRequest(BaseModel):
    task_id: str

@app.post("/api/delete-analysis", summary="Eliminar un análisis guardado")
async def delete_analysis_endpoint(
    req: DeleteAnalysisRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un análisis guardado por su ID de tarea, si pertenece al usuario autenticado.
    """
    account_uuid = uuid.UUID(current_account_id)
    task_uuid = uuid.UUID(req.task_id)
    
    task = await db.get(AnalysisTask, task_uuid)
    if not task or task.account_id != account_uuid:
        raise HTTPException(status_code=404, detail="Análisis no encontrado o no pertenece al usuario.")
    
    await db.delete(task)
    await db.commit()
    return {"message": f"Análisis con ID {req.task_id} eliminado correctamente."}


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

class ThreadPinRequest(BaseModel):
    isPinned: bool

@app.put("/api/threads/{thread_id}/pin", response_model=ThreadResponse, summary="Actualizar estado de fijado de un hilo de chat")
async def update_thread_pin_status(thread_id: str, request: ThreadPinRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Actualiza el estado de fijado de un hilo de chat para el usuario autenticado.
    """
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado o no pertenece al usuario.")
    thread.is_pinned = request.isPinned
    await db.commit()
    await db.refresh(thread)
    return ThreadResponse(id=str(thread.id), title=thread.title, created_at=thread.created_at)

@app.post("/api/threads/{thread_id}/generate-title", response_model=ThreadResponse, summary="Forzar la generación de un nuevo título para un hilo de chat")
async def force_generate_thread_title(thread_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Fuerza la generación de un nuevo título para un hilo de chat específico.
    """
    await force_update_thread_title(thread_id)
    thread = await db.scalar(select(ChatThread).where(ChatThread.id == uuid.UUID(thread_id), ChatThread.account_id == uuid.UUID(current_account_id)))
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de chat no encontrado.")
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

# Modelo Pydantic para la petición de TTS
class TTSRequest(BaseModel):
    text: str

# Usamos el nombre del servicio Docker y el puerto interno correcto.
TTS_SERVICE_URL = "http://openai-edge-tts:5050/v1/audio/speech"

@app.post("/api/dashboard-insights")
async def get_dashboard_insights(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Agrega y devuelve datos de análisis (manuales) y insights (proactivos)
    para el dashboard principal.
    """
    account_uuid = uuid.UUID(current_account_id)

    # 1. Obtener todos los resultados de análisis manuales completados de la tabla AnalysisTask
    analysis_stmt = select(AnalysisTask.result_payload).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.result_payload.isnot(None)
    )
    analysis_results = await db.execute(analysis_stmt)
    analysis_payloads = analysis_results.scalars().all()

    # 2. Procesar y agregar los datos de esos análisis para los gráficos
    all_topics = []

    for payload in analysis_payloads:
        if isinstance(payload, dict):
            # Usamos los temas avanzados si existen, que son de mayor calidad
            all_topics.extend(payload.get("temas_clave_avanzados", []))
    
    # Contar y obtener el Top 10 de temas clave para el gráfico de barras
    # TODO: Reemplazar con análisis semántico una vez que Gemini esté integrado
    topic_counts = Counter(all_topics)
    top_topics_for_chart = [{"topic": topic, "mentions": count} for topic, count in topic_counts.most_common(10)]

    # 3. Verificar si hay un análisis semántico reciente completado
    semantic_analysis_stmt = select(AnalysisTask.result_payload).where(
        AnalysisTask.account_id == account_uuid,
        AnalysisTask.status == "completed",
        AnalysisTask.file_name == "Semantic Topic Analysis",
        AnalysisTask.result_payload.isnot(None)
    ).order_by(desc(AnalysisTask.created_at)).limit(1)
    
    semantic_analysis_result = await db.execute(semantic_analysis_stmt)
    semantic_payload = semantic_analysis_result.scalars().first()
    
    if semantic_payload and "grouped_topics" in semantic_payload:
        # Usar los temas agrupados por análisis semántico si están disponibles
        top_topics_for_chart = semantic_payload["grouped_topics"]
        logger.info(f"Usando temas agrupados por análisis semántico para account {current_account_id}.")

    # 4. Obtener los últimos insights proactivos (sinergias, contradicciones, etc.)
    # Estos son los descubrimientos que la IA hace por sí sola.
    proactive_stmt = select(ProactiveInsight).where(
        ProactiveInsight.account_id == account_uuid
    ).order_by(desc(ProactiveInsight.created_at)).limit(10)
    
    proactive_results = await db.execute(proactive_stmt)
    recent_proactive_insights = proactive_results.scalars().all()

    # 5. Construir y devolver la respuesta final en el formato que el frontend espera
    return {
        "key_topics": top_topics_for_chart, # Para el gráfico de barras
        "proactive_insights": [
            {
                "id": str(insight.id),
                "type": insight.type,
                "summary": insight.insight_message,
                "created_at": insight.created_at.isoformat(),
                "related_items": insight.related_items,
                "action_suggestion": insight.action_suggestion,
                # No necesitamos devolver result_payload aquí, ya que el insight es el resultado
            } for insight in recent_proactive_insights
        ]
        # Ya no devolvemos 'top_entities' ni 'exploration_questions' para este diseño
    }

@app.post("/api/update-semantic-topics", status_code=202, summary="Actualizar temas con análisis semántico")
async def update_semantic_topics_endpoint(
    background_tasks: BackgroundTasks,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db),
    max_terms: Optional[int] = Form(default=15, ge=1, description="Número máximo de términos a analizar para el análisis semántico")
):
    """
    Dispara manualmente el proceso de análisis semántico para agrupar temas por similitud.
    Este proceso se ejecuta en segundo plano y actualiza los datos para el endpoint /api/dashboard-insights.
    Opcionalmente, se puede limitar el número de términos analizados con max_terms.
    """
    account_uuid = uuid.UUID(current_account_id)
    new_task = AnalysisTask(
        account_id=account_uuid,
        file_name="Semantic Topic Analysis",
        status="pending"
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    logger.info(f"Iniciando tarea de análisis semántico con ID {str(new_task.id)} para la cuenta {current_account_id} con límite de {max_terms if max_terms else 'todos'} términos")
    background_tasks.add_task(run_semantic_topic_analysis, str(new_task.id), current_account_id, max_terms)
    
    return {"task_id": str(new_task.id), "message": f"Análisis semántico iniciado en segundo plano con límite de {max_terms if max_terms else 'todos los'} términos."}

async def run_semantic_topic_analysis(task_id: str, account_id: str, max_terms: Optional[int] = None):
    """
    Proceso en segundo plano para realizar análisis semántico y agrupación de temas.
    Este es un placeholder para la integración con Gemini API.
    Se puede limitar el número de términos analizados con max_terms.
    """
    async with SessionLocal() as db_session:
        try:
            # Marcar la tarea como 'processing' y notificar al usuario
            stmt_processing = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(status="processing")
            await db_session.execute(stmt_processing)
            await db_session.commit()
            logger.info(f"Iniciando análisis semántico para tarea {task_id} para la cuenta {account_id}...")
            # Aquí se podría enviar una notificación de inicio a través de un WebSocket o similar

            # 1. Obtener todos los temas de análisis previos
            analysis_stmt = select(AnalysisTask.result_payload).where(
                AnalysisTask.account_id == uuid.UUID(account_id),
                AnalysisTask.status == "completed",
                AnalysisTask.result_payload.isnot(None)
            )
            analysis_results = await db_session.execute(analysis_stmt)
            analysis_payloads = analysis_results.scalars().all()

            all_topics = []
            for payload in analysis_payloads:
                if isinstance(payload, dict):
                    all_topics.extend(payload.get("temas_clave_avanzados", []))
            if max_terms is not None and len(all_topics) > max_terms:
                all_topics = all_topics[:max_terms]
                logger.info(f"Limitando análisis semántico a {max_terms} términos de un total de {len(all_topics)}.")
            else:
                logger.info(f"Procesando {len(all_topics)} temas para análisis semántico sin límite.")

            # 2. Integrar Gemini API para obtener embebidos semánticos usando el LLM ya configurado
            from core.llm_manager import get_fast_llm
            llm_for_embeddings = get_fast_llm()
            if not llm_for_embeddings:
                logger.error("No hay LLM disponible para generar embeddings.")
                raise ValueError("LLM no disponible para análisis semántico.")
                
            embeddings = []
            for topic in all_topics:
                try:
                    logger.info(f"Generando embedding para el tema: {topic}")
                    # Usar un prompt más específico para obtener una representación numérica precisa
                    prompt = f"Convert the topic '{topic}' into a dense numerical vector of 768 dimensions for semantic clustering. Provide the vector as a space-separated list of numbers."
                    response = await llm_for_embeddings.ainvoke(prompt)
                    logger.info(f"Respuesta recibida para el tema: {topic}")
                    # Extraer el contenido como texto y convertir a lista de números
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    # Parsear la respuesta para obtener un vector de números
                    vector = []
                    for val in response_text.split():
                        try:
                            num_val = float(val)
                            vector.append(num_val)
                        except ValueError:
                            continue  # Ignorar valores no numéricos
                    # Ajustar el tamaño del vector a 768 dimensiones
                    while len(vector) < 768:
                        vector.append(0.0)
                    if len(vector) > 768:
                        vector = vector[:768]
                    embeddings.append(vector)
                    logger.info(f"Embedding generado exitosamente para: {topic}")
                except Exception as e:
                    logger.error(f"Error al obtener embedding para {topic}: {e}", exc_info=True)
                    embeddings.append([0.0] * 768)  # Fallback en caso de error
            logger.info(f"Obtenidos embeddings para {len(embeddings)} temas.")

            # 3. Implementar clustering (e.g., K-Means) para agrupar temas por similitud semántica
            from sklearn.cluster import KMeans
            import numpy as np
            if len(embeddings) > 5:  # Solo hacer clustering si hay suficientes temas
                kmeans = KMeans(n_clusters=min(5, len(embeddings) // 2 + 1), random_state=42)
                clusters = kmeans.fit_predict(np.array(embeddings))
            else:
                clusters = list(range(len(embeddings)))  # Asignar un cluster por tema si hay pocos

            # 4. Agrupar temas por cluster y contar menciones
            cluster_dict = {}
            for topic, cluster_id, _ in zip(all_topics, clusters, embeddings):
                if cluster_id not in cluster_dict:
                    cluster_dict[cluster_id] = {"topics": [], "mentions": 0}
                cluster_dict[cluster_id]["topics"].append(topic)
                cluster_dict[cluster_id]["mentions"] += all_topics.count(topic)

            # 5. Generar un término representativo para cada cluster usando el mismo LLM
            grouped_topics = []
            for cluster_id, data in cluster_dict.items():
                try:
                    topics_str = ", ".join(data["topics"][:5])  # Limitar a 5 temas para el prompt
                    prompt = f"Generate a concise tag or term -not phrase, only term-for the following group of topics: {topics_str}. The tag should be a short, specific label (1-3 words) that captures the essence of these topics without any explanation or description. Ensure it is relevant and recognizable to the user."
                    response = await llm_for_embeddings.ainvoke(prompt)
                    representative_term = response.content.strip() if hasattr(response, 'content') else f"Grupo {cluster_id + 1}"
                except Exception as e:
                    logger.error(f"Error al generar término representativo para cluster {cluster_id}: {e}")
                    representative_term = f"Grupo {cluster_id + 1}"
                grouped_topics.append({"topic": representative_term, "mentions": data["mentions"]})

            # Ordenar por menciones descendentes
            simulated_grouped_topics = sorted(grouped_topics, key=lambda x: x["mentions"], reverse=True)[:10]

            # 4. Guardar el resultado y marcar como 'completed'
            stmt_completed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="completed", result_payload={"grouped_topics": simulated_grouped_topics})
            await db_session.execute(stmt_completed)
            await db_session.commit()
            logger.info(f"Análisis semántico para tarea {task_id} completado con {len(simulated_grouped_topics)} grupos de temas.")
            # Aquí se podría enviar una notificación de finalización a través de un WebSocket o similar
        except Exception as e:
            logger.error(f"Fallo en tarea de análisis semántico {task_id}: {e}", exc_info=True)
            stmt_failed = update(AnalysisTask).where(AnalysisTask.id == uuid.UUID(task_id)).values(
                status="failed", error_message=str(e))
            await db_session.execute(stmt_failed)
            await db_session.commit()
            # Aquí se podría enviar una notificación de error a través de un WebSocket o similar

@app.post("/api/text-to-speech", summary="Generar audio desde texto")
async def text_to_speech_endpoint(request: TTSRequest):
    """
    Recibe texto, lo envía al servicio interno de TTS y devuelve el audio como un stream.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    # Parámetros para open-edgetts. Ajusta la voz, etc., según necesites.
    tts_payload = {
        'input': request.text,
        'voice': 'es-MX-DaliaNeural',
        'model': 'edge-tts', # O el modelo que use tu wrapper
        'speed': 1.0, # El wrapper parece esperar un número, no "+10%"
    }


    try:
        async with httpx.AsyncClient() as client:
            # Hacemos una petición GET al servicio de TTS
            response = await client.post(TTS_SERVICE_URL, json=tts_payload, timeout=30.0)     
            response.raise_for_status()
            # Devolvemos el contenido de audio directamente como un stream
            return StreamingResponse(io.BytesIO(response.content), media_type="audio/wav")

    except httpx.RequestError as e:
        logger.error(f"Error de red contactando el servicio TTS: {e}")
        raise HTTPException(status_code=503, detail="El servicio de voz no está disponible.")
    except httpx.HTTPStatusError as e:
        logger.error(f"El servicio TTS devolvió un error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=502, detail="Error en el servicio de generación de voz.")

# ==============================================================================
# SECCIÓN 7: API para Gestión de Equipos
# ==============================================================================

# --- Modelos Pydantic para Equipos ---
class TeamCreateRequest(BaseModel):
    """Define la estructura de datos para crear un nuevo equipo."""
    name: str

class TeamUpdateRequest(BaseModel):
    """Define la estructura de datos para actualizar un equipo existente."""
    name: Optional[str] = None

class TeamShareRequest(BaseModel):
    """Define la estructura de datos para compartir recursos con un equipo."""
    documentIds: List[str] = []
    eventIds: List[int] = []
    noteIds: List[int] = []

class TeamResponse(BaseModel):
    """Define la estructura de datos para la respuesta de un equipo."""
    id: str
    name: str
    created_at: datetime

from core.database import Team

@app.get("/api/teams", response_model=List[TeamResponse], summary="Listar equipos del usuario")
async def list_teams(current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los equipos de un usuario autenticado, incluyendo aquellos donde es administrador o miembro.
    """
    logger.info(f"Listando equipos para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    # Obtener equipos donde el usuario es administrador
    admin_teams_result = await db.execute(select(Team).where(Team.admin_id == account_uuid).order_by(Team.created_at.desc()))
    admin_teams = admin_teams_result.scalars().all()
    # Obtener equipos donde el usuario es miembro
    member_teams_result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.account_id == account_uuid)
        .order_by(Team.created_at.desc())
    )
    member_teams = member_teams_result.scalars().all()
    # Combinar y eliminar duplicados
    teams = list(set(admin_teams + member_teams))
    # Ordenar por fecha de creación descendente
    teams.sort(key=lambda x: x.created_at, reverse=True)
    return [TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at) for team in teams]

@app.get("/api/teams/{team_id}", response_model=TeamResponse, summary="Obtener detalles de un equipo")
async def get_team(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Obtiene los detalles de un equipo específico si pertenece al usuario autenticado.
    """
    logger.info(f"Obteniendo detalles del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    return TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at)

@app.post("/api/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo equipo")
async def create_team(team: TeamCreateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Crea un nuevo equipo para el usuario autenticado.
    """
    logger.info(f"Creando nuevo equipo para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    new_team = Team(admin_id=account_uuid, name=team.name)
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)
    return TeamResponse(id=str(new_team.id), name=new_team.name, created_at=new_team.created_at)

@app.put("/api/teams/{team_id}", response_model=TeamResponse, summary="Actualizar un equipo existente")
async def update_team(team_id: str, team_update: TeamUpdateRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Actualiza un equipo existente si pertenece al usuario autenticado.
    """
    logger.info(f"Actualizando equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    if team_update.name:
        team.name = team_update.name
    await db.commit()
    await db.refresh(team)
    return TeamResponse(id=str(team.id), name=team.name, created_at=team.created_at)

@app.post("/api/teams/{team_id}/share/documents", summary="Compartir documentos con un equipo")
async def share_documents_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte documentos con un equipo específico.
    """
    logger.info(f"Compartiendo documentos con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    for file_name in share_request.documentIds:
        # Update Memory table to associate documents with the team
        # We check for documents where the content or related metadata might match the file_name
        result = await db.execute(
            update(Memory)
            .where(
                Memory.account_id == account_uuid, 
                Memory.type == "document_chunk",
                Memory.content.like(f"%{file_name}%")
            )
            .values(team_id=team_uuid)
        )
        if result.rowcount > 0:
            updated_count += result.rowcount
            logger.info(f"Documento {file_name} compartido con equipo {team_id}, actualizadas {result.rowcount} entradas.")
        else:
            logger.warning(f"No se encontraron entradas para el documento {file_name} con account_id {account_uuid}.")
    
    await db.commit()
    if updated_count == 0:
        logger.warning(f"No se compartieron documentos con el equipo {team_id} para la cuenta {current_account_id}.")
        return {"message": "No se encontraron documentos para compartir. Verifica los IDs de los documentos."}
    return {"message": f"{updated_count} documentos compartidos con equipo {team_id}"}

@app.post("/api/teams/{team_id}/share/events", summary="Compartir eventos con un equipo")
async def share_events_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte eventos con un equipo específico.
    """
    logger.info(f"Compartiendo eventos con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    for event_id in share_request.eventIds:
        # Update AgendaEvent table to associate events with the team
        result = await db.execute(
            update(AgendaEvent)
            .where(AgendaEvent.account_id == account_uuid, AgendaEvent.id == event_id)
            .values(team_id=team_uuid)
        )
        if result.rowcount > 0:
            updated_count += result.rowcount
    
    await db.commit()
    return {"message": f"{updated_count} eventos compartidos con equipo {team_id}"}

@app.post("/api/teams/{team_id}/share/notes", summary="Compartir notas con un equipo")
async def share_notes_with_team(team_id: str, share_request: TeamShareRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Comparte notas con un equipo específico.
    """
    logger.info(f"Compartiendo notas con equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no pertenece al usuario.")
    
    updated_count = 0
    for note_id in share_request.noteIds:
        # Update Nota table to associate notes with the team
        result = await db.execute(
            update(Nota)
            .where(Nota.account_id == account_uuid, Nota.id == note_id)
            .values(team_id=team_uuid)
        )
        if result.rowcount > 0:
            updated_count += result.rowcount
    
    await db.commit()
    return {"message": f"{updated_count} notas compartidas con equipo {team_id}"}

# --- Endpoints para Gestión de Miembros de Equipo ---

from core.database import TeamMember

class TeamMemberAddRequest(BaseModel):
    """Define la estructura de datos para añadir un miembro a un equipo."""
    account_id: str

class TeamMemberRemoveRequest(BaseModel):
    """Define la estructura de datos para eliminar un miembro de un equipo."""
    account_id: str

@app.post("/api/teams/{team_id}/members", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Añadir miembro a un equipo")
async def add_team_member(team_id: str, request: TeamMemberAddRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Añade un miembro a un equipo específico. Solo el administrador del equipo puede realizar esta acción.
    """
    logger.info(f"Añadiendo miembro al equipo {team_id} por la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para gestionar miembros.")
    
    member_uuid = uuid.UUID(request.account_id)
    # Verificar si el miembro ya está en el equipo
    existing_member = await db.scalar(select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == member_uuid))
    if existing_member:
        raise HTTPException(status_code=409, detail="El usuario ya es miembro de este equipo.")
    
    new_member = TeamMember(team_id=team_uuid, account_id=member_uuid)
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return {"message": f"Miembro {request.account_id} añadido al equipo {team_id}"}

@app.delete("/api/teams/{team_id}/members", response_model=dict, summary="Eliminar miembro de un equipo")
async def remove_team_member(team_id: str, request: TeamMemberRemoveRequest, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Elimina un miembro de un equipo específico. Solo el administrador del equipo puede realizar esta acción.
    """
    logger.info(f"Eliminando miembro del equipo {team_id} por la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    team = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para gestionar miembros.")
    
    member_uuid = uuid.UUID(request.account_id)
    member = await db.scalar(select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == member_uuid))
    if not member:
        raise HTTPException(status_code=404, detail="Miembro no encontrado en este equipo.")
    
    await db.delete(member)
    await db.commit()
    return {"message": f"Miembro {request.account_id} eliminado del equipo {team_id}"}

@app.get("/api/teams/{team_id}/members", response_model=List[dict], summary="Listar miembros de un equipo")
async def list_team_members(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los miembros de un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando miembros del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver los miembros.")
    
    members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_uuid))
    members = members_result.scalars().all()
    return [{"account_id": str(member.account_id), "joined_at": member.joined_at} for member in members]

@app.get("/api/teams/{team_id}/documents", response_model=List[dict], summary="Listar documentos compartidos con un equipo")
async def list_team_documents(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todos los documentos compartidos con un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando documentos del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver los documentos.")
    
    documents_result = await db.execute(select(Memory).where(Memory.team_id == team_uuid, Memory.type == "document_chunk"))
    documents = documents_result.scalars().all()
    return [{"file_name": doc.content, "title": doc.content, "shared_at": doc.created_at} for doc in documents]

@app.get("/api/teams/{team_id}/notes", response_model=List[dict], summary="Listar notas compartidas con un equipo")
async def list_team_notes(team_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Lista todas las notas compartidas con un equipo específico. Accesible para cualquier miembro del equipo.
    """
    logger.info(f"Listando notas del equipo {team_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    team_uuid = uuid.UUID(team_id)
    # Verificar si el usuario es administrador o miembro del equipo
    team_as_admin = await db.scalar(select(Team).where(Team.id == team_uuid, Team.admin_id == account_uuid))
    if not team_as_admin:
        team_as_member = await db.scalar(
            select(TeamMember).where(TeamMember.team_id == team_uuid, TeamMember.account_id == account_uuid)
        )
        if not team_as_member:
            raise HTTPException(status_code=404, detail="Equipo no encontrado o no tienes permisos para ver las notas.")
    
    notes_result = await db.execute(select(Nota).where(Nota.team_id == team_uuid))
    notes = notes_result.scalars().all()
    return [{"id": note.id, "title": note.title, "updated_at": note.updated_at} for note in notes]

@app.post("/api/notes/{note_id}/unshare", summary="Eliminar compartición de una nota")
async def unshare_note(note_id: str, current_account_id: str = Depends(get_current_account_id), db: AsyncSession = Depends(get_db)):
    """
    Elimina la asociación de una nota con cualquier equipo, dejándola como no compartida.
    """
    logger.info(f"Eliminando compartición de nota {note_id} para la cuenta: {current_account_id}")
    account_uuid = uuid.UUID(current_account_id)
    note_id_int = int(note_id)
    
    result = await db.execute(
        update(Nota)
        .where(Nota.account_id == account_uuid, Nota.id == note_id_int)
        .values(team_id=None)
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Nota no encontrada o no pertenece al usuario.")
    
    await db.commit()
    return {"message": "Nota ya no está compartida con ningún equipo."}

# ==============================================================================
# SECCIÓN 8: Bloque de Ejecución para Desarrollo Local
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor API en modo de desarrollo local (host 0.0.0.0, port 8000)...")
    uvicorn.run("run_api:app", host="0.0.0.0", port=8000, reload=True)
