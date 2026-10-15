import io
import pytest
import fitz
from PIL import Image, ImageDraw, ImageFont

from utils.document_parser import extract_text_and_metadata_from_document
from utils.ocr_service import is_local_ocr_available, ocr_image_bytes, ocr_pdf_bytes


def create_test_image(text: str) -> bytes:
    """Crea una imagen PNG sintética con texto impreso."""
    img = Image.new("RGB", (700, 150), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("api/fonts/NotoSans-Regular.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    d.text((25, 45), text, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_scanned_pdf(text: str) -> bytes:
    """Crea un PDF que contiene únicamente una imagen rasterizada (sin capa vectorial de texto)."""
    img_bytes = create_test_image(text)
    doc = fitz.open()
    page = doc.new_page(width=700, height=150)
    page.insert_image(page.rect, stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_digital_pdf(text: str) -> bytes:
    """Crea un PDF digital nativo con texto seleccionable."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=300)
    rect = fitz.Rect(50, 50, 550, 250)
    page.insert_textbox(rect, text, fontsize=14)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_ocr_availability():
    """Verifica que el motor RapidOCR está disponible."""
    assert is_local_ocr_available() is True


@pytest.mark.asyncio
async def test_ocr_image_extraction():
    """Verifica la extracción directa de OCR en imagen."""
    test_phrase = "Factura B-00123 Importe 9500"
    img_bytes = create_test_image(test_phrase)
    
    text, conf = await ocr_image_bytes(img_bytes)
    assert len(text.strip()) > 0
    assert "00123" in text or "Factura" in text or "9500" in text
    assert conf > 0.5


@pytest.mark.asyncio
async def test_scanned_pdf_parser_uses_local_ocr():
    """Verifica que un PDF escaneado (sin texto) es procesado por el OCR local."""
    test_phrase = "Certificado Medico Doctor Gomez"
    scanned_pdf_bytes = create_scanned_pdf(test_phrase)
    
    extracted_text, metadata = await extract_text_and_metadata_from_document(
        "receta_escaneada.pdf",
        scanned_pdf_bytes
    )
    
    assert metadata["file_type"] == "pdf"
    assert metadata.get("extraction_method") == "local_ocr_rapidocr"
    assert "ocr_stats" in metadata
    assert len(extracted_text.strip()) > 0
    assert "Gomez" in extracted_text or "Certificado" in extracted_text or "Medico" in extracted_text


@pytest.mark.asyncio
async def test_digital_pdf_bypasses_ocr():
    """Verifica que un PDF con texto nativo suficiente no activa el OCR innecesariamente."""
    long_text = "Este es un documento PDF digital nativo con suficiente longitud para superar el umbral de escaneo de cincuenta caracteres."
    digital_pdf_bytes = create_digital_pdf(long_text)
    
    extracted_text, metadata = await extract_text_and_metadata_from_document(
        "documento_digital.pdf",
        digital_pdf_bytes
    )
    
    assert metadata["file_type"] == "pdf"
    assert metadata.get("extraction_method") == "native_pdf_text"
    assert "cincuenta caracteres" in extracted_text
