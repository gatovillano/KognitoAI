import asyncio
import os
import sys
import logging
import types
from datetime import datetime

# Mocking necessary parts to run the tool standalone
sys.path.append(os.getcwd())

# Create dummy MEDIA_ROOT if it doesn't exist
if not os.path.exists("media"):
    os.makedirs("media/generated_pdfs", exist_ok=True)

# Mock api.galleries.MEDIA_ROOT
galleries = types.ModuleType('api.galleries')
galleries.MEDIA_ROOT = os.path.join(os.getcwd(), "media")
sys.modules['api.galleries'] = galleries

# Mock core.config.settings
config = types.ModuleType('core.config')
class Settings:
    api_server_url = "http://localhost:8000"
config.settings = Settings()
sys.modules['core.config'] = config

from tools.create_pdf_tool import CreatePDFTool

async def run_test():
    tool = CreatePDFTool()
    content = """
# Título de Prueba
Este es un documento generado para probar el renderizado de **Markdown**.

## Características
- Soporte para listas
- Soporte para **negritas**
- Soporte para *cursivas*

| Tabla | Datos |
|-------|-------|
| Fila 1| Valor 1|
| Fila 2| Valor 2|

```python
def hola():
    print("Hola Mundo")
```
"""
    print("Generando PDF...")
    try:
        result = await tool._arun(content=content, title="Prueba de Renderizado")
        print("\n--- Resultado ---")
        print(result)
        
        file_path = result["sources"][0]["metadata"]["file_path"]
        if os.path.exists(file_path):
            print(f"\n✅ PDF generado exitosamente en: {file_path}")
            print(f"Tamaño del archivo: {os.path.getsize(file_path)} bytes")
        else:
            print(f"\n❌ El archivo PDF no se encontró en: {file_path}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
