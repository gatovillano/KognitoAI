# utils/document_parser.py

"""
Módulo de Utilidad para el Parseo de Documentos.

Este módulo proporciona una función central (`extract_text_and_metadata_from_document`)
que toma un archivo en formato binario y extrae su contenido de texto plano.
Es capaz de manejar diferentes tipos de archivos, como PDF, DOCX y TXT.

Esta funcionalidad es el primer paso crucial en el pipeline de RAG (Retrieval-
Augmented Generation), ya que convierte documentos no estructurados en texto
que luego puede ser procesado, dividido en fragmentos (chunks) y convertido en
embeddings para su almacenamiento en la base de datos vectorial.

El módulo está diseñado para ser eficiente y manejar los archivos en memoria,
evitando escrituras innecesarias en disco.
"""

import logging
from io import BytesIO
from typing import Tuple, Dict, Any

# Librerías específicas para cada tipo de archivo
from pdfminer.high_level import extract_text as extract_text_from_pdf
import docx

logger = logging.getLogger(__name__)


def extract_text_and_metadata_from_document(file_name: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae texto plano y metadatos básicos de un archivo en formato binario.

    Detecta el tipo de archivo por su extensión y utiliza la librería
    adecuada para procesarlo.

    Args:
        file_name: El nombre original del archivo, incluyendo su extensión.
        file_bytes: El contenido del archivo como un objeto de bytes.

    Returns:
        Una tupla que contiene:
        - El texto extraído como una única cadena de texto.
        - Un diccionario con metadatos básicos (actualmente solo 'file_type').
    """
    file_name_lower = file_name.lower()
    file_stream = BytesIO(file_bytes)
    text = ""
    metadata = {"file_type": "unknown"}

    logger.info(f"Iniciando extracción de texto para el archivo: '{file_name}'")

    try:
        if file_name_lower.endswith(".pdf"):
            metadata["file_type"] = "pdf"
            logger.debug("Detectado archivo PDF, usando pdfminer...")
            # pdfminer es intensivo, por lo que puede tardar.
            text = extract_text_from_pdf(file_stream)
            logger.info(f"Texto extraído de PDF exitosamente. Longitud: {len(text)} caracteres.")

        elif file_name_lower.endswith(".docx"):
            metadata["file_type"] = "docx"
            logger.debug("Detectado archivo DOCX, usando python-docx...")
            document = docx.Document(file_stream)
            # Unir el texto de todos los párrafos del documento.
            paragraphs = [p.text for p in document.paragraphs]
            text = "\n".join(paragraphs)
            logger.info(f"Texto extraído de DOCX exitosamente. Longitud: {len(text)} caracteres.")

        elif file_name_lower.endswith(".txt"):
            metadata["file_type"] = "txt"
            logger.debug("Detectado archivo TXT, decodificando...")
            # Decodificar el archivo de texto, manejando posibles errores de codificación.
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning("Fallo al decodificar TXT como UTF-8, intentando con latin-1.")
                text = file_bytes.decode('latin-1', errors='replace')
            logger.info(f"Texto extraído de TXT exitosamente. Longitud: {len(text)} caracteres.")
            
        elif file_name_lower.endswith(".md"):
            metadata["file_type"] = "markdown"
            logger.debug("Detectado archivo Markdown, decodificando...")
            # Decodificar el archivo Markdown, manejando posibles errores de codificación.
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning("Fallo al decodificar MD como UTF-8, intentando con latin-1.")
                text = file_bytes.decode('latin-1', errors='replace')
            logger.info(f"Texto extraído de MD exitosamente. Longitud: {len(text)} caracteres.")

        else:
            logger.warning(f"Tipo de archivo no soportado para extracción de texto: '{file_name}'")
            # Devuelve una cadena vacía si el tipo de archivo no es soportado.
            text = ""

    except Exception as e:
        logger.error(f"Error al extraer texto del archivo '{file_name}': {e}", exc_info=True)
        # En caso de error, devuelve una cadena vacía para no detener el proceso.
        text = ""

    return text, metadata
