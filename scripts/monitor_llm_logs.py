#!/usr/bin/env python3
# scripts/monitor_llm_logs.py

"""
Script para monitorear los logs del LLM en tiempo real.
Muestra de manera estructurada toda la comunicación con el LLM.
"""

import os
import sys
import time
import glob
import argparse
from datetime import datetime
from pathlib import Path

def get_latest_llm_log():
    """Obtiene el archivo de log más reciente del LLM."""
    log_pattern = "logs/llm_detailed_*.log"
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        return None
    
    # Ordenar por fecha de modificación, más reciente primero
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]

def tail_file(filename, lines=50):
    """Implementación simple de tail para seguir un archivo."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            # Ir al final del archivo
            f.seek(0, 2)
            file_size = f.tell()
            
            # Leer las últimas líneas
            lines_found = []
            buffer_size = 1024
            
            while len(lines_found) < lines and file_size > 0:
                # Calcular cuánto leer
                read_size = min(buffer_size, file_size)
                file_size -= read_size
                
                # Posicionarse y leer
                f.seek(file_size)
                chunk = f.read(read_size)
                
                # Dividir en líneas y añadir al principio
                chunk_lines = chunk.split('\n')
                lines_found = chunk_lines + lines_found
            
            # Devolver las últimas N líneas
            return lines_found[-lines:] if len(lines_found) > lines else lines_found
    
    except Exception as e:
        print(f"Error leyendo archivo {filename}: {e}")
        return []

def follow_file(filename):
    """Sigue un archivo en tiempo real, similar a tail -f."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            # Ir al final del archivo
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    yield line.rstrip('\n')
                else:
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n🛑 Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"❌ Error siguiendo archivo {filename}: {e}")

def format_log_line(line):
    """Formatea una línea de log para mejor legibilidad."""
    # Detectar tipos especiales de logs
    if "[LLM START]" in line:
        return f"🚀 {line}"
    elif "[CHAT MODEL START]" in line:
        return f"💬 {line}"
    elif "[PROMPT" in line or "[MESSAGE" in line:
        return f"📨 {line}"
    elif "[CONTENT]" in line:
        return f"📄 {line}"
    elif "[LLM END]" in line:
        return f"✅ {line}"
    elif "[RESPONSE" in line:
        return f"📤 {line}"
    elif "[LLM ERROR]" in line or "[TOOL ERROR]" in line:
        return f"❌ {line}"
    elif "[TOOL START]" in line:
        return f"🔧 {line}"
    elif "[TOOL END]" in line:
        return f"✅ {line}"
    elif "[AGENT INPUT]" in line:
        return f"🎯 {line}"
    elif "DEBUG" in line and "langchain" in line:
        return f"🔍 {line}"
    else:
        return line

def main():
    parser = argparse.ArgumentParser(description="Monitor LLM logs in real time")
    parser.add_argument("--file", "-f", help="Specific log file to monitor")
    parser.add_argument("--lines", "-n", type=int, default=50, help="Number of initial lines to show")
    parser.add_argument("--no-follow", action="store_true", help="Don't follow the file, just show recent lines")
    
    args = parser.parse_args()
    
    # Determinar qué archivo monitorear
    if args.file:
        log_file = args.file
    else:
        log_file = get_latest_llm_log()
    
    if not log_file:
        print("❌ No se encontraron archivos de log del LLM.")
        print("💡 Asegúrate de que la aplicación esté ejecutándose y generando logs.")
        sys.exit(1)
    
    if not os.path.exists(log_file):
        print(f"❌ El archivo {log_file} no existe.")
        sys.exit(1)
    
    print(f"📊 Monitoreando logs del LLM: {log_file}")
    print(f"⏰ Iniciado a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Mostrar líneas iniciales
    if not args.no_follow:
        print(f"📜 Mostrando las últimas {args.lines} líneas:")
        print("-" * 80)
        
        initial_lines = tail_file(log_file, args.lines)
        for line in initial_lines:
            if line.strip():
                print(format_log_line(line))
        
        print("-" * 80)
        print("🔄 Siguiendo nuevas líneas en tiempo real (Ctrl+C para salir):")
        print("-" * 80)
    
    # Seguir el archivo en tiempo real
    if not args.no_follow:
        try:
            for line in follow_file(log_file):
                print(format_log_line(line))
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
    else:
        # Solo mostrar líneas recientes
        lines = tail_file(log_file, args.lines)
        for line in lines:
            if line.strip():
                print(format_log_line(line))

if __name__ == "__main__":
    main()
