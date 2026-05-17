---
name: search-and-research
description: |
  Búsqueda y investigación avanzada en internet. Proporciona múltiples fuentes de datos
  (web scraping, APIs de búsqueda, análisis de contenido) para encontrar información
  precisa y actualizada. Úsalo cuando necesites investigar tópicos, validar datos,
  encontrar fuentes o realizar análisis comparativo de información en la web.
license: MIT
compatibility: |
  Python 3.10+
  Requires network access (for web APIs)
  Compatible with: Claude Code, agent-codemode, Pydantic AI
metadata:
  author: KognitoAI Team
  version: "1.1.0"
  tags:
    - search
    - research
    - web
    - information-retrieval
  category: research
  sources:
    - Tavily API
    - DuckDuckGo
    - Web Scraping
  last_updated: "2026-05-15"
allowed-tools: |
  network__fetch
  filesystem__read_file
  filesystem__write_file
---

# Search and Research Skill

## Descripción

Este skill proporciona capacidades de búsqueda y investigación avanzadas para encontrar
información precisa en internet. Integra múltiples fuentes de datos y APIs de búsqueda
para ofrecerle al agente acceso a información actual y verificable.

### Capacidades

- **Web Search**: Búsqueda general en internet con múltiples motores
- **Deep Research**: Análisis profundo con múltiples consultas relacionadas
- **Web Scraping**: Extracción de contenido de sitios específicos
- **Content Analysis**: Análisis de contenido relevante encontrado
- **Source Validation**: Verificación de fuentes y credibilidad

## Cuándo Usarlo

### ✅ Usa este skill cuando:

- Necesites información actual y verificable de internet
- Quieras investigar un tema con profundidad (múltiples ángulos)
- Requieras validar hechos o encontrar fuentes confiables
- Busques información comparativa entre múltiples fuentes
- Necesites extraer contenido específico de sitios web
- El usuario pida "investiga", "busca", "encuentra información", etc.

### ❌ NO uses este skill si:

- La información ya está disponible en la memoria/base de datos
- El usuario busca datos internos de KognitoAI
- Necesitas análisis que requiere acceso a APIs de pago no disponibles
- El tema es tan específico que no será indexado en la web

## Cómo Usarlo

### Búsqueda Simple

```python
from skills.search_and_research.scripts.tavily_search_tool import TavilySearchTool

tool = TavilySearchTool(account_id="user_123", workspace_id="ws_456")
result = await tool.arun(query="inteligencia artificial 2026")

print(result)
# Output: {
#   "results": [
#     {
#       "title": "...",
#       "url": "...",
#       "snippet": "..."
#     },
#     ...
#   ],
#   "sources": [...]
# }
```

### Búsqueda Profunda (Multi-Query)

```python
from skills.search_and_research.scripts.multi_query_search_tool import MultiQuerySearchTool

tool = MultiQuerySearchTool(account_id="user_123")
result = await tool.arun(query="¿Cómo está evolucionando el trabajo remoto?")

# Genera múltiples consultas relacionadas:
# 1. "tendencias trabajo remoto 2026"
# 2. "impacto productividad trabajo desde casa"
# 3. "herramientas colaboración remota"
# 4. "estadísticas empresas híbridas"
```

### Web Scraping de Contenido Específico

```python
from skills.search_and_research.scripts.web_scraper_tool import WebScraperTool

tool = WebScraperTool(account_id="user_123")
result = await tool.arun(url="https://example.com/article")

# Extrae: título, contenido, autor, fecha, links internos, etc.
```

## Parámetros

### TavilySearchTool
| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `query` | str | Sí | Consulta de búsqueda clara y específica |

### MultiQuerySearchTool
| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `query` | str | Sí | Tema o pregunta para investigar en profundidad |
| `num_queries` | int | No (default: 4) | Número de variaciones de consulta |

### WebScraperTool
| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `url` | str | Sí | URL del artículo a extraer |
| `include_code` | bool | No (default: false) | Incluir fragmentos de código |

## Ejemplos Completos

### Investigar un Concepto Nuevo

```python
# El usuario pregunta: "¿Qué es el Agentic AI?"

from skills.search_and_research.scripts.multi_query_search_tool import MultiQuerySearchTool

tool = MultiQuerySearchTool(account_id=user_id)
research_result = await tool.arun(
    query="¿Qué es Agentic AI y cómo está revolucionando IA?"
)

# Esto genera automáticamente variaciones como:
# - "Definición Agentic AI"
# - "Diferencia entre Agentic AI y LLMs"
# - "Aplicaciones prácticas Agentic AI"
# - "Empresas desarrollando Agentic AI"

# Resultado: perspectiva completa del tema
```

### Validar Información

```python
# El usuario afirma algo: "OpenAI fue fundado en 2015"

from skills.search_and_research.scripts.tavily_search_tool import TavilySearchTool

tool = TavilySearchTool(account_id=user_id)
result = await tool.arun(query="OpenAI founding year founded when")

# Busca en internet para verificar (fue 2015: correcto ✓)
```

### Análisis Comparativo

```python
# Comparar opciones disponibles

queries = [
    "Mejor alternativa a Python para ciencia de datos",
    "Julia vs Python rendimiento cálculo científico",
    "Rust vs Python seguridad sistemas críticos"
]

for query in queries:
    result = await tavily_tool.arun(query=query)
    # Compilar comparativa
```

## Composición con Otros Skills

Este skill se compone naturalmente con:

- **[knowledge-memory-management](../knowledge-memory-management)** - Para guardar hallazgos en memoria
- **[document-management](../document-management)** - Para organizar fuentes encontradas
- **[analysis-and-insights](../analysis-and-insights)** - Para analizar datos recopilados
- **[media-generation](../media-generation)** - Para crear informes visuales con hallazgos

### Patrón: Research → Analyze → Document

```python
# 1. Investigar
research_result = await search_tool.arun(query="tema")

# 2. Analizar hallazgos
analysis_result = await analysis_tool.arun(data=research_result)

# 3. Guardar en memoria
await memory_tool.arun(
    title=f"Investigación: {tema}",
    content=analysis_result["summary"],
    sources=research_result["sources"]
)

# 4. Documentar
await document_tool.arun(
    title=f"Research Report: {tema}",
    content=analysis_result["detailed_report"]
)
```

## Limitaciones y Casos de Borde

### Limitación 1: Restricción de APIs
- **Problema**: Tavily y algunas APIs requieren cuota
- **Workaround**: Sistema automático usa DuckDuckGo como fallback

### Limitación 2: Contenido Dinámico
- **Problema**: Sitios con JavaScript pesado no se scrapean bien
- **Workaround**: Intentar con herramientas más especializadas o APIs del sitio

### Limitación 3: Información Falsa
- **Problema**: Internet contiene desinformación
- **Workaround**: Validar con múltiples fuentes, verificar autor/fecha

### Caso de Borde: Query Muy Amplia
```python
# ❌ Malo - demasiado general
query = "tecnología"

# ✅ Bueno - específico
query = "tendencias blockchain 2026 en industria financiera"
```

## Solución de Problemas

### Error: "API Rate Limit Exceeded"
**Causa**: Se alcanzó límite de consultas de la API  
**Solución**:
1. Esperar unos minutos
2. El sistema intenta fallback a DuckDuckGo automáticamente
3. Reducir frecuencia de búsquedas

### Error: "No Results Found"
**Causa**: Query muy específica o tema muy nuevo  
**Solución**:
1. Hacer query más general o con sinónimos
2. Verificar ortografía
3. Probar con términos en inglés si están disponibles

### Warning: "Source Unreliable"
**Causa**: Sitio identificado como potencialmente no confiable  
**Solución**:
1. Revisar manualmente la fuente
2. Buscar corroboración en otras fuentes
3. Verificar fecha de publicación

## Referencias

Para información más detallada:

- [Technical Reference](references/REFERENCE.md) - Detalles de APIs y implementación
- [Search Strategies](references/search-strategies.md) - Tips para mejores búsquedas
- [Data Sources](references/data-sources.md) - Documentación de cada fuente
- [Troubleshooting](references/troubleshooting.md) - Problemas comunes
- [Examples](references/examples.md) - Casos de uso avanzados

## Especificaciones Técnicas

- **Lenguaje**: Python 3.10+
- **Dependencias**: `tavily-python`, `beautifulsoup4`, `requests`
- **Async**: Sí, todas las funciones son async
- **Timeout**: 30 segundos por default
- **Retry**: Automático con exponential backoff
- **Caching**: Resultados cacheados por 1 hora

## Historial de Cambios

| Versión | Fecha | Cambios |
|---|---|---|
| 1.1.0 | 2026-05-15 | Refactorización a agentskills.io format |
| 1.0.0 | 2026-03-01 | Release inicial |
