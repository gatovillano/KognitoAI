# run_api.py

"""
Servidor API y Web centralizado para Kognito AI System.
"""

import logging
import asyncio
import os
import json
import hmac
import hashlib
import time
import random
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import unquote, parse_qs

# --- Framework de API y Servidor ---
from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Módulos del Proyecto (Lógica Compartida) ---
# Se importan todas las funciones y clases necesarias desde sus nuevos hogares.
from core.config import settings
from core.database import (
    create_tables, SessionLocal, Account, PlatformIdentity, Perfil, 
    get_or_create_account_from_platform_id, get_account_by_telegram_id
)
from core.agent import initialize_llms, create_and_run_agent
from utils.db_session import DBSession
from utils.document_parser import extract_text_and_metadata_from_document
from core.memory_manager import process_document_for_rag, list_user_documents, delete_document_chunks
from core.notes_manager import get_notes, add_note, update_note, delete_note
from core.agenda_manager import get_events_as_dicts, schedule_event, cancel_event
from telegram_client.bot_manager import bot_manager
from sqlalchemy import select

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# SECCIÓN 1: INICIALIZACIÓN Y CICLO DE VIDA DE LA APP
# ==============================================================================

app = FastAPI(
    title="Kognito AI System - API Central",
    description="Procesa la lógica de la IA, sirve el panel de Telegram y gestiona la autenticación universal.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Se ejecuta una vez al arrancar el servidor. Inicializa recursos críticos."""
    logger.info("🚀 El servidor central está arrancando...")
    if not settings.jwt_secret_key:
        logger.error("❌ ERROR FATAL: JWT_SECRET_KEY no está configurada. El servicio de autenticación no funcionará.")
    try:
        await create_tables()
        logger.info("✅ Tablas de la base de datos verificadas/creadas.")
        await initialize_llms()
        logger.info("✅ Modelos de Lenguaje (LLMs) inicializados.")
        logger.info("🎉 Servidor listo para aceptar peticiones.")
    except Exception as e:
        logger.error(f"❌ ERROR FATAL DURANTE EL ARRANQUE: {e}", exc_info=True)
        raise

# ==============================================================================
# SECCIÓN 2: MIDDLEWARE Y VALIDACIÓN DE `initData` (Para Panel de Telegram)
# ==============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Considerar restringir esto en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelegramUserData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None

def _validate_telegram_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    """Valida el hash de initData para asegurar que la petición viene de Telegram."""
    if not settings.telegram_bot_token: return None
    try:
        parsed_data = parse_qs(init_data)
        if "hash" not in parsed_data: return None
        
        data_check_string_parts = []
        for key, value in sorted(parsed_data.items()):
            if key != "hash":
                data_check_string_parts.append(f"{key}={value[0]}")
        data_check_string = "\n".join(data_check_string_parts)
        
        secret_key = hmac.new("WebAppData".encode(), settings.telegram_bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == parsed_data["hash"][0]:
            return json.loads(parsed_data["user"][0])
        return None
    except Exception:
        return None

async def get_validated_user_id(initData: str = Form(...)) -> int:
    """Dependencia de FastAPI para validar initData y devolver el user_id."""
    user_data = _validate_telegram_init_data(initData)
    if not user_data:
        raise HTTPException(status_code=403, detail="Datos de inicialización inválidos o ausentes.")
    return int(user_data["id"])

# ==============================================================================
# SECCIÓN 3: AUTENTICACIÓN PARA WEB APP (FLUJO DE CÓDIGO Y JWT)
# ==============================================================================

verification_codes: Dict[str, Dict[str, Any]] = {}

class AuthRequestCode(BaseModel):
    telegram_id: int

class AuthVerifyCode(BaseModel):
    telegram_id: int
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.post("/api/auth/request-code", summary="Solicitar código de verificación")
async def request_verification_code(request_data: AuthRequestCode):
    telegram_id = request_data.telegram_id
    logger.info(f"Solicitud de código de verificación para el usuario de Telegram: {telegram_id}")

    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, telegram_id)
        if not account:
            raise HTTPException(status_code=404, detail="El ID de Telegram proporcionado no se encuentra en nuestro sistema.")

    code = str(random.randint(100000, 999999))
    expiration_time = datetime.utcnow() + timedelta(minutes=10)
    verification_codes[str(telegram_id)] = {"code": code, "exp": expiration_time}

    logger.info(f"Código de verificación generado para {telegram_id}: {code}")

    try:
        message_text = (
            f"Hola, estás intentando iniciar sesión en la aplicación web de Kognito AI.\n\n"
            f"Tu código de verificación es: <b>{code}</b>\n\n"
            f"Este código expirará en 10 minutos. Si no has solicitado este código, puedes ignorar este mensaje."
        )
        await bot_manager.bot.send_message(chat_id=telegram_id, text=message_text, parse_mode='HTML')
        logger.info(f"Código de verificación enviado exitosamente a {telegram_id}.")
        return {"message": "Código de verificación enviado exitosamente a tu chat de Telegram."}
    except Exception as e:
        logger.error(f"Error al enviar el código de verificación por Telegram a {telegram_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo enviar el código de verificación.")

@app.post("/api/auth/verify-code", response_model=TokenResponse, summary="Verificar código y obtener token JWT")
async def verify_code_and_get_token(request_data: AuthVerifyCode):
    telegram_id_str = str(request_data.telegram_id)
    code = request_data.code
    logger.info(f"Intento de verificación de código para Telegram ID: {telegram_id_str}")

    stored_code_data = verification_codes.get(telegram_id_str)
    if not stored_code_data or stored_code_data["code"] != code:
        raise HTTPException(status_code=400, detail="Código de verificación incorrecto.")
    if datetime.utcnow() > stored_code_data["exp"]:
        raise HTTPException(status_code=400, detail="El código de verificación ha expirado.")

    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, int(telegram_id_str))
        if not account:
            raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta asociada a este ID de Telegram.")
        account_id = str(account.id)

    del verification_codes[telegram_id_str]

    payload = {
        "sub": account_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_expiry_days)
    }
    access_token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    logger.info(f"Token JWT emitido exitosamente para la cuenta {account_id}")
    return TokenResponse(access_token=access_token)

# ==============================================================================
# SECCIÓN 4: API PRINCIPAL DEL CHAT
# ==============================================================================

class ChatRequest(BaseModel):
    account_id: str
    telegram_id: int
    user_message: str
    image_base64: Optional[str] = None

class ChatResponse(BaseModel):
    response_text: str

@app.post("/api/chat", response_model=ChatResponse, summary="Procesar Mensaje de Chat")
async def handle_chat(request: ChatRequest) -> ChatResponse:
    logger.info(f"Petición recibida en /api/chat de la cuenta: {request.account_id}")
    try:
        # ¡CORREGIDO! La llamada ahora es limpia y coincide exactamente
        # con la nueva firma de la función en `core/agent.py`.
        final_response_text = await create_and_run_agent(
            account_id=request.account_id,
            telegram_id=request.telegram_id,
            user_message=request.user_message,
            image_base64=request.image_base64
        )
        
        logger.info(f"Agente generó respuesta para la cuenta {request.account_id}.")
        return ChatResponse(response_text=final_response_text)
        
    except Exception as e:
        logger.error(f"❌ Error al procesar la petición de la cuenta {request.account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ocurrió un error interno al procesar tu solicitud.")
# ==============================================================================
# SECCIÓN 5: API PARA EL PANEL DE CONTROL DE TELEGRAM (Protegida por initData)
# ==============================================================================

@app.get("/", include_in_schema=False)
async def serve_telegram_panel():
    panel_path = os.path.join("telegram_panel", "index.html")
    if not os.path.exists(panel_path):
        raise HTTPException(status_code=404, detail="Panel de control no encontrado.")
    return FileResponse(panel_path)

app.mount("/static", StaticFiles(directory="telegram_panel"), name="static")

@app.post("/api/get-system-prompt")
async def get_system_prompt(user_id: int = Depends(get_validated_user_id)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account:
            # ¡CORREGIDO! Manejar el caso de que la cuenta no exista.
            return {"prompt": settings.default_system_prompt, "is_custom": False}
        
        prompt = account.profile.system_prompt if hasattr(account, "profile") and account.profile else settings.default_system_prompt
        is_custom = hasattr(account, "profile") and account.profile and account.profile.system_prompt is not None
        
        return {"prompt": prompt, "is_custom": is_custom}

@app.post("/api/save-system-prompt")
async def save_system_prompt(user_id: int = Depends(get_validated_user_id), system_prompt: str = Form("")):
    async with DBSession(SessionLocal) as db:
        # ¡CORREGIDO! get_or_create_account necesita el `first_name` que ahora no tenemos,
        # así que primero buscamos la cuenta. Si no existe, no podemos continuar.
        account = await get_account_by_telegram_id(db, user_id)
        if not account:
            raise HTTPException(status_code=404, detail="No se pudo encontrar la cuenta para guardar el prompt.")
        
        if not hasattr(account, "profile") or not account.profile:
            account.profile = Perfil()
        
        account.profile.system_prompt = system_prompt.strip() if system_prompt.strip() else None
        await db.commit()
        return {"message": "Prompt del sistema actualizado."}

@app.post("/api/upload-document")
async def upload_document_endpoint(user_id: int = Depends(get_validated_user_id), files: List[UploadFile] = File(...), topic: str = Form(...)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        account_id = str(account.id)
        
        processed_files = 0
        for file in files:
            try:
                content_bytes = await file.read()
                extracted_text, metadata = extract_text_and_metadata_from_document(file.filename, content_bytes)
                if not extracted_text:
                    logger.warning(f"No se pudo extraer texto del archivo '{file.filename}'. Omitiendo.")
                    continue
                metadata.update({"file_name": file.filename, "topic": topic})
                await process_document_for_rag(account_id=account_id, file_name=file.filename, extracted_text=extracted_text, metadata=metadata)
                processed_files += 1
            except Exception as e:
                logger.error(f"Fallo al procesar el archivo {file.filename} para la cuenta {account_id}: {e}", exc_info=True)
        
        if processed_files == 0 and files:
            raise HTTPException(status_code=500, detail="No se pudo procesar ninguno de los archivos.")
        return {"message": f"{processed_files}/{len(files)} archivo(s) procesado(s) y añadido(s) a tu base de conocimiento."}

@app.post("/api/list-documents")
async def list_documents_endpoint(user_id: int = Depends(get_validated_user_id)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: return []
        return await list_user_documents(str(account.id))

@app.post("/api/delete-document")
async def delete_document_endpoint(user_id: int = Depends(get_validated_user_id), file_name: str = Form(...)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        success = await delete_document_chunks(str(account.id), file_name)
        if not success: raise HTTPException(status_code=404, detail="Documento no encontrado o ya eliminado.")
        return {"message": f"El documento '{file_name}' ha sido eliminado."}

# ¡CORREGIDO! El endpoint ahora acepta un `search_term` opcional.
@app.post("/api/list-notes")
async def list_notes_endpoint(user_id: int = Depends(get_validated_user_id), search_term: Optional[str] = Form(None)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: return []
        # Pasamos el search_term a la función de lógica de negocio.
        notes = await get_notes(str(account.id), search_term)
        return notes

@app.post("/api/add-note")
async def add_note_endpoint(user_id: int = Depends(get_validated_user_id), title: Optional[str] = Form(None), content: str = Form(...), category: Optional[str] = Form(None)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        await add_note(str(account.id), content, title, category)
        return {"message": "Nota añadida exitosamente."}

@app.post("/api/update-note")
async def update_note_endpoint(user_id: int = Depends(get_validated_user_id), note_id: int = Form(...), content: str = Form(...), title: Optional[str] = Form(None), category: Optional[str] = Form(None)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        await update_note(str(account.id), note_id, content, title, category)
        return {"message": "Nota actualizada exitosamente."}

@app.post("/api/delete-note")
async def delete_note_endpoint(user_id: int = Depends(get_validated_user_id), note_id: int = Form(...)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        await delete_note(str(account.id), note_id)
        return {"message": "Nota eliminada exitosamente."}

# ¡CORREGIDO! Se llama a la nueva función `get_events_as_dicts`.
@app.post("/api/list-events")
async def list_events_endpoint(user_id: int = Depends(get_validated_user_id)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: return []
        return await get_events_as_dicts(str(account.id))

# ¡CORREGIDO! Se eliminó el parámetro innecesario.
@app.post("/api/add-event")
async def add_event_endpoint(user_id: int = Depends(get_validated_user_id), description: str = Form(...), event_datetime: str = Form(...)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        _, message = await schedule_event(
            account_id=str(account.id), 
            telegram_id=user_id,
            description=description, 
            natural_language_datetime=event_datetime
        )
        return {"message": message}

@app.post("/api/cancel-event")
async def cancel_event_endpoint(user_id: int = Depends(get_validated_user_id), event_id: int = Form(...)):
    async with DBSession(SessionLocal) as db:
        account = await get_account_by_telegram_id(db, user_id)
        if not account: raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        success, message = await cancel_event(account_id=str(account.id), event_id=event_id)
        
        # Es una buena práctica verificar si la cancelación fue exitosa.
        if not success:
            raise HTTPException(status_code=404, detail=message) # Devuelve el mensaje de error del manager.
        return {"message": message}

# ==============================================================================
# SECCIÓN 6: Bloque de Ejecución para Desarrollo Local
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor API en modo de desarrollo local (host 0.0.0.0, port 8000)...")
    # El puerto 8000 es el interno de Docker. docker-compose lo mapea al que definimos (ej. 8080).
    uvicorn.run("run_api:app", host="0.0.0.0", port=8000, reload=True)