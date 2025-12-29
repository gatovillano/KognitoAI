import asyncio
import os
import json
from tools.create_pdf_tool import CreatePDFTool

async def test_v2():
    tool = MarkdownToPDFTool()
    content = """
# Reporte Moderno con Mermaid
Este reporte demuestra las nuevas capacidades de generación de PDF.

## Diagrama de Flujo
```mermaid
graph TD
    A[Inicio] --> B{¿Es Markdown?}
    B -- Sí --> C[Convertir a HTML]
    B -- No --> D[Error]
    C --> E[Generar PDF con WeasyPrint]
    E --> F[Fin]
```

## Tabla de Estilos
| Elemento | Mejora |
| :--- | :--- |
| Fuente | Más pequeña (9.5pt) |
| Colores | Paleta moderna (#0984e3) |
| Mermaid | Renderizado vía mermaid.ink |

### Código
```python
print("Diseño moderno activado")
```
"""
    print("Iniciando generación de PDF v2...")
    result = await tool._arun(content=content, title="Reporte KAI V2", filename="test_v2.pdf")
    
    print("\n--- Resultado de la Herramienta ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    expected_path = os.path.join("media", "generated_pdfs", "test_v2.pdf")
    if os.path.exists(expected_path):
        print(f"\n✅ Archivo generado en: {expected_path}")
    else:
        print(f"\n❌ Error: El archivo no se encontró.")

if __name__ == "__main__":
    asyncio.run(test_v2())