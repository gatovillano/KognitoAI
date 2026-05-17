# utils/document_parser.py

"""
Módulo de Utilidad para el Parseo de Documentos.
"""

import logging
import base64
from io import BytesIO
from typing import Tuple, Dict, Any, List

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
            logger.info("Detectado archivo DOCX, usando python-docx de forma secuencial...")
            file_stream = BytesIO(file_bytes)
            document = docx.Document(file_stream)
            
            # Recorrer todos los elementos del cuerpo preservando el orden secuencial de párrafos y tablas
            body_elements = []
            for element in document.element.body:
                tag = element.tag.split('}')[-1]
                if tag == 'p':
                    p = docx.text.paragraph.Paragraph(element, document)
                    if p.text.strip():
                        body_elements.append(p.text)
                elif tag == 'tbl':
                    table = docx.table.Table(element, document)
                    table_lines = []
                    for row in table.rows:
                        row_cells = []
                        for cell in row.cells:
                            # Extraer todo el texto de los párrafos dentro de la celda
                            cell_txt = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
                            row_cells.append(cell_txt)
                        table_lines.append("| " + " | ".join(row_cells) + " |")
                    
                    if table_lines:
                        # Añadir separador de cabecera si hay más de una fila
                        if len(table_lines) > 1:
                            num_cols = len(table.columns)
                            sep = "|" + "|".join("---" for _ in range(num_cols)) + "|"
                            table_lines.insert(1, sep)
                        body_elements.append("\n" + "\n".join(table_lines) + "\n")
            
            text = "\n".join(body_elements)
            logger.info(f"Texto y tablas extraídos de DOCX secuencialmente. Longitud: {len(text)} caracteres.")

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

        prompt = """Eres un experto en OCR y análisis de documentos. 
Extrae TODO el texto de esta imagen de forma precisa. 
Si es una factura, recibo o apunte, mantén la estructura lo mejor posible.
Si hay escritura a mano, transcríbela con cuidado.
Responde ÚNICAMENTE con el texto extraído, sin comentarios adicionales."""

        async def _ocr_image_bytes(image_data: bytes) -> str:
            base64_image = base64.b64encode(image_data).decode('utf-8')
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ]
            )

            response = await vision_llm.ainvoke([message])
            extracted_text = response.content if hasattr(response, 'content') else str(response)
            return extracted_text.strip()

        if not is_pdf:
            return await _ocr_image_bytes(file_bytes)

        logger.info("Convirtiendo todas las páginas del PDF a imágenes para OCR...")
        extracted_pages: List[str] = []

        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_index, page in enumerate(doc):
                try:
                    pix = page.get_pixmap()
                    page_text = await _ocr_image_bytes(pix.tobytes("jpg"))
                    if page_text:
                        extracted_pages.append(page_text)
                    logger.info(
                        "OCR completado para página %s/%s del PDF.",
                        page_index + 1,
                        len(doc),
                    )
                except Exception as page_error:
                    logger.error(
                        "Error en OCR para página %s del PDF: %s",
                        page_index + 1,
                        page_error,
                        exc_info=True,
                    )

        return "\n\n".join(extracted_pages).strip()

    except Exception as e:
        logger.error(f"Error en OCR multimodal: {e}", exc_info=True)
        return ""
