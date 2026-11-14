# KAI Measurement Skill

## Descripción
Skill para medir métricas reales de KAI: alucinaciones, éxito de herramientas, recall@5.

## Uso

### Medir alucinaciones
```python
from scripts.api_client import KAIClient
from scripts.measurement_engine import MeasurementEngine

client = KAIClient()
engine = MeasurementEngine(client)

test_data = [
    {"query": "¿Cuál es el capital social de Kognito AI Labs?", "expected_answer": "$500.000 CLP"},
    {"query": "¿Cuál es el recall@5 de KAI?", "expected_answer": "0.72"}
]

result = await engine.measure_hallucinations(test_data)
print(f"Tasa de alucinaciones: {result['rate']}")
```

### Medir éxito de herramientas
```python
queries = ["analiza el manifiesto de KAI", "genera un dashboard de métricas"]
result = await engine.measure_tool_success(queries)
print(f"Tasa de éxito: {result['rate']}")
```

## Métricas Disponibles

| Métrica | Descripción | Fórmula |
|---------|-------------|---------|
| Alucinaciones | Respuestas incorrectas | Hallucinations / Total |
| Éxito de herramientas | Herramientas que funcionan | Success / Total tools |
| Recall@5 | Precisión de recuperación | Relevant chunks / 5 |

## Configuración

- **KAI_API_URL**: URL de la API de KAI (default: http://localhost:8000)
- **TEST_DATASET_PATH**: Ruta al dataset de prueba

## Próximas mejoras

- [ ] Integración con knowledge graph
- [ ] Dashboard web
- [ ] Alertas automáticas
- [ ] Comparación A/B