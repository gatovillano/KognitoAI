# utils/paginator.py

"""
Módulo de Utilidad para la Paginación de Texto en Telegram.

Este módulo proporciona una clase `Paginator` y una función de ayuda
`split_text_into_pages` para manejar respuestas largas que exceden el límite
de caracteres de un solo mensaje de Telegram.

La clase `Paginator` se encarga de:
-   Dividir un texto largo en fragmentos (páginas) de un tamaño manejable.
-   Mantener el estado de la página actual.
-   Generar el texto de la página actual con un encabezado y un pie de página
    que indican el número de página.
-   Crear un `InlineKeyboardMarkup` con los botones de navegación ("Anterior" y
    "Siguiente") que se activan o desactivan según la página actual.

Esta utilidad es esencial para mostrar de forma interactiva el contenido de
documentos largos o cualquier otra respuesta extensa del bot.
"""

import logging
import uuid
from typing import List, Tuple, Optional

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode  # <-- Add this import

logger = logging.getLogger(__name__)

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


# ...dentro de paginator.py

class Paginator:
    """
    Gestiona la paginación de texto largo para los mensajes de Telegram.
    """
    def __init__(self,
                 chunks: List[str],
                 title: str = "",
                 parse_mode: str = ParseMode.HTML,
                 initial_page: int = 1,
                 prefix: Optional[str] = None): # <-- ¡NUEVO PARÁMETRO!
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

        # ¡CORREGIDO! Usa el prefijo para generar un ID de sesión más descriptivo.
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

