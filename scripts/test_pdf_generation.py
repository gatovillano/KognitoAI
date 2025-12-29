import asyncio
import os
from tools.create_pdf_tool import CreatePDFTool

async def test_generation():
    tool = MarkdownToPDFTool()
    content = """
# Test de Generación de PDF
Este es un documento de prueba generado por el agente KAI.

## Características:
- **Negrita** y *cursiva*.
- Listas ordenadas y desordenadas.
- Tablas de datos:

| Herramienta | Función | Estado |
| :--- | :--- | :--- |
| Markdown | Conversión HTML | ✅ |
| WeasyPrint | Generación PDF | ✅ |

### Código de ejemplo:
```python
def hello_world():
    print("Hola desde el PDF generado por KAI")
```

> "La elegancia es la única belleza que nunca se marchita." — Audrey Hepburn
"""
    print("Iniciando generación de PDF de prueba...")
    result = await tool._arun(content=content, title="Reporte de Prueba KAI", filename="test_kai_report.pdf")
    print(result)
    
    # Verificar si el archivo existe
    expected_path = os.path.join("media", "generated_pdfs", "test_kai_report.pdf")
    if os.path.exists(expected_path):
        print(f"✅ Verificación exitosa: El archivo existe en {expected_path}")
    else:
        print(f"❌ Error: El archivo no se encontró en {expected_path}")

if __name__ == "__main__":
    asyncio.run(test_generation())