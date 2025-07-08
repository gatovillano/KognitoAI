#!/usr/bin/env python3
# scripts/monitor_docker_llm_logs.py

"""
Script para monitorear los logs del LLM en tiempo real desde contenedores Docker.
"""

import subprocess
import sys
import signal
import time
from datetime import datetime

def find_kognito_containers():
    """Encuentra contenedores relacionados con KognitoAI."""
    try:
        cmd = ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.ID}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 3:
                    name, image, container_id = parts[0], parts[1], parts[2]
                    # Buscar contenedores que puedan ser de KognitoAI
                    if any(keyword in name.lower() or keyword in image.lower() 
                           for keyword in ['kognito', 'api', 'web', 'app', 'main']):
                        containers.append({
                            'name': name,
                            'image': image,
                            'id': container_id
                        })
        
        return containers
    except Exception as e:
        print(f"❌ Error buscando contenedores: {e}")
        return []

def format_log_line(line: str, container_name: str = "") -> str:
    """Formatea una línea de log para mejor legibilidad."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Microsegundos
    
    # Detectar logs específicos del LLM
    if any(keyword in line for keyword in ["[LLM", "[CHAT", "[TOOL", "[AGENT", "LLMCallback"]):
        if any(start in line for start in ["[LLM START]", "[CHAT START]", "💬 [CHAT START]"]):
            return f"🚀 {timestamp} | {container_name} | {line}"
        elif any(end in line for end in ["[LLM END]", "[CHAT END]", "✅ [LLM END]"]):
            return f"✅ {timestamp} | {container_name} | {line}"
        elif any(prompt in line for prompt in ["[PROMPT", "[MESSAGE", "📨"]):
            return f"📨 {timestamp} | {container_name} | {line}"
        elif any(content in line for content in ["[CONTENT]", "[RESPONSE]", "📄", "📤"]):
            return f"📄 {timestamp} | {container_name} | {line}"
        elif "[TOOL START]" in line or "🔧 [TOOL START]" in line:
            return f"🔧 {timestamp} | {container_name} | {line}"
        elif "[TOOL END]" in line or "✅ [TOOL END]" in line:
            return f"🔧✅ {timestamp} | {container_name} | {line}"
        elif "[ERROR]" in line or "❌" in line:
            return f"❌ {timestamp} | {container_name} | {line}"
        elif "[TOKENS]" in line or "🔧 [TOKENS]" in line:
            return f"🪙 {timestamp} | {container_name} | {line}"
        else:
            return f"🧠 {timestamp} | {container_name} | {line}"
    
    # Detectar logs de herramientas específicas
    elif any(keyword in line for keyword in ["comprehensive_web", "web_search", "memory_manager", "Step"]):
        return f"🛠️ {timestamp} | {container_name} | {line}"
    
    # Detectar logs de base de datos
    elif any(keyword in line for keyword in ["database", "postgres", "vector", "embedding"]):
        return f"🗄️ {timestamp} | {container_name} | {line}"
    
    # Logs de nivel estándar
    elif "ERROR" in line:
        return f"❌ {timestamp} | {container_name} | {line}"
    elif "WARNING" in line:
        return f"⚠️ {timestamp} | {container_name} | {line}"
    elif "DEBUG" in line:
        return f"🔍 {timestamp} | {container_name} | {line}"
    elif "INFO" in line:
        return f"ℹ️ {timestamp} | {container_name} | {line}"
    
    # Línea normal
    return f"📝 {timestamp} | {container_name} | {line}"

def monitor_container(container_name: str):
    """Monitorea los logs de un contenedor específico."""
    print(f"🐳 Monitoreando contenedor: {container_name}")
    print("🔄 Siguiendo logs en tiempo real (Ctrl+C para salir)...")
    print("=" * 80)
    
    try:
        # Usar docker logs con follow
        cmd = ["docker", "logs", "-f", "--tail", "50", container_name]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        def signal_handler(signum, frame):
            print("\n🛑 Deteniendo monitoreo...")
            process.terminate()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while True:
            line = process.stdout.readline()
            if line:
                formatted_line = format_log_line(line.strip(), container_name)
                print(formatted_line)
                sys.stdout.flush()
            elif process.poll() is not None:
                break
                
    except Exception as e:
        print(f"❌ Error monitoreando contenedor {container_name}: {e}")

def main():
    print("🚀 Buscando contenedores de KognitoAI...")
    
    containers = find_kognito_containers()
    
    if not containers:
        print("❌ No se encontraron contenedores de KognitoAI ejecutándose.")
        print("💡 Verifica que la aplicación esté ejecutándose en Docker:")
        print("   docker ps")
        sys.exit(1)
    
    print(f"✅ Encontrados {len(containers)} contenedores:")
    for i, container in enumerate(containers):
        print(f"  {i+1}. {container['name']} ({container['image']}) - ID: {container['id'][:12]}")
    
    if len(containers) == 1:
        selected_container = containers[0]['name']
        print(f"\n🎯 Monitoreando automáticamente: {selected_container}")
    else:
        print("\n🤔 ¿Qué contenedor quieres monitorear?")
        try:
            choice = int(input("Ingresa el número (1-{}): ".format(len(containers))))
            if 1 <= choice <= len(containers):
                selected_container = containers[choice-1]['name']
            else:
                print("❌ Opción inválida")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Operación cancelada")
            sys.exit(1)
    
    print(f"\n⏰ Iniciado a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    monitor_container(selected_container)

if __name__ == "__main__":
    main()
