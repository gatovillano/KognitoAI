#!/usr/bin/env python3
"""
Bucle de monitoreo continuo
"""

import time
import subprocess
from datetime import datetime

def run_monitoring_loop(interval_minutes=5):
    """Ejecuta pipeline repetidamente"""
    print(f"Iniciando monitoreo cada {interval_minutes} minutos...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        while True:
            print(f"\n[{datetime.now().isoformat()}] Ejecutando medición...")
            subprocess.run(["python3", "run_measurements.py"])
            print(f"\nEsperando {interval_minutes} minutos...")
            time.sleep(interval_minutes * 60)
    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido.")

if __name__ == "__main__":
    run_monitoring_loop()
