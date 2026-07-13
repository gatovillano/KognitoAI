import bleach
from bleach.css_sanitizer import CSSSanitizer
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Configuración de etiquetas y atributos permitidos para contenido enriquecido (ej. Notas)
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul',
    'p', 'br', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'u', 's', 'pre', 'hr'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
    'span': ['style', 'class'],
    'div': ['style', 'class'],
    'p': ['style', 'class'],
}

ALLOWED_STYLES = [
    'color', 'background-color', 'font-size', 'font-weight', 'text-align', 'text-decoration'
]

css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)

def sanitize_html(html_content: str) -> str:
    """
    Sanitiza contenido HTML permitiendo un subconjunto seguro de etiquetas y estilos.
    Ideal para campos como 'visual_content' en Notas.
    """
    if not html_content:
        return html_content
    
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        strip=True
    )

def sanitize_text(text: str) -> str:
    """
    Elimina TODAS las etiquetas HTML de una cadena de texto.
    Ideal para nombres, bios, títulos, etc.
    """
    if not text:
        return text
    
    return bleach.clean(text, tags=[], attributes={}, strip=True)

def remove_null_bytes(val: Any) -> Any:
    """
    Recursivamente elimina caracteres nulos (\x00) de cadenas, listas, diccionarios y tuplas.
    Evita excepciones psycopg.errors.UntranslatableCharacter en PostgreSQL.
    """
    if isinstance(val, str):
        return val.replace('\x00', '')
    elif isinstance(val, dict):
        return {k: remove_null_bytes(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [remove_null_bytes(item) for item in val]
    elif isinstance(val, tuple):
        return tuple(remove_null_bytes(item) for item in val)
    return val

