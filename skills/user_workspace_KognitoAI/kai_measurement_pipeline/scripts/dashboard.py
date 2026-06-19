#!/usr/bin/env python3
"""
Dashboard simple de métricas en consola
"""

import json
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path("reports")

def show_dashboard():
    """Muestra dashboard de métricas"""
    print("\n" + "="*60)
    print("📊 KAI PERFORMANCE DASHBOARD")
    print("="*60)
    
    # Obtener último reporte
    reports = sorted(REPORTS_DIR.glob("metrics_*.json"), reverse=True)
    if not reports:
        print("No hay reportes disponibles")
        return
    
    latest = reports[0]
    with open(latest) as f:
        data = json.load(f)
    
    print(f"\n📅 Última medición: {data['timestamp']}")
    print("\n📈 Métricas:")
    print("-"*60)
    
    for m in data["metrics"]:
        icon = "✅" if m["status"] == "OK" else "⚠️"
        print(f"{icon} {m['metric']}: {m['value']}{m.get('unit', '')} (meta: {m['reference']}{m.get('unit', '')})")
    
    print("-"*60)
    print(f"⚠️  Alertas: {data['summary']['warnings']}")

if __name__ == "__main__":
    show_dashboard()
