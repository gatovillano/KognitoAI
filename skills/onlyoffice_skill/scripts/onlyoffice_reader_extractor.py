# skills/onlyoffice_skill/scripts/onlyoffice_reader_extractor.py

"""
Extractor avanzado de contenido para documentos de OnlyOffice (DOCX, PPTX, XLSX, PDF, imágenes).
Soporta:
1. Tablas estructuradas en formato Markdown legible.
2. Imágenes integradas:
   - Modo multimodal (is_multimodal=True): comprime/optimiza imágenes y las devuelve
     como bloques de imagen compatibles con LangChain para inspección visual directa por el agente.
   - Modo no multimodal (is_multimodal=False o "sino ocr"): procesa cada imagen con OCR
     (RapidOCR / modelo de visión fallback) e inserta el texto extraído directamente en el documento.
"""

import io
import csv
import base64
import logging
from typing import Tuple, List, Dict, Any, Optional

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    docx = None
    DOCX_AVAILABLE = False

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    PPTX_AVAILABLE = True
except ImportError:
    Presentation = None
    MSO_SHAPE_TYPE = None
    PPTX_AVAILABLE = False

try:
    from openpyxl import load_workbook
    XLSX_AVAILABLE = True
except ImportError:
    load_workbook = None
    XLSX_AVAILABLE = False

try:
    import pymupdf as fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PDF_AVAILABLE = True
    except ImportError:
        fitz = None
        PDF_AVAILABLE = False

from PIL import Image
from utils.ocr_service import ocr_image_bytes

logger = logging.getLogger(__name__)

# Extensiones de imagen soportadas
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "tiff", "tif", "bmp"}


def optimize_and_encode_image(
    image_bytes: bytes,
    max_dimension: int = 1280,
    quality: int = 80,
    min_size_bytes: int = 50,
    min_dimension: int = 20,
) -> Optional[Dict[str, Any]]:
    """
    Valida, redimensiona y comprime una imagen a JPEG en Base64.
    Filtra imágenes diminutas (viñetas, espaciadores transparentes o iconos decorativos).
    """
    if not image_bytes or len(image_bytes) < min_size_bytes:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            # Ignorar viñetas o iconos diminutos
            if im.width < min_dimension or im.height < min_dimension:
                return None

            # Convertir a RGB para asegurar compatibilidad JPEG
            if im.mode in ("RGBA", "LA", "P"):
                # Crear fondo blanco para transparencias
                bg = Image.new("RGB", im.size, (255, 255, 255))
                if im.mode == "P":
                    im = im.convert("RGBA")
                if "A" in im.mode:
                    bg.paste(im, mask=im.split()[-1])
                    rgb_im = bg
                else:
                    rgb_im = im.convert("RGB")
            elif im.mode != "RGB":
                rgb_im = im.convert("RGB")
            else:
                rgb_im = im.copy()

            # Redimensionar si excede la dimensión máxima
            w, h = rgb_im.size
            if max(w, h) > max_dimension:
                ratio = max_dimension / max(w, h)
                new_w = max(1, int(w * ratio))
                new_h = max(1, int(h * ratio))
                rgb_im = rgb_im.resize((new_w, new_h), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            rgb_im.save(buf, format="JPEG", quality=quality, optimize=True)
            jpeg_bytes = buf.getvalue()
            b64_str = base64.b64encode(jpeg_bytes).decode("ascii")

            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_str}",
                    "detail": "auto",
                },
                "bytes": jpeg_bytes,
                "width": rgb_im.width,
                "height": rgb_im.height,
            }
    except Exception as e:
        logger.debug(f"No se pudo procesar la imagen con PIL: {e}")
        return None


async def _handle_single_image(
    image_bytes: bytes,
    image_idx: int,
    image_label: str,
    is_multimodal: bool,
    image_blocks: List[Dict[str, Any]],
    max_images: int = 10,
) -> str:
    """
    Procesa una imagen individual según el modo multimodal:
    - Multimodal: la optimiza y la añade a image_blocks, retornando un marcador.
    - No multimodal: ejecuta OCR e inserta el texto detectado en el documento.
    """
    if is_multimodal:
        if len(image_blocks) < max_images:
            optimized = optimize_and_encode_image(image_bytes)
            if optimized:
                image_blocks.append({
                    "type": "image_url",
                    "image_url": optimized["image_url"],
                })
                return f"\n[Imagen #{image_idx} ({image_label}): Ver imagen adjunta #{len(image_blocks)}]\n"
        # Si se superó el límite de imágenes multimodales o no se pudo optimizar
        return f"\n[Imagen #{image_idx} ({image_label})]\n"

    # Rama no multimodal: "sino ocr"
    try:
        ocr_text, ocr_conf = await ocr_image_bytes(image_bytes)
        if ocr_text and ocr_text.strip():
            return (
                f"\n[Imagen #{image_idx} ({image_label}) | Texto extraído por OCR (confianza: {ocr_conf:.2f}):\n"
                f'"{ocr_text.strip()}"]\n'
            )
        else:
            return f"\n[Imagen #{image_idx} ({image_label}) | Sin texto detectable por OCR]\n"
    except Exception as ocr_err:
        logger.warning(f"Error ejecutando OCR en imagen {image_idx}: {ocr_err}")
        return f"\n[Imagen #{image_idx} ({image_label}) | No se pudo procesar OCR: {ocr_err}]\n"


def _safe_extract_blips(element) -> List[str]:
    """Extrae r_ids de imágenes en un elemento DOCX con manejo seguro de namespaces."""
    rids: List[str] = []
    try:
        found = element.xpath(".//a:blip/@r:embed")
        if found:
            rids.extend(found)
    except Exception:
        pass

    if not rids:
        try:
            found_vml = element.xpath(
                ".//v:imagedata/@r:id",
                namespaces={
                    "v": "urn:schemas-microsoft-com:vml",
                    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                },
            )
            if found_vml:
                rids.extend(found_vml)
        except Exception:
            pass

    return rids


async def extract_docx_with_tables_and_images(
    file_bytes: bytes,
    is_multimodal: bool,
    max_images: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Extrae párrafos, tablas en Markdown e imágenes en orden secuencial de un DOCX."""
    if not DOCX_AVAILABLE:
        return "⚠️ La librería 'python-docx' no está instalada.", []

    doc = docx.Document(io.BytesIO(file_bytes))
    body_elements: List[str] = []
    image_blocks: List[Dict[str, Any]] = []
    image_counter = 0
    seen_image_rids = set()

    for element in doc.element.body:
        tag = element.tag.split("}")[-1]

        if tag == "p":
            p = docx.text.paragraph.Paragraph(element, doc)
            p_text = p.text.strip()
            if p_text:
                body_elements.append(p_text)

            # Buscar imágenes incrustadas en el párrafo
            blip_rids = _safe_extract_blips(element)
            for rid in blip_rids:
                if rid not in seen_image_rids and rid in doc.part.related_parts:
                    seen_image_rids.add(rid)
                    rel_part = doc.part.related_parts[rid]
                    img_bytes = rel_part.blob
                    image_counter += 1
                    part_name = getattr(rel_part, "partname", f"imagen_{image_counter}")
                    marker = await _handle_single_image(
                        img_bytes,
                        image_counter,
                        str(part_name).split("/")[-1],
                        is_multimodal,
                        image_blocks,
                        max_images=max_images,
                    )
                    body_elements.append(marker)

        elif tag == "tbl":
            table = docx.table.Table(element, doc)
            table_rows: List[List[str]] = []
            for row in table.rows:
                row_cells: List[str] = []
                for cell in row.cells:
                    # Extraer texto de párrafos dentro de la celda
                    cell_text = " ".join(
                        cp.text.strip() for cp in cell.paragraphs if cp.text.strip()
                    )
                    clean_cell = cell_text.replace("|", "\\|").replace("\n", " ").strip()
                    row_cells.append(clean_cell)

                    # Verificar si hay imágenes dentro de la celda
                    for cp in cell.paragraphs:
                        cell_blips = _safe_extract_blips(cp._p)
                        for rid in cell_blips:
                            if rid not in seen_image_rids and rid in doc.part.related_parts:
                                seen_image_rids.add(rid)
                                rel_part = doc.part.related_parts[rid]
                                image_counter += 1
                                part_name = getattr(rel_part, "partname", f"tabla_img_{image_counter}")
                                marker = await _handle_single_image(
                                    rel_part.blob,
                                    image_counter,
                                    str(part_name).split("/")[-1],
                                    is_multimodal,
                                    image_blocks,
                                    max_images=max_images,
                                )
                                body_elements.append(marker)

                table_rows.append(row_cells)

            if table_rows:
                num_cols = max(len(r) for r in table_rows)
                header_row = table_rows[0] + [""] * (num_cols - len(table_rows[0]))
                md_table = [
                    "| " + " | ".join(header_row) + " |",
                    "| " + " | ".join(["---"] * num_cols) + " |",
                ]
                for r in table_rows[1:]:
                    padded_r = r + [""] * (num_cols - len(r))
                    md_table.append("| " + " | ".join(padded_r[:num_cols]) + " |")
                body_elements.append("\n" + "\n".join(md_table) + "\n")

    # Respaldo: buscar imágenes no capturadas en el recorrido de párrafos
    for rel_id, rel_part in doc.part.related_parts.items():
        if rel_id not in seen_image_rids:
            target_ref = str(getattr(rel_part, "partname", "")).lower()
            if any(ext in target_ref for ext in (".png", ".jpg", ".jpeg", ".webp")):
                seen_image_rids.add(rel_id)
                image_counter += 1
                marker = await _handle_single_image(
                    rel_part.blob,
                    image_counter,
                    target_ref.split("/")[-1],
                    is_multimodal,
                    image_blocks,
                    max_images=max_images,
                )
                body_elements.append(marker)

    return "\n".join(body_elements).strip(), image_blocks


async def extract_pptx_with_tables_and_images(
    file_bytes: bytes,
    is_multimodal: bool,
    max_images: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Extrae diapositivas, textos, tablas en Markdown e imágenes de una presentación PPTX."""
    if not PPTX_AVAILABLE:
        return "⚠️ La librería 'python-pptx' no está instalada.", []

    prs = Presentation(io.BytesIO(file_bytes))
    parts: List[str] = []
    image_blocks: List[Dict[str, Any]] = []
    image_counter = 0

    for i, slide in enumerate(prs.slides, 1):
        slide_parts: List[str] = [f"[Diapositiva {i}]"]

        for shape in slide.shapes:
            # 1. Tablas
            if getattr(shape, "has_table", False):
                table_rows: List[List[str]] = []
                for row in shape.table.rows:
                    row_cells = [
                        c.text.strip().replace("|", "\\|").replace("\n", " ")
                        for c in row.cells
                    ]
                    table_rows.append(row_cells)
                if table_rows:
                    num_cols = max(len(r) for r in table_rows)
                    header_row = table_rows[0] + [""] * (num_cols - len(table_rows[0]))
                    md_table = [
                        "| " + " | ".join(header_row) + " |",
                        "| " + " | ".join(["---"] * num_cols) + " |",
                    ]
                    for r in table_rows[1:]:
                        padded_r = r + [""] * (num_cols - len(r))
                        md_table.append("| " + " | ".join(padded_r[:num_cols]) + " |")
                    slide_parts.append("\n" + "\n".join(md_table) + "\n")

            # 2. Imágenes
            elif (
                (MSO_SHAPE_TYPE and shape.shape_type == MSO_SHAPE_TYPE.PICTURE)
                or getattr(shape, "shape_type", None) == 13
            ):
                try:
                    img = shape.image
                    image_counter += 1
                    fname = getattr(img, "filename", f"slide_{i}_img_{image_counter}")
                    marker = await _handle_single_image(
                        img.blob,
                        image_counter,
                        f"Slide {i} - {fname}",
                        is_multimodal,
                        image_blocks,
                        max_images=max_images,
                    )
                    slide_parts.append(marker)
                except Exception as img_err:
                    logger.debug(f"Error extrayendo imagen de diapositiva {i}: {img_err}")

            # 3. Formas de texto
            elif hasattr(shape, "text") and shape.text.strip():
                slide_parts.append(shape.text.strip())

        if len(slide_parts) > 1:
            parts.extend(slide_parts)

    return "\n\n".join(parts).strip(), image_blocks


async def extract_xlsx_with_tables_and_images(
    file_bytes: bytes,
    is_multimodal: bool,
    max_images: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Extrae hojas completas formateadas como tablas Markdown e imágenes integradas de un XLSX."""
    if not XLSX_AVAILABLE:
        return "⚠️ La librería 'openpyxl' no está instalada.", []

    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    parts: List[str] = []
    image_blocks: List[Dict[str, Any]] = []
    image_counter = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"### [Hoja: {sheet_name}]")

        all_rows: List[List[str]] = []
        max_cols = 0
        for row in ws.iter_rows(min_row=1, values_only=True):
            if any(cell is not None and str(cell).strip() != "" for cell in row):
                row_vals = [
                    "" if c is None else str(c).replace("|", "\\|").replace("\n", " ").strip()
                    for c in row
                ]
                max_cols = max(max_cols, len(row_vals))
                all_rows.append(row_vals)

        if all_rows:
            header_row = all_rows[0] + [""] * (max_cols - len(all_rows[0]))
            md_table = [
                "| " + " | ".join(header_row) + " |",
                "| " + " | ".join(["---"] * max_cols) + " |",
            ]
            for r in all_rows[1:]:
                padded_r = r + [""] * (max_cols - len(r))
                md_table.append("| " + " | ".join(padded_r[:max_cols]) + " |")
            parts.append("\n".join(md_table))

        # Imágenes en la hoja
        ws_images = getattr(ws, "_images", []) or []
        for img_obj in ws_images:
            try:
                img_data = img_obj._data()
                image_counter += 1
                marker = await _handle_single_image(
                    img_data,
                    image_counter,
                    f"Hoja '{sheet_name}'",
                    is_multimodal,
                    image_blocks,
                    max_images=max_images,
                )
                parts.append(marker)
            except Exception as img_err:
                logger.debug(f"Error extrayendo imagen de XLSX en hoja {sheet_name}: {img_err}")

    return "\n\n".join(parts).strip(), image_blocks


async def extract_pdf_with_tables_and_images(
    file_bytes: bytes,
    is_multimodal: bool,
    max_images: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Extrae texto, tablas detectadas con PyMuPDF e imágenes de un PDF."""
    if not PDF_AVAILABLE:
        return "⚠️ La librería PyMuPDF ('fitz') no está instalada.", []

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts: List[str] = []
    image_blocks: List[Dict[str, Any]] = []
    image_counter = 0
    seen_xrefs = set()

    for p_idx, page in enumerate(doc, 1):
        parts.append(f"--- Página {p_idx} ---")

        # 1. Tablas en la página si están disponibles
        if hasattr(page, "find_tables"):
            try:
                tabs = page.find_tables()
                if tabs and tabs.tables:
                    for tab in tabs:
                        extracted = tab.extract()
                        if extracted and len(extracted) > 0:
                            num_cols = max(len(r) for r in extracted)
                            header = [
                                ("" if c is None else str(c)).replace("|", "\\|").replace("\n", " ")
                                for c in extracted[0]
                            ]
                            header += [""] * (num_cols - len(header))
                            md_table = [
                                "| " + " | ".join(header) + " |",
                                "| " + " | ".join(["---"] * num_cols) + " |",
                            ]
                            for r in extracted[1:]:
                                padded = [
                                    ("" if c is None else str(c)).replace("|", "\\|").replace("\n", " ")
                                    for c in r
                                ]
                                padded += [""] * (num_cols - len(padded))
                                md_table.append("| " + " | ".join(padded[:num_cols]) + " |")
                            parts.append("\n" + "\n".join(md_table) + "\n")
            except Exception as tab_err:
                logger.debug(f"Error extrayendo tablas de PDF en pág {p_idx}: {tab_err}")

        # 2. Texto nativo de la página
        page_text = page.get_text().strip()
        if page_text:
            parts.append(page_text)

        # 3. Imágenes en la página
        if hasattr(page, "get_images"):
            try:
                img_list = page.get_images(full=True)
                for img_info in img_list:
                    xref = img_info[0]
                    if xref not in seen_xrefs:
                        seen_xrefs.add(xref)
                        base_img = doc.extract_image(xref)
                        if base_img and "image" in base_img:
                            image_counter += 1
                            img_ext = base_img.get("ext", "png")
                            marker = await _handle_single_image(
                                base_img["image"],
                                image_counter,
                                f"Página {p_idx} (xref {xref}.{img_ext})",
                                is_multimodal,
                                image_blocks,
                                max_images=max_images,
                            )
                            parts.append(marker)
            except Exception as img_err:
                logger.debug(f"Error extrayendo imágenes de PDF en pág {p_idx}: {img_err}")

    text = "\n\n".join(parts).strip()
    return text, image_blocks


async def extract_onlyoffice_document_content(
    filename: str,
    file_bytes: bytes,
    is_multimodal: bool,
    max_images: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Función orquestadora principal para la lectura estructurada de archivos OnlyOffice.
    Retorna:
    - text: Texto plano formateado con tablas Markdown y marcas de posición de imágenes / OCR.
    - image_blocks: Lista de bloques de imágenes {"type": "image_url", ...} si is_multimodal es True.
    """
    ext = filename.lower().split(".")[-1]

    # 1. Documentos Word (.docx)
    if ext == "docx":
        return await extract_docx_with_tables_and_images(
            file_bytes, is_multimodal=is_multimodal, max_images=max_images
        )

    # 2. Presentaciones PowerPoint (.pptx)
    if ext == "pptx":
        return await extract_pptx_with_tables_and_images(
            file_bytes, is_multimodal=is_multimodal, max_images=max_images
        )

    # 3. Hojas de cálculo Excel (.xlsx)
    if ext == "xlsx":
        return await extract_xlsx_with_tables_and_images(
            file_bytes, is_multimodal=is_multimodal, max_images=max_images
        )

    # 4. Documentos PDF (.pdf)
    if ext == "pdf":
        return await extract_pdf_with_tables_and_images(
            file_bytes, is_multimodal=is_multimodal, max_images=max_images
        )

    # 5. Archivos de imagen directa (.png, .jpg, .jpeg, .webp, etc.)
    if ext in IMAGE_EXTENSIONS:
        image_blocks: List[Dict[str, Any]] = []
        marker = await _handle_single_image(
            file_bytes,
            1,
            filename,
            is_multimodal,
            image_blocks,
            max_images=max_images,
        )
        return marker.strip(), image_blocks

    # 6. Tablas CSV
    if ext == "csv":
        try:
            decoded = file_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(decoded.splitlines())
            rows = [list(r) for r in reader if any(c.strip() for c in r)]
            if rows:
                num_cols = max(len(r) for r in rows)
                header = rows[0] + [""] * (num_cols - len(rows[0]))
                clean_header = [c.replace("|", "\\|") for c in header]
                md_table = [
                    "| " + " | ".join(clean_header) + " |",
                    "| " + " | ".join(["---"] * num_cols) + " |",
                ]
                for r in rows[1:]:
                    padded = [c.replace("|", "\\|") for c in r] + [""] * (num_cols - len(r))
                    md_table.append("| " + " | ".join(padded[:num_cols]) + " |")
                return "\n".join(md_table), []
            return "", []
        except Exception as e:
            return f"❌ Error al procesar CSV: {e}", []

    # 7. Texto plano y Markdown (.txt, .md)
    if ext in {"txt", "md"}:
        try:
            decoded = file_bytes.decode("utf-8", errors="replace")
            return decoded, []
        except Exception as e:
            return f"❌ Error al leer texto: {e}", []

    # 8. Fallback binario
    if file_bytes[:4] in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
        return (
            f"⚠️ El archivo '{filename}' ({ext}) es un formato binario no reconocido directamente.",
            [],
        )

    try:
        decoded = file_bytes.decode("utf-8", errors="replace")
        return decoded, []
    except Exception as e:
        return f"❌ Error al decodificar archivo: {e}", []
