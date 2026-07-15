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
import re

logger = logging.getLogger(__name__)


#def sanitize_html(text: str) -> str:
    #Limpia una cadena de texto para su uso seguro en mensajes de Telegram con ParseMode.HTML.
    #
    #Telegram soporta un subconjunto muy limitado de etiquetas HTML:
    #<b>, <i>, <u>, <s>, <code>, <pre>, <a>.
    #Cualquier otro carácter HTML como '<', '>' o '&' debe ser escapado para evitar
    #errores de parseo por parte de la API de Telegram.
    #
    #Esta función escapa los caracteres especiales de HTML, pero deja intactas
    #las etiquetas HTML que sí están permitidas por Telegram.
    #
    #Args:
    #    text: La cadena de texto a limpiar.
    #
    #Returns:
    #    La cadena de texto limpiada y segura para ser enviada a Telegram.
    #if not text:
    #    return ""

    # Primero, escapamos TODOS los caracteres especiales de HTML.
    # Esto convierte '<' en '<', '>' en '>', y '&' en '&'.
    #escaped_text = html.escape(text)

    # Ahora, volvemos a "des-escapar" selectivamente las etiquetas permitidas por Telegram.
    # Esto convierte '<b>' de nuevo en '<b>', pero deja otros como '<div>'.
    #allowed_tags = {
        #"<b>": "<b>",
        #"</b>": "</b>",
        #"<i>": "<i>",
        #"</i>": "</i>",
        #"<u>": "<u>",
        #"</u>": "</u>",
        #"<s>": "<s>",
        #"</s>": "</s>",
        #"<strike>": "<strike>",
        #"</strike>": "</strike>",
        #"<del>": "<del>",
        #"</del>": "</del>",
        #"<code>": "<code>",
        #"</code>": "</code>",        # NOTA: <pre> y <a> son más complejos de manejar aquí debido a sus atributos
        # (class, href), por lo que por ahora se dejan escapados para mayor seguridad.
        # Si se necesita generar enlaces <a>, se debe hacer con cuidado.
    #}

    #for escaped_tag, original_tag in allowed_tags.items():
    #    escaped_text = escaped_text.replace(escaped_tag, original_tag)

    # return escaped_text

def markdown_to_telegram_html(text: str) -> str:
    """
    Convierte un subconjunto simple de Markdown al formato HTML que entiende Telegram.
    Es una conversión básica y no cubre todos los casos.
    """
    if not text:
        return ""

    # 1. Negrita: **texto** -> <b>texto</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # 2. Cursiva: *texto* -> <i>texto</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)

    # 3. Código en línea: `texto` -> <code>texto</code>
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # 4. Bloques de código: ```python...``` -> <pre><code class="language-python">...</code></pre>
    # Esta es la más compleja. Telegram usa <pre> para bloques preservando el formato.
    def code_block_replacer(match):
        lang = match.group(1) or ""
        code = match.group(2)
        # Escapamos caracteres HTML dentro del bloque de código para evitar conflictos
        escaped_code = html.escape(code)
        if lang:
            return f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
        else:
            return f'<pre>{escaped_code}</pre>'

    text = re.sub(r'```(\w*)\n(.*?)\n```', code_block_replacer, text, flags=re.DOTALL)
    
    # IMPORTANTE: Escapar los caracteres HTML restantes que Telegram no debe interpretar.
    # Esta parte es crucial para evitar errores de "malformed HTML".
    # Lo hacemos después de las conversiones para no escapar nuestras propias etiquetas.
    # Esta es una simplificación. Una función robusta requeriría un parseo más inteligente.
    # Por ahora, nos enfocamos en el formato que controlamos.

    return text

# Aquí se podrían añadir otras funciones de ayuda en el futuro, por ejemplo:
## def format_timestamp(ts: float) -> str:
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


import math
from typing import Any

def clean_nan_values(val: Any) -> Any:
    """
    Recursivamente convierte valores flotantes no válidos (NaN, Inf, -Inf) en None,
    lo que los hace compatibles con la serialización JSON.
    """
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(val, dict):
        return {k: clean_nan_values(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [clean_nan_values(v) for v in val]
    elif isinstance(val, tuple):
        return tuple(clean_nan_values(v) for v in val)
    return val

