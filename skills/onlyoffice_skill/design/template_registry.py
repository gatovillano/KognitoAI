"""
Catálogo central de Plantillas Maestras para documentos OnlyOffice (Word, Excel, PowerPoint).
Genera archivos completos con diseño premium, portadas, gráficos, dashboards y diapositivas temáticas.
"""

import os
import logging
from typing import Optional, List, Dict, Any

try:
    import docx
    from docx.shared import Pt, RGBColor
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    XLSX_AVAILABLE = True
except Exception:
    XLSX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except Exception:
    PPTX_AVAILABLE = False

from skills.onlyoffice_skill.design.themes import get_theme, hex_to_rgb
import skills.onlyoffice_skill.design.docx_engine as docx_eng
import skills.onlyoffice_skill.design.xlsx_engine as xlsx_eng
import skills.onlyoffice_skill.design.pptx_engine as pptx_eng

logger = logging.getLogger(__name__)

TEMPLATES: Dict[str, Dict[str, Any]] = {
    # --- WORD TEMPLATES ---
    "executive_report": {
        "id": "executive_report",
        "name": "Reporte Ejecutivo Corporativo",
        "doc_type": "word",
        "default_theme": "corporate_blue",
        "description": "Informe de gestión completo con portada moderna, resumen de KPIs, tabla de hallazgos, notas y numeración de página."
    },
    "commercial_proposal": {
        "id": "commercial_proposal",
        "name": "Propuesta Comercial & Servicios",
        "doc_type": "word",
        "default_theme": "dark_slate",
        "description": "Propuesta de servicios con portada elegante, alcance de trabajo, cronograma de hitos, tabla de inversión con totales y condiciones comerciales."
    },
    "project_charter": {
        "id": "project_charter",
        "name": "Acta de Constitución de Proyecto",
        "doc_type": "word",
        "default_theme": "emerald_green",
        "description": "Project Charter formal con portada en bloque sólido, métricas clave del proyecto, objetivos y matriz de riesgos."
    },
    # --- EXCEL TEMPLATES ---
    "financial_budget": {
        "id": "financial_budget",
        "name": "Presupuesto Financiero Operativo",
        "doc_type": "excel",
        "default_theme": "corporate_blue",
        "description": "Libro contable multi-pestaña con resumen ejecutivo de KPIs, gráfico de columnas y desglose detallado de ingresos y gastos con fórmulas."
    },
    "sales_dashboard": {
        "id": "sales_dashboard",
        "name": "Dashboard de Ventas & Rendimiento",
        "doc_type": "excel",
        "default_theme": "emerald_green",
        "description": "Tablero de control de ventas con tarjetas de métricas, tabla formateada con semáforos condicionales y gráfico de columnas."
    },
    "project_tracker": {
        "id": "project_tracker",
        "name": "Planilla de Control y Tareas de Proyecto",
        "doc_type": "excel",
        "default_theme": "dark_slate",
        "description": "Seguimiento de tareas con responsables, fechas, estados formateados condicionalmente (Completado/En Progreso/Atrasado) y métricas superiores."
    },
    # --- POWERPOINT TEMPLATES ---
    "pitch_deck": {
        "id": "pitch_deck",
        "name": "Pitch Deck Comercial / Startups",
        "doc_type": "powerpoint",
        "default_theme": "dark_slate",
        "description": "Presentación de 6 diapositivas de alto impacto: Portada, El Problema, Solución comparativa, Métricas (Big Numbers), Modelo de Negocio y Cierre con CTA."
    },
    "quarterly_review": {
        "id": "quarterly_review",
        "name": "Revisión Estratégica Trimestral (QBR)",
        "doc_type": "powerpoint",
        "default_theme": "corporate_blue",
        "description": "Presentación ejecutiva de 5 diapositivas: Portada QBR, Agenda estructurada, KPIs del Trimestre, 3 Columnas de Iniciativas y Conclusiones."
    },
}


def list_templates() -> List[Dict[str, Any]]:
    """Devuelve la lista de plantillas maestras disponibles."""
    return list(TEMPLATES.values())


def get_template_info(template_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve la información de una plantilla por su ID."""
    return TEMPLATES.get(template_id.lower().strip())


# ==========================================
# GENERADORES DE PLANTILLAS WORD
# ==========================================

def _generate_word_executive_report(file_path: str, title: str, subtitle: Optional[str], theme_name: str):
    doc = docx.Document()
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]
    p_rgb = RGBColor(*hex_to_rgb(theme["primary"]))

    # 1. Portada
    docx_eng.add_cover_page(
        doc,
        title=title or "Reporte Ejecutivo de Gestión",
        subtitle=subtitle or "Evaluación Estratégica y Rendimiento Operativo",
        author="KAI Assistant",
        organization="Kognito AI Corp",
        theme_name=theme_name,
        style="modern"
    )

    # 2. Resumen Ejecutivo
    p_h1 = doc.add_heading("1. Resumen Ejecutivo", level=1)
    p_h1.runs[0].font.name = font_name
    p_h1.runs[0].font.color.rgb = p_rgb

    p_intro = doc.add_paragraph(
        "El presente informe consolida los resultados estratégicos y el rendimiento obtenido durante el período analizado. "
        "Se destacan mejoras sustanciales en eficiencia operativa, adopción de herramientas tecnológicas y optimización de recursos."
    )
    p_intro.paragraph_format.line_spacing = 1.15
    p_intro.paragraph_format.space_after = Pt(12)

    # 3. KPI Cards
    cards = [
        {"label": "Crecimiento General", "value": "+28.4%", "change": "▲ Superó meta"},
        {"label": "Eficiencia en Costos", "value": "-15.2%", "change": "▲ Ahorro neto"},
        {"label": "Satisfacción de Usuarios", "value": "98.5%", "change": "▲ Récord histórico"}
    ]
    docx_eng.add_kpi_cards(doc, cards, theme_name=theme_name)

    # 4. Diagnóstico y Hallazgos
    p_h2 = doc.add_heading("2. Hallazgos Principales y Desempeño", level=1)
    p_h2.runs[0].font.name = font_name
    p_h2.runs[0].font.color.rgb = p_rgb

    p_diag = doc.add_paragraph(
        "A continuación se presenta el desglose cuantitativo por unidad de negocio evaluada:"
    )
    p_diag.paragraph_format.space_after = Pt(8)

    table_data = [
        ["Unidad Estratégica", "Meta Anual", "Ejecutado", "Cumplimiento %"],
        ["Transformación Digital", "$500,000", "$540,000", "108%"],
        ["Operaciones y Logística", "$350,000", "$342,000", "98%"],
        ["Desarrollo y Producto", "$620,000", "$680,000", "110%"],
        ["Totales", "$1,470,000", "$1,562,000", "106%"]
    ]
    tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
    tbl.autofit = True
    docx_eng._set_table_borders_none(tbl)
    for r_i, r_data in enumerate(table_data):
        for c_i, val in enumerate(r_data):
            cell = tbl.cell(r_i, c_i)
            docx_eng._set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
            p = cell.paragraphs[0]
            p.text = val
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if r_i == 0:
                docx_eng._set_cell_background(cell, theme["primary"])
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
            elif r_i == len(table_data) - 1:
                docx_eng._set_cell_background(cell, theme["bg_light"])
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = p_rgb
            else:
                if r_i % 2 == 1:
                    docx_eng._set_cell_background(cell, "FFFFFF")
                else:
                    docx_eng._set_cell_background(cell, theme["bg_light"])

    # Espacio
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 5. Callout
    docx_eng.render_callout(
        doc,
        callout_type="TIP",
        text="Se recomienda mantener el ritmo de inversión en automatización e inteligencia artificial durante el próximo ciclo trimestral.",
        theme_name=theme_name
    )

    # 6. Conclusiones
    p_h3 = doc.add_heading("3. Conclusiones y Próximos Pasos", level=1)
    p_h3.runs[0].font.name = font_name
    p_h3.runs[0].font.color.rgb = p_rgb

    points = [
        "Aprobación del plan de escalabilidad por parte del comité directivo.",
        "Implementación del nuevo protocolo de control de calidad para el Q4.",
        "Monitoreo continuo de KPIs a través de los tableros analíticos automatizados."
    ]
    for pt in points:
        p_pt = doc.add_paragraph(pt, style="List Bullet")
        p_pt.paragraph_format.space_after = Pt(4)

    # 7. Pie de página
    docx_eng.add_page_number_footer(doc, doc_title=title, confidentiality="Confidencial")

    doc.save(file_path)
    return True


def _generate_word_commercial_proposal(file_path: str, title: str, subtitle: Optional[str], theme_name: str):
    doc = docx.Document()
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]
    p_rgb = RGBColor(*hex_to_rgb(theme["primary"]))

    docx_eng.add_cover_page(
        doc,
        title=title or "Propuesta Comercial de Servicios",
        subtitle=subtitle or "Solución Integral de Inteligencia Artificial y Automatización",
        author="KAI Solutions",
        organization="KAI Client",
        theme_name=theme_name,
        style="minimal"
    )

    p_h1 = doc.add_heading("1. Introducción y Entendimiento del Negocio", level=1)
    p_h1.runs[0].font.name = font_name
    p_h1.runs[0].font.color.rgb = p_rgb

    p_intro = doc.add_paragraph(
        "Agradecemos la oportunidad de presentar esta propuesta. Nuestro compromiso es potenciar la productividad y "
        "capacidades analíticas de su organización mediante agentes de software autónomos integrados a su infraestructura."
    )
    p_intro.paragraph_format.space_after = Pt(12)

    p_h2 = doc.add_heading("2. Alcance del Servicio y Entregables", level=1)
    p_h2.runs[0].font.name = font_name
    p_h2.runs[0].font.color.rgb = p_rgb

    services = [
        "Despliegue y configuración del entorno de agentes KAI en nube privada.",
        "Integración con bases de conocimientos corporativas y pipelines RAG.",
        "Personalización de habilidades operativas y flujos de trabajo específicos.",
        "Capacitación ejecutiva y acompañamiento técnico durante 60 días."
    ]
    for s in services:
        doc.add_paragraph(s, style="List Bullet").paragraph_format.space_after = Pt(4)

    p_h3 = doc.add_heading("3. Propuesta Económica e Inversión", level=1)
    p_h3.runs[0].font.name = font_name
    p_h3.runs[0].font.color.rgb = p_rgb

    table_data = [
        ["Concepto / Servicio", "Modalidad", "Plazo", "Inversión (USD)"],
        ["Fase 1: Configuración & Arquitectura", "Única", "2 semanas", "$4,500"],
        ["Fase 2: Desarrollo e Integraciones", "Hito", "4 semanas", "$8,000"],
        ["Fase 3: Soporte y Optimización Continua", "Mensual", "3 meses", "$2,500"],
        ["Total Estimado", "Proyecto", "6 meses", "$15,000"]
    ]
    tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
    tbl.autofit = True
    docx_eng._set_table_borders_none(tbl)
    for r_i, r_data in enumerate(table_data):
        for c_i, val in enumerate(r_data):
            cell = tbl.cell(r_i, c_i)
            docx_eng._set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
            p = cell.paragraphs[0]
            p.text = val
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if r_i == 0:
                docx_eng._set_cell_background(cell, theme["primary"])
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
            elif r_i == len(table_data) - 1:
                docx_eng._set_cell_background(cell, theme["bg_light"])
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = p_rgb
            else:
                docx_eng._set_cell_background(cell, theme["bg_light"] if r_i % 2 == 0 else "FFFFFF")

    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    docx_eng.render_callout(
        doc,
        callout_type="NOTE",
        text="Esta propuesta económica tiene una validez de 30 días corridos a partir de la fecha de emisión.",
        theme_name=theme_name
    )

    docx_eng.add_page_number_footer(doc, doc_title=title, confidentiality="Propuesta Comercial")
    doc.save(file_path)
    return True


def _generate_word_project_charter(file_path: str, title: str, subtitle: Optional[str], theme_name: str):
    doc = docx.Document()
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]
    p_rgb = RGBColor(*hex_to_rgb(theme["primary"]))

    docx_eng.add_cover_page(
        doc,
        title=title or "Acta de Constitución de Proyecto",
        subtitle=subtitle or "Project Charter & Definición de Objetivos",
        author="Project Management Office",
        organization="KAI Enterprise",
        theme_name=theme_name,
        style="header_block"
    )

    doc.add_heading("1. Propósito y Objetivos del Proyecto", level=1)
    doc.add_paragraph(
        "El propósito de este proyecto es formalizar los recursos, plazos y metas comprometidas para la modernización de la plataforma digital."
    )

    cards = [
        {"label": "Presupuesto Asignado", "value": "$85,000", "change": "Fijo"},
        {"label": "Duración Estimada", "value": "16 semanas", "change": "4 Sprints"},
        {"label": "Equipo Central", "value": "6 personas", "change": "Dedicación exclusiva"}
    ]
    docx_eng.add_kpi_cards(doc, cards, theme_name=theme_name)

    doc.add_heading("2. Matriz Preliminar de Riesgos", level=1)
    risks_data = [
        ["Riesgo Identificado", "Impacto", "Probabilidad", "Plan de Mitigación"],
        ["Demora en entrega de APIs externas", "Alto", "Media", "Desarrollo de mocks y contratos tempranos"],
        ["Disponibilidad de entornos de prueba", "Medio", "Baja", "Aprovisionamiento en Docker/Kubernetes"],
        ["Curva de adopción en usuarios finales", "Alto", "Baja", "Plan intensivo de talleres y documentación"]
    ]
    tbl = doc.add_table(rows=len(risks_data), cols=len(risks_data[0]))
    tbl.autofit = True
    docx_eng._set_table_borders_none(tbl)
    for r_i, r_data in enumerate(risks_data):
        for c_i, val in enumerate(r_data):
            cell = tbl.cell(r_i, c_i)
            docx_eng._set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
            p = cell.paragraphs[0]
            p.text = val
            if r_i == 0:
                docx_eng._set_cell_background(cell, theme["primary"])
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
            else:
                docx_eng._set_cell_background(cell, theme["bg_light"] if r_i % 2 == 0 else "FFFFFF")

    docx_eng.add_page_number_footer(doc, doc_title=title, confidentiality="Uso Interno")
    doc.save(file_path)
    return True


# ==========================================
# GENERADORES DE PLANTILLAS EXCEL
# ==========================================

def _generate_excel_financial_budget(file_path: str, title: str, theme_name: str):
    wb = openpyxl.Workbook()
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]

    # 1. Hoja Resumen
    ws_sum = wb.active
    ws_sum.title = "Resumen"
    ws_sum.views.sheetView[0].showGridLines = True

    # Título principal
    ws_sum["B1"] = (title or "PRESUPUESTO FINANCIERO ANUAL").upper()
    ws_sum["B1"].font = Font(name=font_name, size=16, bold=True, color=theme["primary"])

    # KPI cards en filas 3 a 5
    cards = [
        {"label": "Ingresos Proyectados", "value": "$280,000", "change": "▲ +12% YoY"},
        {"label": "Gastos Operativos", "value": "$195,000", "change": "▼ Controlado"},
        {"label": "Margen Neto Estimado", "value": "$85,000", "change": "30.3% Rentabilidad"}
    ]
    xlsx_eng.add_kpi_cards(ws_sum, cards, theme_name=theme_name, start_row=3, start_col=2)

    # Tabla resumen por trimestre
    ws_sum["B7"] = "Evolución por Trimestre"
    ws_sum["B7"].font = Font(name=font_name, size=12, bold=True, color=theme["primary"])

    headers = ["Trimestre", "Ingresos", "Gastos", "Margen"]
    for c_idx, h in enumerate(headers, start=2):
        cell = ws_sum.cell(row=8, column=c_idx, value=h)
        cell.font = Font(name=font_name, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=theme["primary"], end_color=theme["primary"], fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    q_data = [
        ("Q1", 60000, 45000),
        ("Q2", 70000, 48000),
        ("Q3", 72000, 50000),
        ("Q4", 78000, 52000),
    ]
    for i, (q, ing, gas) in enumerate(q_data, start=9):
        ws_sum.cell(row=i, column=2, value=q).alignment = Alignment(horizontal="center")
        c_ing = ws_sum.cell(row=i, column=3, value=ing)
        c_ing.number_format = "$#,##0"
        c_gas = ws_sum.cell(row=i, column=4, value=gas)
        c_gas.number_format = "$#,##0"
        # Fórmula de margen = C - D
        c_mar = ws_sum.cell(row=i, column=5, value=f"=C{i}-D{i}")
        c_mar.number_format = "$#,##0"

    # Fila de totales
    ws_sum.cell(row=13, column=2, value="Total").font = Font(bold=True)
    ws_sum.cell(row=13, column=3, value="=SUM(C9:C12)").font = Font(bold=True)
    ws_sum.cell(row=13, column=3).number_format = "$#,##0"
    ws_sum.cell(row=13, column=4, value="=SUM(D9:D12)").font = Font(bold=True)
    ws_sum.cell(row=13, column=4).number_format = "$#,##0"
    ws_sum.cell(row=13, column=5, value="=SUM(E9:E12)").font = Font(bold=True)
    ws_sum.cell(row=13, column=5).number_format = "$#,##0"

    # Gráfico en la misma hoja
    xlsx_eng.add_chart(
        ws_sum,
        chart_type="column",
        data_range="C8:D12",
        categories_range="B9:B12",
        target_cell="G7",
        title="Ingresos vs Gastos por Trimestre",
        theme_name=theme_name,
        width=14,
        height=9
    )

    xlsx_eng.auto_fit_columns_and_freeze(ws_sum, freeze_cell="B9")

    # 2. Hoja Ingresos Detallados
    ws_ing = wb.create_sheet(title="Ingresos")
    ws_ing.views.sheetView[0].showGridLines = True
    ws_ing["A1"] = "DETALLE DE INGRESOS"
    ws_ing["A1"].font = Font(name=font_name, size=14, bold=True, color=theme["primary"])

    ing_headers = ["ID", "Línea de Negocio", "Cliente Principal", "Presupuesto", "Ejecutado"]
    for c_idx, h in enumerate(ing_headers, start=1):
        cell = ws_ing.cell(row=3, column=c_idx, value=h)
        cell.font = Font(name=font_name, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=theme["secondary"], end_color=theme["secondary"], fill_type="solid")

    ing_rows = [
        ("ING-001", "Suscripciones SaaS", "Empresas Varias", 120000, 125000),
        ("ING-002", "Consultoría Estratégica", "Corporación Global", 80000, 82000),
        ("ING-003", "Capacitaciones & Licencias", "Pymes Regionales", 50000, 48000),
        ("ING-004", "Integraciones a Medida", "Sector Financiero", 30000, 32000),
    ]
    for r_idx, row_vals in enumerate(ing_rows, start=4):
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws_ing.cell(row=r_idx, column=c_idx, value=val)
            if c_idx in (4, 5):
                c.number_format = "$#,##0"

    xlsx_eng.auto_fit_columns_and_freeze(ws_ing, freeze_cell="A4")

    # 3. Hoja Gastos Detallados
    ws_gas = wb.create_sheet(title="Gastos")
    ws_gas.views.sheetView[0].showGridLines = True
    ws_gas["A1"] = "DETALLE DE GASTOS"
    ws_gas["A1"].font = Font(name=font_name, size=14, bold=True, color=theme["primary"])

    gas_headers = ["ID", "Departamento", "Rubro / Concepto", "Asignado", "Gastado"]
    for c_idx, h in enumerate(gas_headers, start=1):
        cell = ws_gas.cell(row=3, column=c_idx, value=h)
        cell.font = Font(name=font_name, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=theme["primary"], end_color=theme["primary"], fill_type="solid")

    gas_rows = [
        ("GAS-001", "Ingeniería & IT", "Servidores Cloud & DevOps", 60000, 58000),
        ("GAS-002", "Marketing & Ventas", "Campañas Digitales", 45000, 47000),
        ("GAS-003", "Operaciones", "Infraestructura & Licencias", 35000, 34000),
        ("GAS-004", "Recursos Humanos", "Contrataciones y Bienestar", 25000, 24000),
    ]
    for r_idx, row_vals in enumerate(gas_rows, start=4):
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws_gas.cell(row=r_idx, column=c_idx, value=val)
            if c_idx in (4, 5):
                c.number_format = "$#,##0"

    xlsx_eng.auto_fit_columns_and_freeze(ws_gas, freeze_cell="A4")

    wb.save(file_path)
    return True


def _generate_excel_sales_dashboard(file_path: str, title: str, theme_name: str):
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Ventas"
    sheet.views.sheetView[0].showGridLines = True
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]

    sheet["B1"] = (title or "DASHBOARD DE VENTAS").upper()
    sheet["B1"].font = Font(name=font_name, size=16, bold=True, color=theme["primary"])

    cards = [
        {"label": "Ventas Acumuladas", "value": "$450,200", "change": "+18.4% vs meta"},
        {"label": "Tasa de Cierre", "value": "32.5%", "change": "+3.1%"},
        {"label": "Ticket Promedio", "value": "$4,250", "change": "Saludable"}
    ]
    xlsx_eng.add_kpi_cards(sheet, cards, theme_name=theme_name, start_row=3, start_col=2)

    headers = ["Ejecutivo", "Región", "Oportunidades", "Ventas (USD)", "Estado"]
    for c_i, h in enumerate(headers, start=2):
        cell = sheet.cell(row=8, column=c_i, value=h)
        cell.font = Font(name=font_name, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=theme["primary"], end_color=theme["primary"], fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    sales_data = [
        ("Carlos Gómez", "Norte", 45, 120000, "Completado"),
        ("María Rodríguez", "Centro", 38, 145000, "Completado"),
        ("Andrés Silva", "Sur", 29, 85000, "En Progreso"),
        ("Lucía Fernández", "Este", 31, 95000, "En Progreso"),
        ("Javier Martínez", "Oeste", 18, 42000, "Atrasado"),
    ]
    for r_i, row in enumerate(sales_data, start=9):
        for c_i, val in enumerate(row, start=2):
            cell = sheet.cell(row=r_i, column=c_i, value=val)
            if c_i == 5:
                cell.number_format = "$#,##0"
            if c_i in (2, 3, 6):
                cell.alignment = Alignment(horizontal="center")

    xlsx_eng.apply_conditional_formatting(sheet, "F9:F13", rule_type="status_highlights")

    xlsx_eng.add_chart(
        sheet,
        chart_type="bar",
        data_range="E8:E13",
        categories_range="B9:B13",
        target_cell="H7",
        title="Ventas por Ejecutivo",
        theme_name=theme_name,
        width=13,
        height=8
    )

    xlsx_eng.auto_fit_columns_and_freeze(sheet, freeze_cell="B9")
    wb.save(file_path)
    return True


def _generate_excel_project_tracker(file_path: str, title: str, theme_name: str):
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Tareas"
    sheet.views.sheetView[0].showGridLines = True
    theme = get_theme(theme_name)
    font_name = theme["font_heading"]

    sheet["B1"] = (title or "SEGUIMIENTO Y CONTROL DE PROYECTO").upper()
    sheet["B1"].font = Font(name=font_name, size=16, bold=True, color=theme["primary"])

    cards = [
        {"label": "Total Tareas", "value": "24", "change": "Planificadas"},
        {"label": "Completadas", "value": "14", "change": "58% Avance"},
        {"label": "En Progreso", "value": "7", "change": "En curso"},
        {"label": "Atrasadas", "value": "3", "change": "Requieren atención"}
    ]
    xlsx_eng.add_kpi_cards(sheet, cards, theme_name=theme_name, start_row=3, start_col=2)

    headers = ["ID", "Nombre de Tarea", "Responsable", "Fecha Inicio", "Fecha Límite", "Estado", "Prioridad"]
    for c_i, h in enumerate(headers, start=2):
        cell = sheet.cell(row=8, column=c_i, value=h)
        cell.font = Font(name=font_name, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=theme["primary"], end_color=theme["primary"], fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    tasks = [
        ("TSK-101", "Definición de Requerimientos", "Ana Morales", "2026-09-01", "2026-09-07", "Completado", "Alta"),
        ("TSK-102", "Diseño de Arquitectura", "Marcos Paz", "2026-09-08", "2026-09-15", "Completado", "Alta"),
        ("TSK-103", "Desarrollo de Microservicios", "Equipo Backend", "2026-09-16", "2026-09-30", "En Progreso", "Alta"),
        ("TSK-104", "Integración con OnlyOffice", "Equipo Frontend", "2026-09-20", "2026-10-05", "En Progreso", "Media"),
        ("TSK-105", "Pruebas de Carga y Seguridad", "Equipo QA", "2026-09-25", "2026-09-28", "Atrasado", "Crítica"),
    ]
    for r_i, row in enumerate(tasks, start=9):
        for c_i, val in enumerate(row, start=2):
            cell = sheet.cell(row=r_i, column=c_i, value=val)
            if c_i in (2, 5, 6, 7, 8):
                cell.alignment = Alignment(horizontal="center")

    xlsx_eng.apply_conditional_formatting(sheet, "G9:G13", rule_type="status_highlights")
    xlsx_eng.auto_fit_columns_and_freeze(sheet, freeze_cell="B9")
    wb.save(file_path)
    return True


# ==========================================
# GENERADORES DE PLANTILLAS POWERPOINT
# ==========================================

def _generate_pptx_pitch_deck(file_path: str, title: str, subtitle: Optional[str], theme_name: str):
    prs = Presentation()

    # Slide 1: Portada
    pptx_eng.add_slide(
        prs,
        layout_type="title",
        data={
            "title": title or "KAI Autonomous Ecosystem",
            "subtitle": subtitle or "La Próxima Generación de Inteligencia Artificial para Empresas",
            "category": "INVESTOR PITCH DECK",
            "author": "Kognito AI Team",
            "organization": "Kognito AI Corp",
            "date": "2026"
        },
        theme_name=theme_name,
        speaker_notes="Bienvenidos. Hoy presentamos la plataforma de trabajo autónomo con IA más avanzada para empresas."
    )

    # Slide 2: El Problema
    pptx_eng.add_slide(
        prs,
        layout_type="content",
        data={
            "title": "El Problema del Mercado",
            "subtitle": "La fragmentación y los procesos manuales frenan la innovación corporativa",
            "bullets": [
                "Los equipos gastan más del 40% de su tiempo en tareas repetitivas de ofimática y reportes.",
                "Las herramientas de IA actuales operan aisladas, sin contexto de negocio persistente ni memoria de equipo.",
                "La falta de integración entre editores de documentos y agentes de software genera retrabajo constante."
            ]
        },
        theme_name=theme_name,
        speaker_notes="Enfóquense en el dolor del usuario: tiempo desperdiciado y falta de herramientas verdaderamente autónomas."
    )

    # Slide 3: La Solución (2 columnas)
    pptx_eng.add_slide(
        prs,
        layout_type="two_columns",
        data={
            "title": "Nuestra Solución: Plataforma KAI",
            "subtitle": "Un ecosistema unificado de agentes y suites ofimáticas inteligentes",
            "columns": [
                {
                    "title": "Antes de KAI",
                    "items": [
                        "Procesos desconectados y manuales",
                        "Reportes lentos con formato descuidado",
                        "Pérdida de memoria institucional",
                        "Altos costos operativos"
                    ]
                },
                {
                    "title": "Con KAI Autónomo",
                    "items": [
                        "Creación de documentos y hojas ejecutivas en segundos",
                        "Estética premium y profesional automática",
                        "Memoria episódica y grafo de conocimiento",
                        "Escalabilidad inmediata 24/7"
                    ]
                }
            ]
        },
        theme_name=theme_name,
        speaker_notes="Resaltar la ventaja competitiva de la integración nativa de OnlyOffice y memoria viva."
    )

    # Slide 4: Métricas y Tracción
    pptx_eng.add_slide(
        prs,
        layout_type="kpi_metrics",
        data={
            "title": "Tracción y Métricas Clave",
            "subtitle": "Crecimiento exponencial en usuarios y retención sostenida",
            "cards": [
                {"label": "Usuarios Activos", "value": "125K+", "description": "+45% crecimiento mensual"},
                {"label": "Documentos Creados", "value": "1.8M", "description": "Word, Excel y PPTX"},
                {"label": "Retención Neta", "value": "118%", "description": "Excelente satisfacción"},
                {"label": "Tiempo Ahorrado", "value": "65%", "description": "Por colaborador"}
            ]
        },
        theme_name=theme_name,
        speaker_notes="Estos números validan el product-market fit y el apetito de las empresas por soluciones autónomas."
    )

    # Slide 5: Modelo de Negocio
    pptx_eng.add_slide(
        prs,
        layout_type="content",
        data={
            "title": "Modelo de Negocio y Escalabilidad",
            "subtitle": "Ingresos recurrentes predecibles con alta expansión de cuentas",
            "bullets": [
                "Suscripción SaaS Enterprise: Licenciamiento por puestos de trabajo y agentes dedicados.",
                "Marketplace de Habilidades (Skills): Ecosistema de herramientas ampliadas y conectores de datos.",
                "Servicios Gestionados & Despliegue On-Premise: Para clientes con altas exigencias de soberanía de datos."
            ]
        },
        theme_name=theme_name,
        speaker_notes="El modelo permite crecer orgánicamente tanto en volumen de agentes como en skills especializadas."
    )

    # Slide 6: Conclusión y Cierre
    pptx_eng.add_slide(
        prs,
        layout_type="conclusion",
        data={
            "title": "Conclusión y Ronda de Inversión",
            "subtitle": "Oportunidad de liderar la transformación del trabajo intelectual con IA",
            "points": [
                "Tecnología probada y desplegada en producción.",
                "Mercado en rápida aceleración hacia agentes autónomos.",
                "Equipo fundador con probada trayectoria en IA y desarrollo de producto."
            ],
            "cta_title": "Únete al Viaje",
            "cta_text": "Ronda Serie A abierta para acelerar expansión comercial y desarrollo de modelos de lenguaje dedicados."
        },
        theme_name=theme_name,
        speaker_notes="Agradecer y abrir espacio para preguntas e intercambio con los inversores."
    )

    prs.save(file_path)
    return True


def _generate_pptx_quarterly_review(file_path: str, title: str, subtitle: Optional[str], theme_name: str):
    prs = Presentation()

    pptx_eng.add_slide(
        prs,
        layout_type="title",
        data={
            "title": title or "Revisión Estratégica Trimestral (QBR)",
            "subtitle": subtitle or "Evaluación de Resultados y Objetivos del Próximo Trimestre",
            "category": "QUARTERLY BUSINESS REVIEW",
            "author": "Dirección Estratégica",
            "date": "2026"
        },
        theme_name=theme_name
    )

    pptx_eng.add_slide(
        prs,
        layout_type="agenda",
        data={
            "title": "Agenda de la Sesión",
            "items": [
                {"title": "1. Resumen Ejecutivo y Rendimiento", "description": "Visión general de las metas logradas en el trimestre."},
                {"title": "2. Métricas y KPIs por Departamento", "description": "Análisis cuantitativo de ventas, producto y operaciones."},
                {"title": "3. Desafíos y Lecciones Aprendidas", "description": "Obstáculos enfrentados y soluciones implementadas."},
                {"title": "4. Objetivos y Plan de Acción Q4", "description": "Prioridades estratégicas para el cierre del año."}
            ]
        },
        theme_name=theme_name
    )

    pptx_eng.add_slide(
        prs,
        layout_type="kpi_metrics",
        data={
            "title": "Rendimiento Global del Trimestre",
            "cards": [
                {"label": "Facturación Q3", "value": "$1.42M", "description": "104% vs meta"},
                {"label": "Nuevos Clientes", "value": "84", "description": "Ticket promedio alto"},
                {"label": "NPS Clientes", "value": "78", "description": "Zona de excelencia"}
            ]
        },
        theme_name=theme_name
    )

    pptx_eng.add_slide(
        prs,
        layout_type="three_columns",
        data={
            "title": "Iniciativas Estratégicas Prioritarias",
            "columns": [
                {"title": "Producto & IA", "items": ["Lanzamiento suite OnlyOffice", "Mejora de latencia a <500ms", "Indexación RAG automática"]},
                {"title": "Ventas & Expansión", "items": ["Apertura mercado regional", "Alianzas con integradores", "Automatización de demos"]},
                {"title": "Operaciones", "items": ["Certificación de seguridad", "Migración a multi-cloud", "Onboarding acelerado"]}
            ]
        },
        theme_name=theme_name
    )

    pptx_eng.add_slide(
        prs,
        layout_type="conclusion",
        data={
            "title": "Próximos Pasos y Acuerdos",
            "points": [
                "Alineación completa de metas OKR para todo el equipo.",
                "Revisión presupuestaria aprobada sin desviaciones.",
                "Próxima sesión de seguimiento en 30 días."
            ],
            "cta_title": "Compromiso",
            "cta_text": "Foco total en la ejecución y calidad de los entregables del Q4."
        },
        theme_name=theme_name
    )

    prs.save(file_path)
    return True


# ==========================================
# DESPACHADOR PRINCIPAL
# ==========================================

def create_from_template(
    template_id: str,
    file_path: str,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    theme_name: Optional[str] = None,
) -> bool:
    """
    Crea un documento completamente estructurado a partir del ID de una plantilla maestra.
    Retorna True si la creación fue exitosa.
    """
    info = get_template_info(template_id)
    if not info:
        logger.error(f"Plantilla '{template_id}' no encontrada en el catálogo.")
        return False

    effective_theme = theme_name or info.get("default_theme", "corporate_blue")
    doc_title = title or info["name"]
    doc_sub = subtitle or ""

    try:
        t_id = info["id"]
        # Word
        if t_id == "executive_report":
            return _generate_word_executive_report(file_path, doc_title, doc_sub, effective_theme)
        elif t_id == "commercial_proposal":
            return _generate_word_commercial_proposal(file_path, doc_title, doc_sub, effective_theme)
        elif t_id == "project_charter":
            return _generate_word_project_charter(file_path, doc_title, doc_sub, effective_theme)
        # Excel
        elif t_id == "financial_budget":
            return _generate_excel_financial_budget(file_path, doc_title, effective_theme)
        elif t_id == "sales_dashboard":
            return _generate_excel_sales_dashboard(file_path, doc_title, effective_theme)
        elif t_id == "project_tracker":
            return _generate_excel_project_tracker(file_path, doc_title, effective_theme)
        # PowerPoint
        elif t_id == "pitch_deck":
            return _generate_pptx_pitch_deck(file_path, doc_title, doc_sub, effective_theme)
        elif t_id == "quarterly_review":
            return _generate_pptx_quarterly_review(file_path, doc_title, doc_sub, effective_theme)
        else:
            logger.error(f"Generador no implementado para plantilla '{t_id}'.")
            return False

    except Exception as e:
        logger.error(f"Error al generar documento desde plantilla '{template_id}': {e}", exc_info=True)
        return False
