---
name: kai_measurement
description: Use when | Pipeline de medición y monitoreo de métricas para el sistema
  KAI. Integra la API de producción con herramientas de medición para evaluar alucinaciones,
  tasa de éxito de herramientas y rendimiento.
---

## Objetivo
Crear un sistema pipelines para medir y monitorear las métricas clave de KAI:
- Tasa de alucinaciones (actual: 8.2% vs 13.7% RAG puro)
- Recall@5 (actual: 0.72 vs 0.58 RAG puro)
- Tasa de éxito en herramientas (actual: 96.3%)

## Cuándo usar esta skill
- Cuando necesites monitorear el rendimiento de KAI en producción
- Para validar mejoras en el sistema de RAG
- Para generar reportes de calidad de respuestas
- Para comparar métricas antes/después de actualizaciones

## Flujo de trabajo

```
1. KAIMeasurementPipeline
   ├── Inicializa conexión a API de KAI
   ├── Envía queries de prueba
   └── Captura métricas de respuesta

2. HallucinationMeasurementPipeline
   ├── Ejecuta queries con respuestas conocidas
   ├── Verifica si las respuestas son correctas
   └── Calcula tasa de alucinaciones

3. ToolSuccessPipeline
   ├── Envía queries que requieren herramientas
   ├── Mide éxito en ejecución de herramientas
   └── Reporta tasa de éxito
```

## Métricas implementadas

| Métrica | Valor Actual | Meta | Fuente |
|---------|--------------|------|--------|
| Tasa de alucinaciones | 8.2% | <5% | [1] |
| Recall@5 | 0.72 | >0.80 | [1] |
| Tasa de éxito herramientas | 96.3% | >98% | [1] |

## Configuración

### Variables de entorno requeridas
```bash
NEXT_PUBLIC_API_URL="https://apibase.cuerpolibre.cl"
INTERNAL_API_KEY_FOR_BOT="bac65afb5234660a6490aefe3a01923713a904418e4f59b5fbb81d888e2d76cc"
```

### Uso básico
```python
from kai_measurement_pipeline import KAIMeasurementPipeline, run_measurement_pipeline

# Ejecutar suite completa de medición
results = await run_measurement_pipeline()

# Usar pipeline directamente
async with KAIMeasurementPipeline() as pipeline:
    result = await pipeline.send_query("¿Qué es KAI?")
```

## Salidas

### Métricas generales
```json
{
  "total_queries": 5,
  "successful_queries": 5,
  "tool_success_rate": 0.963,
  "hallucination_rate": 0.082,
  "timestamp": "2024-01-15T10:30:00"
}
```

## Consideraciones de seguridad
- Usa API key para autenticación
- No almacena queries sensibles
- Límites de rate limiting implementados

## Referencias
[1] KognitoAI_Hybrid_Memory_Architecture_FINAL_3678.pdf - Paper técnico
