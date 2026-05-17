---
name: knowledge-memory-management
description: |
  Gestión del conocimiento y memoria del usuario. Almacena información, notas,
  aprendizajes y relaciones entre conceptos en bases de datos vectoriales y grafos
  de conocimiento. Úsalo cuando el agente descubra información valiosa que deba
  persistir, cuando cree nuevas relaciones entre conceptos, o cuando necesite
  actualizar el perfil de conocimiento del usuario.
license: MIT
compatibility: |
  Python 3.10+
  Requires: PostgreSQL with pgvector
  Requires: Neo4j knowledge graph
metadata:
  author: KognitoAI Team
  version: "1.1.0"
  tags:
    - memory
    - knowledge-management
    - semantic-storage
    - graph-relations
  category: knowledge-management
allowed-tools: |
  database__write
  database__embeddings
  knowledge_graph__write
  knowledge_graph__update_relations
---


# Knowledge & Memory Management

## Descripción Procedimental Detallada

Este skill implementa un sistema avanzado de gestión de conocimiento y memoria para agentes inteligentes. Su objetivo es permitir que el agente aprenda, recuerde, relacione y actualice información relevante del usuario de manera estructurada y persistente, combinando almacenamiento vectorial (pgvector) para búsqueda semántica y grafos de conocimiento (Neo4j) para relaciones conceptuales.

### ¿Cuándo usar este skill?

1. **Cuando el usuario comparte información valiosa** que debe ser recordada para futuras sesiones, análisis o recomendaciones.
2. **Al descubrir relaciones entre conceptos** (por ejemplo, conectar una nota sobre "FastAPI" con otra sobre "async/await").
3. **Cuando se requiere actualizar el perfil de conocimiento** del usuario, agregando aprendizajes, proyectos, notas o insights.
4. **Para organizar información** por workspace, usuario o contexto, facilitando búsquedas y análisis posteriores.
5. **Al enriquecer la memoria** tras búsquedas, investigaciones o análisis realizados por otros skills.

### Procedimiento paso a paso

1. **Identificar información relevante**: El agente debe filtrar y seleccionar solo aquella información que aporte valor, sea generalizable y no sea confidencial.
2. **Estructurar el contenido**: Organizar la información en títulos, secciones y etiquetas para facilitar su recuperación y análisis.
3. **Guardar el conocimiento**: Usar `MemoryStorageTool` para almacenar la información en la base vectorial, incluyendo metadatos y tags.
4. **Crear relaciones**: Si la nueva información se vincula a conceptos previos, usar `KnowledgeRelationTool` para establecer relaciones en el grafo.
5. **Actualizar o limpiar memoria**: Si se detecta información obsoleta o redundante, actualizar o eliminar según corresponda.
6. **Validar persistencia**: Confirmar que la información y relaciones han sido correctamente almacenadas y son recuperables.

### Ejemplo de uso completo

```python
# 1. El usuario comparte un aprendizaje clave
memory_tool = MemoryStorageTool(account_id="user_123", workspace_id="ws_456")
result = await memory_tool.arun(
  title="Async/Await Best Practice",
  content="""
  Usar async/await en Python mejora la performance en aplicaciones I/O bound.
  Ejemplo: 10 requests en 1 segundo en vez de 10.
  """,
  tags=["python", "performance", "async"],
  type="learning"
)

# 2. Relacionar con otro concepto existente
relation_tool = KnowledgeRelationTool(account_id="user_123")
await relation_tool.arun(
  source_id=result["id"],
  target_id="fastapi_note_id",
  relation_type="depends_on",
  strength=0.9
)

# 3. Actualizar información previa si es necesario
updated_result = await memory_tool.arun(
  title="FastAPI Advanced Patterns",
  content="Nueva información sobre FastAPI...",
  update_related=True
)
```

### Reglas y mejores prácticas

- **Ser selectivo**: No guardar todo, solo lo valioso y reutilizable.
- **Estructura clara**: Usar títulos, secciones y tags descriptivos.
- **Relaciones significativas**: Solo conectar nodos con relación real y fuerza > 0.7.
- **Privacidad**: Nunca almacenar datos sensibles sin autorización.
- **Mantenimiento**: Limpiar información obsoleta periódicamente.

### Advertencias y solución de problemas

- Si ocurre un error de "Embedding Dimension Mismatch", re-embedder los documentos.
- Si se detectan dependencias circulares, revisar la lógica de relaciones antes de guardar.

### Integración con otros skills

Este skill se usa típicamente después de:
- **search-and-research**: Para guardar hallazgos relevantes.
- **retrieval-augmented-generation**: Para enriquecer la memoria con información recuperada.
- **analysis-and-insights**: Para almacenar resultados de análisis.

### Patrón recomendado: Learn → Remember → Connect

1. Investigar tema (con search-and-research)
2. Analizar hallazgos (con analysis-and-insights)
3. Guardar en memoria (con este skill)
4. Conectar con conocimiento existente (relaciones)

---

## Cuándo Usarlo

### ✅ Usa este skill cuando:

- Descubras información valiosa que deba recordarse
- Necesites crear nuevas relaciones entre conceptos
- El usuario comparta información que debe persistir
- Requieras actualizar el perfil de conocimiento
- Necesites establecer conexiones entre documentos/notas

### ❌ NO uses este skill si:

- Solo es conversación temporal sin valor futuro
- La información es privada/sensible no autorizada
- Es información pública que no agrega valor al usuario

## Uso Básico

```python
from skills.knowledge_memory_skill.scripts.memory_storage_tool import MemoryStorageTool
from skills.knowledge_memory_skill.scripts.knowledge_relation_tool import KnowledgeRelationTool

# Guardar nuevo conocimiento
memory_tool = MemoryStorageTool(account_id="user_123", workspace_id="ws_456")
result = await memory_tool.arun(
    title="Proyectos Python 2026",
    content="Lista de proyectos realizados en Python durante 2026...",
    tags=["python", "projects", "2026"],
    type="project_summary"
)

# Crear relación con información existente
relation_tool = KnowledgeRelationTool(account_id="user_123")
await relation_tool.arun(
    source_id=result["id"],
    target_id="existing_tech_doc_id",
    relation_type="related_to",
    strength=0.8
)
```

## Parámetros

### MemoryStorageTool
| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `title` | str | Sí | Título del conocimiento |
| `content` | str | Sí | Contenido detallado |
| `tags` | list | No | Etiquetas para categorización |
| `type` | str | No | Tipo de contenido (note, project, concept, etc.) |
| `metadata` | dict | No | Información adicional |

### KnowledgeRelationTool
| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `source_id` | str | Sí | ID del nodo origen |
| `target_id` | str | Sí | ID del nodo destino |
| `relation_type` | str | Sí | Tipo de relación (related_to, depends_on, etc.) |
| `strength` | float | No | Fuerza de la relación (0-1) |

## Ejemplos

### Guardar Aprendizaje

```python
# El usuario comparte: "He aprendido que usar async/await mejora performance"

await memory_tool.arun(
    title="Async/Await Best Practice",
    content="""
    Usar async/await en Python mejora significativamente la performance
    en aplicaciones I/O bound. Permite que múltiples operaciones se ejecuten
    concurrentemente sin bloqueo.
    
    Ejemplo:
    - Antes: 10 requests = 10 segundos
    - Después (con async): 10 requests = 1 segundo
    """,
    tags=["python", "performance", "async", "best-practice"],
    type="learning"
)
```

### Conectar Información Relacionada

```python
# El agente descubre que "FastAPI" y "async/await" están relacionados

# Primero: guardar/encontrar IDs
fastapi_id = "..."  # ID de nota sobre FastAPI
async_id = "..."    # ID del aprendizaje anterior

# Crear relación
await relation_tool.arun(
    source_id=fastapi_id,
    target_id=async_id,
    relation_type="depends_on",
    strength=0.9
)
```

### Actualizar Conocimiento

```python
# El usuario comparte información nueva que actualiza anterior

updated_result = await memory_tool.arun(
    title="FastAPI Advanced Patterns",
    content="Nueva información sobre FastAPI...",
    update_related=True  # Actualiza automáticamente relaciones
)
```

## Composición con Otros Skills

Este skill se usa típicamente después de:

- **[search-and-research](../search-and-research)** - Para guardar hallazgos
- **[retrieval-augmented-generation](../retrieval-augmented-generation)** - Para enriquecer memoria
- **[analysis-and-insights](../analysis-and-insights)** - Para almacenar análisis

## Patrón: Learn → Remember → Connect

```python
# Flujo típico del agente:

# 1. Investigar tema
research = await search_tool.arun(query="tema interesante")

# 2. Analizar hallazgos
analysis = await analysis_tool.arun(data=research)

# 3. Guardar en memoria
memory_id = await memory_tool.arun(
    title=f"Investigación: {tema}",
    content=analysis["summary"],
    tags=analysis["tags"]
)

# 4. Conectar con conocimiento existente
for related_id in analysis["related_concepts"]:
    await relation_tool.arun(
        source_id=memory_id,
        target_id=related_id,
        relation_type="related_to"
    )
```

## Mejores Prácticas

### 1. Ser Selectivo
```python
# ❌ Guardar todo
# ✅ Guardar solo información valiosa, generalizable, no confidencial
```

### 2. Estructura Clara
```python
# ❌ Content sin estructura
await memory_tool.arun(
    title="Stuff",
    content="random information about many things..."
)

# ✅ Content bien estructurado
await memory_tool.arun(
    title="Python Async Best Practices",
    content="""
    ## Conceptos Clave
    - async/await is non-blocking
    
    ## Cuándo Usarlo
    - I/O bound operations
    
    ## Ejemplos
    - Web scraping
    - API calls
    """,
    tags=["python", "async", "performance"]
)
```

### 3. Relaciones Significativas
```python
# ❌ Conectar todo con todo
# ✅ Conectar solo relaciones significativas con fuerza > 0.7
```

## Limitaciones

- **Privacidad**: No guardar información sensible del usuario
- **Escalabilidad**: Muy muchas relaciones pueden ralentizar búsquedas
- **Mantenimiento**: Requiere limpieza periódica de información obsoleta

## Solución de Problemas

### Error: "Embedding Dimension Mismatch"
**Causa**: Cambio de modelo embedding  
**Solución**: Re-embedder documentos existentes

### Error: "Circular Dependencies Detected"
**Causa**: Relaciones circulares en grafo  
**Solución**: Revisar lógica de relaciones antes de guardar

## Referencias

- [Technical Reference](references/REFERENCE.md)
- [Schema Documentation](references/schema.md)
- [Performance Tuning](references/performance.md)
