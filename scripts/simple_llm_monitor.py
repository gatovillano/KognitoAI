#!/usr/bin/env python3
"""
🔍 Monitor Simple de LLM
=======================

Script simple para monitorear prompts del LLM usando docker logs.

Uso:
    # Monitorear logs en tiempo real
    docker logs -f kognito_core 2>&1 | python scripts/simple_llm_monitor.py
    
    # Solo prompts
    docker logs -f kognito_core 2>&1 | python scripts/simple_llm_monitor.py --only-prompts
"""

import sys
import re
import signal
from datetime import datetime

class SimpleLLMMonitor:
    def __init__(self, only_prompts=False):
        self.only_prompts = only_prompts
        self.running = True
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n🛑 Deteniendo monitor...")
        self.running = False
        sys.exit(0)
    
    def _is_relevant(self, line):
        """Determina si una línea es relevante para el monitor."""
        keywords = [
            "📤 PROMPT",
            "📥 RESPUESTA", 
            "🔧 HERRAMIENTA",
            "📊 TOKENS",
            "create_and_run_agent",
            "Ejecutando agente",
            "AgentExecutor",
            "Tool execution",
            "LLMCallback"
        ]
        return any(keyword in line for keyword in keywords)
    
    def _format_line(self, line):
        """Formatea una línea para mejor visualización."""
        # Extraer timestamp
        now = datetime.now().strftime('%H:%M:%S')
        
        # Extraer account_id si existe
        account_match = re.search(r'account_id[:\s]+(\w+)', line, re.IGNORECASE)
        account = account_match.group(1) if account_match else "N/A"
        
        if "📤 PROMPT" in line or "PROMPT ENVIADO" in line:
            return f"\n{'='*60}\n📤 PROMPT AL LLM [{now}] Account: {account}\n{'='*60}\n{line}"
        elif "📥 RESPUESTA" in line or "RESPUESTA DEL LLM" in line:
            if self.only_prompts:
                return None
            return f"\n{'-'*60}\n📥 RESPUESTA LLM [{now}] Account: {account}\n{'-'*60}\n{line}"
        elif "🔧 HERRAMIENTA" in line or "Tool execution" in line:
            return f"\n🔧 TOOL [{now}] Account: {account}\n{line}"
        elif "📊 TOKENS" in line:
            return f"📊 TOKENS [{now}] Account: {account} | {line}"
        elif "create_and_run_agent" in line:
            return f"\n🚀 AGENTE INICIADO [{now}] Account: {account}\n{line}"
        else:
            return f"🤖 [{now}] {line}"
    
    def monitor(self):
        """Monitorea logs desde stdin."""
        print("🔍 Monitor Simple de LLM")
        print("=" * 40)
        print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.only_prompts:
            print("📤 Modo: Solo prompts")
        print("=" * 40)
        print("🔄 Monitoreando... (Ctrl+C para salir)")
        
        try:
            for line in sys.stdin:
                if not self.running:
                    break
                
                line = line.strip()
                if self._is_relevant(line):
                    formatted = self._format_line(line)
                    if formatted:
                        print(formatted)
                        
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor simple de LLM")
    parser.add_argument("--only-prompts", action="store_true", help="Solo mostrar prompts")
    
    args = parser.parse_args()
    
    monitor = SimpleLLMMonitor(only_prompts=args.only_prompts)
    monitor.monitor()

if __name__ == "__main__":
    main()
