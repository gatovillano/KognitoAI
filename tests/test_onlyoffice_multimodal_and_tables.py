# tests/test_onlyoffice_multimodal_and_tables.py

import io
import uuid
import pytest
from types import SimpleNamespace
from PIL import Image
import docx
from pptx import Presentation
from pptx.util import Inches
import openpyxl
from openpyxl.drawing.image import Image as XLImage

from core.agent import is_multimodal_model
from skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool import (
    ReadOnlyOfficeDocumentTool,
)
from skills.onlyoffice_skill.scripts.onlyoffice_reader_extractor import (
    extract_onlyoffice_document_content,
    optimize_and_encode_image,
)


def _create_sample_image(color: str = "blue", size: tuple = (100, 100)) -> bytes:
    """Crea una imagen PNG válida en memoria."""
    im = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _create_sample_docx_with_table_and_image() -> bytes:
    """Crea un documento DOCX con párrafos, una tabla y una imagen."""
    doc = docx.Document()
    doc.add_paragraph("Título del Documento DOCX")

    # Agregar tabla
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Columna A"
    table.cell(0, 1).text = "Columna B"
    table.cell(1, 0).text = "Dato 1"
    table.cell(1, 1).text = "Dato 2"

    # Agregar imagen
    img_bytes = _create_sample_image(color="red", size=(120, 120))
    doc.add_paragraph("Párrafo previo a la imagen")
    doc.add_picture(io.BytesIO(img_bytes))
    doc.add_paragraph("Párrafo posterior a la imagen")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _create_sample_pptx_with_table_and_image() -> bytes:
    """Crea una presentación PPTX con una tabla y una imagen."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Tabla
    table_shape = slide.shapes.add_table(2, 2, Inches(1), Inches(1), Inches(4), Inches(2))
    table = table_shape.table
    table.cell(0, 0).text = "Cabecera 1"
    table.cell(0, 1).text = "Cabecera 2"
    table.cell(1, 0).text = "Valor 1"
    table.cell(1, 1).text = "Valor 2"

    # Imagen
    img_bytes = _create_sample_image(color="green", size=(150, 150))
    slide.shapes.add_picture(io.BytesIO(img_bytes), Inches(1), Inches(3.5), Inches(2), Inches(2))

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _create_sample_xlsx_with_table_and_image() -> bytes:
    """Crea un archivo XLSX con datos tabulares y una imagen."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws["A1"] = "Producto"
    ws["B1"] = "Precio"
    ws["A2"] = "Laptop"
    ws["B2"] = 1200
    ws["A3"] = "Mouse"
    ws["B3"] = 25

    img_bytes = _create_sample_image(color="yellow", size=(100, 100))
    xl_img = XLImage(io.BytesIO(img_bytes))
    ws.add_image(xl_img, "D1")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class _FakeDBResult:
    def __init__(self, item):
        self._item = item

    def scalar_one_or_none(self):
        return self._item


class _FakeSession:
    def __init__(self, doc):
        self._doc = doc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute(self, stmt):
        return _FakeDBResult(self._doc)

    async def get(self, model, ident):
        return None


def test_is_multimodal_model_detection():
    """Verifica que el detector de modelos multimodales identifique correctamente los modelos."""
    assert is_multimodal_model("gemini-2.0-flash") is True
    assert is_multimodal_model("gemini-1.5-pro") is True
    assert is_multimodal_model("gpt-4o") is True
    assert is_multimodal_model("gpt-4o-mini") is True
    assert is_multimodal_model("claude-3-5-sonnet") is True
    assert is_multimodal_model("claude-3-7-sonnet") is True
    assert is_multimodal_model("qwen-vl-max") is True
    assert is_multimodal_model("qwen2.5-vl-72b-instruct") is True

    # No multimodales
    assert is_multimodal_model("llama-3-8b-instruct") is False
    assert is_multimodal_model("deepseek-coder-v2") is False
    assert is_multimodal_model("mistral-7b-instruct") is False
    assert is_multimodal_model(None) is False


def test_optimize_and_encode_image():
    """Verifica que las imágenes válidas se redimensionen y codifiquen a JPEG Base64."""
    raw_img = _create_sample_image(color="purple", size=(2000, 1000))
    res = optimize_and_encode_image(raw_img, max_dimension=800)
    assert res is not None
    assert res["type"] == "image_url"
    assert res["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert res["width"] == 800
    assert res["height"] == 400

    # Imagen muy pequeña (filtro de icono decorativo)
    tiny_img = _create_sample_image(color="black", size=(10, 10))
    assert optimize_and_encode_image(tiny_img, min_dimension=30) is None


@pytest.mark.anyio
async def test_extract_docx_multimodal_returns_tables_and_image_blocks():
    """Verifica que en modo multimodal un DOCX extraiga tablas en Markdown e imágenes en bloques."""
    docx_bytes = _create_sample_docx_with_table_and_image()
    text, images = await extract_onlyoffice_document_content(
        filename="documento.docx",
        file_bytes=docx_bytes,
        is_multimodal=True,
    )

    # Verificar tabla Markdown
    assert "| Columna A | Columna B |" in text
    assert "| --- | --- |" in text
    assert "| Dato 1 | Dato 2 |" in text

    # Verificar que contiene párrafos
    assert "Título del Documento DOCX" in text
    assert "Párrafo previo a la imagen" in text
    assert "Párrafo posterior a la imagen" in text

    # Verificar bloques de imagen adjunta
    assert len(images) >= 1
    assert images[0]["type"] == "image_url"
    assert images[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "Ver imagen adjunta" in text


@pytest.mark.anyio
async def test_extract_docx_non_multimodal_applies_ocr(monkeypatch):
    """Verifica que en modo NO multimodal ('sino ocr') se ejecute OCR sobre las imágenes del DOCX."""
    async def fake_ocr(img_bytes):
        return "TEXTO DETECTADO POR OCR EN DOCX", 0.95

    monkeypatch.setattr("skills.onlyoffice_skill.scripts.onlyoffice_reader_extractor.ocr_image_bytes", fake_ocr)

    docx_bytes = _create_sample_docx_with_table_and_image()
    text, images = await extract_onlyoffice_document_content(
        filename="documento.docx",
        file_bytes=docx_bytes,
        is_multimodal=False,
    )

    # No debe retornar bloques de imagen para no confundir a un modelo de texto
    assert len(images) == 0

    # El texto de OCR debe estar incrustado en el cuerpo del documento
    assert "Texto extraído por OCR" in text
    assert "TEXTO DETECTADO POR OCR EN DOCX" in text
    assert "| Columna A | Columna B |" in text


@pytest.mark.anyio
async def test_extract_pptx_with_tables_and_images():
    """Verifica que PPTX extraiga tablas en Markdown e imágenes en modo multimodal."""
    pptx_bytes = _create_sample_pptx_with_table_and_image()
    text, images = await extract_onlyoffice_document_content(
        filename="presentacion.pptx",
        file_bytes=pptx_bytes,
        is_multimodal=True,
    )

    assert "[Diapositiva 1]" in text
    assert "| Cabecera 1 | Cabecera 2 |" in text
    assert "| --- | --- |" in text
    assert "| Valor 1 | Valor 2 |" in text
    assert len(images) >= 1
    assert images[0]["type"] == "image_url"


@pytest.mark.anyio
async def test_extract_xlsx_with_tables_and_images():
    """Verifica que XLSX extraiga hojas completas como tablas Markdown e imágenes."""
    xlsx_bytes = _create_sample_xlsx_with_table_and_image()
    text, images = await extract_onlyoffice_document_content(
        filename="cuentas.xlsx",
        file_bytes=xlsx_bytes,
        is_multimodal=True,
    )

    assert "[Hoja: Ventas]" in text
    assert "| Producto | Precio |" in text
    assert "| Laptop | 1200 |" in text
    assert "| Mouse | 25 |" in text
    assert len(images) >= 1


@pytest.mark.anyio
async def test_extract_pdf_multimodal_and_non_multimodal():
    """Verifica que PDF extraiga texto e imágenes en modo multimodal y aplique OCR en modo no multimodal."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Reporte Financiero PDF")

    im_bytes = _create_sample_image(color="cyan", size=(100, 100))
    page.insert_image(fitz.Rect(50, 100, 150, 200), stream=im_bytes)
    pdf_bytes = doc.write()

    # Multimodal
    text_mm, imgs_mm = await extract_onlyoffice_document_content(
        filename="reporte.pdf",
        file_bytes=pdf_bytes,
        is_multimodal=True,
    )
    assert "Reporte Financiero PDF" in text_mm
    assert len(imgs_mm) == 1
    assert imgs_mm[0]["type"] == "image_url"

    # No multimodal
    text_ocr, imgs_ocr = await extract_onlyoffice_document_content(
        filename="reporte.pdf",
        file_bytes=pdf_bytes,
        is_multimodal=False,
    )
    assert "Reporte Financiero PDF" in text_ocr
    assert len(imgs_ocr) == 0
    assert "Sin texto detectable por OCR" in text_ocr


@pytest.mark.anyio
async def test_read_onlyoffice_tool_multimodal_end_to_end(monkeypatch, tmp_path):
    """Prueba de integración end-to-end de ReadOnlyOfficeDocumentTool en modo multimodal."""
    docx_bytes = _create_sample_docx_with_table_and_image()
    file_path = tmp_path / "informe.docx"
    file_path.write_bytes(docx_bytes)

    doc_id = uuid.uuid4()
    account_id = uuid.uuid4()
    doc_record = SimpleNamespace(
        id=doc_id,
        account_id=account_id,
        filename="informe.docx",
        extension="docx",
        file_path="informe.docx",
    )

    tool = ReadOnlyOfficeDocumentTool(
        account_id=str(account_id),
        is_multimodal=True,
    )

    import skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool as rtool_mod
    monkeypatch.setattr(rtool_mod, "SessionLocal", lambda: _FakeSession(doc_record))
    monkeypatch.setattr(rtool_mod, "resolve_onlyoffice_file_path", lambda _: file_path)

    result = await tool._arun(document_id=str(doc_id))

    # Debe ser una lista de bloques: primero el texto, luego las imágenes
    assert isinstance(result, list)
    assert result[0]["type"] == "text"
    assert "--- CONTENIDO DE 'informe.docx' ---" in result[0]["text"]
    assert "| Columna A | Columna B |" in result[0]["text"]
    assert result[1]["type"] == "image_url"
    assert result[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.anyio
async def test_read_onlyoffice_tool_non_multimodal_end_to_end(monkeypatch, tmp_path):
    """Prueba de integración end-to-end de ReadOnlyOfficeDocumentTool en modo NO multimodal ('sino ocr')."""
    docx_bytes = _create_sample_docx_with_table_and_image()
    file_path = tmp_path / "informe.docx"
    file_path.write_bytes(docx_bytes)

    doc_id = uuid.uuid4()
    account_id = uuid.uuid4()
    doc_record = SimpleNamespace(
        id=doc_id,
        account_id=account_id,
        filename="informe.docx",
        extension="docx",
        file_path="informe.docx",
    )

    async def fake_ocr(img_bytes):
        return "Texto OCR verificado", 0.98

    monkeypatch.setattr("skills.onlyoffice_skill.scripts.onlyoffice_reader_extractor.ocr_image_bytes", fake_ocr)

    tool = ReadOnlyOfficeDocumentTool(
        account_id=str(account_id),
        is_multimodal=False,
    )

    import skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool as rtool_mod
    monkeypatch.setattr(rtool_mod, "SessionLocal", lambda: _FakeSession(doc_record))
    monkeypatch.setattr(rtool_mod, "resolve_onlyoffice_file_path", lambda _: file_path)

    result = await tool._arun(document_id=str(doc_id))

    # Debe ser un string plano con texto y el resultado de OCR
    assert isinstance(result, str)
    assert "--- CONTENIDO DE 'informe.docx' ---" in result
    assert "| Columna A | Columna B |" in result
    assert "Texto OCR verificado" in result
