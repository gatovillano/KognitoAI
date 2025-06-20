# utils/helpers.py

"""
Módulo de Utilidad con Funciones de Ayuda Generales.

Este archivo actúa como una "caja de herramientas" para funciones pequeñas y
reutilizables que no pertenecen a un módulo de lógica de negocio específico,
pero que son necesarias en varias partes de la aplicación.

El objetivo es evitar la duplicación de código y mantener un lugar centralizado
para tareas de utilidad comunes, como la limpieza y el formateo de texto.
"""

import logging
import html

logger = logging.getLogger(__name__)


def sanitize_html(text: str) -> str:
    """
    Limpia una cadena de texto para su uso seguro en mensajes de Telegram con ParseMode.HTML.

    Telegram soporta un subconjunto muy limitado de etiquetas HTML:
    <b>, <i>, <u>, <s>, <code>, <pre>, <a>.
    Cualquier otro carácter HTML como '<', '>' o '&' debe ser escapado para evitar
    errores de parseo por parte de la API de Telegram.

    Esta función escapa los caracteres especiales de HTML, pero deja intactas
    las etiquetas HTML que sí están permitidas por Telegram.

    Args:
        text: La cadena de texto a limpiar.

    Returns:
        La cadena de texto limpiada y segura para ser enviada a Telegram.
    """
    if not text:
        return ""

    # Primero, escapamos TODOS los caracteres especiales de HTML.
    # Esto convierte '<' en '&lt;', '>' en '&gt;', y '&' en '&amp;'.
    escaped_text = html.escape(text)

    # Ahora, volvemos a "des-escapar" selectivamente las etiquetas permitidas por Telegram.
    # Esto convierte '&lt;b&gt;' de nuevo en '<b>', pero deja otros como '&lt;div&gt;'.
    allowed_tags = {
        "&lt;b&gt;": "<b>", "&lt;/b&gt;": "</b>",
        "&lt;i&gt;": "<i>", "&lt;/i&gt;": "</i>",
        "&lt;u&gt;": "<u>", "&lt;/u&gt;": "</u>",
        "&lt;s&gt;": "<s>", "&lt;/s&gt;": "</s>",
        "&lt;strike&gt;": "<strike>", "&lt;/strike&gt;": "</strike>",
        "&lt;del&gt;": "<del>", "&lt;/del&gt;": "</del>",
        "&lt;code&gt;": "<code>", "&lt;/code&gt;": "</code>"
        # NOTA: <pre> y <a> son más complejos de manejar aquí debido a sus atributos
        # (class, href), por lo que por ahora se dejan escapados para mayor seguridad.
        # Si se necesita generar enlaces <a>, se debe hacer con cuidado.
    }

    for escaped_tag, original_tag in allowed_tags.items():
        escaped_text = escaped_text.replace(escaped_tag, original_tag)

    return escaped_text

# Aquí se podrían añadir otras funciones de ayuda en el futuro, por ejemplo:
#
# def format_timestamp(ts: float) -> str:
#     """Formatea un timestamp de Unix a una cadena de texto legible."""
#     from datetime import datetime
#     return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
#
# def generate_random_id(length: int = 8) -> str:
#     """Genera un ID aleatorio y corto."""
#     import secrets
#     import string
#     alphabet = string.ascii_lowercase + string.digits
#     return ''.join(secrets.choice(alphabet) for _ in range(length))
