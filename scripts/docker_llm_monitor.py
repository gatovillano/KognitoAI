#!/usr/bin/env python3
"""
🐳 Monitor de LLM para Contenedores Docker
==========================================

Script optimizado para monitorear prompts del LLM desde dentro de contenedores Docker
o desde el host usando logs de Docker.

Uso:
    # Desde el host (recomendado)
    python scripts/docker_llm_monitor.py --container kognito_core

    # Desde dentro del contenedor
    python scripts/docker_llm_monitor.py --internal

    # Con filtros específicos
    python scripts/docker_llm_monitor.py --container kognito_core --account-id 12345

Ejemplos:
    # Monitor básico desde el host
    python scripts/docker_llm_monitor.py --container kognito_core

    # Monitor desde dentro del contenedor
    python scripts/docker_llm_monitor.py --internal

    # Solo prompts, sin respuestas
    python scripts/docker_llm_monitor.py --container kognito_core --only-prompts

    # Guardar en archivo
    python scripts/docker_llm_monitor.py --container kognito_core --save-to logs/docker_llm.log
"""

import argparse
import json
import re
import sys
import time
import subprocess
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class DockerLLMMonitor:
    def __init__(self, 
                 container_name: Optional[str] = None,
                 internal_mode: bool = False,
                 only_prompts: bool = False,
                 account_id_filter: Optional[str] = None,
                 no_truncate: bool = False,
                 save_to_file: Optional[str] = None):
        self.container_name = container_name
        self.internal_mode = internal_mode
        self.only_prompts = only_prompts
        self.account_id_filter = account_id_filter
        self.no_truncate = no_truncate
        self.save_to_file = save_to_file
        self.running = True
        self.file_handle = None
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        if self.save_to_file:
            self.file_handle = open(self.save_to_file, 'a', encoding='utf-8')
    
    def _signal_handler(self, signum, frame):
        """Maneja la señal de interrupción para cerrar limpiamente."""
        print("\n🛑 Deteniendo monitor...")
        self.running = False
        if self.file_handle:
            self.file_handle.close()
        sys.exit(0)
    
    def _write_output(self, text: str):
        """Escribe la salida tanto a consola como a archivo si está configurado."""
        print(text)
        if self.file_handle:
            self.file_handle.write(text + '\n')
            self.file_handle.flush()
    
    def _format_timestamp(self) -> str:
        """Formatea el timestamp actual."""
        return f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    
    def _extract_session_info(self, log_line: str) -> Dict[str, str]:
        """Extrae información de sesión del log."""
        session_info = {}
        
        # Buscar account_id
        account_match = re.search(r'Account: (\w+)', log_line)
        if account_match:
            session_info['account_id'] = account_match.group(1)
        
        # Buscar thread_id
        thread_match = re.search(r'Thread: (\w+)', log_line)
        if thread_match:
            session_info['thread_id'] = thread_match.group(1)
        
        # Buscar modelo
        model_match = re.search(r'Model: ([\w-]+)', log_line)
        if model_match:
            session_info['model'] = model_match.group(1)
        
        return session_info
    
    def _format_prompt_content(self, content: str) -> str:
        """Formatea el contenido del prompt para mejor visualización."""
        if not self.no_truncate and len(content) > 1000:
            content = content[:1000] + "\n... [TRUNCADO - usa --no-truncate para ver completo] ..."
        
        # Resaltar secciones importantes (sin colores para compatibilidad)
        content = re.sub(r'(--- .+ ---)', r'>>> \1 <<<', content)
        content = re.sub(r'(System:|Human:|Assistant:)', r'*** \1 ***', content)
        content = re.sub(r'(Question:|Thought:|Action:|Observation:)', r'=== \1 ===', content)
        
        return content
    
    def _should_show_log(self, session_info: Dict[str, str]) -> bool:
        """Determina si se debe mostrar este log basado en los filtros."""
        if self.account_id_filter:
            session_account = session_info.get('account_id', '')
            if session_account != self.account_id_filter:
                return False
        return True
    
    def _process_log_line(self, line: str):
        """Procesa una línea de log buscando información del LLM."""
        try:
            # Buscar logs del LLM
            if "LLMCallback" in line or "📤 PROMPT ENVIADO" in line or "📥 RESPUESTA DEL LLM" in line:
                session_info = self._extract_session_info(line)
                
                if not self._should_show_log(session_info):
                    return
                
                timestamp = self._format_timestamp()
                session_str = " | ".join([f"{k}: {v}" for k, v in session_info.items() if v])
                
                if "📤 PROMPT ENVIADO" in line:
                    self._write_output(f"\n{'='*80}")
                    self._write_output(f"📤 PROMPT ENVIADO AL LLM {timestamp}")
                    self._write_output(f"📋 Sesión: {session_str}")
                    self._write_output(f"{'='*80}")
                    
                    # Extraer contenido del prompt
                    content_match = re.search(r'Contenido: (.+)', line, re.DOTALL)
                    if content_match:
                        prompt_content = content_match.group(1)
                        self._write_output(self._format_prompt_content(prompt_content))
                
                elif "📥 RESPUESTA DEL LLM" in line and not self.only_prompts:
                    self._write_output(f"\n{'-'*80}")
                    self._write_output(f"📥 RESPUESTA DEL LLM {timestamp}")
                    self._write_output(f"📋 Sesión: {session_str}")
                    self._write_output(f"{'-'*80}")
                    
                    # Extraer contenido de la respuesta
                    content_match = re.search(r'Contenido: (.+)', line, re.DOTALL)
                    if content_match:
                        response_content = content_match.group(1)
                        self._write_output(self._format_prompt_content(response_content))
                
                elif "🔧 HERRAMIENTA EJECUTADA" in line:
                    tool_match = re.search(r'Herramienta: (\w+)', line)
                    tool_name = tool_match.group(1) if tool_match else "Desconocida"
                    
                    input_match = re.search(r'Input: (.+)', line)
                    tool_input = input_match.group(1) if input_match else "No disponible"
                    
                    self._write_output(f"\n🔧 HERRAMIENTA: {tool_name} {timestamp}")
                    self._write_output(f"📋 Sesión: {session_str}")
                    self._write_output(f"📝 Input: {tool_input}")
                
                elif "📊 TOKENS UTILIZADOS" in line:
                    tokens_match = re.search(r'Input: (\d+), Output: (\d+), Total: (\d+)', line)
                    if tokens_match:
                        self._write_output(f"📊 TOKENS {timestamp} | {session_str}")
                        self._write_output(f"   Input: {tokens_match.group(1)} | Output: {tokens_match.group(2)} | Total: {tokens_match.group(3)}")
                
        except Exception as e:
            self._write_output(f"❌ Error procesando línea: {e}")
    
    def monitor_from_host(self):
        """Monitorea logs desde el host usando docker logs."""
        if not self.container_name:
            self._write_output("❌ Error: Se requiere --container cuando se ejecuta desde el host")
            return
        
        self._write_output("🐳 Monitor de LLM para Contenedores Docker")
        self._write_output("=" * 50)
        self._write_output(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write_output(f"📦 Contenedor: {self.container_name}")
        
        if self.account_id_filter:
            self._write_output(f"🎯 Filtrando por Account ID: {self.account_id_filter}")
        if self.only_prompts:
            self._write_output("📤 Modo: Solo prompts (sin respuestas)")
        if self.save_to_file:
            self._write_output(f"💾 Guardando en: {self.save_to_file}")
        
        self._write_output("=" * 50)
        self._write_output("🔄 Monitoreando logs en tiempo real (Ctrl+C para salir)...")
        
        try:
            # Usar docker logs para seguir los logs del contenedor
            cmd = ["docker", "logs", "-f", "--tail", "10", self.container_name]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combinar stderr con stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            while self.running and process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        self._process_log_line(line.strip())
                except Exception as e:
                    self._write_output(f"❌ Error procesando línea: {e}")
                    
        except KeyboardInterrupt:
            self._write_output("\n🛑 Monitor detenido por el usuario")
        except Exception as e:
            self._write_output(f"❌ Error en el monitor: {e}")
        finally:
            if self.file_handle:
                self.file_handle.close()
    
    def monitor_internal(self):
        """Monitorea logs desde dentro del contenedor usando stdout/stderr."""
        self._write_output("🐳 Monitor Interno de LLM (Contenedor)")
        self._write_output("=" * 40)
        self._write_output(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write_output("📝 Nota: Ejecutándose desde dentro del contenedor")
        self._write_output("💡 Para mejor experiencia, usa desde el host con --container")
        self._write_output("=" * 40)
        
        # En modo interno, simplemente esperamos input del usuario para simular
        # En una implementación real, aquí conectarías con el sistema de logging interno
        self._write_output("⚠️  Modo interno requiere integración con el sistema de logging de la aplicación")
        self._write_output("🔄 Para monitoreo en tiempo real, ejecuta desde el host:")
        self._write_output(f"   python scripts/docker_llm_monitor.py --container {self.container_name or 'kognito_core'}")
    
    def run(self):
        """Ejecuta el monitor según el modo configurado."""
        if self.internal_mode:
            self.monitor_internal()
        else:
            self.monitor_from_host()

def main():
    parser = argparse.ArgumentParser(
        description="Monitor de LLM para contenedores Docker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--container",
        type=str,
        help="Nombre del contenedor Docker a monitorear (ej: kognito_core)"
    )
    
    parser.add_argument(
        "--internal",
        action="store_true",
        help="Ejecutar en modo interno (desde dentro del contenedor)"
    )
    
    parser.add_argument(
        "--only-prompts",
        action="store_true",
        help="Solo mostrar prompts enviados (sin respuestas del LLM)"
    )
    
    parser.add_argument(
        "--account-id",
        type=str,
        help="Filtrar por un account_id específico"
    )
    
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="No truncar contenido largo de prompts"
    )
    
    parser.add_argument(
        "--save-to",
        type=str,
        help="Guardar logs también en un archivo"
    )
    
    args = parser.parse_args()
    
    # Validaciones
    if not args.internal and not args.container:
        print("❌ Error: Se requiere --container o --internal")
        print("Ejemplos:")
        print("  python scripts/docker_llm_monitor.py --container kognito_core")
        print("  python scripts/docker_llm_monitor.py --internal")
        sys.exit(1)
    
    monitor = DockerLLMMonitor(
        container_name=args.container,
        internal_mode=args.internal,
        only_prompts=args.only_prompts,
        account_id_filter=args.account_id,
        no_truncate=args.no_truncate,
        save_to_file=args.save_to
    )
    
    monitor.run()

if __name__ == "__main__":
    main()
