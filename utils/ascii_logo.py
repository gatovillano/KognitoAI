#!/usr/bin/env python3
"""
Logo ASCII art de Kognito AI con colores para mostrar en el inicio del sistema.
"""

import sys
from typing import Optional

# Códigos de color ANSI
class Colors:
    # Colores básicos
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Colores de texto
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Colores brillantes
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Colores de fondo
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

def get_kognito_logo() -> str:
    """
    Retorna el logo ASCII art de Kognito AI con colores basado en el logo oficial.
    Representa el cerebro con circuitos electrónicos usando letras y números.
    """
    # Logo principal de Kognito AI - Cerebro con circuitos de letras y números
    logo = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}                    ╔══════════════════════════════════╗
                    ║        {Colors.BRIGHT_BLUE}A1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}B2{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}C3{Colors.BRIGHT_CYAN}   {Colors.BRIGHT_BLUE}X7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Y8{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Z9{Colors.BRIGHT_CYAN}        ║
                    ║       {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}   {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}       ║
                    ║    {Colors.BRIGHT_BLUE}D4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}E5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}F6{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}U4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}V5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}W6{Colors.BRIGHT_CYAN}    ║
                    ║   {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}G7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}H8{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}I9{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}R1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}S2{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}T3{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}   ║
                    ║  {Colors.BRIGHT_BLUE}J0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}K1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}L2{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}M3{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}N4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}O5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}P6{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Q7{Colors.BRIGHT_CYAN}  ║
                    ║ {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}A8{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}B9{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}C0{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}X1{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}Y2{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}Z3{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} ║
                    ║{Colors.BRIGHT_BLUE}D1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}E2{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}F3{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}G4{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}H5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}I6{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}J7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}K8{Colors.BRIGHT_CYAN}║
                    ║{Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}L9{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}M0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}N1{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}O2{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}P3{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Q4{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}║
                    ║{Colors.BRIGHT_BLUE}R5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}S6{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}T7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}U8{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}V9{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}W0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}X1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Y2{Colors.BRIGHT_CYAN}║
                    ║ {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}Z3{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}A4{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}B5{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}C6{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}D7{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}E8{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} ║
                    ║  {Colors.BRIGHT_BLUE}F9{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}G0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}H1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}I2{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}J3{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}K4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}L5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}M6{Colors.BRIGHT_CYAN}  ║
                    ║   {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}N7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}O8{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}P9{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}Q0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}R1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}S2{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}   ║
                    ║    {Colors.BRIGHT_BLUE}T3{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}U4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}V5{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}W6{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}X7{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}Y8{Colors.BRIGHT_CYAN}    ║
                    ║       {Colors.BRIGHT_BLUE}Z9{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}A0{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}B1{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}C2{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}D3{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}E4{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}F5{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}G6{Colors.BRIGHT_CYAN}       ║
                    ╚══════════════════════════════════╝{Colors.RESET}

{Colors.BRIGHT_CYAN}{Colors.BOLD}    ██╗  ██╗ ██████╗  ██████╗ ███╗   ██╗██╗████████╗ ██████╗
    ██║ ██╔╝██╔═══██╗██╔════╝ ████╗  ██║██║╚══██╔══╝██╔═══██╗
    █████╔╝ ██║   ██║██║  ███╗██╔██╗ ██║██║   ██║   ██║   ██║
    ██╔═██╗ ██║   ██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║
    ██║  ██╗╚██████╔╝╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝{Colors.RESET}

{Colors.BRIGHT_BLUE}{Colors.BOLD}                          AI LABS{Colors.RESET}
"""
    return logo

def get_system_info() -> str:
    """
    Retorna información del sistema híbrido.
    """
    info = f"""
{Colors.BRIGHT_GREEN}{Colors.BOLD}    🚀 SISTEMA HÍBRIDO AVANZADO{Colors.RESET}
    {Colors.CYAN}┌─────────────────────────────────────────────────────────┐{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_YELLOW}⚡ Qdrant{Colors.RESET}     │ Almacenamiento vectorial ultra-rápido   {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_BLUE}🧠 Cognee{Colors.RESET}     │ Análisis conceptual avanzado            {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_GREEN}🤖 Ollama{Colors.RESET}     │ Embeddings locales optimizados          {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_MAGENTA}🗄️ pgvector{Colors.RESET}   │ Memoria histórica inteligente           {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_RED}🕸️ Neo4j{Colors.RESET}      │ Grafos de conocimiento                  {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}└─────────────────────────────────────────────────────────┘{Colors.RESET}
"""
    return info

def get_startup_message(version: Optional[str] = None) -> str:
    """
    Retorna el mensaje completo de inicio.
    """
    version_str = version or "1.0.0"
    
    message = f"""
{Colors.BRIGHT_WHITE}{Colors.BOLD}    ═══════════════════════════════════════════════════════════{Colors.RESET}
{Colors.BRIGHT_CYAN}{Colors.BOLD}                        KOGNITO AI CORE v{version_str}{Colors.RESET}
{Colors.BRIGHT_WHITE}{Colors.BOLD}    ═══════════════════════════════════════════════════════════{Colors.RESET}
    
    {Colors.BRIGHT_GREEN}✅ Sistema híbrido inicializado{Colors.RESET}
    {Colors.BRIGHT_BLUE}🌐 API disponible en puerto 8000{Colors.RESET}
    {Colors.BRIGHT_YELLOW}⚡ Experiencia 5x superior activada{Colors.RESET}
    
    {Colors.DIM}🔗 Documentación: https://docs.kognito.ai{Colors.RESET}
    {Colors.DIM}💬 Soporte: https://support.kognito.ai{Colors.RESET}
    
{Colors.BRIGHT_WHITE}{Colors.BOLD}    ═══════════════════════════════════════════════════════════{Colors.RESET}
"""
    return message

def print_startup_logo(version: Optional[str] = None, show_system_info: bool = True):
    """
    Imprime el logo completo de inicio de Kognito AI.
    
    Args:
        version: Versión del sistema
        show_system_info: Si mostrar información del sistema híbrido
    """
    print(get_kognito_logo())
    
    if show_system_info:
        print(get_system_info())
    
    print(get_startup_message(version))

def get_simple_logo() -> str:
    """
    Retorna una versión simplificada del logo para logs.
    """
    return f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}        ╭─────────────────────╮
       ╱  {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}   {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}  ╲
      ╱   {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}   {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}   ╲
     ╱ {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}─{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN} ╲
    ╱  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}  {Colors.BRIGHT_BLUE}│{Colors.BRIGHT_CYAN}  ╲
   ╱   {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}┼{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}   ╲
  ╱     {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN} {Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}──{Colors.BRIGHT_BLUE}●{Colors.BRIGHT_CYAN}     ╲
 ╱_________________________________╲{Colors.RESET}

{Colors.BRIGHT_CYAN}{Colors.BOLD}    ██╗  ██╗ ██████╗  ██████╗ ███╗   ██╗██╗████████╗ ██████╗
    ██║ ██╔╝██╔═══██╗██╔════╝ ████╗  ██║██║╚══██╔══╝██╔═══██╗
    █████╔╝ ██║   ██║██║  ███╗██╔██╗ ██║██║   ██║   ██║   ██║
    ██╔═██╗ ██║   ██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║
    ██║  ██╗╚██████╔╝╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝{Colors.RESET}
    {Colors.BRIGHT_BLUE}{Colors.BOLD}AI LABS{Colors.RESET} {Colors.DIM}| Sistema Híbrido Avanzado{Colors.RESET}
"""

def get_mini_logo() -> str:
    """
    Retorna una versión mini del logo para usar en logs pequeños.
    """
    return f"{Colors.BRIGHT_CYAN}{Colors.BOLD}🧠 KOGNITO AI{Colors.RESET} {Colors.DIM}| Híbrido{Colors.RESET}"

def is_color_supported() -> bool:
    """
    Verifica si la terminal soporta colores.
    """
    import os
    return (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
        'TERM' in os.environ and os.environ['TERM'] != 'dumb'
    )

def get_logo_no_color() -> str:
    """
    Retorna el logo sin colores para terminales que no los soportan.
    """
    return """
    ██╗  ██╗ ██████╗  ██████╗ ███╗   ██╗██╗████████╗ ██████╗ 
    ██║ ██╔╝██╔═══██╗██╔════╝ ████╗  ██║██║╚══██╔══╝██╔═══██╗
    █████╔╝ ██║   ██║██║  ███╗██╔██╗ ██║██║   ██║   ██║   ██║
    ██╔═██╗ ██║   ██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║
    ██║  ██╗╚██████╔╝╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ 
    
                        🧠 KOGNITO AI SYSTEM
                     Sistema Híbrido Avanzado
    
    ═══════════════════════════════════════════════════════════
                        KOGNITO AI CORE
    ═══════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    # Test del logo
    import os
    
    print("🎨 Test del logo ASCII de Kognito AI")
    print("=" * 60)
    
    # Logo completo
    print_startup_logo("1.0.0", True)
    
    print("\n" + "=" * 60)
    print("🔸 Logo simple:")
    print(get_simple_logo())
    
    print("\n" + "=" * 60)
    print("🔹 Logo mini:")
    print(get_mini_logo())
