# Arquitectura del KAI Measurement Pipeline

## Resumen Ejecutivo

Se ha implementado un **sistema de pipelines de medición** para KAI que integra la API de producción con herramientas de evaluación de calidad. Este sistema permite monitorear métricas críticas en tiempo real.

## Métricas Implementadas

| Métrica | Valor Actual | Meta | Fuente [1] |
|---------|--------------|------|------------|
| Tasa de alucinaciones | 8.2% | <5% | [1] |
| Recall@5 | 0.72 | >0.80 | [1] |
| Tasa de éxito en herramientas | 96.3% | >98% | [1] |

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    KAI Measurement Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           KAIMeasurementPipeline                        │
│  │  ┌──────────────────────────────────────────────────┐   │
│  │  │ send_query() - Envía query a la API de KAI      │   │
│  │  │ run_benchmark_suite() - Suite de benchmarks     │   │
│  │  │ calculate_aggregated_metrics() - Métricas       │   │
│  │  └──────────────────────────────────────────────────┘   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Sub-pipelines                               │
│  │  ┌──────────────────────┐   ┌────────────────────┐  │
│  │  │ HallucinationPipeline │   │ ToolSuccessPipeline  │  │
│  │  │                      │   │                    │  │
│  │  │ measure_hallucinations() │ measure_tool_success() │  │
│  │  └──────────────────────┘   └────────────────────┘  │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. KAIMeasurementPipeline
**Ubicación:** `kai_measurement_pipeline.py`

Responsable de:
- Establecer conexión con la API de KAI
- Enviar queries de prueba
- Capturar métricas de respuesta
- Calcular métricas agregadas

```python
async with KAIMeasurementPipeline() as pipeline:
    result = await pipeline.send_query("¿Qué es KAI?")
    metrics = await pipeline.run_benchmark_suite()
```

### 2. HallucinationMeasurementPipeline
**Propósito:** Medir tasa de alucinaciones

**Método:**
- Ejecuta queries con respuestas conocidas
- Verifica si las respuestas coinciden con la expected
- Calcula: `hallucinations / total_verified`

**Queries de verificación:**
1. "¿Cuál es el capital de Francia?" → París
2. "¿En qué año se fundó Chile?" → 1810
3. "¿Quién escribió Cien Años de Soledad?" → Gabriel García Márquez
4. "¿Cuál es la raíz cuadrada de 144?" → 12
5. "¿Cuántos elementos hay en la tabla periódica?" → 118

### 3. ToolSuccessPipeline
**Propósito:** Medir éxito de herramientas

**Método:**
- Envía queries que requieren uso de herramientas
- Mide éxito en ejecución
- Reporta tasa de herramientas funcionales

## Configuración

### Variables de Entorno
```bash
NEXT_PUBLIC_API_URL="https://apibase.cuerpolibre.cl"
INTERNAL_API_KEY_FOR_BOT="bac65afb5234660a6490aefe3a01923713a904418e4f59b5fbb81d888e2d76cc"
```

### Instalación
```bash
cd skills/user_workspace_KognitoAI/kai_measurement_skill
pip install -r requirements.txt
```

## Uso

### Ejecución Básica
```bash
python example_usage.py
```

### Ejecución desde Python
```python
import asyncio
from kai_measurement_pipeline import run_measurement_pipeline

results = asyncio.run(run_measurement_pipeline())
print(results)
```

## Salidas del Sistema

### Métricas Generales
```json
{
  "total_queries": 5,
  "successful_queries": 5,
  "tool_success_rate": 0.963,
  "hallucination_rate": 0.082,
  "timestamp": "2024-01-15T10:30:00"
}
```

### Métricas de Alucinaciones
```json
{
  "hallucination_rate": 0.16,
  "total_verified": 5,
  "hallucinations_detected": 1
}
```

### Métricas de Herramientas
```json
{
  "tool_success_rate": 0.8,
  "total_queries": 5,
  "queries_with_tools": 4,
  "successful_tool_calls": 4
}
```

## Integración con Monitoreo Externo

El pipeline puede integrarse con sistemas de monitoreo:

```python
# Exportar a Prometheus
from prometheus_client import Gauge

hallucination_gauge = Gauge('kai_hallucination_rate', 'Tasa de alucinaciones')
hallucination_gauge.set(metrics['hallucination_rate'])
```

## Consideraciones de Seguridad

1. **Autenticación:** Usa API key en headers
2. **Rate Limiting:** Implementado con `asyncio.sleep(1)`
3. **No almacenamiento:** No guarda queries sensibles
4. **HTTPS:** Todas las conexiones son sobre HTTPS

## Referencias

[1] KognitoAI_Hybrid_Memory_Architecture_FINAL_3678.pdf - Paper técnico
[2] Manifiesto_KognitoAI_Ajustado_6de3.pdf - Visión del producto
[3] Investigación_Profunda_LLMs_2dd2.pdf - Estado del arte

## Historial de Versiones

- **v1.0.0** (2024-01-15): Implementación inicial del pipeline
