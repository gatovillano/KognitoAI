# 🔍 Búsqueda en Colecciones de Documentos

## Descripción General

Se ha implementado una funcionalidad de búsqueda híbrida (vectorial + textual) para documentos dentro de las colecciones en la página de Conocimientos.

## Características

### 🎯 Tipos de Búsqueda

1. **Búsqueda Híbrida** (Recomendada)
   - Combina búsqueda semántica (vectorial) y textual (FTS)
   - Ofrece los mejores resultados al considerar tanto el significado como las palabras exactas
   - Ideal para la mayoría de los casos de uso

2. **Búsqueda Vectorial**
   - Búsqueda semántica basada en embeddings
   - Encuentra documentos por significado, no solo por palabras exactas
   - Útil para búsquedas conceptuales

3. **Búsqueda Textual (FTS)**
   - Búsqueda de texto completo usando PostgreSQL FTS
   - Encuentra coincidencias exactas de palabras y frases
   - Útil para búsquedas precisas

### 📊 Características de los Resultados

- **Resaltado de texto**: Las coincidencias se resaltan en los resultados
- **Puntuación**: Cada resultado muestra su score de relevancia
- **Metadatos**: Muestra el nombre del archivo, título y fragmento del documento
- **Navegación**: Click en un resultado para ver el documento completo

## Componentes Implementados

### Backend

**Archivo**: `api/collection_search.py`

- **Endpoint**: `GET /api/collections/search`
- **Parámetros**:
  - `query` (string, requerido): Texto de búsqueda
  - `topic` (string, requerido): Nombre de la colección
  - `account_id` (string, requerido): ID del usuario
  - `workspace_id` (string, opcional): ID del workspace
  - `search_type` (enum, opcional): `"hybrid"`, `"vector"`, o `"text"` (default: `"hybrid"`)
  - `k` (int, opcional): Número máximo de resultados (1-50, default: 10)

**Respuesta**:

```json
{
  "results": [
    {
      "document_id": "uuid",
      "file_name": "documento.pdf",
      "title": "Título del Documento",
      "content": "Fragmento de texto relevante...",
      "topic": "nombre_coleccion",
      "chunk_index": 0,
      "score": 0.85,
      "rank_score": 2.5
    }
  ],
  "total_results": 10,
  "search_type": "hybrid"
}
```

### Frontend

**Componente**: `src/components/CollectionSearch.tsx`

Componente React que proporciona:

- Barra de búsqueda con autocompletado
- Selector de tipo de búsqueda
- Visualización de resultados con resaltado
- Navegación a documentos

**Integración**: El componente se ha integrado en `DocumentCollectionDisplay.tsx` y aparece automáticamente en todas las páginas de colecciones.

## Uso

### Para Usuarios

1. Navega a cualquier colección de documentos
2. Usa la barra de búsqueda en la parte superior
3. Selecciona el tipo de búsqueda (Híbrida, Vectorial o Textual)
4. Escribe tu consulta y presiona Enter o haz click en "Buscar"
5. Revisa los resultados y haz click en cualquiera para ver más detalles

### Para Desarrolladores

#### Usar el endpoint directamente

```python
import requests

response = requests.get(
    'http://localhost:8000/api/collections/search',
    params={
        'query': 'inteligencia artificial',
        'topic': 'mi_coleccion',
        'account_id': 'user-uuid',
        'search_type': 'hybrid',
        'k': 20
    }
)

results = response.json()
```

#### Integrar el componente en otra página

```tsx
import { CollectionSearch } from '@/components/CollectionSearch';

function MyComponent() {
  return (
    <CollectionSearch
      topic="nombre_coleccion"
      accountId={userId}
      workspaceId={workspaceId}
      onResultClick={(result) => {
        console.log('Resultado seleccionado:', result);
        // Manejar el click en el resultado
      }}
    />
  );
}
```

## Arquitectura Técnica

### Flujo de Búsqueda

1. **Frontend**: Usuario ingresa consulta y selecciona tipo de búsqueda
2. **API**: Endpoint `/api/collections/search` recibe la solicitud
3. **Backend**:
   - Para búsqueda vectorial: Genera embedding de la consulta usando `get_cached_embedding()`
   - Para búsqueda textual: Usa PostgreSQL FTS con `_run_fts_search()`
   - Para búsqueda híbrida: Combina ambos métodos
4. **Base de Datos**: Consulta la tabla `langchain_pg_embedding` con filtros por:
   - `account_id`: Usuario actual
   - `topic`: Colección específica
   - `content_type`: Solo documentos de usuario
   - `workspace_id`: Workspace (si aplica)
5. **Respuesta**: Resultados ordenados por relevancia y limitados por `k`

### Optimizaciones

- **Caché de embeddings**: Los embeddings de consultas se cachean para evitar regeneración
- **Índices de base de datos**:
  - Índice vectorial para búsqueda semántica
  - Índice GIN para FTS
  - Índices en `account_id`, `topic`, `content_type`
- **Límite de resultados**: Máximo 50 resultados para evitar sobrecarga
- **Umbral de similitud**: 0.5 para búsqueda vectorial (configurable)

## Mejoras Futuras

- [ ] Filtros adicionales (por fecha, autor, tipo de documento)
- [ ] Búsqueda avanzada con operadores booleanos
- [ ] Historial de búsquedas
- [ ] Sugerencias de búsqueda (autocomplete)
- [ ] Exportar resultados de búsqueda
- [ ] Búsqueda en múltiples colecciones simultáneamente
- [ ] Reranking de resultados con modelos más avanzados

## Troubleshooting

### No se encuentran resultados

1. Verifica que la colección tenga documentos procesados
2. Prueba con diferentes tipos de búsqueda
3. Simplifica la consulta (menos palabras)
4. Revisa que los documentos estén correctamente indexados

### Errores de búsqueda

1. Verifica la conexión a la base de datos
2. Confirma que el modelo de embeddings esté inicializado
3. Revisa los logs del backend para más detalles
4. Verifica que el usuario tenga permisos en la colección

## Referencias

- Código backend: `api/collection_search.py`
- Código frontend: `src/components/CollectionSearch.tsx`
- Integración: `src/components/DocumentCollectionDisplay.tsx`
- Funciones de búsqueda: `core/memory_manager.py` (`_run_semantic_search`, `_run_fts_search`)
