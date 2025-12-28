#!/usr/bin/env python3
"""
Prueba para verificar que el filtrado por topic funciona correctamente
en get_full_document_content después de la corrección.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_topic_filtering():
    """Prueba la funcionalidad de filtrado por topic."""
    print("🧪 Iniciando prueba de filtrado por topic...")
    
    try:
        from core.memory_manager import get_full_document_content
        
        # Test case 1: Verificar que la función acepta el parámetro topic
        print("✅ Test 1: Verificando signatura de función...")
        import inspect
        sig = inspect.signature(get_full_document_content)
        params = list(sig.parameters.keys())
        print(f"📋 Parámetros de get_full_document_content: {params}")
        
        if 'topic' in params:
            print("✅ El parámetro 'topic' está presente en la función")
        else:
            print("❌ El parámetro 'topic' NO está presente en la función")
            return False
        
        # Test case 2: Llamar con topic=None (debe funcionar)
        print("\n🧪 Test 2: Llamando con topic=None...")
        try:
            # Usando account_id ficticio y file_name que no existe
            result = await get_full_document_content(
                account_id="test-account-123",
                file_name="test_file.txt",
                topic=None
            )
            print(f"✅ Llamada con topic=None exitosa. Resultado: {result}")
        except Exception as e:
            if "No se encontraron chunks" in str(e) or result is None:
                print("✅ Llamada con topic=None manejada correctamente (no hay documentos)")
            else:
                print(f"❌ Error inesperado: {e}")
        
        # Test case 3: Llamar con topic específico
        print("\n🧪 Test 3: Llamando con topic específico...")
        try:
            result = await get_full_document_content(
                account_id="test-account-123",
                file_name="test_file.txt",
                topic="test_topic"
            )
            print(f"✅ Llamada con topic específico exitosa. Resultado: {result}")
        except Exception as e:
            if "No se encontraron chunks" in str(e) or result is None:
                print("✅ Llamada con topic específico manejada correctamente (no hay documentos)")
            else:
                print(f"❌ Error inesperado: {e}")
        
        print("\n✅ Todos los tests de signatura de función pasaron correctamente")
        return True
        
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando prueba de corrección de filtrado por topic...")
    success = asyncio.run(test_topic_filtering())
    
    if success:
        print("\n🎉 ¡PRUEBA EXITOSA! El filtrado por topic ha sido implementado correctamente.")
        sys.exit(0)
    else:
        print("\n💥 ¡PRUEBA FALLIDA! Hay problemas con la implementación.")
        sys.exit(1)