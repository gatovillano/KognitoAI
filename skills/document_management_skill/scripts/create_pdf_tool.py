# tools/create_pdf_tool.py

"""
Tool to convert Markdown content into modern, well-ordered PDF documents.
Uses the `markdown` library to convert to HTML and `WeasyPrint` for PDF generation.
Supports Mermaid diagrams via mermaid.ink.
"""

import logging
import os
import uuid
import re
import base64
from typing import Any, Type, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import markdown
from weasyprint import HTML, CSS

# Logger configuration
logger = logging.getLogger(__name__)

class CreatePDFInput(BaseModel):
    """Input schema for the Create PDF tool."""
    content: str = Field(
        ...,
        description=(
            "El contenido a convertir. DEBE ser un texto largo y estructurado. PREFERIBLEMENTE HTML. "
            "EL TAMAÑO DE PÁGINA ES ESTRICTAMENTE A4 (21cm x 29.7cm). Diseña tu HTML para que encaje en este formato: "
            "el ancho imprimible es de ~17cm (debido a márgenes de 2cm) y el alto de ~25.7cm por página. "
            "Usa clases estructuradas y evita desbordar estas dimensiones."
        )
    )
    is_html: bool = Field(
        True,
        description="DEBE ser True si envías HTML. Se recomienda encarecidamente usar HTML para evitar bloques de texto sin formato."
    )
    filename: Optional[str] = Field(
        None,
        description="Optional filename for the generated PDF. If not provided, a random name will be used."
    )
    title: Optional[str] = Field(
        "Documento Generado",
        description="The title of the document, used in the header."
    )
    custom_css: Optional[str] = Field(
        None,
        description="CSS adicional que se inyectará al final para personalizar o sobrescribir el estilo."
    )
    orientation: Optional[str] = Field(
        "portrait",
        description="Orientación de la página: 'portrait' (vertical) o 'landscape' (horizontal)."
    )
    margin: Optional[str] = Field(
        "2cm",
        description="Margen exterior de las páginas (ej. '2cm', '1.5in', '20mm')."
    )
    theme: Optional[str] = Field(
        "modern",
        description="Tema de color predefinido: 'modern', 'emerald', 'amber', 'minimalist'."
    )
    header_text: Optional[str] = Field(
        None,
        description="Texto opcional para la cabecera superior derecha. Soporta placeholders [page] y [pages]."
    )
    footer_text: Optional[str] = Field(
        None,
        description="Texto opcional para el pie de página inferior izquierdo. Soporta placeholders [page] y [pages]."
    )


class CreatePDFTool(BaseTool):
    """
    A LangChain tool that converts HTML or Markdown text into a styled PDF document.
    """
    name: str = "create_pdf_tool"
    description: str = (
        "Genera documentos PDF de CALIDAD PROFESIONAL y diseño avanzado. "
        "EL TAMAÑO DE PÁGINA ES ESTRICTAMENTE A4 (210mm x 297mm / 21cm x 29.7cm). "
        "IMPORTANTE: El CSS define márgenes de 2cm en todos los bordes para páginas normales, "
        "pero la primera página (portada) NO tiene márgenes para permitir fondos de color a página completa. "
        "El tamaño máximo de página es 21cm x 29.7cm (A4 completo). "
        "REGLAS DE DISEÑO OBLIGATORIAS PARA EL AGENTE:\n"
        "1. ESTRUCTURA PREMIUM: Usa 'is_html=True' y envía un HTML completo.\n"
        "2. DIMENSIONES ESTRICTAS: "
        "Tamaño máximo de página: 21cm x 29.7cm (A4 completo). "
        "Márgenes de página: 2cm en todos los bordes (definidos en CSS para páginas normales). "
        "Portada (primera página): SIN MÁRGENES para fondos de color a página completa. "
        "NUNCA generes HTML que exceda 21cm de ancho o 29.7cm de alto. "
        "Usa max-width: 17cm en contenedores de contenido principal.\n"
        "3. PORTADA (cover): Usa <div class='cover'><h1>Título</h1><p>Subtítulo</p></div> al inicio. "
        "La clase .cover ocupa toda la primera página A4 (21cm x 29.7cm) SIN MÁRGENES. "
        "Ideal para fondos de color o imagen de portada. No añadas márgenes negativos ni padding excesivo.\n"
        "4. CONTENIDO: Todo cuerpo de texto debe ir dentro de <div class='content'>. "
        "Las imágenes deben tener max-width: 100%. Las tablas deben tener width: 100%.\n"
        "5. COMPONENTES VISUALES CSS DISPONIBLES:\n"
        "   - <div class='card'> para resaltar secciones o datos clave.\n"
        "   - <div class='info-box'>, <div class='warning-box'>, <div class='error-box'> para notas.\n"
        "   - <div class='grid-2'> para diseños de dos columnas.\n"
        "   - <table><thead>...</thead></table> para datos comparativos.\n"
        "6. DIAGRAMAS: Incluye bloques ```mermaid para visualizaciones automáticas.\n"
        "7. ADVERTENCIA CRÍTICA: Si el contenido excede las dimensiones A4, WeasyPrint lo cortará o lo pondrá en una nueva página. "
        "Diseña el HTML para que cada página encaje perfectamente en 21cm x 29.7cm. "
        "Usa page-break-before: always en secciones largas y page-break-inside: avoid en tablas y tarjetas."
    )
    
    # Standard context attributes
    account_id: Optional[str] = Field(None, description="User account ID.")
    workspace_id: Optional[str] = Field(None, description="Current workspace ID.")
    
    args_schema: Type[BaseModel] = CreatePDFInput
    return_direct: bool = False

    
    def _process_mermaid_blocks(self, content: str) -> str:
        """
        Extremely robust detection of Mermaid diagrams.
        Matches:
        1. ```mermaid ... ```
        2. ``` ... (starting with graph/etc) ... ```
        3. <pre><code class="language-mermaid"> ... </code></pre>
        4. Generic <pre> or <code> blocks that START with mermaid keywords.
        """
        mermaid_keywords = (
            r'graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|'
            r'erDiagram|journey|gantt|pie|quadrantChart|requirementDiagram|'
            r'gitGraph|C4Context|mindmap|timeline|zenuml|architecture'
        )

        def replace_mermaid(match):
            # Try to get the code from the first non-empty capturing group
            mermaid_code = next((g for g in match.groups() if g is not None), "").strip()
            
            # If the code is missing or too short, return original
            if not mermaid_code or len(mermaid_code) < 10:
                return match.group(0)

            # Check if it looks like mermaid (either by tag or by content start)
            is_explicit = 'mermaid' in match.group(0).lower()
            starts_with_keyword = re.match(rf'^({mermaid_keywords})', mermaid_code, re.IGNORECASE)
            
            if not (is_explicit or starts_with_keyword):
                return match.group(0) # Not a mermaid block

            # Cleanup: decodificar posibles escapes si viene de HTML
            mermaid_code = (mermaid_code
                .replace('&lt;', '<')
                .replace('&gt;', '>')
                .replace('&amp;', '&')
                .replace('&quot;', '"')
                .replace('&#039;', "'")
            )

            # Ensure the first line is exactly the keyword if it was detected by content
            # (Mermaid rendering can fail if there's leading garbage)
            logger.info(f"Processing Mermaid block: {mermaid_code[:40]}...")
            
            try:
                # Use mermaid.ink for rendering
                mermaid_bytes = mermaid_code.encode('utf-8')
                mermaid_base64 = base64.b64encode(mermaid_bytes).decode('utf-8')
                image_url = f"https://mermaid.ink/img/{mermaid_base64}"
                
                # We return a centered div for the image
                return (
                    f'\n\n<div class="mermaid-diagram" style="text-align:center; margin:2.5em 0; padding:1.5em; '
                    f'background:#f8f9fa; border:1px solid #e9ecef; border-radius:12px; page-break-inside:avoid;">'
                    f'<img src="{image_url}" alt="Diagrama Mermaid" style="max-width:100%; height:auto; display:inline-block;" />'
                    f'</div>\n\n'
                )
            except Exception as e:
                logger.error(f"Error rendering mermaid: {e}")
                return match.group(0)

        # 1. Regex for Markdown blocks (tagged or untagged)
        # r'```(?:mermaid)?\s*([\s\S]*?)\s*```'
        content = re.sub(r'```(?:mermaid)?\s*([\s\S]*?)\s*```', replace_mermaid, content, flags=re.IGNORECASE)

        # 2. Regex for HTML blocks: <pre><code>...</code></pre> (with or without class)
        content = re.sub(r'<pre[^>]*>(?:\s*<code[^>]*>)?([\s\S]*?)(?:</code>\s*)?</pre>', replace_mermaid, content, flags=re.IGNORECASE)
        
        # 3. Final cleanup for orphaned mermaid code tags just in case
        content = re.sub(r'<code[^>]*class="[^"]*mermaid[^"]*"[^>]*>([\s\S]*?)</code>', replace_mermaid, content, flags=re.IGNORECASE)

        return content



    def _format_css_string(self, text: str) -> str:
        """Format string replacing placeholders with CSS counters."""
        escaped = text.replace('"', '\\"')
        # Split by [page] and [pages] to insert them outside the CSS quotes
        parts = re.split(r'(\[page\]|\[pages\])', escaped)
        formatted_parts = []
        for part in parts:
            if part == '[page]':
                formatted_parts.append('counter(page)')
            elif part == '[pages]':
                formatted_parts.append('counter(pages)')
            elif part:
                formatted_parts.append(f'"{part}"')
        return " ".join(formatted_parts)

    def _get_modern_css(
        self,
        orientation: str = "portrait",
        margin: str = "2cm",
        theme: str = "modern",
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> str:
        """Returns a high-end professional CSS string for the PDF styling."""
        # Theme mapping
        if theme == "emerald":
            primary = "#10b981"
            primary_light = "#ecfdf5"
            primary_dark = "#047857"
            secondary = "#64748b"
        elif theme == "amber":
            primary = "#f59e0b"
            primary_light = "#fffbeb"
            primary_dark = "#b45309"
            secondary = "#78716c"
        elif theme == "minimalist":
            primary = "#0f172a"
            primary_light = "#f8fafc"
            primary_dark = "#000000"
            secondary = "#475569"
        else:  # modern (default)
            primary = "#2563eb"
            primary_light = "#eff6ff"
            primary_dark = "#1e40af"
            secondary = "#64748b"

        # Headers and footers
        header_val = header_text if header_text is not None else "Página [page] de [pages]"
        footer_val = footer_text if footer_text is not None else "Generado por KAI AI System"

        css_header = self._format_css_string(header_val)
        css_footer = self._format_css_string(footer_val)

        return f"""
        @page {{
            size: A4 {orientation};
            margin: {margin};
            @top-right {{
                content: {css_header};
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #a0aec0;
            }}
            @bottom-left {{
                content: {css_footer};
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #a0aec0;
            }}
        }}

        /* Página sin márgenes para portadas completas */
        @page :first {{
            margin: 0;
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
        }}
        
        :root {{
            --primary: {primary};
            --primary-light: {primary_light};
            --primary-dark: {primary_dark};
            --secondary: {secondary};
            --dark: #1e293b;
            --light: #f8fafc;
            --border: #e2e8f0;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }}

        body {{
            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--dark);
        }}

        .content {{
            max-width: 17cm;
            margin: 0 auto;
        }}

        /* === PORTADAS (COVERS) === */
        .cover-classic {{
            width: 100%;
            height: 29.7cm;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background-color: var(--primary-dark);
            color: #ffffff;
            padding: 2cm;
            box-sizing: border-box;
            page-break-after: always;
        }}
        .cover-classic h1 {{
            font-size: 32pt;
            margin-bottom: 0.3em;
            color: #ffffff;
            border: none;
            line-height: 1.2;
        }}
        .cover-classic .subtitle {{
            font-size: 14pt;
            color: var(--primary-light);
            max-width: 14cm;
            margin: 0 auto;
        }}
        .cover-classic .meta {{
            font-size: 10pt;
            color: #e2e8f0;
            margin-top: 3em;
        }}

        .cover-modern {{
            width: 100%;
            height: 29.7cm;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background: linear-gradient(135deg, var(--primary-dark) 0%, #0f172a 100%);
            color: #ffffff;
            padding: 3cm 2cm;
            box-sizing: border-box;
            page-break-after: always;
        }}
        .cover-modern h1 {{
            font-size: 36pt;
            font-weight: 800;
            color: #ffffff;
            border: none;
            margin-top: 2cm;
            line-height: 1.1;
        }}
        .cover-modern .subtitle {{
            font-size: 16pt;
            color: var(--primary-light);
            margin-top: 0.5em;
        }}
        .cover-modern .meta {{
            border-top: 2px solid var(--primary);
            padding-top: 1.5em;
            font-size: 10pt;
            color: #94a3b8;
        }}

        .cover-minimal {{
            width: 100%;
            height: 29.7cm;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background-color: var(--light);
            color: var(--dark);
            padding: 3cm;
            box-sizing: border-box;
            page-break-after: always;
        }}
        .cover-minimal h1 {{
            font-size: 40pt;
            font-weight: 900;
            color: var(--primary-dark);
            border: none;
            text-align: left;
            line-height: 1.05;
            margin-bottom: 0.5em;
        }}
        .cover-minimal .subtitle {{
            font-size: 16pt;
            color: var(--secondary);
            text-align: left;
            margin-bottom: 2em;
        }}
        .cover-minimal .meta {{
            font-size: 10pt;
            color: var(--secondary);
            border-top: 1px solid var(--border);
            padding-top: 1em;
            margin-top: 2cm;
        }}

        /* === TIPOGRAFÍA === */
        h1 {{
            color: var(--dark);
            border-bottom: 3px solid var(--primary);
            padding-bottom: 0.3em;
            margin-top: 1.5em;
            font-size: 22pt;
            font-weight: 800;
        }}
        h2 {{
            color: var(--primary);
            margin-top: 1.8em;
            font-size: 16pt;
            font-weight: 700;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.2em;
        }}
        h3 {{
            color: var(--secondary);
            margin-top: 1.5em;
            font-size: 12pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        p {{ margin-bottom: 1em; text-align: justify; }}
        .lead {{
            font-size: 1.2em;
            font-weight: 500;
            color: var(--secondary);
            line-height: 1.6;
        }}
        .divider {{
            margin: 2em 0;
            border: 0;
            height: 1px;
            background: var(--border);
        }}

        /* === COMPONENTES === */
        .card {{
            background: var(--light);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5em;
            margin: 1.5em 0;
            page-break-inside: avoid;
        }}
        .card-accent {{
            background: var(--light);
            border: 1px solid var(--border);
            border-left: 5px solid var(--primary);
            border-radius: 4px 12px 12px 4px;
            padding: 1.5em;
            margin: 1.5em 0;
            page-break-inside: avoid;
        }}

        .info-box, .warning-box, .error-box, .success-box, .note-box {{
            padding: 1em 1.5em;
            border-radius: 8px;
            margin: 1.5em 0;
            border-left: 5px solid;
            page-break-inside: avoid;
        }}
        .info-box {{ background: #eff6ff; border-color: var(--primary); color: #1e40af; }}
        .warning-box {{ background: #fffbeb; border-color: var(--warning); color: #92400e; }}
        .error-box {{ background: #fef2f2; border-color: var(--error); color: #991b1b; }}
        .success-box {{ background: #ecfdf5; border-color: var(--success); color: #065f46; }}
        .note-box {{ background: var(--light); border-color: var(--secondary); color: var(--dark); }}

        /* === GRID LAYOUT === */
        .grid-2, .grid-3, .grid-4 {{
            display: flex;
            gap: 20px;
            margin: 1.5em 0;
            page-break-inside: avoid;
        }}
        .grid-2 > div {{ flex: 1; }}
        .grid-3 > div {{ flex: 1; }}
        .grid-4 > div {{ flex: 1; }}

        /* === BADGES / ETIQUETAS === */
        .badge {{
            display: inline-block;
            padding: 0.25em 0.6em;
            font-size: 75%;
            font-weight: 700;
            line-height: 1;
            text-align: center;
            white-space: nowrap;
            vertical-align: baseline;
            border-radius: 10rem;
        }}
        .badge-primary {{ background-color: var(--primary-light); color: var(--primary-dark); }}
        .badge-success {{ background-color: #d1fae5; color: #065f46; }}
        .badge-warning {{ background-color: #fef3c7; color: #92400e; }}
        .badge-error {{ background-color: #fee2e2; color: #991b1b; }}

        /* === TABLAS === */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2em 0;
            font-size: 9.5pt;
            page-break-inside: avoid;
        }}
        th {{
            background-color: var(--light);
            color: var(--dark);
            font-weight: 700;
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border);
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
        }}
        .table-striped tr:nth-child(even) {{ background-color: var(--light); }}
        .table-bordered td, .table-bordered th {{ border: 1px solid var(--border); }}
        .table-dense td, .table-dense th {{ padding: 6px 8px; }}

        /* === UTILIDADES === */
        code {{
            background-color: var(--light);
            padding: 0.2em 0.4em;
            border-radius: 4px;
            font-family: 'Fira Code', 'DejaVu Sans Mono', monospace;
            font-size: 0.9em;
            color: #be185d;
        }}
        pre {{
            background-color: #0f172a;
            color: #f8fafc;
            padding: 1.2em;
            border-radius: 10px;
            font-size: 9pt;
            margin-bottom: 1.5em;
            border-left: 5px solid var(--primary);
            white-space: pre-wrap;
            page-break-inside: avoid;
        }}
        .page-break {{ page-break-before: always; }}
        .no-break {{ page-break-inside: avoid; }}
        .text-center {{ text-align: center; }}
        .text-left {{ text-align: left; }}
        .text-right {{ text-align: right; }}
        .text-justify {{ text-align: justify; }}
        """

    def _repair_markdown(self, content: str) -> str:
        """
        Attempts to repair malformed markdown where newlines might be missing
        or escaped.
        """
        # 1. Replace literal \n and \r\n (common in JSON strings from LLMs)
        content = content.replace('\\n', '\n').replace('\\r', '')
        
        # 2. Ensure headers have a blank line before them if they follow text
        # Pattern: (any non-space char) (any whitespace) (#+ space)
        content = re.sub(r'([^\s])\s*(#{1,6}\s)', r'\1\n\n\2', content)
        
        # 3. Ensure lists have a blank line before them
        # Pattern: (any non-space char) (any whitespace) (list marker space)
        content = re.sub(r'([^\s])\s*([\*\-\+]\s|\d+\.\s)', r'\1\n\n\2', content)
        
        # 4. Force newlines around horizontal rules
        content = re.sub(r'(?<=\S)\s+(---|___|\*\*\*)\s+', r'\n\n\1\n\n', content)
        
        return content

    async def _arun(
        self, 
        content: str, 
        is_html: bool = False, 
        filename: Optional[str] = None, 
        title: str = "Documento Generado",
        custom_css: Optional[str] = None,
        orientation: str = "portrait",
        margin: str = "2cm",
        theme: str = "modern",
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """
        Executes the tool logic asynchronously.
        """
        logger.info(f"Generating PDF from {'HTML' if is_html else 'Markdown'}. Title: {title}")
        
        if not content or len(content.strip()) < 10:
            return {
                "context_for_llm": "Error: El contenido proporcionado para el PDF es demasiado corto o está vacío. Por favor, genera un contenido sustancial antes de crear el PDF.",
                "sources": []
            }
        
        try:
            # 0. Cleanup old files
            from utils.file_cleanup import cleanup_old_generated_files
            cleanup_old_generated_files()
            
            # 1. Create directory for generated media using absolute MEDIA_ROOT
            from api.galleries import MEDIA_ROOT
            
            # Ensure MEDIA_ROOT is absolute
            absolute_media_root = os.path.abspath(MEDIA_ROOT)
            output_dir = os.path.abspath(os.path.join(absolute_media_root, "generated_pdfs"))
            
            # Security check: verify that output_dir is within MEDIA_ROOT (prevent path traversal)
            try:
                common_path = os.path.commonpath([absolute_media_root, output_dir])
                if common_path != absolute_media_root:
                    raise ValueError("El directorio de salida no está dentro de MEDIA_ROOT.")
            except Exception as path_err:
                logger.error(f"❌ Error de validación de seguridad de ruta: {path_err}")
                raise ValueError(f"Acceso denegado: El directorio de salida debe estar aislado dentro de MEDIA_ROOT. Detalle: {path_err}")
            
            # Fallback and validation mechanism for write permissions
            is_writable = False
            
            # Check if exists and test write permission
            if os.path.exists(output_dir):
                test_file = os.path.join(output_dir, f".write_test_{uuid.uuid4().hex}")
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    is_writable = True
                except (PermissionError, OSError) as write_err:
                    logger.warning(f"⚠️ El directorio {output_dir} existe pero no es escribible: {write_err}. Intentando resolver...")
                    # Parent directory is usually writable. Try to rename it.
                    try:
                        backup_dir = os.path.join(absolute_media_root, f"generated_pdfs_backup_{uuid.uuid4().hex[:6]}")
                        os.rename(output_dir, backup_dir)
                        logger.info(f"✅ Se renombró el directorio no escribible a: {backup_dir}")
                    except Exception as rename_err:
                        logger.error(f"❌ No se pudo renombrar el directorio no escribible: {rename_err}")
                        # Fallback to a fallback folder name under MEDIA_ROOT
                        output_dir = os.path.abspath(os.path.join(absolute_media_root, "generated_pdfs_fallback"))
            
            # Ensure output directory exists
            try:
                os.makedirs(output_dir, exist_ok=True)
                # Test write on the newly created or fallback directory
                test_file = os.path.join(output_dir, f".write_test_{uuid.uuid4().hex}")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                is_writable = True
            except (PermissionError, OSError) as create_err:
                logger.error(f"❌ No se pudo crear o escribir en el directorio ({output_dir}): {create_err}. Usando fallback local en el workspace.")
                # Local workspace fallback
                output_dir = os.path.abspath("media/generated_pdfs")
                os.makedirs(output_dir, exist_ok=True)
                
                # Test write on the local fallback
                test_file = os.path.join(output_dir, f".write_test_{uuid.uuid4().hex}")
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    is_writable = True
                except (PermissionError, OSError) as local_err:
                    logger.critical(f"❌ ERROR CRÍTICO: Tampoco es posible escribir en el fallback local ({output_dir}): {local_err}")
                    raise PermissionError(f"No hay permisos de escritura en ningún directorio de salida disponible: {local_err}")
            
            # 2. Determine final filename with uniqueness to avoid caching
            suffix = uuid.uuid4().hex[:4]
            if not filename:
                filename = f"doc_{uuid.uuid4().hex[:8]}.pdf"
            else:
                # Add suffix before extension
                name_part, ext_part = os.path.splitext(filename)
                if not ext_part:
                    ext_part = ".pdf"
                filename = f"{name_part}_{suffix}{ext_part}"
            
            # Clean filename
            filename = re.sub(r'[^\w\.-]', '_', filename)
            file_path = os.path.abspath(os.path.join(output_dir, filename))
            
            # Security check: verify that file_path is within output_dir
            try:
                common_path = os.path.commonpath([output_dir, file_path])
                if common_path != output_dir:
                    raise ValueError("El archivo destino no está dentro del directorio de salida.")
            except Exception as path_err:
                logger.error(f"❌ Error de validación de seguridad de archivo: {path_err}")
                raise ValueError(f"Acceso denegado: El archivo destino debe estar aislado dentro del directorio de salida.")
            
            # 3. Process content based on is_html flag
            
            # Robust auto-detection: If it has clear HTML tags, treat as HTML
            has_html_tags = re.search(r'<\s*[a-z!/]', content, re.IGNORECASE)
            has_markdown_indicators = re.search(r'^#{1,6}\s|\n#{1,6}\s|\*\*|---|^\s*[\*\-\+]\s|\n\s*[\*\-\+]\s', content, re.MULTILINE)
            
            if is_html and has_markdown_indicators and not has_html_tags:
                logger.warning("Content marked as HTML but looks like Markdown. Forcing Markdown processing.")
                is_html = False
            elif not is_html and has_html_tags:
                logger.info("Content contains HTML tags. Treating as HTML.")
                is_html = True

            # Generate the dynamic base CSS block
            modern_css = self._get_modern_css(
                orientation=orientation,
                margin=margin,
                theme=theme,
                header_text=header_text,
                footer_text=footer_text
            )
            
            custom_css_style = f"\n<style>\n{custom_css}\n</style>\n" if custom_css else ""

            if is_html:
                content = self._process_mermaid_blocks(content)
                is_full_doc = re.search(r'<(html|body|head)', content, re.IGNORECASE)
                if is_full_doc:
                    # Inject CSS into full HTML head
                    css_to_inject = f"\n<style>\n{modern_css}\n</style>\n" + custom_css_style
                    if re.search(r'</head>', content, re.IGNORECASE):
                        full_html = re.sub(r'(</head>)', f"{css_to_inject}\\1", content, flags=re.IGNORECASE, count=1)
                    elif re.search(r'<body>', content, re.IGNORECASE):
                        full_html = re.sub(r'(<body>)', f"\\1{css_to_inject}", content, flags=re.IGNORECASE, count=1)
                    else:
                        full_html = css_to_inject + content
                else:
                    full_html = f"""
                    <!DOCTYPE html>
                    <html lang="es">
                    <head>
                        <meta charset="UTF-8">
                        <title>{title}</title>
                        <style>
                            {modern_css}
                            .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                            .content li {{ margin-bottom: 5px; }}
                            .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                        </style>
                        {custom_css_style}
                    </head>
                    <body>
                        <div class="footer">Generado por KAI - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                        <div class="content">
                            {content}
                        </div>
                    </body>
                    </html>
                    """
            else:
                repaired_content = self._repair_markdown(content)
                processed_content = self._process_mermaid_blocks(repaired_content)
                final_html_body = markdown.markdown(
                    processed_content, 
                    extensions=['extra', 'toc', 'nl2br', 'sane_lists']
                )
                full_html = f"""
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <title>{title}</title>
                    <style>
                        {modern_css}
                        .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                        .content li {{ margin-bottom: 5px; }}
                        .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                    </style>
                    {custom_css_style}
                </head>
                <body>
                    <div class="footer">Generado por KAI - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                    <div class="content">
                        {final_html_body}
                    </div>
                </body>
                </html>
                """
            
            # 5. Generate PDF using WeasyPrint
            import asyncio
            loop = asyncio.get_event_loop()
            workspace_dir = os.getcwd()
            
            await loop.run_in_executor(
                None,
                lambda: HTML(string=full_html, base_url=workspace_dir).write_pdf(file_path)
            )
            
            logger.info(f"✅ PDF successfully generated at: {file_path}")
            
            # Automatically save to OnlyOffice documents cloud if account_id is present
            onlyoffice_saved = False
            onlyoffice_doc_id = None
            if self.account_id:
                try:
                    import shutil
                    from core.database import SessionLocal, Document
                    from core.config import settings
                    
                    onlyoffice_docs_root = settings.onlyoffice_docs_root
                    onlyoffice_user_dir = os.path.join(onlyoffice_docs_root, self.account_id)
                    os.makedirs(onlyoffice_user_dir, exist_ok=True)
                    
                    onlyoffice_unique_filename = f"{uuid.uuid4().hex}.pdf"
                    onlyoffice_file_path = os.path.join(onlyoffice_user_dir, onlyoffice_unique_filename)
                    
                    # Copy the generated PDF file to OnlyOffice documents path
                    shutil.copy2(file_path, onlyoffice_file_path)
                    
                    # DB Registration
                    acc_id = uuid.UUID(self.account_id)
                    wsp_id = None
                    if self.workspace_id and self.workspace_id != "null":
                        try:
                            wsp_id = uuid.UUID(self.workspace_id)
                        except ValueError:
                            pass
                    
                    display_filename = filename
                    if not display_filename.lower().endswith(".pdf"):
                        display_filename = f"{display_filename}.pdf"
                    
                    AGENT_PDF_FOLDER_NAME = "🤖 Documentos PDF (Agente)"

                    async with SessionLocal() as db:
                        from sqlalchemy import select
                        from core.database import DocumentFolder

                        # Find or create dedicated folder for agent-generated PDFs
                        stmt = select(DocumentFolder).where(
                            DocumentFolder.account_id == acc_id,
                            DocumentFolder.name == AGENT_PDF_FOLDER_NAME,
                            DocumentFolder.parent_id == None
                        )
                        if wsp_id:
                            stmt = stmt.where(DocumentFolder.workspace_id == wsp_id)
                        else:
                            stmt = stmt.where(DocumentFolder.workspace_id == None)

                        res = await db.execute(stmt)
                        agent_folder = res.scalars().first()

                        if not agent_folder:
                            agent_folder = DocumentFolder(
                                account_id=acc_id,
                                workspace_id=wsp_id,
                                parent_id=None,
                                name=AGENT_PDF_FOLDER_NAME
                            )
                            db.add(agent_folder)
                            await db.commit()
                            await db.refresh(agent_folder)

                        new_doc = Document(
                            account_id=acc_id,
                            workspace_id=wsp_id,
                            folder_id=agent_folder.id,
                            filename=display_filename,
                            extension="pdf",
                            file_path=os.path.join(self.account_id, onlyoffice_unique_filename)
                        )
                        db.add(new_doc)
                        await db.commit()
                        await db.refresh(new_doc)
                        onlyoffice_saved = True
                        onlyoffice_doc_id = str(new_doc.id)
                        logger.info(f"PDF automatically saved to OnlyOffice documents cloud in folder '{AGENT_PDF_FOLDER_NAME}'. ID: {new_doc.id}")
                except Exception as oo_err:
                    logger.error(f"Error automatically saving PDF to OnlyOffice documents cloud: {oo_err}", exc_info=True)

            # Construct the download URL using the absolute API server URL
            from core.config import settings
            base_url = settings.api_server_url.rstrip("/")
            folder_name = os.path.basename(output_dir)
            download_url = f"{base_url}/media/{folder_name}/{filename}"
            
            context_msg = f"PDF generado exitosamente: '{title}'."
            if onlyoffice_saved:
                context_msg += f" El documento también se guardó automáticamente en la nube de OnlyOffice (ID: {onlyoffice_doc_id})."
            context_msg += f" La URL de descarga es: {download_url}. El usuario puede descargarlo desde el archivo adjunto o usando este enlace."

            # Return structured output with sources so it renders as an attachment
            return {
                "context_for_llm": context_msg,
                "sources": [
                    {
                        "id": 1,
                        "title": f"📄 PDF: {title}",
                        "url": download_url,
                        "snippet": f"Documento PDF generado a partir de {'HTML' if is_html else 'Markdown'} con diseño moderno y soporte para diagramas. Título: {title}",
                        "type": "document",
                        "metadata": {
                            "filename": filename,
                            "file_path": file_path,
                            "generated_at": datetime.now().isoformat(),
                            "size_hint": "A4",
                            "onlyoffice_document_id": onlyoffice_doc_id if onlyoffice_saved else None
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            return {
                "context_for_llm": f"Ocurrió un error al intentar generar el PDF: {e}",
                "sources": []
            }

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous execution is not supported."""
        raise NotImplementedError("create_pdf_tool does not support synchronous execution.")