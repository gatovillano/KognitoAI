#!/usr/bin/env python3
"""
Inicialización del pipeline de medición
"""

import os
import sys
from pathlib import Path

def init_pipeline():
    """Inicializa el entorno del pipeline"""
    pipeline_dir = Path(__file__).parent.parent
    
    # Crear directorios necesarios
    (pipeline_dir / "reports").mkdir(exist_ok=True)
    (pipeline_dir / "logs").mkdir(exist_ok=True)
    
    # Verificar dependencias
    print("Verificando dependencias...")
    try:
        import aiohttp
        print("  ✅ aiohttp disponible")
    except ImportError:
        print("  ❌ aiohttp no instalado")
        return False
    
    print("\n✅ Pipeline inicializado correctamente")
    print(f"Directorio: {pipeline_dir}")
    return True

if __name__ == "__main__":
    init_pipeline()
