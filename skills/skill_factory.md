# Skill Factory

Esta habilidad permite a KAI expandir sus propias capacidades creando nuevas "Skills".
Úsala cuando te des cuenta de que necesitas una herramienta que no existe actualmente (por ejemplo, para interactuar con una API específica, procesar datos de una forma nueva o realizar cálculos complejos).

### Cómo usarla:
1. **Diseña la lógica**: Define qué parámetros necesita la herramienta y qué debe devolver.
2. **Genera el código Python**: Debes escribir una clase que herede de `BaseTool` de LangChain.
3. **Genera la documentación Markdown**: Escribe instrucciones claras sobre cuándo y cómo usar esta nueva habilidad.
4. **Ejecuta la factoría**: Pasa el nombre de la skill, el código y el markdown.

La nueva skill estará disponible inmediatamente en el siguiente turno de la conversación.

### Ejemplo de Estructura de código:
```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class InputSchema(BaseModel):
    query: str = Field(description="Descripción del parámetro")

class MyNewSkill(BaseTool):
    name: str = "my_new_skill"
    description: str = "Resumen corto"
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, query: str) -> str:
        # Tu lógica aquí
        return f"Resultado para {query}"
```
