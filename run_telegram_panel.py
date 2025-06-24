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

# --- Importaciones de la lógica del Bot ---
from core.memory_manager import process_document_for_rag, list_user_documents, delete_document_chunks
from core.agenda_manager import cancel_event
# ===== NUEVAS IMPORTACIONES PARA NOTAS =====
from core.notes_manager import add_note, update_note, delete_note

from utils.document_parser import extract_text_and_metadata_from_document
from core.config import settings
from utils.db_session import DBSession
from core.database import SessionLocal, Account, PlatformIdentity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from typing import Tuple, Dict, Any
from datetime import datetime
from core.notes_manager import add_note, update_note, delete_note, get_notes
from core.agenda_manager import schedule_event, get_events_as_dicts, cancel_event
from utils.db_session import DBSession

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

# --- Endpoints de la API ---

@app.get("/api/get-system-prompt")
async def get_system_prompt_endpoint(initData: str = Query(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            return {"prompt": settings.default_system_prompt, "is_custom": False}
        account = await db.get(Account, identity.account_id)
        if account and account.custom_system_prompt:
            return {"prompt": account.custom_system_prompt, "is_custom": True}
        return {"prompt": settings.default_system_prompt, "is_custom": False}

@app.post("/api/save-system-prompt")
async def save_system_prompt_endpoint(system_prompt: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        account = await db.get(Account, identity.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        account.custom_system_prompt = system_prompt.strip() or None
        await db.commit()
    return {"message": "Prompt guardado correctamente."}

@app.post("/api/upload-document")
async def upload_document_endpoint(files: List[UploadFile] = File(...), topic: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async def process_file(file: UploadFile, topic: str, user_id: int):
        file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                content = await file.read()
                tmp.write(content)
                file_path = tmp.name
            text, metadata = extract_text_and_metadata_from_document(file_path, file.filename)
            if not text or not text.strip(): return 0
            metadata.update({"file_name": file.filename, "topic": topic})
            async with DBSession(SessionLocal) as db:
                identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user_id)))
                identity = identity_result.scalars().first()
                if not identity:
                    return 0
                return await process_document_for_rag(account_id=str(identity.account_id), file_name=file.filename, extracted_text=text, metadata=metadata)
        finally:
            if file_path and os.path.exists(file_path): os.remove(file_path)
    results = await asyncio.gather(*(process_file(f, topic, user.id) for f in files))
    success_count = sum(1 for r in results if isinstance(r, int) and r > 0)
    if success_count > 0: return {"message": f"Se procesaron {success_count} de {len(files)} archivos."}
    raise HTTPException(status_code=500, detail="No se pudo procesar ningún archivo.")

@app.post("/api/list-documents")
async def list_documents_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            return []
        documents = await list_user_documents(account_id=str(identity.account_id))
        return documents

@app.post("/api/delete-document")
async def delete_document_endpoint(file_name: str = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        deleted_count = await delete_document_chunks(account_id=str(identity.account_id), file_name=file_name)
        if deleted_count > 0: return {"message": f"Documento '{file_name}' eliminado."}
        raise HTTPException(status_code=404, detail=f"No se encontró el documento '{file_name}'.")

@app.post("/api/add-event")
async def add_event_endpoint(initData: str = Form(...), description: str = Form(...), event_datetime: str = Form(...), reminder_offset_minutes: int = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        success, message, _ = await schedule_event(account_id=str(identity.account_id), description=description, natural_language_datetime=event_datetime)
        if success: return {"message": message}
        raise HTTPException(status_code=400, detail=message)

@app.post("/api/list-events")
async def list_events_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            return []
        events = await get_events_as_dicts(account_id=str(identity.account_id))
        return events

@app.post("/api/cancel-event")
async def cancel_event_endpoint(event_id: int = Form(...), initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        success, message = await cancel_event(account_id=str(identity.account_id), event_id=event_id)
        if success: return {"message": message}
        raise HTTPException(status_code=404, detail=message)

# ===== ENDPOINTS PARA EL GESTOR DE NOTAS =====
@app.post("/api/list-notes")
async def list_notes_endpoint(initData: str = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            return []
        notes = await get_notes(account_id=str(identity.account_id))
        return notes

@app.post("/api/add-note")
async def add_note_endpoint(initData: str = Form(...), title: Optional[str] = Form(None), content: str = Form(...), category: Optional[str] = Form(None)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        message = await add_note(account_id=str(identity.account_id), content=content, title=title or "", category=category or "")
        return {"message": message}

@app.post("/api/update-note")
async def update_note_endpoint(initData: str = Form(...), note_id: int = Form(...), title: Optional[str] = Form(None), content: Optional[str] = Form(None), category: Optional[str] = Form(None)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        message = await update_note(account_id=str(identity.account_id), note_id=note_id, new_content=content, new_title=title, new_category=category)
        if "actualizada" in message: return {"message": message}
        raise HTTPException(status_code=400, detail=message)

@app.post("/api/delete-note")
async def delete_note_endpoint(initData: str = Form(...), note_id: int = Form(...)):
    user = await validate_telegram_data(initData)
    async with DBSession(SessionLocal) as db:
        identity_result = await db.execute(select(PlatformIdentity).where(PlatformIdentity.platform == 'telegram', PlatformIdentity.platform_user_id == str(user.id)))
        identity = identity_result.scalars().first()
        if not identity:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        message = await delete_note(account_id=str(identity.account_id), note_id=note_id)
        if "eliminada" in message: return {"message": message}
        raise HTTPException(status_code=404, detail=message)

# --- Servir Archivos ---
app.mount("/static", StaticFiles(directory="webapp"), name="static")
@app.get("/", response_class=HTMLResponse)
async def read_index():
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    return FileResponse(os.path.join("webapp", "index.html"), headers=headers)

if __name__ == "__main__":
    uvicorn.run("run_telegram_panel:app", host="0.0.0.0", port=8000, reload=True)
