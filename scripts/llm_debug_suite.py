#!/usr/bin/env python3
"""
🛠️ Suite de Debugging del LLM
=============================

Script unificado para debugging y análisis de prompts del LLM con múltiples modos de operación.

Uso:
    python scripts/llm_debug_suite.py [modo] [opciones]

Modos disponibles:
    monitor     - Monitor en tiempo real de prompts y respuestas
    analyze     - Análisis detallado de estructura de prompts
    stats       - Estadísticas y métricas de uso del LLM
    interactive - Modo interactivo para explorar logs

Ejemplos:
    # Monitor básico en tiempo real
    python scripts/llm_debug_suite.py monitor

    # Análisis de estructura con estadísticas
    python scripts/llm_debug_suite.py analyze --stats

    # Monitor filtrado por account_id
    python scripts/llm_debug_suite.py monitor --account-id 12345

    # Análisis de archivo específico
    python scripts/llm_debug_suite.py analyze --log-file logs/llm.log

    # Modo interactivo
    python scripts/llm_debug_suite.py interactive
"""

import argparse
import sys
import subprocess
from pathlib import Path

def run_monitor(args):
    """Ejecuta el monitor de prompts en tiempo real."""
    cmd = [sys.executable, "scripts/detailed_llm_prompt_monitor.py"]
    
    if args.only_prompts:
        cmd.append("--only-prompts")
    if args.account_id:
        cmd.extend(["--account-id", args.account_id])
    if args.no_truncate:
        cmd.append("--no-truncate")
    if args.save_to:
        cmd.extend(["--save-to", args.save_to])
    if args.no_tokens:
        cmd.append("--no-tokens")
    if args.no_tools:
        cmd.append("--no-tools")
    
    subprocess.run(cmd)

def run_analyzer(args):
    """Ejecuta el analizador de estructura de prompts."""
    cmd = [sys.executable, "scripts/prompt_structure_analyzer.py"]
    
    if args.log_file:
        cmd.extend(["--log-file", args.log_file])
    if args.stats:
        cmd.append("--stats")
    if args.export:
        cmd.extend(["--export", args.export])
    
    subprocess.run(cmd)

def run_stats(args):
    """Muestra estadísticas del LLM."""
    print("📊 Generando estadísticas del LLM...")
    
    # Ejecutar analizador con estadísticas habilitadas
    cmd = [sys.executable, "scripts/prompt_structure_analyzer.py", "--stats"]
    
    if args.log_file:
        cmd.extend(["--log-file", args.log_file])
    if args.export:
        cmd.extend(["--export", args.export])
    
    subprocess.run(cmd)

def run_interactive():
    """Modo interactivo para explorar logs."""
    print("🔍 Modo Interactivo de Debugging del LLM")
    print("=" * 40)
    
    while True:
        print("\nOpciones disponibles:")
        print("1. Monitor en tiempo real")
        print("2. Análisis de estructura")
        print("3. Estadísticas")
        print("4. Monitor filtrado por account_id")
        print("5. Análisis de archivo específico")
        print("6. Salir")
        
        choice = input("\nSelecciona una opción (1-6): ").strip()
        
        if choice == "1":
            print("\n🔄 Iniciando monitor en tiempo real...")
            subprocess.run([sys.executable, "scripts/detailed_llm_prompt_monitor.py"])
        
        elif choice == "2":
            print("\n🔬 Iniciando análisis de estructura...")
            subprocess.run([sys.executable, "scripts/prompt_structure_analyzer.py", "--stats"])
        
        elif choice == "3":
            print("\n📊 Generando estadísticas...")
            subprocess.run([sys.executable, "scripts/prompt_structure_analyzer.py", "--stats"])
        
        elif choice == "4":
            account_id = input("Ingresa el account_id a filtrar: ").strip()
            if account_id:
                print(f"\n🎯 Monitoreando account_id: {account_id}")
                subprocess.run([
                    sys.executable, 
                    "scripts/detailed_llm_prompt_monitor.py",
                    "--account-id", account_id
                ])
        
        elif choice == "5":
            log_file = input("Ingresa la ruta del archivo de log: ").strip()
            if log_file and Path(log_file).exists():
                print(f"\n📁 Analizando archivo: {log_file}")
                subprocess.run([
                    sys.executable,
                    "scripts/prompt_structure_analyzer.py",
                    "--log-file", log_file,
                    "--stats"
                ])
            else:
                print("❌ Archivo no encontrado o ruta inválida")
        
        elif choice == "6":
            print("👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida. Por favor selecciona 1-6.")

def show_help():
    """Muestra ayuda detallada."""
    print(__doc__)
    print("\n🔧 HERRAMIENTAS INCLUIDAS:")
    print("=" * 30)
    print("• detailed_llm_prompt_monitor.py - Monitor en tiempo real")
    print("• prompt_structure_analyzer.py   - Análisis de estructura")
    print("• llm_debug_suite.py            - Suite unificada (este script)")
    
    print("\n📋 CASOS DE USO COMUNES:")
    print("=" * 25)
    print("• Debugging de prompts mal formateados")
    print("• Análisis de rendimiento y uso de tokens")
    print("• Monitoreo de herramientas ejecutadas")
    print("• Estadísticas de complejidad de prompts")
    print("• Filtrado por sesión o usuario específico")

def main():
    parser = argparse.ArgumentParser(
        description="Suite de debugging del LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Modo de operación')
    
    # Subparser para monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitor en tiempo real')
    monitor_parser.add_argument('--only-prompts', action='store_true', help='Solo prompts')
    monitor_parser.add_argument('--account-id', type=str, help='Filtrar por account_id')
    monitor_parser.add_argument('--no-truncate', action='store_true', help='No truncar contenido')
    monitor_parser.add_argument('--save-to', type=str, help='Guardar en archivo')
    monitor_parser.add_argument('--no-tokens', action='store_true', help='No mostrar tokens')
    monitor_parser.add_argument('--no-tools', action='store_true', help='No mostrar herramientas')
    
    # Subparser para analyzer
    analyze_parser = subparsers.add_parser('analyze', help='Análisis de estructura')
    analyze_parser.add_argument('--log-file', type=str, help='Archivo de log específico')
    analyze_parser.add_argument('--stats', action='store_true', help='Mostrar estadísticas')
    analyze_parser.add_argument('--export', type=str, help='Exportar a JSON')
    
    # Subparser para stats
    stats_parser = subparsers.add_parser('stats', help='Estadísticas del LLM')
    stats_parser.add_argument('--log-file', type=str, help='Archivo de log específico')
    stats_parser.add_argument('--export', type=str, help='Exportar a JSON')
    
    # Subparser para interactive
    subparsers.add_parser('interactive', help='Modo interactivo')
    
    # Subparser para help
    subparsers.add_parser('help', help='Mostrar ayuda detallada')
    
    args = parser.parse_args()
    
    if not args.mode:
        print("🛠️ Suite de Debugging del LLM")
        print("=" * 30)
        print("Usa --help para ver todas las opciones")
        print("\nModos rápidos:")
        print("• python scripts/llm_debug_suite.py monitor")
        print("• python scripts/llm_debug_suite.py analyze --stats")
        print("• python scripts/llm_debug_suite.py interactive")
        return
    
    if args.mode == 'monitor':
        run_monitor(args)
    elif args.mode == 'analyze':
        run_analyzer(args)
    elif args.mode == 'stats':
        run_stats(args)
    elif args.mode == 'interactive':
        run_interactive()
    elif args.mode == 'help':
        show_help()
    else:
        print(f"❌ Modo desconocido: {args.mode}")
        parser.print_help()

if __name__ == "__main__":
    main()
