# Herramienta de Análisis de Código con Guardado en Base de Datos

## Descripción

La herramienta `analyze_code_for_insights_tool.py` ha sido actualizada para permitir el guardado automático de los resultados de análisis en la base de datos del sistema. Esto permite hacer seguimiento de los análisis realizados y acceder a ellos desde la interfaz de usuario.

## Características

- **Compatibilidad hacia atrás**: La herramienta sigue funcionando como antes para casos existentes
- **Guardado opcional**: Los resultados pueden guardarse en la tabla `analysis_tasks` con tipo `code_insights`
- **Metadatos completos**: Incluye información sobre la herramienta utilizada y timestamp
- **Manejo de errores**: Si falla el guardado, el análisis continúa normalmente

## Uso

### 1. Uso tradicional (sin guardado en BD)

```python
from tools.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool

tool = AnalyzeCodeForInsightsTool()
result = await tool._arun(code_content="tu código aquí")
```

### 2. Uso con guardado en base de datos

```python
from tools.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool

tool = AnalyzeCodeForInsightsTool()
result = await tool._arun(
    code_content="tu código aquí",
    account_id="uuid-del-usuario",
    file_name="Análisis de mi_archivo.py",
    save_to_database=True
)
```

### 3. Función auxiliar (recomendada para nuevos casos)

```python
from tools.analyze_code_for_insights_tool import analyze_code_and_save

result = await analyze_code_and_save(
    code_content="tu código aquí",
    account_id="uuid-del-usuario",
    file_name="Análisis de mi_archivo.py"
)
```

## Estructura en Base de Datos

Los análisis se guardan en la tabla `analysis_tasks` con:

- **analysis_type**: `"code_insights"`
- **file_name**: Nombre descriptivo del análisis
- **status**: `"completed"`
- **result_payload**: JSON con el resultado completo del análisis

### Estructura del result_payload

```json
{
  "executive_summary": "Resumen ejecutivo del análisis...",
  "code_structure": [...],
  "design_patterns": [...],
  "dependencies": [...],
  "potential_issues": [...],
  "recommendations": [...],
  "tool_used": "analyze_code_for_insights_tool.py",
  "analysis_metadata": {
    "tool_used": "analyze_code_for_insights_tool.py",
    "analysis_type": "code_insights",
    "created_at": "2024-01-01T12:00:00",
    "file_name": "Análisis de mi_archivo.py"
  }
}
```

## Integración con Frontend

Los análisis guardados aparecerán automáticamente en:

- La sección de análisis del dashboard
- Los filtros por tipo de análisis
- Las búsquedas de análisis

El tipo `code_insights` se muestra como "Análisis de Código (Insights)" con icono 🔍.

## Notas Importantes

1. **Compatibilidad**: Los usos existentes de la herramienta siguen funcionando sin cambios
2. **account_id requerido**: Para guardar en BD, se debe proporcionar un account_id válido
3. **Manejo de errores**: Si falla el guardado, se registra un warning pero el análisis continúa
4. **Rendimiento**: El guardado es asíncrono y no afecta el tiempo de respuesta del análisis
