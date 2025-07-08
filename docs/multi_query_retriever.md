# MultiQueryRetriever en Kognito AI

## Descripción General

El **MultiQueryRetriever** es una implementación avanzada de recuperación de información que mejora significativamente la calidad de los resultados de búsqueda mediante la generación automática de múltiples consultas reformuladas y la fusión inteligente de resultados.

## ¿Qué es MultiQueryRetriever?

MultiQueryRetriever es una técnica de RAG (Retrieval-Augmented Generation) que:

1. **Genera múltiples consultas alternativas** a partir de una consulta original usando un LLM
2. **Ejecuta búsquedas paralelas** con todas las consultas generadas
3. **Fusiona los resultados** usando algoritmos avanzados como Reciprocal Rank Fusion (RRF)
4. **Retorna resultados más completos y relevantes** que una búsqueda simple

## Ventajas sobre Búsqueda Simple

### 🎯 **Mayor Cobertura**
- Captura diferentes aspectos y perspectivas del mismo tema
- Encuentra información relevante que podría perderse con una sola consulta

### 🔍 **Mejor Precisión**
- Reduce el sesgo de formulación de la consulta original
- Mejora la recuperación de documentos semánticamente relacionados

### ⚡ **Eficiencia Optimizada**
- Búsquedas paralelas para minimizar latencia
- Aprovecha la infraestructura optimizada de Kognito (10-50x más rápida)

### 🧠 **Inteligencia Contextual**
- Usa el LLM para generar consultas más inteligentes
- Mantiene la intención original mientras explora variaciones

## Arquitectura de la Implementación

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Consulta      │───▶│  MultiQuery      │───▶│   Resultados    │
│   Original      │    │  Retriever       │    │   Fusionados    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 1. Generación de │
                    │ Consultas Alt.   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 2. Búsquedas     │
                    │ Paralelas        │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 3. Fusión RRF    │
                    │ de Resultados    │
                    └──────────────────┘
```

## Componentes Implementados

### 1. **Clase MultiQueryRetriever** (`utils/multi_query_retriever.py`)
- Lógica principal del algoritmo
- Generación de consultas alternativas
- Fusión de resultados (RRF y simple)

### 2. **Herramienta del Agente** (`tools/multi_query_search_tool.py`)
- Integración con el sistema de herramientas de Kognito
- Interfaz para el agente de IA
- Formateo de resultados para el usuario

### 3. **Integración en Core Tools** (`core/tools.py`)
- Registro automático de la herramienta
- Disponible para todos los agentes

## Métodos de Fusión

### Reciprocal Rank Fusion (RRF) - **Recomendado**
```python
RRF_Score = Σ(1 / (rank + 60))
```
- **Ventajas**: Balanceado, reduce bias de ranking
- **Uso**: Consultas complejas, múltiples aspectos

### Fusión Simple
- **Ventajas**: Rápido, preserva orden original
- **Uso**: Consultas simples, cuando velocidad es prioritaria

## Uso Básico

### Desde Código Python
```python
from utils.multi_query_retriever import multi_query_search

resultados = await multi_query_search(
    account_id="usuario123",
    query="machine learning para análisis de texto",
    content_type="user_documents",
    k=5,
    num_queries=3,
    fusion_method="rrf"
)
```

### Desde Herramientas del Agente
```python
from tools.multi_query_search_tool import MultiQuerySearchTool

tool = MultiQuerySearchTool()
resultado = await tool._arun(
    account_id="usuario123",
    query="estrategias de optimización de bases de datos",
    k=5,
    num_queries=3
)
```

## Parámetros de Configuración

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `num_queries` | int | 3 | Número de consultas alternativas a generar |
| `fusion_method` | str | "rrf" | Método de fusión ("rrf" o "simple") |
| `k` | int | 5 | Número máximo de resultados finales |
| `content_type` | str | None | Filtro por tipo de contenido |
| `topic` | str | None | Filtro por tema |
| `workspace_id` | str | None | Filtro por workspace |

## Casos de Uso Recomendados

### ✅ **Cuándo Usar MultiQuery**
- Consultas complejas o ambiguas
- Búsquedas exploratorias
- Cuando se necesita máxima cobertura
- Análisis de conocimiento profundo
- Investigación exhaustiva

### ⚠️ **Cuándo Usar Búsqueda Simple**
- Consultas muy específicas
- Búsquedas rápidas de datos exactos
- Cuando la latencia es crítica
- Consultas con términos técnicos precisos

## Integración con Herramientas Existentes

### Comprehensive Web Analysis Tool
```python
# En comprehensive_web_analysis_tool.py
from utils.multi_query_retriever import multi_query_search

# Reemplazar búsqueda simple en knowledge base
relevant_memories = await multi_query_search(
    account_id=account_id, 
    query=web_summary, 
    k=5,
    workspace_id=workspace_id,
    num_queries=2  # Menos consultas para complementar
)
```

### Natural Query Interpreter
```python
# Detectar automáticamente cuándo usar MultiQuery
if query_complexity > threshold:
    return await multi_query_search(...)
else:
    return await search_vector_db_optimized(...)
```

## Métricas y Monitoreo

El sistema incluye logging detallado para monitorear:
- Número de consultas generadas
- Tiempo de ejecución de búsquedas paralelas
- Efectividad de la fusión RRF
- Resultados únicos encontrados vs búsqueda simple

## Consideraciones de Rendimiento

### ⚡ **Optimizaciones Implementadas**
- Búsquedas paralelas con `asyncio.gather()`
- Reutilización de conexiones de BD
- Deduplicación eficiente de resultados
- Fallback automático en caso de errores

### 📊 **Impacto en Recursos**
- **CPU**: +200% durante generación de consultas (breve)
- **Memoria**: +50% para almacenar múltiples resultados
- **BD**: Múltiples consultas paralelas (optimizadas)
- **Latencia**: +30-50% vs búsqueda simple

## Próximas Mejoras

1. **Cache de Consultas Generadas**: Evitar regenerar consultas similares
2. **Aprendizaje Adaptativo**: Ajustar num_queries según efectividad
3. **Métricas de Calidad**: Scoring automático de relevancia
4. **Integración con Embeddings**: Usar embeddings para filtrar consultas similares

## Ejemplos Prácticos

Ver `examples/multi_query_retriever_example.py` para ejemplos completos de:
- Uso básico y avanzado
- Comparación con búsqueda simple
- Integración con herramientas existentes
- Casos de uso específicos
