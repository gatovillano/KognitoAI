# Arquitectura de Herramientas en Kognito AI

Este documento describe la arquitectura de las herramientas (LangChain Tools) utilizadas en el proyecto Kognito AI, enfocándose en su definición, instanciación y la gestión de parámetros como el `account_id`.

## 1. Definición de Herramientas

Las herramientas en Kognito AI se definen como clases que heredan de `langchain_core.tools.BaseTool`. Estas clases utilizan `Pydantic` para definir sus esquemas de entrada (`args_schema`) y sus atributos.

**Ejemplo de Definición (`tools/example_tool.py`):**

```python
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

class ExampleToolInput(BaseModel):
    """Schema de entrada para ExampleTool."""
    param1: str = Field(..., description="Descripción del parámetro 1.")

class ExampleTool(BaseTool):
    name: str = "example_tool"
    description: str = "Una herramienta de ejemplo."
    args_schema: Type[BaseModel] = ExampleToolInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")

    async def _arun(self, param1: str, **kwargs) -> str:
        # Lógica de la herramienta
        return f"Ejecutando ExampleTool con param1: {param1} para account_id: {self.account_id}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("ExampleTool no soporta ejecución síncrona.")
```

**Puntos Clave:**
- **Herencia:** Todas las herramientas heredan de `BaseTool`.
- **Esquema de Entrada (`args_schema`):** Se define usando una clase `Pydantic.BaseModel` que especifica los parámetros que la herramienta espera recibir del LLM.
- **Atributos de la Herramienta:** Los atributos de la propia herramienta (como `account_id`) se definen directamente en la clase de la herramienta usando `Pydantic.Field`.
- **`account_id` como `Field(...)`:** Es crucial que el `account_id` se defina como un `Pydantic.Field(...)` (con los `...` indicando que es un campo requerido) en la clase de la herramienta. Esto asegura que Pydantic lo reconozca como un parámetro esperado en el constructor y permita su inyección.
- **Métodos `_arun` y `_run`:** Las herramientas implementan `_arun` para la lógica asíncrona (preferida en este proyecto) y `_run` para la lógica síncrona (generalmente no implementada o marcada como `NotImplementedError`).

## 2. Instanciación de Herramientas

Las herramientas se instancian centralmente en la función `get_all_langchain_tools` ubicada en `core/tools.py`. Esta función es responsable de recopilar todas las herramientas disponibles y prepararlas para ser utilizadas por el agente de IA.

**Proceso de Instanciación en `core/tools.py`:**

```python
# Extracto de core/tools.py
import logging
from typing import List
from langchain_core.tools import Tool
# ... (otras importaciones de herramientas)

logger = logging.getLogger(__name__)

def get_all_langchain_tools(account_id: str, telegram_id: str = "") -> List[Tool]:
    logger.info("⚙️ Ensamblando la caja de herramientas del agente...")
    available_tools: List[Tool] = []

    # Lista de todas las clases de herramientas que se instancian directamente.
    tool_classes_to_instantiate = [
        # ... (lista completa de ToolClass)
    ]

    for ToolClass in tool_classes_to_instantiate:
        try:
            tool_instance = None
            tool_name = getattr(ToolClass, 'name', ToolClass.__name__)

            # Lógica para pasar account_id y telegram_id
            if 'account_id' in ToolClass.model_fields: # Verifica si 'account_id' es un campo de Pydantic
                kwargs = {"account_id": account_id}
                if 'telegram_id' in ToolClass.model_fields: # Verifica si 'telegram_id' es un campo de Pydantic
                    kwargs["telegram_id"] = telegram_id
                tool_instance = ToolClass(**kwargs)
            else: # Herramientas generales que no requieren account_id o telegram_id
                tool_instance = ToolClass()

            if tool_instance:
                available_tools.append(tool_instance)
                logger.debug(f"  [+] Herramienta cargada: {tool_instance.name}")
        except Exception as e:
            logger.error(f"❌ Fallo al instanciar la herramienta '{tool_name}': {e}", exc_info=True)
    
    # Instanciar herramientas que provienen de funciones de fábrica.
    # ... (lógica de fábrica)
    
    logger.info("--- 🧰 Caja de Herramientas Ensamblada ---")
    for tool in available_tools:
        logger.info(f"  ✅ {tool.name}")
    logger.info(f"  Total de herramientas operativas: {len(available_tools)}")
    logger.info("-------------------------------------------")

    return available_tools
```

**Puntos Clave del Proceso:**
- **Centralización:** `get_all_langchain_tools` es el único punto donde se instancian la mayoría de las herramientas.
- **Detección de `account_id`:** La función utiliza `ToolClass.model_fields` para detectar si una herramienta requiere el `account_id` (y opcionalmente `telegram_id`). Esta es la forma robusta de verificar los campos definidos por Pydantic.
- **Inyección de Parámetros:** Si se detecta `account_id` (y/o `telegram_id`), estos se pasan al constructor de la herramienta a través de `**kwargs`.
- **Manejo de Errores:** Cada instanciación está envuelta en un bloque `try...except` para evitar que una herramienta fallida detenga la carga de las demás.

## 3. Gestión del `account_id`

El `account_id` es un identificador crucial que asegura el aislamiento de los datos del usuario entre diferentes sesiones o usuarios. Se inyecta a las herramientas que lo requieren en el momento de su instanciación.

**Flujo del `account_id`:**
1. **Definición de la Herramienta:** La herramienta declara `account_id: str = Field(..., description="...")` para indicar que espera este parámetro.
2. **Instanciación Centralizada:** La función `get_all_langchain_tools` recibe el `account_id` del contexto de la aplicación (por ejemplo, de la sesión del usuario o del `run_manager` del agente).
3. **Inyección en el Constructor:** `get_all_langchain_tools` pasa este `account_id` al constructor de la herramienta si la herramienta lo ha declarado como un campo de Pydantic.
4. **Uso Interno:** La herramienta utiliza `self.account_id` en sus métodos `_arun` para filtrar operaciones, como búsquedas en bases de datos o acceso a documentos, garantizando que solo se acceda a los datos del usuario correcto.

## 4. Herramientas Asíncronas

La mayoría de las herramientas en Kognito AI están diseñadas para ser asíncronas (`async def _arun(...)`). Esto es fundamental para la escalabilidad y el rendimiento del sistema, permitiendo que el agente maneje múltiples operaciones de E/S sin bloquear el hilo principal. Las llamadas síncronas (`_run`) generalmente lanzan un `NotImplementedError` o simplemente envuelven la llamada asíncrona.

## Conclusión

La arquitectura de herramientas de Kognito AI se basa en un diseño modular con `LangChain` y `Pydantic`, permitiendo una definición clara de las entradas y atributos de las herramientas, y una gestión centralizada y robusta de su instanciación y de la inyección de parámetros contextuales como el `account_id`. Esto facilita la extensibilidad, el mantenimiento y la seguridad de la interacción del agente con los datos del usuario.