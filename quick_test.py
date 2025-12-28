#!/usr/bin/env python3
"""
Prueba rápida para verificar que el filtrado por topic funciona correctamente.
"""

import inspect
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_function_signature():
    """Prueba la signatura de la función."""
    print("🧪 Verificando signatura de get_full_document_content...")
    
    try:
        from core.memory_manager import get_full_document_content
        
        sig = inspect.signature(get_full_document_content)
        params = list(sig.parameters.keys())
        print(f"📋 Parámetros: {params}")
        
        if 'topic' in params:
            print("✅ Parámetro 'topic' presente")
            return True
        else:
            print("❌ Parámetro 'topic' NO presente")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_function_signature()
    if success:
        print("🎉 ¡Corrección implementada correctamente!")
    else:
        print("💥 ¡La corrección falló!")
    sys.exit(0 if success else 1)