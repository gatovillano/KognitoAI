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
        description="El contenido a convertir. DEBE ser un texto largo y estructurado. PREFERIBLEMENTE HTML con etiquetas estructuradas (h2, p, ul, table). NUNCA envíes este campo vacío."
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

class CreatePDFTool(BaseTool):
    """
    A LangChain tool that converts HTML or Markdown text into a styled PDF document.
    """
    name: str = "create_pdf_tool"
    description: str = (
        "Crea un documento PDF profesional y estilizado. "
        "REGLAS DE FORMATO OBLIGATORIAS:\n"
        "1. USA HTML SIEMPRE: Escribe el contenido en HTML y establece 'is_html' en True.\n"
        "2. ESTRUCTURA: Usa etiquetas <h2>, <h3>, <p>, <ul>/<li>.\n"
        "3. TABLAS: Usa etiquetas <table> para datos estructurados.\n"
        "4. DIAGRAMAS: Soporta Mermaid. Usa bloques ```mermaid ... ``` o <pre><code>graph ...</code></pre>. "
        "Se convertirán automáticamente en imágenes de alta calidad en el PDF."
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



    def _get_modern_css(self) -> str:
        """Returns a modern CSS string for the PDF styling."""
        return """
        @page {
            size: A4;
            margin: 1.5cm;
            @top-right {
                content: "Página " counter(page) " de " counter(pages);
                font-family: 'DejaVu Sans', sans-serif;
                font-size: 7pt;
                color: #999;
            }
            @bottom-left {
                content: element(footer);
            }
        }
        body {
            font-family: 'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', 'DejaVu Sans', Arial, sans-serif;
            line-height: 1.5;
            color: #2d3436;
            background-color: #fff;
            font-size: 10pt;
        }

        h1 {
            color: #2d3436;
            border-bottom: 2.5px solid #0984e3;
            padding-bottom: 8px;
            margin-top: 0;
            font-size: 18pt;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        h2 {
            color: #0984e3;
            margin-top: 1.5em;
            border-bottom: 1px solid #dfe6e9;
            padding-bottom: 4px;
            font-size: 14pt;
            font-weight: 700;
        }

        h3 {
            color: #636e72;
            margin-top: 1.2em;
            font-size: 11pt;
            font-weight: 600;
        }

        p {
            margin-bottom: 0.8em;
            text-align: justify;
        }

        code {
            background-color: #f1f2f6;
            padding: 1px 3px;
            border-radius: 3px;
            font-family: 'DejaVu Sans Mono', monospace;
            font-size: 0.85em;
            color: #d63031;
        }

        pre {
            background-color: #2d3436;
            color: #f1f2f6;
            padding: 10px;
            border-radius: 6px;
            overflow-x: auto;
            margin-bottom: 1.2em;
            font-size: 8pt;
            line-height: 1.3;
            border-left: 4px solid #0984e3;
        }

        blockquote {
            margin: 1em 0;
            padding: 8px 16px;
            border-left: 4px solid #0984e3;
            color: #636e72;
            font-style: italic;
            background-color: #f9f9f9;
            border-radius: 0 4px 4px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5em;
            font-size: 8.5pt;
        }

        th, td {
            padding: 8px 10px;
            border: 1px solid #dfe6e9;
            text-align: left;
        }

        th {
            background-color: #f1f2f6;
            font-weight: 700;
            color: #2d3436;
        }

        tr:nth-child(even) {
            background-color: #fafafa;
        }

        .footer {
            position: running(footer);
            font-size: 7pt;
            color: #b2bec3;
            text-align: left;
            border-top: 1px solid #dfe6e9;
            padding-top: 4px;
        }

        /* List styles */
        ul, ol {
            margin-bottom: 1em;
            padding-left: 1.5em;
        }

        li {
            margin-bottom: 0.3em;
        }
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

    async def _arun(self, content: str, is_html: bool = False, filename: Optional[str] = None, title: str = "Documento Generado", **kwargs: Any) -> Any:
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
            output_dir = os.path.join(MEDIA_ROOT, "generated_pdfs")
            os.makedirs(output_dir, exist_ok=True)
            
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
            file_path = os.path.join(output_dir, filename)
            
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

            if is_html:
                # 3a. Process Mermaid blocks even in HTML (they might be inside pre/code or just blocks)
                content = self._process_mermaid_blocks(content)
                
                # Check if it's a full document or just a fragment
                is_full_doc = re.search(r'<(html|body|head)', content, re.IGNORECASE)
                if is_full_doc:
                    # It's a full document, use it as is
                    full_html = content
                else:
                    # It's a fragment, wrap it in our modern boilerplate
                    final_html_body = content
                    full_html = f"""
                    <!DOCTYPE html>
                    <html lang="es">
                    <head>
                        <meta charset="UTF-8">
                        <title>{title}</title>
                        <style>
                            {self._get_modern_css()}
                            .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                            .content li {{ margin-bottom: 5px; }}
                            .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="footer">Generado por KAI - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                        <div class="content">
                            {final_html_body}
                        </div>
                    </body>
                    </html>
                    """
            else:
                # Repair structure (fix missing newlines)
                repaired_content = self._repair_markdown(content)
                
                # Process Mermaid blocks before markdown conversion
                processed_content = self._process_mermaid_blocks(repaired_content)
                
                # Convert Markdown to HTML using 'extra' for full feature support
                final_html_body = markdown.markdown(
                    processed_content, 
                    extensions=['extra', 'toc', 'nl2br', 'sane_lists']
                )

                
                # Wrap fragment in boilerplate
                full_html = f"""
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <title>{title}</title>
                    <style>
                        {self._get_modern_css()}
                        .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                        .content li {{ margin-bottom: 5px; }}
                        .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                    </style>
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
            
            await loop.run_in_executor(
                None,
                lambda: HTML(string=full_html).write_pdf(file_path)
            )
            
            logger.info(f"✅ PDF successfully generated at: {file_path}")
            
            # Construct the download URL using the absolute API server URL
            from core.config import settings
            base_url = settings.api_server_url.rstrip("/")
            download_url = f"{base_url}/media/generated_pdfs/{filename}"
            
            # Return structured output with sources so it renders as an attachment
            return {
                "context_for_llm": f"PDF generado exitosamente: '{title}'. La URL de descarga es: {download_url}. El usuario puede descargarlo desde el archivo adjunto o usando este enlace.",
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
                            "size_hint": "A4"
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