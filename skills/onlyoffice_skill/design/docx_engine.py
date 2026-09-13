"""
Motor de diseño premium para documentos Word (.docx).
Proporciona portadas ejecutivas, cajas callout, tarjetas de métricas/KPI y pie con numeración dinámica.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import docx
    from docx.shared import Pt, RGBColor, Inches, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import parse_xml, OxmlElement
    from docx.oxml.ns import nsdecls, qn
    DOCX_AVAILABLE = True
except Exception as e:
    DOCX_AVAILABLE = False

from skills.onlyoffice_skill.design.themes import (
    get_theme,
    hex_to_rgb,
    lighten_color,
    darken_color,
)

logger = logging.getLogger(__name__)

CALLOUT_TYPES: Dict[str, Dict[str, str]] = {
    "NOTE": {
        "title": "NOTA",
        "icon": "ℹ️",
        "border_color": "2563EB",  # blue-600
        "bg_color": "EFF6FF",      # blue-50
    },
    "TIP": {
        "title": "CONSEJO",
        "icon": "💡",
        "border_color": "059669",  # emerald-600
        "bg_color": "ECFDF5",      # emerald-50
    },
    "WARNING": {
        "title": "ADVERTENCIA",
        "icon": "⚠️",
        "border_color": "D97706",  # amber-600
        "bg_color": "FFFBEB",      # amber-50
    },
    "IMPORTANT": {
        "title": "IMPORTANTE",
        "icon": "🚨",
        "border_color": "DC2626",  # red-600
        "bg_color": "FEF2F2",      # red-50
    },
    "CAUTION": {
        "title": "PRECAUCIÓN",
        "icon": "⚡",
        "border_color": "EA580C",  # orange-600
        "bg_color": "FFF7ED",      # orange-50
    },
    "QUOTE": {
        "title": "",
        "icon": "❝",
        "border_color": "94A3B8",  # slate-400
        "bg_color": "F8FAFC",      # slate-50
    },
}


def _set_cell_background(cell, hex_color: str):
    """Aplica sombreado de fondo a una celda de Word."""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        tcPr.append(shd)
    except Exception as e:
        logger.warning(f"Error al establecer fondo de celda: {e}")


def _set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
    """Establece márgenes internos (en dxa: 20 dxa = 1 pt) de una celda."""
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(
            f'<w:tcMar {nsdecls("w")}>'
            f'  <w:top w:w="{top}" w:type="dxa"/>'
            f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
            f'  <w:left w:w="{left}" w:type="dxa"/>'
            f'  <w:right w:w="{right}" w:type="dxa"/>'
            f'</w:tcMar>'
        )
        tcPr.append(tcMar)
    except Exception as e:
        logger.warning(f"Error al establecer márgenes de celda: {e}")


def _set_table_borders_none(table):
    """Elimina todos los bordes exteriores e interiores de una tabla."""
    try:
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'  <w:top w:val="none"/>'
            f'  <w:bottom w:val="none"/>'
            f'  <w:left w:val="none"/>'
            f'  <w:right w:val="none"/>'
            f'  <w:insideH w:val="none"/>'
            f'  <w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr.append(borders)
    except Exception as e:
        logger.warning(f"Error al eliminar bordes de tabla: {e}")


def add_cover_page(
    doc,
    title: str,
    subtitle: Optional[str] = None,
    author: Optional[str] = None,
    organization: Optional[str] = None,
    date_str: Optional[str] = None,
    theme_name: str = "corporate_blue",
    style: str = "modern",
):
    """
    Inserta una portada ejecutiva completa al inicio del documento.
    Soporta estilos 'modern', 'minimal' y 'header_block'.
    """
    if not DOCX_AVAILABLE:
        return

    theme = get_theme(theme_name)
    p_rgb = RGBColor(*hex_to_rgb(theme["primary"]))
    s_rgb = RGBColor(*hex_to_rgb(theme["secondary"]))
    m_rgb = RGBColor(*hex_to_rgb(theme["text_muted"]))
    txt_rgb = RGBColor(*hex_to_rgb(theme["text_primary"]))
    font_name = theme["font_heading"]
    date_display = date_str or datetime.now().strftime("%d de %B de %Y")

    if style == "header_block":
        # Bloque superior sólido a todo el ancho
        header_table = doc.add_table(rows=1, cols=1)
        header_table.autofit = False
        _set_table_borders_none(header_table)
        cell = header_table.cell(0, 0)
        _set_cell_background(cell, theme["primary"])
        _set_cell_margins(cell, top=700, bottom=700, left=400, right=400)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(8)
        run_title = p.add_run(title)
        run_title.font.name = font_name
        run_title.font.size = Pt(28)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(255, 255, 255)

        if subtitle:
            p_sub = cell.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(0)
            p_sub.paragraph_format.space_after = Pt(12)
            run_sub = p_sub.add_run(subtitle)
            run_sub.font.name = font_name
            run_sub.font.size = Pt(14)
            run_sub.font.color.rgb = RGBColor(*hex_to_rgb(theme["bg_light"]))

        # Espacio debajo del bloque
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(80)

        # Metadatos
        meta_table = doc.add_table(rows=3, cols=2)
        _set_table_borders_none(meta_table)
        meta_fields = [
            ("PREPARADO POR:", author or "KAI Assistant"),
            ("ORGANIZACIÓN:", organization or "Kognito AI"),
            ("FECHA DE PUBLICACIÓN:", date_display),
        ]
        for row_idx, (label, val) in enumerate(meta_fields):
            r = meta_table.rows[row_idx]
            p_lbl = r.cells[0].paragraphs[0]
            r_lbl = p_lbl.add_run(label)
            r_lbl.font.name = font_name
            r_lbl.font.size = Pt(9)
            r_lbl.font.bold = True
            r_lbl.font.color.rgb = m_rgb

            p_val = r.cells[1].paragraphs[0]
            r_val = p_val.add_run(val)
            r_val.font.name = font_name
            r_val.font.size = Pt(10.5)
            r_val.font.color.rgb = txt_rgb

    elif style == "minimal":
        # Estilo editorial minimalista
        p_sp1 = doc.add_paragraph()
        p_sp1.paragraph_format.space_before = Pt(90)

        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(8)
        run_title = p_title.add_run(title)
        run_title.font.name = font_name
        run_title.font.size = Pt(32)
        run_title.font.bold = True
        run_title.font.color.rgb = p_rgb

        # Línea de acento horizontal delgada
        p_div = doc.add_paragraph()
        p_div.paragraph_format.space_before = Pt(6)
        p_div.paragraph_format.space_after = Pt(12)
        try:
            pPr = p_div._p.get_or_add_pPr()
            pBdr = parse_xml(
                f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="{theme["secondary"]}"/></w:pBdr>'
            )
            pPr.append(pBdr)
        except Exception:
            pass

        if subtitle:
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(6)
            p_sub.paragraph_format.space_after = Pt(40)
            run_sub = p_sub.add_run(subtitle)
            run_sub.font.name = font_name
            run_sub.font.size = Pt(14)
            run_sub.font.color.rgb = m_rgb

        p_sp2 = doc.add_paragraph()
        p_sp2.paragraph_format.space_before = Pt(120)

        meta_p = doc.add_paragraph()
        meta_p.paragraph_format.line_spacing = 1.2
        meta_items = [
            f"Preparado por: {author or 'KAI Assistant'}",
            f"Organización: {organization or 'Kognito AI'}",
            f"Fecha: {date_display}",
        ]
        for item in meta_items:
            r = meta_p.add_run(item + "\n")
            r.font.name = font_name
            r.font.size = Pt(9.5)
            r.font.color.rgb = m_rgb

    else:
        # 'modern' por defecto
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(60)

        # Franja decorativa de categoría
        p_cat = doc.add_paragraph()
        p_cat.paragraph_format.space_after = Pt(4)
        run_cat = p_cat.add_run("DOCUMENTO CORPORATIVO")
        run_cat.font.name = font_name
        run_cat.font.size = Pt(9)
        run_cat.font.bold = True
        run_cat.font.color.rgb = s_rgb

        # Título principal
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(4)
        p_title.paragraph_format.space_after = Pt(8)
        run_title = p_title.add_run(title)
        run_title.font.name = font_name
        run_title.font.size = Pt(30)
        run_title.font.bold = True
        run_title.font.color.rgb = p_rgb

        # Barra decorativa de acento
        p_line = doc.add_paragraph()
        p_line.paragraph_format.space_before = Pt(4)
        p_line.paragraph_format.space_after = Pt(12)
        try:
            pPr = p_line._p.get_or_add_pPr()
            pBdr = parse_xml(
                f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="18" w:space="1" w:color="{theme["primary"]}"/></w:pBdr>'
            )
            pPr.append(pBdr)
        except Exception:
            pass

        # Subtítulo
        if subtitle:
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(6)
            p_sub.paragraph_format.space_after = Pt(30)
            run_sub = p_sub.add_run(subtitle)
            run_sub.font.name = font_name
            run_sub.font.size = Pt(14)
            run_sub.font.color.rgb = txt_rgb

        p_sp2 = doc.add_paragraph()
        p_sp2.paragraph_format.space_before = Pt(100)

        # Tabla de metadatos estilizada
        meta_table = doc.add_table(rows=1, cols=3)
        meta_table.autofit = True
        _set_table_borders_none(meta_table)

        col_data = [
            ("AUTOR", author or "KAI Assistant"),
            ("EMPRESA", organization or "Kognito AI"),
            ("FECHA", date_display),
        ]
        for col_idx, (label, val) in enumerate(col_data):
            cell = meta_table.cell(0, col_idx)
            _set_cell_background(cell, theme["bg_light"])
            _set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
            
            p_l = cell.paragraphs[0]
            p_l.paragraph_format.space_after = Pt(2)
            r_l = p_l.add_run(label)
            r_l.font.name = font_name
            r_l.font.size = Pt(8)
            r_l.font.bold = True
            r_l.font.color.rgb = m_rgb

            p_v = cell.add_paragraph()
            p_v.paragraph_format.space_before = Pt(0)
            r_v = p_v.add_run(val)
            r_v.font.name = font_name
            r_v.font.size = Pt(10)
            r_v.font.bold = True
            r_v.font.color.rgb = txt_rgb

    # Salto de página para separar la portada del contenido
    doc.add_page_break()


def render_callout(doc, callout_type: str, text: str, theme_name: str = "corporate_blue"):
    """
    Inserta una caja de llamada/alerta con barra lateral y fondo sombreado suave.
    callout_type: 'NOTE', 'TIP', 'WARNING', 'IMPORTANT', 'CAUTION', 'QUOTE'
    """
    if not DOCX_AVAILABLE:
        return None

    norm_type = callout_type.upper().strip()
    cfg = CALLOUT_TYPES.get(norm_type, CALLOUT_TYPES["NOTE"])
    theme = get_theme(theme_name)
    font_name = theme["font_body"]

    table = doc.add_table(rows=1, cols=1)
    table.autofit = True
    cell = table.cell(0, 0)

    # Fondo sombreado
    _set_cell_background(cell, cfg["bg_color"])
    _set_cell_margins(cell, top=160, bottom=160, left=200, right=180)

    # Borde izquierdo grueso, los demás invisibles
    try:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{cfg["border_color"]}"/>'
            f'  <w:top w:val="none"/>'
            f'  <w:bottom w:val="none"/>'
            f'  <w:right w:val="none"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(tcBorders)
    except Exception as e:
        logger.warning(f"Error al establecer bordes de callout: {e}")

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15

    # Etiqueta con icono
    if cfg["title"]:
        run_header = p.add_run(f"{cfg['icon']} {cfg['title']}\n")
        run_header.font.name = font_name
        run_header.font.size = Pt(9.5)
        run_header.font.bold = True
        run_header.font.color.rgb = RGBColor(*hex_to_rgb(cfg["border_color"]))

    # Texto principal
    run_text = p.add_run(text)
    run_text.font.name = font_name
    run_text.font.size = Pt(10)
    run_text.font.color.rgb = RGBColor(*hex_to_rgb(theme["text_primary"]))

    # Párrafo posterior para espaciado
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

    return table


def add_kpi_cards(doc, cards: List[Dict[str, str]], theme_name: str = "corporate_blue"):
    """
    Inserta una cuadrícula horizontal de 2 a 4 tarjetas de métricas (Big Numbers).
    cards: [{'value': '$4.5M', 'label': 'Ingresos', 'change': '+15%'}, ...]
    """
    if not DOCX_AVAILABLE or not cards:
        return None

    theme = get_theme(theme_name)
    font_name = theme["font_heading"]
    p_rgb = RGBColor(*hex_to_rgb(theme["primary"]))
    m_rgb = RGBColor(*hex_to_rgb(theme["text_muted"]))

    num_cards = min(4, len(cards))
    table = doc.add_table(rows=1, cols=num_cards)
    table.autofit = True
    _set_table_borders_none(table)

    for idx in range(num_cards):
        card = cards[idx]
        cell = table.cell(0, idx)
        _set_cell_background(cell, theme["bg_light"])
        _set_cell_margins(cell, top=180, bottom=180, left=180, right=180)

        # Borde sutil en la celda
        try:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'  <w:left w:val="single" w:sz="6" w:space="0" w:color="{theme["border"]}"/>'
                f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="{theme["border"]}"/>'
                f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{theme["border"]}"/>'
                f'  <w:right w:val="single" w:sz="6" w:space="0" w:color="{theme["border"]}"/>'
                f'</w:tcBorders>'
            )
            tcPr.append(tcBorders)
        except Exception:
            pass

        # 1. Label
        p_label = cell.paragraphs[0]
        p_label.paragraph_format.space_before = Pt(0)
        p_label.paragraph_format.space_after = Pt(2)
        r_label = p_label.add_run(card.get("label", "").upper())
        r_label.font.name = font_name
        r_label.font.size = Pt(8.5)
        r_label.font.bold = True
        r_label.font.color.rgb = m_rgb

        # 2. Big Number
        p_val = cell.add_paragraph()
        p_val.paragraph_format.space_before = Pt(0)
        p_val.paragraph_format.space_after = Pt(2)
        r_val = p_val.add_run(str(card.get("value", "")))
        r_val.font.name = font_name
        r_val.font.size = Pt(20)
        r_val.font.bold = True
        r_val.font.color.rgb = p_rgb

        # 3. Change / Subtext
        change = card.get("change")
        if change:
            p_ch = cell.add_paragraph()
            p_ch.paragraph_format.space_before = Pt(0)
            p_ch.paragraph_format.space_after = Pt(0)
            r_ch = p_ch.add_run(str(change))
            r_ch.font.name = font_name
            r_ch.font.size = Pt(8.5)
            r_ch.font.bold = True
            if str(change).startswith("+"):
                r_ch.font.color.rgb = RGBColor(5, 150, 105)  # emerald-600
            elif str(change).startswith("-"):
                r_ch.font.color.rgb = RGBColor(220, 38, 38)  # red-600
            else:
                r_ch.font.color.rgb = m_rgb

    # Espacio tras las tarjetas
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(6)

    return table


def add_page_number_footer(doc, doc_title: Optional[str] = None, confidentiality: Optional[str] = "Confidencial"):
    """
    Configura el pie de página con título/confidencialidad y número de página nativo 'PAGE de NUMPAGES'.
    """
    if not DOCX_AVAILABLE or not doc.sections:
        return None

    section = doc.sections[-1]
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.text = ""  # Limpiar previo
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    font_name = "Segoe UI"
    gray_rgb = RGBColor(148, 163, 184)

    # Texto a la izquierda
    left_notes = []
    if doc_title:
        left_notes.append(doc_title)
    if confidentiality:
        left_notes.append(f"[{confidentiality}]")
    prefix_text = " — ".join(left_notes)

    if prefix_text:
        # Añadimos tabuladores para separar izquierda y derecha
        r_left = p.add_run(prefix_text + "\t\t")
        r_left.font.name = font_name
        r_left.font.size = Pt(8.5)
        r_left.font.color.rgb = gray_rgb

    r_lbl = p.add_run("Página ")
    r_lbl.font.name = font_name
    r_lbl.font.size = Pt(8.5)
    r_lbl.font.color.rgb = gray_rgb

    # Campo PAGE nativo
    try:
        fld_page = parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="PAGE"/>')
        p._p.append(fld_page)
    except Exception:
        pass

    r_mid = p.add_run(" de ")
    r_mid.font.name = font_name
    r_mid.font.size = Pt(8.5)
    r_mid.font.color.rgb = gray_rgb

    # Campo NUMPAGES nativo
    try:
        fld_numpages = parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="NUMPAGES"/>')
        p._p.append(fld_numpages)
    except Exception:
        pass

    return footer
