# telegram_gateway/helpers.py - Utilidades de formato y paginación (sin deps de core)

"""
Módulo de Utilidad con Funciones de Ayuda Generales y Paginación.

Combina las funciones de utils/helpers.py y utils/paginator.py sin
ninguna dependencia del módulo core.
"""

import logging
import html
import re
import uuid
from typing import List, Tuple, Optional

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Funciones de helpers (de utils/helpers.py)
# ---------------------------------------------------------------------------

def markdown_to_telegram_html(text: str) -> str:
    """
    Convierte Markdown a un formato HTML compatible con Telegram de forma robusta.
    Escapa de forma segura los caracteres HTML para evitar errores de parseo (BadRequest),
    e impide que los asteriscos de las viñetas se interpreten como marcas de cursiva.
    """
    if not text:
        return ""

    # 1. Extraer bloques de código (```) para protegerlos de transformaciones
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        placeholder = f"CODE-BLOCK-PLACEHOLDER-{len(code_blocks)}"
        escaped_code = html.escape(code)
        if lang:
            tag = f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
        else:
            tag = f'<pre>{escaped_code}</pre>'
        code_blocks.append(tag)
        return placeholder

    text = re.sub(r'```(\w*)\n(.*?)\n```', save_code_block, text, flags=re.DOTALL)
    text = re.sub(r'```(\w*)(.*?)\n?```', save_code_block, text, flags=re.DOTALL)

    # 2. Convertir tablas Markdown a bloques de código alineados y protegerlos en code_blocks.
    # El regex tolera líneas vacías/espacios intermedias en la tabla.
    table_regex = re.compile(
        r"((?:^[ \t]*[^\n]*\|[^\n]*\n)"
        r"(?:[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*\n)"
        r"(?:[ \t]*[^\n]*\|[^\n]*(?:\n|$)|[ \t]*\n)+)",
        re.MULTILINE
    )
    def save_table_block(match):
        md_table = match.group(1)
        try:
            aligned = align_markdown_table(md_table)
            escaped_table = html.escape(aligned)
            tag = f'<pre><code>{escaped_table}</code></pre>'
            placeholder = f"CODE-BLOCK-PLACEHOLDER-{len(code_blocks)}"
            code_blocks.append(tag)
            return f"\n{placeholder}\n"
        except Exception as e:
            logger.error(f"Error procesando tabla en markdown_to_telegram_html: {e}", exc_info=True)
            return md_table

    text = table_regex.sub(save_table_block, text)

    # 3. Extraer código en línea (`) después de haber procesado y protegido las tablas
    inline_codes = []
    def save_inline_code(match):
        code = match.group(1)
        placeholder = f"INLINE-CODE-PLACEHOLDER-{len(inline_codes)}"
        tag = f"<code>{html.escape(code)}</code>"
        inline_codes.append(tag)
        return placeholder

    text = re.sub(r'`(.*?)`', save_inline_code, text)

    # 4. Escapar todos los caracteres HTML generales (&, <, >) del resto del texto
    text = html.escape(text)

    # 5. Procesar encabezados (# Título) por línea
    lines = text.split('\n')
    for i, line in enumerate(lines):
        lines[i] = re.sub(r'^(#{1,6})\s+(.*?)$', r'<b>\2</b>', line)
    text = '\n'.join(lines)

    # 6. Convertir enlaces markdown: [texto](url) -> <a href="url">texto</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', text)

    # 7. Negrita: **texto** o __texto__ -> <b>texto</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    # 8. Tachado: ~~texto~~ -> <s>texto</s>
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)

    # 9. Cursiva: *texto* y _texto_ (evitando asteriscos de viñetas al inicio de línea)
    text = re.sub(r'(?<!\w)\*(?!\s)([^*]+?)(?<!\s)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(?!\s)([^_]+?)(?<!\s)_(?!\w)', r'<i>\1</i>', text)

    # 10. Limpiar viñetas de listas: cambiar * o - al inicio de línea por •
    text = re.sub(r'^(\s*)[*-]\s+', r'\1• ', text, flags=re.MULTILINE)

    # 11. Restaurar los bloques de código y código en línea protegidos
    for i, tag in enumerate(inline_codes):
        text = text.replace(f"INLINE-CODE-PLACEHOLDER-{i}", tag)

    for i, tag in enumerate(code_blocks):
        text = text.replace(f"CODE-BLOCK-PLACEHOLDER-{i}", tag)

    # 12. Limpiar escapes excesivos de comillas para mejor lectura en texto plano
    text = text.replace("&quot;", '"').replace("&#x27;", "'").replace("&apos;", "'")
    return text

def clean_markdown_for_table(text: str) -> str:
    """
    Elimina formato markdown (negrita, cursiva, enlaces, backticks) para que no rompa
    la visualización ni el espaciado monoespaciado en Telegram.
    """
    if not text:
        return ""
    # Strip links: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Strip bold/italic/strike-through markers and backticks
    text = re.sub(r'\*\*|__|\*|_|~~|`', '', text)
    return text

def parse_markdown_table(md_table_str: str):
    """Parsea una tabla markdown en encabezados y filas de datos, limpiando su formato."""
    lines = [line.strip() for line in md_table_str.strip().split('\n')]
    if len(lines) < 3:
        return None
    
    # Extraer encabezados y eliminar columnas vacías iniciales/finales
    headers_raw = lines[0].split('|')
    if headers_raw[0] == "": headers_raw.pop(0)
    if headers_raw[-1] == "": headers_raw.pop()
    headers = [clean_markdown_for_table(col.strip()) for col in headers_raw]
    
    # Extraer filas
    rows = []
    for line in lines[2:]:
        if '|' in line:
            cols_raw = line.split('|')
            if cols_raw[0] == "": cols_raw.pop(0)
            if cols_raw[-1] == "": cols_raw.pop()
            cols = [clean_markdown_for_table(col.strip()) for col in cols_raw]
            rows.append(cols)
    return {"headers": headers, "rows": rows}

def align_markdown_table(md_table_str: str) -> str:
    """
    Toma una tabla markdown cruda y devuelve una versión formateada y alineada
    con espacios de relleno, ideal para ser mostrada en fuentes monoespaciadas.
    """
    parsed = parse_markdown_table(md_table_str)
    if not parsed:
        return md_table_str
        
    headers = parsed["headers"]
    rows = parsed["rows"]
    
    # Calcular anchos máximos de columna
    col_widths = [len(h) for h in headers]
    for row in rows:
        for col_idx, cell in enumerate(row):
            if col_idx < len(col_widths):
                col_widths[col_idx] = max(col_widths[col_idx], len(cell))
                
    lines = []
    
    # Línea de cabecera
    header_cells = [h.ljust(col_widths[idx]) for idx, h in enumerate(headers)]
    lines.append("| " + " | ".join(header_cells) + " |")
    
    # Línea separadora
    separator_cells = ["-" * col_widths[idx] for idx in range(len(headers))]
    lines.append("|-" + "-|-".join(separator_cells) + "-|")
    
    # Filas de datos
    for row in rows:
        while len(row) < len(headers):
            row.append("")
        row_cells = [cell.ljust(col_widths[idx]) for idx, cell in enumerate(row[:len(headers)])]
        lines.append("| " + " | ".join(row_cells) + " |")
        
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Funciones y clase de paginación (de utils/paginator.py)
# ---------------------------------------------------------------------------

# Límite de caracteres de Telegram para un mensaje. Dejamos un margen de seguridad.
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def split_text_into_pages(text: str, max_chars: int = TELEGRAM_MAX_MESSAGE_LENGTH - 200) -> List[str]:
    """
    Divide un texto largo en una lista de páginas más pequeñas.

    Intenta dividir el texto de forma inteligente en saltos de línea para
    mantener la legibilidad, pero si un párrafo es demasiado largo, lo corta.

    Args:
        text: El texto completo a dividir.
        max_chars: El número máximo de caracteres por página.

    Returns:
        Una lista de cadenas, donde cada cadena es una página.
    """
    if not text:
        return []

    pages = []
    current_page = ""
    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        # Si el párrafo en sí es más largo que el máximo, lo dividimos a la fuerza.
        while len(paragraph) > max_chars:
            part = paragraph[:max_chars]
            if current_page:  # Si ya hay contenido en la página, la cerramos
                pages.append(current_page)
            pages.append(part)
            current_page = ""
            paragraph = paragraph[max_chars:]

        # Si añadir el siguiente párrafo excede el límite, cerramos la página actual.
        if len(current_page) + len(paragraph) + 1 > max_chars:
            if current_page:
                pages.append(current_page)
            current_page = paragraph
        else:
            if current_page:
                current_page += "\n" + paragraph
            else:
                current_page = paragraph

    # Añadir la última página si queda algo.
    if current_page:
        pages.append(current_page)

    return pages


class Paginator:
    """
    Gestiona la paginación de texto largo para los mensajes de Telegram.
    """
    def __init__(self,
                 chunks: List[str],
                 title: str = "",
                 parse_mode: str = ParseMode.HTML,
                 initial_page: int = 1,
                 prefix: Optional[str] = None):
        """
        Inicializa el paginador.

        Args:
            chunks: Una lista de cadenas, donde cada cadena es una página.
            title: Un título opcional que aparecerá en el encabezado de cada página.
            parse_mode: El modo de parseo para el mensaje (HTML, MarkdownV2).
            initial_page: La página con la que comenzar (por defecto 1).
            prefix: Un prefijo opcional para el ID de la sesión, útil para depuración.
        """
        if not chunks:
            raise ValueError("La lista de chunks no puede estar vacía.")

        self.chunks = chunks
        self.title = title
        self.total_pages = len(chunks)
        self.parse_mode = parse_mode
        self.current_page = max(1, min(initial_page, self.total_pages))

        # Usa el prefijo para generar un ID de sesión más descriptivo.
        prefix_str = prefix if prefix and prefix.strip() else "paginator"
        self.session_id: str = f"{prefix_str}_{uuid.uuid4().hex[:8]}"

    def get_page(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Obtiene el texto y los botones para la página actual.
        """
        page_index = self.current_page - 1
        text_chunk = self.chunks[page_index]

        header = f"📄 <b>{self.title}</b>\n\n" if self.title else ""
        footer = f"\n\n--- Página {self.current_page}/{self.total_pages} ---"

        full_text = f"{header}{text_chunk}{footer}"

        keyboard = []
        row = []
        if self.current_page > 1:
            row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{self.session_id}:prev"))
        if self.current_page < self.total_pages:
            row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"{self.session_id}:next"))
        if row:
            keyboard.append(row)

        return full_text, InlineKeyboardMarkup(keyboard)

    def next_page(self):
        """Avanza a la siguiente página."""
        if self.current_page < self.total_pages:
            self.current_page += 1

    def previous_page(self):
        """Retrocede a la página anterior."""
        if self.current_page > 1:
            self.current_page -= 1
