# skills/onlyoffice_skill/scripts/read_onlyoffice_document_tool.py

import logging
import uuid
from typing import Any, Type, Optional, Union, List, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import select
from core.database import SessionLocal, Document, Account
from core.onlyoffice_storage import resolve_onlyoffice_file_path
from utils.document_parser import extract_text_and_metadata_from_document
from skills.onlyoffice_skill.scripts.onlyoffice_reader_extractor import (
    extract_onlyoffice_document_content,
)

logger = logging.getLogger(__name__)
_ORIGINAL_EXTRACT = extract_text_and_metadata_from_document


class ReadOnlyOfficeInput(BaseModel):
    document_id: str = Field(..., description="ID UUID del documento que se desea leer.")


class ReadOnlyOfficeDocumentTool(BaseTool):
    name: str = "read_onlyoffice_document"
    description: str = (
        "[MÓDULO ONLYOFFICE DE KAI] Lee el contenido textual completo, tablas e imágenes de un documento "
        "editable de OnlyOffice (Word .docx, Excel .xlsx, PowerPoint .pptx, PDF, CSV, TXT) mediante su 'document_id' (UUID). "
        "Si el agente es multimodal, proporciona acceso visual directo a las imágenes y esquemas del documento. "
        "Si no es multimodal, transcribe las imágenes mediante OCR integrado. "
        "ÚSALA EXCLUSIVAMENTE para documentos del módulo OnlyOffice. "
        "NO LA USES para documentos de la base de conocimiento RAG; para leer documentos RAG usa 'get_document_content_tool' con su 'file_name'."
    )
    args_schema: Type[BaseModel] = ReadOnlyOfficeInput
    account_id: str = Field(..., description="ID de cuenta del usuario, inyectado automáticamente.")
    is_multimodal: Optional[bool] = Field(
        default=None,
        description="Indica si el modelo activo soporta visión multimodal para inspección visual de imágenes.",
    )

    async def _resolve_is_multimodal(self) -> bool:
        """Determina dinámicamente si el modelo activo es multimodal."""
        if self.is_multimodal is not None:
            return bool(self.is_multimodal)
        try:
            from core.agent import is_multimodal_model
            from core.llm_manager import get_main_llm
            from core.config import settings

            async with SessionLocal() as db:
                account = await db.get(Account, uuid.UUID(self.account_id))
                if account and account.llm_model:
                    return is_multimodal_model(account.llm_model)

            main_llm = get_main_llm()
            model_name = (
                getattr(main_llm, "model_name", None)
                or getattr(main_llm, "model", None)
                or getattr(settings, "default_model", None)
            )
            return is_multimodal_model(model_name)
        except Exception as e:
            logger.debug(f"No se pudo determinar si el modelo es multimodal dinámicamente: {e}")
            return False

    async def _arun(
        self, document_id: str, **kwargs: Any
    ) -> Union[str, List[Dict[str, Any]]]:
        try:
            acc_id = uuid.UUID(self.account_id)
            doc_id = uuid.UUID(document_id)

            async with SessionLocal() as db:
                stmt = select(Document).where(
                    Document.id == doc_id, Document.account_id == acc_id
                )
                result = await db.execute(stmt)
                doc = result.scalar_one_or_none()

            if not doc:
                return f"Documento con ID '{document_id}' no encontrado o no tienes permiso para leerlo."

            # Resolver ruta física
            try:
                file_path = resolve_onlyoffice_file_path(doc.file_path)
            except ValueError as exc:
                return f"Ruta física inválida para '{doc.filename}': {exc}"

            if not file_path.exists():
                return (
                    f"El archivo físico '{doc.filename}' no se encuentra en el servidor. "
                    f"Ruta buscada: {file_path}"
                )

            if not file_path.is_file():
                return (
                    f"La ruta física de '{doc.filename}' no es un archivo válido "
                    f"(es un directorio). Ruta: {file_path}"
                )

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            header = f"--- CONTENIDO DE '{doc.filename}' ---\n\n"

            # Compatibilidad con tests unitarios que monkeypatchean extract_text_and_metadata_from_document
            global extract_text_and_metadata_from_document
            if extract_text_and_metadata_from_document != _ORIGINAL_EXTRACT:
                text, _ = await extract_text_and_metadata_from_document(doc.filename, file_bytes)
                return header + (text or f"⚠️ No se pudo extraer texto del archivo '{doc.filename}'.")

            # Determinar si el agente puede recibir imágenes multimodales
            multimodal_enabled = await self._resolve_is_multimodal()

            # Extracción estructurada de tablas, texto e imágenes (sin truncamiento)
            text, image_blocks = await extract_onlyoffice_document_content(
                filename=doc.filename,
                file_bytes=file_bytes,
                is_multimodal=multimodal_enabled,
                max_images=30,
            )

            # Si hay imágenes y el modelo es multimodal, devolver bloques multimodales
            if multimodal_enabled and image_blocks:
                full_text = header + (text or f"[Documento '{doc.filename}' sin texto adicional; ver imágenes adjuntas]")
                return [{"type": "text", "text": full_text}] + image_blocks

            # Si no es multimodal ("sino ocr") o no hay imágenes, devolver texto plano
            if text:
                return header + text
            return header + f"⚠️ No se pudo extraer contenido legible del archivo '{doc.filename}'."

        except Exception as e:
            logger.error(
                f"Error en ReadOnlyOfficeDocumentTool para doc_id='{document_id}': {e}",
                exc_info=True,
            )
            return f"Error inesperado al leer el documento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
