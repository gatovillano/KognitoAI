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
    Retorna el logo ASCII art de Kognito AI con colores.
    """
    # Logo principal de Kognito AI
    logo = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}
    ██╗  ██╗ ██████╗  ██████╗ ███╗   ██╗██╗████████╗ ██████╗ 
    ██║ ██╔╝██╔═══██╗██╔════╝ ████╗  ██║██║╚══██╔══╝██╔═══██╗
    █████╔╝ ██║   ██║██║  ███╗██╔██╗ ██║██║   ██║   ██║   ██║
    ██╔═██╗ ██║   ██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║
    ██║  ██╗╚██████╔╝╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ 
{Colors.RESET}
{Colors.BRIGHT_MAGENTA}{Colors.BOLD}                        ╔═══════════════════════════════════╗
                        ║           🧠 AI SYSTEM            ║
                        ╚═══════════════════════════════════╝{Colors.RESET}
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
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_MAGENTA}🗄️  pgvector{Colors.RESET}   │ Memoria histórica inteligente           {Colors.CYAN}│{Colors.RESET}
    {Colors.CYAN}│{Colors.RESET} {Colors.BRIGHT_RED}🕸️  Neo4j{Colors.RESET}      │ Grafos de conocimiento                  {Colors.CYAN}│{Colors.RESET}
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
    
{Colors.BRIGHT_WHITE}{Colors.BOLD}    ═══════════════════════════════════════════════════════════{Colors.RESET}
"""
    return message

def print_startup_logo(version: str = "1.0.0", show_system_info: bool = False) -> None:
    """
    Imprime el logo de inicio de Kognito AI con información del sistema.
    
    Args:
        version: Versión del sistema
        show_system_info: Si mostrar información adicional del sistema
    """
    try:
        # Imprimir el logo principal
        print(get_kognito_logo())
        print(get_system_info())
        
        # Información de versión
        print(f"{Colors.BRIGHT_WHITE}    Versión: {Colors.BRIGHT_GREEN}{version}{Colors.RESET}")
        

       
           
        
    except Exception as e:
        # Fallback si hay problemas con los colores
        print("🧠 KOGNITO AI - Sistema de Inteligencia Artificial")
        print(f"   Versión: {version}")
        print("   Estado: Iniciando...")
        print()

def get_simple_logo() -> str:
    """Retorna un logo simple sin colores para compatibilidad."""
    return """
╔══════════════════════════════════════╗
║            KOGNITO AI                ║
║    Sistema de Inteligencia           ║
║         Artificial                   ║
╚══════════════════════════════════════╝
"""

def get_mini_logo() -> str:
    """Retorna un logo mini para usar en logs."""
    return f"{Colors.BRIGHT_BLUE}🧠 KOGNITO AI{Colors.RESET}"

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
