#!/usr/bin/env python3
"""
🔍 Monitor de LLM para Contenedor Docker
=======================================

Script simplificado para monitorear prompts del LLM dentro del contenedor Docker.
Este script está optimizado para funcionar en el entorno de contenedor sin dependencias externas.

Uso:
    # Desde fuera del contenedor
    docker logs -f kognito_core | python scripts/container_llm_monitor.py
    
    # Desde dentro del contenedor
    python scripts/container_llm_monitor.py --live
"""

import sys
import re
import json
import signal
from datetime import datetime
from typing import Dict, Optional, Any
import argparse

class ContainerLLMMonitor:
    def __init__(self, live_mode: bool = False, only_prompts: bool = False):
        self.live_mode = live_mode
        self.only_prompts = only_prompts
        self.running = True
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja la señal de interrupción para cerrar limpiamente."""
        print("\n🛑 Deteniendo monitor...")
        self.running = False
        sys.exit(0)
    
    def _format_timestamp(self) -> str:
        """Formatea el timestamp actual."""
        return f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    
    def _extract_session_info(self, log_line: str) -> Dict[str, str]:
        """Extrae información de sesión del log."""
        session_info = {}
        
        # Buscar account_id
        account_match = re.search(r'account_id[:\s]+(\w+)', log_line, re.IGNORECASE)
        if account_match:
            session_info['account_id'] = account_match.group(1)
        
        # Buscar thread_id
        thread_match = re.search(r'thread_id[:\s]+(\w+)', log_line, re.IGNORECASE)
        if thread_match:
            session_info['thread_id'] = thread_match.group(1)
        
        return session_info
    
    def _is_llm_log(self, line: str) -> bool:
        """Determina si una línea es relevante para el monitor de LLM."""
        llm_indicators = [
            "📤 PROMPT ENVIADO",
            "📥 RESPUESTA DEL LLM",
            "🔧 HERRAMIENTA EJECUTADA",
            "📊 TOKENS UTILIZADOS",
            "LLMCallback",
            "AgentExecutor",
            "create_and_run_agent",
            "Ejecutando agente",
            "Tool execution",
            "Agent response"
        ]
        
        return any(indicator in line for indicator in llm_indicators)
    
    def _format_log_line(self, line: str) -> str:
        """Formatea una línea de log para mejor visualización."""
        # Extraer timestamp si existe
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%H:%M:%S')
        
        # Extraer información de sesión
        session_info = self._extract_session_info(line)
        session_str = " | ".join([f"{k}: {v}" for k, v in session_info.items() if v])
        
        # Determinar tipo de log y formatear
        if "📤 PROMPT ENVIADO" in line or "PROMPT" in line.upper():
            return f"\n{'='*80}\n📤 PROMPT ENVIADO AL LLM 🕐 {timestamp}\n📋 {session_str}\n{'='*80}\n{line}"
        elif "📥 RESPUESTA" in line or "RESPONSE" in line.upper():
            if self.only_prompts:
                return ""
            return f"\n{'-'*80}\n📥 RESPUESTA DEL LLM 🕐 {timestamp}\n📋 {session_str}\n{'-'*80}\n{line}"
        elif "🔧 HERRAMIENTA" in line or "TOOL" in line.upper():
            return f"\n🔧 HERRAMIENTA EJECUTADA 🕐 {timestamp} | {session_str}\n{line}"
        elif "📊 TOKENS" in line or "TOKEN" in line.upper():
            return f"📊 TOKENS 🕐 {timestamp} | {session_str}\n{line}"
        else:
            # Log general relacionado con LLM
            return f"🤖 LLM LOG 🕐 {timestamp} | {session_str}\n{line}"
    
    def monitor_stdin(self):
        """Monitorea logs desde stdin (para uso con docker logs)."""
        print("🔍 Monitor de LLM para Contenedor Docker")
        print("=" * 50)
        print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📡 Fuente: stdin (docker logs)")
        if self.only_prompts:
            print("📤 Modo: Solo prompts")
        print("=" * 50)
        print("🔄 Monitoreando logs... (Ctrl+C para salir)")
        
        try:
            for line in sys.stdin:
                if not self.running:
                    break
                
                line = line.strip()
                if self._is_llm_log(line):
                    formatted = self._format_log_line(line)
                    if formatted:
                        print(formatted)
                        
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido por el usuario")
        except Exception as e:
            print(f"❌ Error en el monitor: {e}")
    
    def monitor_live(self):
        """Monitorea logs en vivo desde el sistema de logging de Python."""
        print("🔍 Monitor de LLM en Vivo")
        print("=" * 50)
        print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📡 Fuente: logging en vivo")
        if self.only_prompts:
            print("📤 Modo: Solo prompts")
        print("=" * 50)
        print("🔄 Monitoreando logs en vivo... (Ctrl+C para salir)")
        
        # Configurar logging handler personalizado
        import logging
        
        class LLMLogHandler(logging.Handler):
            def __init__(self, monitor):
                super().__init__()
                self.monitor = monitor
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    if self.monitor._is_llm_log(msg):
                        formatted = self.monitor._format_log_line(msg)
                        if formatted:
                            print(formatted)
                except Exception:
                    pass
        
        # Agregar handler a los loggers relevantes
        handler = LLMLogHandler(self)
        handler.setLevel(logging.INFO)
        
        # Obtener loggers principales
        loggers = [
            logging.getLogger('core.agent'),
            logging.getLogger('core.tools'),
            logging.getLogger('core.llm_manager'),
            logging.getLogger('langchain'),
            logging.getLogger('__main__')
        ]
        
        for logger in loggers:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        try:
            print("✅ Handler de logging configurado. Esperando actividad del LLM...")
            
            # Mantener el script corriendo
            while self.running:
                import time
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido por el usuario")
        except Exception as e:
            print(f"❌ Error en el monitor: {e}")
        finally:
            # Limpiar handlers
            for logger in loggers:
                logger.removeHandler(handler)
    
    def run(self):
        """Ejecuta el monitor según el modo configurado."""
        if self.live_mode:
            self.monitor_live()
        else:
            self.monitor_stdin()

def main():
    parser = argparse.ArgumentParser(
        description="Monitor de LLM para contenedor Docker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="Modo en vivo: monitorear logging de Python directamente"
    )
    
    parser.add_argument(
        "--only-prompts",
        action="store_true",
        help="Solo mostrar prompts enviados (sin respuestas del LLM)"
    )
    
    args = parser.parse_args()
    
    monitor = ContainerLLMMonitor(
        live_mode=args.live,
        only_prompts=args.only_prompts
    )
    
    monitor.run()

if __name__ == "__main__":
    main()
