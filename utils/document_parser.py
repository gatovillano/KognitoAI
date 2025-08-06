# utils/document_parser.py

"""
Módulo de Utilidad para el Parseo de Documentos.
"""

import logging
from io import BytesIO
from typing import Tuple, Dict, Any

# Librerías específicas para cada tipo de archivo
import fitz  # PyMuPDF
import docx

logger = logging.getLogger(__name__)


def extract_text_and_metadata_from_document(file_name: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae texto plano y metadatos básicos de un archivo en formato binario.
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
            logger.info(f"Texto extraído de PDF exitosamente. Longitud: {len(text)} caracteres.")

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
