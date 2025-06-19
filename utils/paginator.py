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


class Paginator:
    """
    Gestiona el estado y la presentación de un texto paginado.
    """
    def __init__(self,
                 chunks: List[str],
                 session_id: Optional[str] = None,
                 title: str = "Respuesta",
                 parse_mode: str = 'HTML'):
        """
        Inicializa una nueva sesión de paginación.

        Args:
            chunks: La lista de páginas (texto ya dividido).
            session_id: Un ID único para esta sesión de paginación. Se genera si no se proporciona.
            title: Un título para mostrar en el encabezado de cada página.
            parse_mode: El modo de parseo para el texto (HTML, MarkdownV2).
        """
        self.chunks = chunks
        self.total_pages = len(chunks)
        self.current_page_index = 0
        self.session_id = session_id or str(uuid.uuid4())
        self.title = title
        self.parse_mode = parse_mode

    def get_page(self) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Obtiene el texto formateado y el teclado de botones para la página actual.

        Returns:
            Una tupla que contiene:
            - El texto de la página actual con su encabezado y pie de página.
            - Un `InlineKeyboardMarkup` con los botones de navegación, o `None` si solo hay una página.
        """
        if not self.chunks:
            return "No hay contenido para mostrar.", None

        page_content = self.chunks[self.current_page_index]
        page_num = self.current_page_index + 1
        
        # Formatear el texto completo del mensaje
        header = f"📄 <b>{self.title}</b> (Página {page_num}/{self.total_pages})\n"
        footer = f"\n(Página {page_num}/{self.total_pages})"
        
        full_text = header + page_content + footer

        # Crear el teclado de botones
        keyboard = self._create_keyboard()

        return full_text, keyboard

    def _create_keyboard(self) -> Optional[InlineKeyboardMarkup]:
        """Crea el teclado en línea con los botones de navegación."""
        if self.total_pages <= 1:
            return None

        buttons = []
        # Botón "Anterior" (deshabilitado en la primera página)
        if self.current_page_index > 0:
            buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"paginator:{self.session_id}:prev"))
        
        # Botón "Siguiente" (deshabilitado en la última página)
        if self.current_page_index < self.total_pages - 1:
            buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"paginator:{self.session_id}:next"))

        return InlineKeyboardMarkup([buttons])

    def next_page(self):
        """Avanza a la siguiente página, si es posible."""
        if self.current_page_index < self.total_pages - 1:
            self.current_page_index += 1

    def previous_page(self):
        """Retrocede a la página anterior, si es posible."""
        if self.current_page_index > 0:
            self.current_page_index -= 1
