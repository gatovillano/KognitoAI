"""
Sistema unificado de temas y paletas visuales para documentos OnlyOffice (Word, Excel, PowerPoint).
Proporciona colores semánticos, fuentes y funciones de manipulación cromática.
"""

from typing import Dict, Any, Optional, Tuple

DEFAULT_THEME = "corporate_blue"

THEMES: Dict[str, Dict[str, Any]] = {
    "corporate_blue": {
        "name": "Corporate Blue",
        "primary": "1E3A8A",       # Azul Marino Profundo
        "secondary": "2563EB",     # Azul Real
        "accent": "3B82F6",        # Azul Claro
        "bg_light": "F8FAFC",      # Pizarra Suave (zebra / cards)
        "bg_tint": "EFF6FF",       # Tint azul pastel
        "border": "CBD5E1",        # Gris borde sutil
        "text_primary": "1E293B",  # Texto oscuro principal
        "text_muted": "64748B",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "emerald_green": {
        "name": "Emerald Green",
        "primary": "065F46",       # Verde Bosque
        "secondary": "059669",     # Esmeralda
        "accent": "10B981",        # Menta Claro
        "bg_light": "F0FDF4",      # Verde Suave
        "bg_tint": "ECFDF5",       # Tint menta pastel
        "border": "A7F3D0",        # Borde esmeralda suave
        "text_primary": "064E3B",  # Texto oscuro
        "text_muted": "047857",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "dark_slate": {
        "name": "Dark Slate",
        "primary": "0F172A",       # Pizarra Oscuro / Grafito
        "secondary": "334155",     # Gris Azulado
        "accent": "64748B",        # Acero
        "bg_light": "F1F5F9",      # Gris Frío Suave
        "bg_tint": "F8FAFC",       # Tint gris suave
        "border": "94A3B8",        # Borde gris
        "text_primary": "0F172A",  # Texto grafito
        "text_muted": "64748B",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "sunset_amber": {
        "name": "Sunset Amber",
        "primary": "9A3412",       # Ámbar Oscuro
        "secondary": "D97706",     # Naranja Ámbar
        "accent": "F59E0B",        # Amarillo Cálido
        "bg_light": "FFFBEB",      # Arena Suave
        "bg_tint": "FEF3C7",       # Tint ámbar pastel
        "border": "FDE68A",        # Borde ámbar suave
        "text_primary": "451A03",  # Texto oscuro cálido
        "text_muted": "92400E",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "violet_gold": {
        "name": "Violet Gold",
        "primary": "581C87",       # Púrpura Real
        "secondary": "7C3AED",     # Índigo / Violeta
        "accent": "A855F7",        # Lavanda
        "bg_light": "FAF5FF",      # Púrpura Suave
        "bg_tint": "F3E8FF",       # Tint lavanda pastel
        "border": "D8B4FE",        # Borde lavanda suave
        "text_primary": "3B0764",  # Texto oscuro
        "text_muted": "6B21A8",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "minimalist_gray": {
        "name": "Minimalist Gray",
        "primary": "262626",       # Negro Neutro / Carbón
        "secondary": "525252",     # Gris Medio
        "accent": "737373",        # Gris Claro
        "bg_light": "F9FAFB",      # Blanco Humo
        "bg_tint": "F3F4F6",       # Tint gris neutro
        "border": "D1D5DB",        # Borde neutro
        "text_primary": "171717",  # Texto negro suave
        "text_muted": "737373",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
}


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convierte una cadena hexadecimal (ej. '1E3A8A' o '#1E3A8A') a tupla RGB (r, g, b)."""
    hex_clean = hex_str.lstrip("#").strip()
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return (0, 0, 0)
    return (int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convierte componentes RGB a cadena hexadecimal sin '#', en mayúsculas."""
    r_clamped = max(0, min(255, int(r)))
    g_clamped = max(0, min(255, int(g)))
    b_clamped = max(0, min(255, int(b)))
    return f"{r_clamped:02X}{g_clamped:02X}{b_clamped:02X}"


def lighten_color(hex_str: str, factor: float = 0.5) -> str:
    """Aclara un color mezclándolo con blanco (factor 0.0 = idéntico, 1.0 = blanco)."""
    r, g, b = hex_to_rgb(hex_str)
    r_new = r + (255 - r) * factor
    g_new = g + (255 - g) * factor
    b_new = b + (255 - b) * factor
    return rgb_to_hex(int(r_new), int(g_new), int(b_new))


def darken_color(hex_str: str, factor: float = 0.2) -> str:
    """Oscurece un color reduciendo su brillo (factor 0.0 = idéntico, 1.0 = negro)."""
    r, g, b = hex_to_rgb(hex_str)
    r_new = r * (1.0 - factor)
    g_new = g * (1.0 - factor)
    b_new = b * (1.0 - factor)
    return rgb_to_hex(int(r_new), int(g_new), int(b_new))


def get_theme(theme_name: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Retorna el diccionario de tokens del tema solicitado.
    Si el tema no existe, aplica DEFAULT_THEME.
    Permite aplicar overrides personalizados (ej. 'primary': 'E11D48').
    """
    norm_name = (theme_name or DEFAULT_THEME).strip().lower()
    base_theme = THEMES.get(norm_name, THEMES[DEFAULT_THEME]).copy()

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                # Si el override es un color hex con '#', limpiarlo
                if isinstance(v, str) and k in ("primary", "secondary", "accent", "bg_light", "bg_tint", "border", "text_primary", "text_muted"):
                    base_theme[k] = v.lstrip("#").upper()
                else:
                    base_theme[k] = v

    return base_theme
