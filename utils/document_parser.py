# utils/document_parser.py

"""
Módulo de Utilidad para el Parseo de Documentos.
"""

import logging
import base64
from io import BytesIO
from typing import Tuple, Dict, Any

# Librerías específicas para cada tipo de archivo
import fitz  # PyMuPDF
import docx
from langchain_core.messages import HumanMessage

from core.llm_manager import get_vision_llm

logger = logging.getLogger(__name__)


async def extract_text_and_metadata_from_document(file_name: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae texto plano y metadatos básicos de un archivo en formato binario.
    Si es una imagen o un PDF sin texto, utiliza un modelo de visión multimodal.
    """
    file_name_lower = file_name.lower()
    text = ""
    metadata = {"file_type": "unknown"}

    logger.info(f"Iniciando extracción de texto para el archivo: '{file_name}'")

    try:
        if file_name_lower.endswith(".pdf"):
            metadata["file_type"] = "pdf"
            logger.info("Detectado archivo PDF, usando PyMuPDF (fitz)...")
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)
            
            # Si el PDF no tiene texto (escaneado), intentar con visión
            if not text.strip() or len(text.strip()) < 50:
                logger.info("El PDF parece ser un escaneo (poco texto detectado). Intentando OCR con modelo de visión...")
                text = await _extract_text_from_image_multimodal(file_bytes, is_pdf=True)
            
            logger.info(f"Texto extraído de PDF exitosamente. Longitud: {len(text)} caracteres.")

        elif file_name_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            metadata["file_type"] = "image"
            logger.info(f"Detectada imagen '{file_name}', usando modelo de visión multimodal...")
            text = await _extract_text_from_image_multimodal(file_bytes)
            logger.info(f"Texto extraído de imagen exitosamente. Longitud: {len(text)} caracteres.")

        elif file_name_lower.endswith(".docx"):
            metadata["file_type"] = "docx"
            logger.info("Detectado archivo DOCX, usando python-docx...")
            file_stream = BytesIO(file_bytes)
            document = docx.Document(file_stream)
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            logger.info(f"Texto extraído de DOCX exitosamente. Longitud: {len(text)} caracteres.")

        elif file_name_lower.endswith((".txt", ".md")):
            file_type = "txt" if file_name_lower.endswith(".txt") else "markdown"
            metadata["file_type"] = file_type
            logger.info(f"Detectado archivo {file_type.upper()}, decodificando...")
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"Fallo al decodificar {file_type.upper()} como UTF-8, intentando con latin-1.")
                text = file_bytes.decode('latin-1', errors='replace')
            logger.info(f"Texto extraído de {file_type.upper()} exitosamente. Longitud: {len(text)} caracteres.")

        else:
            logger.warning(f"Tipo de archivo no soportado para extracción de texto: '{file_name}'")
            text = ""

    except Exception as e:
        logger.error(f"Error al extraer texto del archivo '{file_name}': {e}", exc_info=True)
        text = ""

    return text, metadata


async def _extract_text_from_image_multimodal(file_bytes: bytes, is_pdf: bool = False) -> str:
    """
    Utiliza el modelo de visión multimodal para extraer texto de una imagen o PDF escaneado.
    """
    try:
        vision_llm = get_vision_llm()
        if not vision_llm:
            logger.error("No hay modelo de visión disponible para OCR.")
            return ""

        # Si es PDF, necesitamos convertir la primera página a imagen para el OCR simple
        # O enviar el PDF si el modelo lo soporta (Mistral en OpenRouter suele preferir imágenes base64)
        image_data = file_bytes
        mime_type = "image/jpeg"
        
        if is_pdf:
            logger.info("Convirtiendo primera página de PDF a imagen para OCR...")
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                page = doc.load_page(0)
                pix = page.get_pixmap()
                image_data = pix.tobytes("jpg")
        
        base64_image = base64.b64encode(image_data).decode('utf-8')

        prompt = """Eres un experto en OCR y análisis de documentos. 
Extrae TODO el texto de esta imagen de forma precisa. 
Si es una factura, recibo o apunte, mantén la estructura lo mejor posible.
Si hay escritura a mano, transcríbela con cuidado.
Responde ÚNICAMENTE con el texto extraído, sin comentarios adicionales."""

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                },
            ]
        )

        response = await vision_llm.ainvoke([message])
        extracted_text = response.content if hasattr(response, 'content') else str(response)
        
        return extracted_text.strip()

    except Exception as e:
        logger.error(f"Error en OCR multimodal: {e}", exc_info=True)
        return ""
