---
name: kai_measurement_pipeline
description: Pipeline para medición de rendimiento real de KognitoAI
version: 1.0.0
author: KAI Agent
---

## Objetivo

Pipeline automatizado para medir y monitorear métricas de rendimiento de KAI:
- Tasa de alucinaciones
- Recall@5
- Éxito de herramientas

## Métricas Actuales

| Métrica | Valor | Meta | Estado |
|---------|-------|------|--------|
| Alucinaciones | 8.2% | <5% | ⚠️ |
| Recall@5 | 0.72 | >0.80 | ⚠️ |
| Éxito tools | 96.3% | >98% | ⚠️ |

## Uso

```bash
cd skills/user_workspace_KognitoAI/kai_measurement_pipeline
python scripts/run_measurements.py
```

## Componentes

- `scripts/run_measurements.py` - Pipeline principal
- `scripts/api_integration.py` - Integración con API KAI
- `config.json` - Configuración de métricas

## Salida

Genera reporte JSON con métricas y estado.
