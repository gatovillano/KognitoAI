import logging
import os
import tempfile
import json
import hmac
import hashlib
import time
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import unquote, parse_qs

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# --- Importaciones para comunicación con API ---
import httpx
from core.config import settings
from fastapi import HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Configuración Inicial ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = FastAPI()

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class TelegramUserData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

async def validate_telegram_data(init_data: str) -> TelegramUserData:
    if not init_data: raise HTTPException(status_code=400, detail="initData no fue proporcionado.")
    try:
        params = {k: v[0] for k, v in parse_qs(unquote(init_data)).items()}
        hash_received = params.pop('hash', None)
        if not hash_received: raise HTTPException(status_code=400, detail="El initData no contiene un hash.")
        data_check_string = "\n".join(sorted([f"{k}={v}" for k, v in params.items()]))
        if settings.telegram_bot_token:
            secret_key = hmac.new("WebAppData".encode(), settings.telegram_bot_token.encode(), hashlib.sha256).digest()
        else:
            raise HTTPException(status_code=500, detail="Token de bot de Telegram no configurado.")
        hash_calculated = hmac.new(key=secret_key, msg=data_check_string.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(hash_calculated, hash_received): raise HTTPException(status_code=403, detail="Firma de datos inválida.")
        user_data_str = params.get('user')
        if not user_data_str: raise HTTPException(status_code=400, detail="Datos de usuario no encontrados.")
        return TelegramUserData(**json.loads(user_data_str))
    except Exception as e:
        logger.error(f"Error crítico durante la validación de initData: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno durante la validación.")

async def get_jwt_token(user: TelegramUserData) -> str:
    """Obtiene un token JWT para el usuario de Telegram mediante la API de autenticación."""
    telegram_login_url = f"{settings.api_server_url}/api/auth/telegram/callback"
    auth_date = int(time.time())
    hash_value = calculate_telegram_login_hash(user, settings.telegram_bot_token, auth_date)
    telegram_login_payload = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": getattr(user, "last_name", None),
        "username": getattr(user, "username", None),
        "photo_url": getattr(user, "photo_url", None),
        "auth_date": auth_date,
        "hash": hash_value
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(telegram_login_url, json=telegram_login_payload, timeout=10)
            resp.raise_for_status()
            token_data = resp.json()
            return token_data.get("access_token")
    except Exception as e:
        logger.error(f"No se pudo obtener el token JWT para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo autenticar tu sesión. Intenta de nuevo más tarde.")

def calculate_telegram_login_hash(user, bot_token, auth_date):
    import hashlib
    import hmac
    data_check_arr = [
        f"auth_date={auth_date}",
        f"first_name={user.first_name}",
        f"id={user.id}"
    ]
    if getattr(user, "last_name", None):
        data_check_arr.append(f"last_name={user.last_name}")
    if getattr(user, "username", None):
        data_check_arr.append(f"username={user.username}")
    if getattr(user, "photo_url", None):
        data_check_arr.append(f"photo_url={user.photo_url}")
    data_check_arr.sort()
    data_check_string = '\n'.join(data_check_arr)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

# --- Endpoints de la API ---

@app.get("/api/get-system-prompt")
async def get_system_prompt_endpoint(initData: str = Query(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/user-profile"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            user_data = response.json()
            if "custom_system_prompt" in user_data and user_data["custom_system_prompt"]:
                return {"prompt": user_data["custom_system_prompt"], "is_custom": True}
            return {"prompt": settings.default_system_prompt, "is_custom": False}
    except Exception as e:
        logger.error(f"Error al obtener el system prompt para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener el perfil de usuario.")

@app.post("/api/save-system-prompt")
async def save_system_prompt_endpoint(system_prompt: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/user-profile"
    payload = {"custom_system_prompt": system_prompt.strip() or None}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return {"message": "Prompt guardado correctamente."}
    except Exception as e:
        logger.error(f"Error al guardar el system prompt para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al guardar el perfil de usuario.")

@app.post("/api/upload-document")
async def upload_document_endpoint(files: List[UploadFile] = File(...), topic: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/rag/upload-document"
    
    async def process_file(file: UploadFile, topic: str):
        try:
            content = await file.read()
            form_data = {
                "topic": topic,
                "file": (file.filename, content, file.content_type)
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, files={"file": (file.filename, content, file.content_type)}, data={"topic": topic}, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json().get("message", "Archivo procesado.")
        except Exception as e:
            logger.error(f"Error al procesar archivo {file.filename}: {e}", exc_info=True)
            return 0
    
    results = await asyncio.gather(*(process_file(f, topic) for f in files))
    success_count = sum(1 for r in results if r != 0)
    if success_count > 0: return {"message": f"Se procesaron {success_count} de {len(files)} archivos."}
    raise HTTPException(status_code=500, detail="No se pudo procesar ningún archivo.")

@app.post("/api/list-documents")
async def list_documents_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/rag/documents"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al listar documentos para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener la lista de documentos.")

@app.post("/api/delete-document")
async def delete_document_endpoint(file_name: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/rag/delete-document"
    payload = {"file_name": file_name}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al eliminar documento para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al eliminar el documento '{file_name}'.")

@app.post("/api/add-event")
async def add_event_endpoint(initData: str = Form(...), description: str = Form(...), event_datetime: str = Form(...), reminder_offset_minutes: int = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/agenda/add-event"
    payload = {
        "description": description,
        "event_datetime": event_datetime,
        "reminder_offset_minutes": reminder_offset_minutes
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al agregar evento para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al agregar el evento.")

@app.post("/api/list-events")
async def list_events_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/agenda/events"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al listar eventos para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener la lista de eventos.")

@app.post("/api/cancel-event")
async def cancel_event_endpoint(event_id: int = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/agenda/cancel-event"
    payload = {"event_id": event_id}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al cancelar evento para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al cancelar el evento.")

# ===== ENDPOINTS PARA EL GESTOR DE NOTAS =====
@app.post("/api/list-notes")
async def list_notes_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/notes"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al listar notas para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al obtener la lista de notas.")

@app.post("/api/add-note")
async def add_note_endpoint(initData: str = Form(...), title: Optional[str] = Form(None), content: str = Form(...), category: Optional[str] = Form(None)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/notes/add"
    payload = {
        "title": title or "",
        "content": content,
        "category": category or ""
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al agregar nota para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al agregar la nota.")

@app.post("/api/update-note")
async def update_note_endpoint(initData: str = Form(...), note_id: int = Form(...), title: Optional[str] = Form(None), content: Optional[str] = Form(None), category: Optional[str] = Form(None)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/notes/update/{note_id}"
    payload = {
        "title": title,
        "content": content,
        "category": category
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al actualizar nota para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al actualizar la nota.")

@app.post("/api/delete-note")
async def delete_note_endpoint(initData: str = Form(...), note_id: int = Form(...)):
    user = await validate_telegram_data(initData)
    jwt_token = await get_jwt_token(user)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    api_url = f"{settings.api_server_url}/api/notes/delete/{note_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error al eliminar nota para el usuario {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al eliminar la nota.")

# --- Servir Archivos ---
app.mount("/static", StaticFiles(directory="telegram_panel"), name="static")
@app.get("/", response_class=HTMLResponse)
async def read_index():
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    return FileResponse(os.path.join("telegram_panel", "index.html"), headers=headers)

if __name__ == "__main__":
    uvicorn.run("run_telegram_panel:app", host="0.0.0.0", port=8000, reload=True)
