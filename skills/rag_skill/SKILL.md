---
name: retrieval-augmented-generation
description: |
  Recuperación y análisis de información desde bases de datos de conocimiento.
  Implementa RAG (Retrieval Augmented Generation) para combinar búsqueda semántica
  en pgvector con análisis inteligente. Úsalo cuando necesites información específica
  del usuario, análisis de contexto profundo o respuestas basadas en documentos propios.
license: MIT
compatibility: |
  Python 3.10+
  Requires: PostgreSQL with pgvector extension
  Requires: Access to knowledge graph (Neo4j)
metadata:
  author: KognitoAI Team
  version: "1.0.0"
  tags:
    - rag
    - retrieval
    - semantic-search
    - knowledge-graphs
  category: knowledge-management
allowed-tools: |
  database__query
  database__semantic_search
  knowledge_graph__query
---

# Retrieval-Augmented Generation (RAG)

## Descripción

Sistema híbrido de recuperación de información que combina búsqueda vectorial en pgvector
con análisis de grafos de conocimiento en Neo4j. Permite al agente acceder a información
específica del usuario, documentos, notas y relaciones entre conceptos.

### Capacidades

- **Semantic Search**: Búsqueda por similaridad semántica en pgvector
- **Knowledge Graph Navigation**: Exploración de relaciones conceptuales
- **Scoped Analysis**: Búsqueda filtrada por usuario/workspace
- **Multi-source Retrieval**: Combina resultados de múltiples fuentes
- **Confidence Scoring**: Evaluación de relevancia de resultados

## Cuándo Usarlo

### ✅ Usa este skill cuando:

- Necesites información específica del usuario (notas, documentos, etc.)
- Busques contexto para responder preguntas
- Quieras encontrar relaciones entre conceptos
- Requieras análisis basado en conocimiento previo del usuario
- El usuario pregunta sobre sus propias notas/documentos

### ❌ NO uses este skill si:

- La información general está disponible públicamente (usa search-and-research)
- No hay base de conocimiento del usuario para consultar
- Necesitas información en tiempo real que cambia constantemente

## Uso Básico

```python
from skills.rag_skill.scripts.scoped_rag_analysis import ScopedRAGAnalysisTool

tool = ScopedRAGAnalysisTool(
    account_id="user_123",
    workspace_id="workspace_456"
)

# Búsqueda semántica simple
result = await tool.arun(
    query="proyectos en los que trabajé con Python",
    num_results=5
)

print(result)
# Output: {
#   "relevant_documents": [...],
#   "knowledge_graph_relations": [...],
#   "summary": "...",
#   "confidence_score": 0.95
# }
```

## Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `query` | str | Sí | Consulta en lenguaje natural |
| `num_results` | int | No (default: 5) | Número de resultados |
| `filters` | dict | No | Filtros adicionales (tipo, fecha, etc.) |
| `depth` | int | No (default: 2) | Profundidad de exploración en grafo |

## Ejemplos

### Buscar Notas Relacionadas

```python
# El usuario pregunta: "¿Qué notas tengo sobre diseño de APIs?"

result = await rag_tool.arun(
    query="diseño de APIs RESTful best practices",
    num_results=10
)

# Retorna:
# - Notas que mencionan "API design"
# - Documentos relacionados
# - Relaciones en el grafo de conocimiento
```

### Análisis Contextual

```python
# Usar para mejorar respuestas del agente

user_context = await rag_tool.arun(
    query="contexto del usuario últimos proyectos",
    depth=3  # Explorar 3 niveles en grafo
)

# Usar context para personalizar respuestas
```

## Flujo de Integración

```python
# Patrón recomendado:
# 1. Detectar que se necesita información del usuario
# 2. Consultar RAG
# 3. Usar resultados para enriquecer respuesta
# 4. Opcionalmente: guardar nueva información en grafo

if user_query_requires_context:
    context = await rag_tool.arun(query=user_query)
    enriched_response = generate_response_with_context(
        user_query,
        context["relevant_documents"],
        context["knowledge_graph_relations"]
    )
```

## Referencias

- [Technical Reference](references/REFERENCE.md) - Detalles técnicos
- [Query Optimization](references/query-optimization.md) - Tips de performance
- [Troubleshooting](references/troubleshooting.md) - Problemas comunes
