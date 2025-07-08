#!/usr/bin/env python3
# scripts/monitor_llm_logs_live.py

"""
Script para monitorear los logs del LLM en tiempo real directamente desde los procesos.
Captura toda la comunicación con el LLM sin necesidad de archivos de log.
"""

import os
import sys
import time
import subprocess
import argparse
import signal
import re
from datetime import datetime
from typing import Optional, List

class LiveLLMMonitor:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def find_kognito_processes(self) -> List[dict]:
        """Encuentra todos los procesos relacionados con KognitoAI."""
        try:
            # Buscar procesos de uvicorn y python relacionados con la aplicación
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            processes = []
            for line in result.stdout.split('\n'):
                if any(keyword in line.lower() for keyword in ['uvicorn', 'run_api', 'web_server', 'main.py']):
                    if 'kognito' in line.lower() or 'uvicorn' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                processes.append({
                                    'pid': pid,
                                    'command': ' '.join(parts[10:]) if len(parts) > 10 else line,
                                    'user': parts[0]
                                })
                            except ValueError:
                                continue
            
            return processes
        except Exception as e:
            print(f"❌ Error buscando procesos: {e}")
            return []

    def format_log_line(self, line: str, source: str = "") -> str:
        """Formatea una línea de log para mejor legibilidad."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Detectar tipos especiales de logs del LLM
        if any(keyword in line for keyword in ["[LLM", "[CHAT", "[TOOL", "[AGENT"]):
            if "[LLM START]" in line or "[CHAT START]" in line:
                return f"🚀 {timestamp} | {source} | {line}"
            elif "[LLM END]" in line or "[CHAT END]" in line:
                return f"✅ {timestamp} | {source} | {line}"
            elif "[PROMPT" in line or "[MESSAGE" in line:
                return f"📨 {timestamp} | {source} | {line}"
            elif "[CONTENT]" in line or "[RESPONSE]" in line:
                return f"📄 {timestamp} | {source} | {line}"
            elif "[TOOL START]" in line:
                return f"🔧 {timestamp} | {source} | {line}"
            elif "[TOOL END]" in line:
                return f"🔧✅ {timestamp} | {source} | {line}"
            elif "[ERROR]" in line:
                return f"❌ {timestamp} | {source} | {line}"
            else:
                return f"🔍 {timestamp} | {source} | {line}"
        
        # Detectar logs de herramientas específicas
        elif any(keyword in line for keyword in ["comprehensive_web", "web_search", "memory_manager"]):
            return f"🛠️ {timestamp} | {source} | {line}"
        
        # Detectar logs de base de datos
        elif any(keyword in line for keyword in ["database", "postgres", "vector"]):
            return f"🗄️ {timestamp} | {source} | {line}"
        
        # Logs generales de INFO/DEBUG/ERROR
        elif any(keyword in line for keyword in ["INFO", "DEBUG", "WARNING", "ERROR"]):
            if "ERROR" in line:
                return f"❌ {timestamp} | {source} | {line}"
            elif "WARNING" in line:
                return f"⚠️ {timestamp} | {source} | {line}"
            elif "DEBUG" in line:
                return f"🔍 {timestamp} | {source} | {line}"
            else:
                return f"ℹ️ {timestamp} | {source} | {line}"
        
        # Línea normal
        return f"📝 {timestamp} | {source} | {line}"

    def monitor_process_logs(self, pid: int, command: str):
        """Monitorea los logs de un proceso específico usando journalctl."""
        try:
            # Usar journalctl para seguir los logs del proceso
            cmd = ["journalctl", "-f", f"_PID={pid}", "--no-pager", "-o", "cat"]
            
            print(f"🔍 Monitoreando proceso PID {pid}: {command[:50]}...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            while self.running and process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        formatted_line = self.format_log_line(line.strip(), f"PID{pid}")
                        print(formatted_line)
                        sys.stdout.flush()
                except Exception as e:
                    print(f"❌ Error leyendo logs del proceso {pid}: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error monitoreando proceso {pid}: {e}")

    def monitor_docker_logs(self):
        """Monitorea logs de contenedores Docker si la aplicación está en Docker."""
        try:
            # Buscar contenedores relacionados con KognitoAI
            cmd = ["docker", "ps", "--format", "{{.Names}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            containers = []
            for line in result.stdout.split('\n'):
                if line.strip() and any(keyword in line.lower() for keyword in ['kognito', 'api', 'web']):
                    containers.append(line.strip())
            
            if containers:
                print(f"🐳 Contenedores Docker encontrados: {containers}")
                for container in containers:
                    self.monitor_docker_container(container)
            else:
                print("🐳 No se encontraron contenedores Docker relevantes")
                
        except FileNotFoundError:
            print("🐳 Docker no está disponible")
        except Exception as e:
            print(f"❌ Error buscando contenedores Docker: {e}")

    def monitor_docker_container(self, container_name: str):
        """Monitorea logs de un contenedor Docker específico."""
        try:
            cmd = ["docker", "logs", "-f", container_name]
            
            print(f"🐳 Monitoreando contenedor: {container_name}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            while self.running and process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        formatted_line = self.format_log_line(line.strip(), f"🐳{container_name}")
                        print(formatted_line)
                        sys.stdout.flush()
                except Exception as e:
                    print(f"❌ Error leyendo logs del contenedor {container_name}: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error monitoreando contenedor {container_name}: {e}")

    def monitor_application_output(self):
        """Monitorea la salida directa de la aplicación si está ejecutándose localmente."""
        try:
            # Intentar conectarse a los logs de systemd si la app está como servicio
            cmd = ["journalctl", "-f", "-u", "*kognito*", "--no-pager", "-o", "cat"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append(process)
            
            print("📊 Monitoreando logs del sistema...")
            
            while self.running and process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        formatted_line = self.format_log_line(line.strip(), "SYSTEM")
                        print(formatted_line)
                        sys.stdout.flush()
                except Exception as e:
                    print(f"❌ Error leyendo logs del sistema: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error monitoreando logs del sistema: {e}")

    def signal_handler(self, signum, frame):
        """Maneja la señal de interrupción."""
        print("\n🛑 Deteniendo monitoreo...")
        self.running = False
        for process in self.processes:
            try:
                process.terminate()
            except:
                pass
        sys.exit(0)

    def start_monitoring(self, method: str = "auto"):
        """Inicia el monitoreo según el método especificado."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print("🚀 Iniciando monitoreo de logs del LLM en tiempo real...")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if method == "auto" or method == "processes":
            processes = self.find_kognito_processes()
            if processes:
                print(f"🔍 Procesos encontrados: {len(processes)}")
                for proc in processes[:3]:  # Limitar a 3 procesos para evitar spam
                    print(f"  - PID {proc['pid']}: {proc['command'][:60]}...")
                print("-" * 80)
                
                # Monitorear cada proceso en paralelo sería complejo, 
                # mejor usar el método de Docker o sistema
        
        if method == "auto" or method == "docker":
            self.monitor_docker_logs()
        
        if method == "auto" or method == "system":
            self.monitor_application_output()
        
        # Si no hay procesos activos, mostrar mensaje
        if not self.processes:
            print("❌ No se pudo conectar a ningún proceso.")
            print("💡 Asegúrate de que la aplicación KognitoAI esté ejecutándose.")
            print("💡 Prueba ejecutar este script con sudo si es necesario.")

def main():
    parser = argparse.ArgumentParser(description="Monitor LLM logs in real time")
    parser.add_argument("--method", "-m", 
                       choices=["auto", "docker", "system", "processes"], 
                       default="auto",
                       help="Método de monitoreo (auto, docker, system, processes)")
    
    args = parser.parse_args()
    
    monitor = LiveLLMMonitor()
    monitor.start_monitoring(args.method)

if __name__ == "__main__":
    main()
