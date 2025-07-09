#!/usr/bin/env python3
"""
🔍 Monitor Detallado de Prompts del LLM
======================================

Script para monitorear en tiempo real exactamente cómo llegan los prompts al LLM,
incluyendo estructura completa, tokens, herramientas y metadatos.

Uso:
    python scripts/detailed_llm_prompt_monitor.py [opciones]

Ejemplos:
    # Monitoreo básico en tiempo real
    python scripts/detailed_llm_prompt_monitor.py

    # Solo mostrar prompts (sin respuestas)
    python scripts/detailed_llm_prompt_monitor.py --only-prompts

    # Filtrar por account_id específico
    python scripts/detailed_llm_prompt_monitor.py --account-id 12345

    # Mostrar prompts completos sin truncar
    python scripts/detailed_llm_prompt_monitor.py --no-truncate

    # Guardar en archivo además de mostrar en pantalla
    python scripts/detailed_llm_prompt_monitor.py --save-to logs/detailed_prompts.log
"""

import argparse
import json
import re
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import signal

class LLMPromptMonitor:
    def __init__(self, 
                 only_prompts: bool = False,
                 account_id_filter: Optional[str] = None,
                 no_truncate: bool = False,
                 save_to_file: Optional[str] = None,
                 show_tokens: bool = True,
                 show_tools: bool = True):
        self.only_prompts = only_prompts
        self.account_id_filter = account_id_filter
        self.no_truncate = no_truncate
        self.save_to_file = save_to_file
        self.show_tokens = show_tokens
        self.show_tools = show_tools
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
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Formatea el timestamp para mejor legibilidad."""
        try:
            # Extraer timestamp del log
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', timestamp_str)
            if match:
                return f"🕐 {match.group(1)}"
            return f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        except:
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
        
        # Resaltar secciones importantes
        content = re.sub(r'(--- .+ ---)', r'\033[1;36m\1\033[0m', content)  # Cyan bold para secciones
        content = re.sub(r'(System:|Human:|Assistant:)', r'\033[1;33m\1\033[0m', content)  # Yellow bold para roles
        content = re.sub(r'(Question:|Thought:|Action:|Observation:)', r'\033[1;32m\1\033[0m', content)  # Green bold para ReAct
        
        return content
    
    def _parse_llm_interaction(self, log_line: str) -> Optional[Dict[str, Any]]:
        """Parsea una línea de log de interacción con el LLM."""
        try:
            # Buscar diferentes tipos de logs del LLM
            if "📤 PROMPT ENVIADO AL LLM" in log_line:
                return self._parse_prompt_log(log_line)
            elif "📥 RESPUESTA DEL LLM" in log_line and not self.only_prompts:
                return self._parse_response_log(log_line)
            elif "🔧 HERRAMIENTA EJECUTADA" in log_line and self.show_tools:
                return self._parse_tool_log(log_line)
            elif "📊 TOKENS UTILIZADOS" in log_line and self.show_tokens:
                return self._parse_token_log(log_line)
            
            return None
        except Exception as e:
            print(f"❌ Error parseando log: {e}")
            return None
    
    def _parse_prompt_log(self, log_line: str) -> Dict[str, Any]:
        """Parsea un log de prompt enviado al LLM."""
        session_info = self._extract_session_info(log_line)
        
        # Extraer el contenido del prompt
        prompt_match = re.search(r'Contenido: (.+)', log_line, re.DOTALL)
        prompt_content = prompt_match.group(1) if prompt_match else "No se pudo extraer el contenido"
        
        return {
            'type': 'prompt',
            'session_info': session_info,
            'content': prompt_content,
            'timestamp': self._format_timestamp(log_line)
        }
    
    def _parse_response_log(self, log_line: str) -> Dict[str, Any]:
        """Parsea un log de respuesta del LLM."""
        session_info = self._extract_session_info(log_line)
        
        # Extraer el contenido de la respuesta
        response_match = re.search(r'Contenido: (.+)', log_line, re.DOTALL)
        response_content = response_match.group(1) if response_match else "No se pudo extraer el contenido"
        
        return {
            'type': 'response',
            'session_info': session_info,
            'content': response_content,
            'timestamp': self._format_timestamp(log_line)
        }
    
    def _parse_tool_log(self, log_line: str) -> Dict[str, Any]:
        """Parsea un log de herramienta ejecutada."""
        session_info = self._extract_session_info(log_line)
        
        # Extraer información de la herramienta
        tool_match = re.search(r'Herramienta: (\w+)', log_line)
        tool_name = tool_match.group(1) if tool_match else "Desconocida"
        
        input_match = re.search(r'Input: (.+)', log_line)
        tool_input = input_match.group(1) if input_match else "No disponible"
        
        return {
            'type': 'tool',
            'session_info': session_info,
            'tool_name': tool_name,
            'input': tool_input,
            'timestamp': self._format_timestamp(log_line)
        }
    
    def _parse_token_log(self, log_line: str) -> Dict[str, Any]:
        """Parsea un log de uso de tokens."""
        session_info = self._extract_session_info(log_line)
        
        # Extraer información de tokens
        tokens_match = re.search(r'Input: (\d+), Output: (\d+), Total: (\d+)', log_line)
        if tokens_match:
            tokens_info = {
                'input': int(tokens_match.group(1)),
                'output': int(tokens_match.group(2)),
                'total': int(tokens_match.group(3))
            }
        else:
            tokens_info = {'input': 0, 'output': 0, 'total': 0}
        
        return {
            'type': 'tokens',
            'session_info': session_info,
            'tokens': tokens_info,
            'timestamp': self._format_timestamp(log_line)
        }
    
    def _should_show_log(self, interaction: Dict[str, Any]) -> bool:
        """Determina si se debe mostrar este log basado en los filtros."""
        if self.account_id_filter:
            session_account = interaction.get('session_info', {}).get('account_id', '')
            if session_account != self.account_id_filter:
                return False
        
        return True
    
    def _display_interaction(self, interaction: Dict[str, Any]):
        """Muestra una interacción formateada."""
        if not self._should_show_log(interaction):
            return
        
        interaction_type = interaction['type']
        timestamp = interaction['timestamp']
        session_info = interaction['session_info']
        
        # Header con información de sesión
        session_str = " | ".join([f"{k}: {v}" for k, v in session_info.items() if v])
        
        if interaction_type == 'prompt':
            self._write_output(f"\n{'='*80}")
            self._write_output(f"📤 PROMPT ENVIADO AL LLM {timestamp}")
            self._write_output(f"📋 Sesión: {session_str}")
            self._write_output(f"{'='*80}")
            self._write_output(self._format_prompt_content(interaction['content']))
            
        elif interaction_type == 'response':
            self._write_output(f"\n{'-'*80}")
            self._write_output(f"📥 RESPUESTA DEL LLM {timestamp}")
            self._write_output(f"📋 Sesión: {session_str}")
            self._write_output(f"{'-'*80}")
            self._write_output(self._format_prompt_content(interaction['content']))
            
        elif interaction_type == 'tool':
            self._write_output(f"\n🔧 HERRAMIENTA: {interaction['tool_name']} {timestamp}")
            self._write_output(f"📋 Sesión: {session_str}")
            self._write_output(f"📝 Input: {interaction['input']}")
            
        elif interaction_type == 'tokens':
            tokens = interaction['tokens']
            self._write_output(f"📊 TOKENS {timestamp} | {session_str}")
            self._write_output(f"   Input: {tokens['input']} | Output: {tokens['output']} | Total: {tokens['total']}")
    
    def _detect_log_source(self):
        """Detecta la mejor fuente de logs disponible."""
        # Opciones en orden de preferencia
        log_sources = [
            # 1. Docker logs del contenedor actual (si estamos en contenedor)
            ("docker", ["docker", "logs", "-f", "kognito_core"]),
            # 2. Archivo de log específico si existe
            ("file", ["/var/log/kognito.log"]),
            # 3. journalctl si está disponible (sistemas con systemd)
            ("journalctl", ["journalctl", "-f", "--no-pager", "-o", "cat"]),
            # 4. Fallback: monitorear stdout/stderr actual
            ("stdout", None)
        ]

        for source_type, cmd in log_sources:
            try:
                if source_type == "docker":
                    # Verificar si docker está disponible y el contenedor existe
                    result = subprocess.run(["docker", "ps", "--filter", "name=kognito_core", "--format", "{{.Names}}"],
                                          capture_output=True, text=True, timeout=5)
                    if "kognito_core" in result.stdout:
                        return source_type, cmd
                elif source_type == "file":
                    # Verificar si el archivo de log existe
                    if Path(cmd[0]).exists():
                        return source_type, ["tail", "-f", cmd[0]]
                elif source_type == "journalctl":
                    # Verificar si journalctl está disponible
                    result = subprocess.run(["which", "journalctl"], capture_output=True, timeout=5)
                    if result.returncode == 0:
                        return source_type, cmd
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                continue

        return "stdout", None

    def monitor_logs(self):
        """Monitorea los logs en tiempo real."""
        self._write_output("🔍 Monitor Detallado de Prompts del LLM")
        self._write_output("=" * 50)
        self._write_output(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if self.account_id_filter:
            self._write_output(f"🎯 Filtrando por Account ID: {self.account_id_filter}")
        if self.only_prompts:
            self._write_output("📤 Modo: Solo prompts (sin respuestas)")
        if self.save_to_file:
            self._write_output(f"💾 Guardando en: {self.save_to_file}")

        # Detectar fuente de logs
        log_source, cmd = self._detect_log_source()
        self._write_output(f"📡 Fuente de logs: {log_source}")

        self._write_output("=" * 50)
        self._write_output("🔄 Monitoreando logs en tiempo real (Ctrl+C para salir)...")

        try:
            if log_source == "stdout":
                self._write_output("⚠️  No se encontró fuente de logs externa. Monitoreando entrada estándar...")
                self._write_output("💡 Tip: Ejecuta este script con 'docker logs -f kognito_core | python scripts/detailed_llm_prompt_monitor.py'")

                # Leer desde stdin
                while self.running:
                    try:
                        line = sys.stdin.readline()
                        if not line:  # EOF
                            break
                        if "LLMCallback" in line:
                            interaction = self._parse_llm_interaction(line.strip())
                            if interaction:
                                self._display_interaction(interaction)
                    except Exception as e:
                        self._write_output(f"❌ Error procesando línea: {e}")
            else:
                # Usar comando externo
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                while self.running and process.poll() is None:
                    try:
                        line = process.stdout.readline()
                        if line and "LLMCallback" in line:
                            interaction = self._parse_llm_interaction(line.strip())
                            if interaction:
                                self._display_interaction(interaction)
                    except Exception as e:
                        self._write_output(f"❌ Error procesando línea: {e}")

        except KeyboardInterrupt:
            self._write_output("\n🛑 Monitor detenido por el usuario")
        except Exception as e:
            self._write_output(f"❌ Error en el monitor: {e}")
        finally:
            if self.file_handle:
                self.file_handle.close()

def main():
    parser = argparse.ArgumentParser(
        description="Monitor detallado de prompts del LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
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
    
    parser.add_argument(
        "--no-tokens",
        action="store_true",
        help="No mostrar información de tokens"
    )
    
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="No mostrar información de herramientas"
    )
    
    args = parser.parse_args()
    
    monitor = LLMPromptMonitor(
        only_prompts=args.only_prompts,
        account_id_filter=args.account_id,
        no_truncate=args.no_truncate,
        save_to_file=args.save_to,
        show_tokens=not args.no_tokens,
        show_tools=not args.no_tools
    )
    
    monitor.monitor_logs()

if __name__ == "__main__":
    main()
