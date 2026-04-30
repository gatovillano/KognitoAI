# tests/test_structured_data_tool.py

import asyncio
import os
import sys

# Añadir el directorio raíz al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from skills.data_and_forms_skill.scripts.structured_data_generator_tool import StructuredDataGeneratorTool

async def test_tool():
    tool = StructuredDataGeneratorTool()
    
    test_data = [
        {"Nombre": "Juan", "Edad": 30, "Ciudad": "Madrid"},
        {"Nombre": "Ana", "Edad": 25, "Ciudad": "Barcelona"},
        {"Nombre": "Luis", "Edad": 35, "Ciudad": "Valencia"}
    ]
    
    formats = ["csv", "xlsx", "ods"]
    
    print("🚀 Iniciando pruebas de StructuredDataGeneratorTool...")
    
    for fmt in formats:
        print(f"\n--- Probando formato: {fmt} ---")
        try:
            result = await tool._arun(
                data=test_data,
                format=fmt,
                title=f"Prueba de datos {fmt}",
                filename=f"test_output_{fmt}"
            )
            
            if "sources" in result and len(result["sources"]) > 0:
                source = result["sources"][0]
                file_path = source["metadata"]["file_path"]
                download_url = source["url"]
                
                if os.path.exists(file_path):
                    print(f"✅ Archivo generado: {file_path}")
                    print(f"✅ URL de descarga: {download_url}")
                else:
                    print(f"❌ Error: El archivo no existe en {file_path}")
            else:
                print(f"❌ Error en el resultado: {result.get('context_for_llm')}")
                
        except Exception as e:
            print(f"❌ Excepción durante la prueba de {fmt}: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool())
