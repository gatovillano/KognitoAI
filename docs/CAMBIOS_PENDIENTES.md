# Registro de Cambios - Soporte Multi-LLM para Herramientas

**Fecha**: 30-11-2024  
**Problema**: Los LLMs no-Gemini (especialmente GPT-5) enviaban argumentos vacíos `{}` a las herramientas, causando errores de validación de Pydantic y bucles infinitos.

## Cambios Implementados

### 1. `core/agent.py` - Compatibilidad Multi-LLM y Validación

#### Funciones Nuevas

- **`format_validation_error_for_llm()`**: Convierte errores de Pydantic en mensajes claros con instrucciones
- **`should_stop_retrying_tool()`**: Previene bucles infinitos después de 3 intentos fallidos

#### Modificaciones en `AgentState`

- Agregado campo `tool_error_counts: Optional[Dict[str, int]]` para tracking de errores

#### Modificaciones en `call_model_node()`

- Eliminado `cast(ChatGoogleGenerativeAI, llm)` que solo funcionaba con Gemini
- Implementado binding genérico de herramientas compatible con cualquier LLM
- Manejo graceful de LLMs que no soportan `bind_tools`

#### Modificaciones en `tool_node()`

- **Validación PRE-EJECUCIÓN**: Detecta argumentos faltantes ANTES de que LangChain intente parsearlos
- Validación de nombres de herramientas vacíos
- Tracking automático de errores por herramienta
- Mensajes de error específicos para errores de validación vs errores generales
- Incremento automático del contador de errores

### 2. `tools/web_search_tool.py` - Mejora de Descripción

#### Cambios en `WebSearchInput`

- Eliminado `json_schema_extra={"type": "string"}` que confundía a GPT-5
- Descripción más detallada del parámetro `query`

#### Cambios en `WebSearchTool.description`

- Descripción más concisa y directa
- **Mención explícita de parámetros requeridos** al inicio
- **Ejemplo de uso** incluido en la descripción
- Eliminadas instrucciones largas sobre formato de respuesta

### 3. `core/llm_manager.py` - Optimización para OpenAI

#### Cambios en `initialize_llms()`

- Configuración dinámica de `llm_kwargs`
- Detección automática de modelos OpenAI/GPT
- Parámetro `tool_choice: "auto"` para modelos GPT
- Manejo condicional de `api_base`

## Archivos Modificados

1. `/home/gato/KognitoAI/kognito-ai/core/agent.py`
   - Líneas 30: Import de `ValidationError`
   - Líneas 128-210: Funciones de validación
   - Líneas 592-607: Binding genérico de herramientas
   - Líneas 767-887: Validación pre-ejecución y tracking
   - Líneas 893-933: Manejo mejorado de excepciones

2. `/home/gato/KognitoAI/kognito-ai/tools/web_search_tool.py`
   - Líneas 30-35: Schema mejorado de `WebSearchInput`
   - Líneas 47-53: Descripción optimizada para GPT-5

3. `/home/gato/KognitoAI/kognito-ai/core/llm_manager.py`
   - Líneas 38-65: Configuración optimizada para OpenAI

## Resultados Esperados

### Antes

```
ERROR: 1 validation error for WebSearchInput
query
  Field required [type=missing, input_value={}, input_type=dict]
```

*El error se repetía infinitamente*

### Después

```
⚠️ Argumentos faltantes detectados ANTES de ejecutar 'web_search': ['query']

❌ Error al ejecutar la herramienta 'web_search':

Faltan los siguientes parámetros requeridos:
- query

Argumentos recibidos: {}

💡 INSTRUCCIONES PARA CORREGIR:
1. La herramienta 'web_search' REQUIERE los siguientes parámetros: query
2. Debes proporcionar un valor válido para cada parámetro requerido
3. Ejemplo de uso correcto:
   {
     "query": "valor_apropiado"
   }

⚠️ IMPORTANTE: Si no estás seguro de qué valor usar, o si has intentado varias veces sin éxito:
- Intenta responder la pregunta del usuario SIN usar esta herramienta
- O usa una herramienta DIFERENTE que pueda ayudar
```

*Después de 3 intentos, el sistema sugiere al LLM usar otra estrategia*

## Próximos Pasos para Probar

1. **Reiniciar el servicio**:

   ```bash
   docker compose restart core
   ```

2. **Monitorear logs**:

   ```bash
   docker compose logs -f core | grep -E "bind_tools|Argumentos faltantes|tool_error_counts"
   ```

3. **Probar con GPT-5**:
   - Hacer una pregunta que requiera búsqueda web
   - Verificar que el LLM reciba el mensaje de error claro
   - Verificar que no entre en bucle infinito
   - Verificar que eventualmente responda sin la herramienta o la use correctamente

## Notas Técnicas

- El problema NO era la capacidad de GPT-5, sino cómo LiteLLM traduce el esquema de herramientas
- La validación pre-ejecución es crucial porque evita que LangChain intente parsear argumentos inválidos
- El `tool_choice: "auto"` ayuda a GPT-5 a entender mejor cuándo y cómo usar herramientas
- La descripción concisa con ejemplo explícito mejora significativamente el tool calling
