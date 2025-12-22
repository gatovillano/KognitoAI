# Sistema de Colecciones de Conocimientos (Topics) - Investigación Completa

**Fecha:** 22-12-2025  
**Proyecto:** KognitoAI  
**Investigador:** Análisis Directo del Código Fuente

## Resumen Ejecutivo

El sistema de colecciones de conocimientos (topics) de KognitoAI es una arquitectura compleja y bien estructurada que permite a los usuarios organizar, almacenar y recuperar documentos de manera inteligente. El sistema está diseñado con una arquitectura universal que separa las identidades de plataforma y se basa en un modelo de datos robusto con soporte para búsqueda semántica, filtros por workspace, y integración con grafos de conocimiento.

## 1. Arquitectura General del Sistema

### 1.1 Principios de Diseño

- **Identidad Universal**: Sistema basado en `account_id` (UUID) que es independiente de la plataforma
- **Arquitectura Multi-tenant**: Soporte para workspaces compartidos con control de permisos granular
- **Búsqueda Híbrida**: Combinación de búsqueda semántica (embeddings) y búsqueda de texto completo (FTS)
- **Optimización de Rendimiento**: Columnas directas en `langchain_pg_embedding` para evitar JOINs costosos
- **Integración con RAG**: Seamless integration con el sistema de Retrieval Augmented Generation

### 1.2 Componentes Principales

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Layer     │    │   Core Layer     │    │  Data Layer     │
│                 │    │                  │    │                 │
│ • collections.py│    │ • memory_manager │    │ • PostgreSQL    │
│ • knowledge_... │    │ • tools.py       │    │ • pgvector      │
│ • workspaces.py │    │ • agents/        │    │ • Neo4j         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   Frontend       │
                    │                  │
                    │ • CommonChat     │
                    │ • Context...     │
                    └──────────────────┘
```

## 2. Modelo de Datos y Estructura

### 2.1 Tabla Principal: `UserDocumentTopic`

```python
class UserDocumentTopic(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True)
    
    name = Column(String(255), nullable=False)  # Nombre del topic/colección
    description = Column(Text, nullable=True)   # Descripción opcional
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
```

**Características Clave:**
- Relación muchos-a-muchos con `ContactProfile` via tabla de asociación
- Índices únicos que previenen duplicados por cuenta/workspace
- Soporte para workspaces opcionales (colecciones personales vs. de workspace)

### 2.2 Tabla de Embeddings: `langchain_pg_embedding`

```python
class LangchainPgEmbedding(Base):
    # Columnas optimizadas para evitar JOINs
    account_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    topic = Column(String(100), nullable=True)
    category = Column(String(50), nullable=True)
    
    # Metadatos y contenido
    document = Column(String, nullable=True)  # Contenido del chunk
    cmetadata = Column(JSONB, nullable=True)  # Metadatos adicionales
    embedding = Column(Vector(), nullable=True)  # Vector de embeddings
    text_search_vector = Column(TSVECTOR, nullable=True)  # Para FTS
```

**Optimizaciones de Rendimiento:**
- Columnas directas para filtros frecuentes (`account_id`, `workspace_id`, `topic`)
- Índices GIN para búsquedas JSONB
- Soporte para pgvector para búsquedas semánticas
- Columna TSVECTOR para búsqueda de texto completo

## 3. API Endpoints y Funcionalidades

### 3.1 Endpoints de Colecciones (`api/collections.py`)

#### 3.1.1 Listar Colecciones
```http
GET /api/collections?workspace_id={workspace_id}
```
- **Función**: `list_collections()`
- **Filtros**: Por workspace (opcional)
- **Respuesta**: Lista de `CollectionResponse` con conteo de documentos

#### 3.1.2 Crear Colección
```http
POST /api/collections
Content-Type: application/json

{
  "topic": "nombre_coleccion",
  "description": "descripción opcional",
  "workspaceId": "uuid_del_workspace"
}
```
- **Función**: `create_collection()`
- **Validaciones**: Permisos de workspace
- **Comportamiento**: Crea entrada en `UserDocumentTopic` si no existe

#### 3.1.3 Actualizar Colección
```http
POST /api/update-collection
Content-Type: application/json

{
  "old_topic": "nombre_anterior",
  "new_topic": "nuevo_nombre",
  "new_description": "nueva_descripción",
  "workspace_id": "uuid_workspace"
}
```
- **Función**: `update_collection()`
- **Atomicidad**: Actualiza tanto metadatos como documentos asociados

#### 3.1.4 Obtener Detalles de Colección
```http
GET /api/collections/{topic}/details?workspace_id={workspace_id}
```
- **Función**: `get_collection_details_by_name()`
- **Incluye**: Perfiles de contacto vinculados, conteo de documentos

### 3.2 Endpoints de Conocimiento (`api/knowledge_graph.py`)

#### 3.2.1 Estado del Grafo
```http
GET /api/knowledge-graph/status?workspace_id={workspace_id}
```

#### 3.2.2 Búsqueda en Grafo
```http
POST /api/knowledge-graph/search-graph
Content-Type: application/json

{
  "query": "consulta en lenguaje natural",
  "workspace_id": "uuid_workspace",
  "limit": 50
}
```

#### 3.2.3 Procesamiento de Documentos
```http
POST /api/knowledge-graph/process-knowledge-graph-optimized
Content-Type: application/json

{
  "workspace_id": "uuid_workspace",
  "force_reprocess": false,
  "topic": "colección_específica",
  "processing_mode": "hybrid"
}
```

### 3.3 Endpoints de Workspaces (`api/workspaces.py`)

#### 3.3.1 Gestión de Permisos
```http
GET /api/workspaces/{workspace_id}/my-role
POST /api/workspaces/{workspace_id}/share
PUT /api/workspaces/{workspace_id}/permissions/{account_id}
```

## 4. Funcionalidades del Backend

### 4.1 Gestión de Memoria (`core/memory_manager.py`)

#### 4.1.1 Búsqueda Híbrida
```python
async def get_relevant_memories(
    account_id: str,
    query: str,
    k: int = 20,
    workspace_id: Optional[str] = None,
    filter_topics: Optional[List[str]] = None,
    content_types: Optional[List[str]] = None,
    hybrid_search: bool = True
) -> ToolOutputWithSources
```

**Características:**
- **Búsqueda Semántica**: Usando embeddings vectoriales
- **Búsqueda de Texto Completo**: Con ranking por relevancia
- **Ensemble Retriever**: Combina ambos métodos con pesos configurables
- **Reranking**: Reordena resultados usando Cross-Encoder
- **Filtros Múltiples**: Por workspace, topics, tipos de contenido

#### 4.1.2 Procesamiento de Documentos
```python
async def process_document_for_rag(
    file_name: str,
    extracted_text: str,
    topic: str = "general_documents",
    account_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int
```

**Pipeline de Procesamiento:**
1. **División de Texto**: Usando `RecursiveCharacterTextSplitter`
2. **Generación de Embeddings**: Batch processing para eficiencia
3. **Almacenamiento Vectorial**: En `langchain_pg_embedding`
4. **Actualización de Metadatos**: Columnas optimizadas para búsquedas
5. **Notificaciones WebSocket**: Para updates en tiempo real

#### 4.1.3 Gestión de Colecciones

```python
async def list_user_collections(
    account_id: str, 
    workspace_id: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Lógica de Filtrado:**
- **Con workspace_id**: Solo colecciones de ese workspace
- **Sin workspace_id**: Todas las colecciones del usuario (incluyendo personales)
- **Conteo de Documentos**: Consulta optimizada sin JOINs

### 4.2 Herramientas Especializadas

#### 4.2.1 Knowledge Graph Tool (`tools/knowledge_graph_tool.py`)

```python
class KnowledgeGraphTool(BaseTool):
    name: str = "knowledge_graph"
    description: str = (
        "Realiza una consulta en lenguaje natural al grafo de conocimiento para descubrir entidades, "
        "relaciones y patrones complejos."
    )
```

**Capacidades:**
- Consultas en lenguaje natural sobre el grafo
- Integración con `KnowledgeGraphService`
- Formateo inteligente de resultados

#### 4.2.2 Document RAG Tool (`tools/document_rag_tool.py`)

```python
class DocumentRAGTool(BaseTool):
    name: str = "process_document_for_rag"
    description: str = """
    Useful when the user provides a document and wants its content added to their knowledge base (RAG).
    """
```

**Funcionalidades:**
- Procesamiento de documentos subidos
- Asignación automática a colecciones
- Soporte para metadatos personalizados

### 4.3 Integración con Knowledge Graph

#### 4.3.1 Arquitectura de Grafo

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Graph Service                  │
├─────────────────────────────────────────────────────────────┤
│  • GraphIntegration                                         │
│  • GraphDatabase (Neo4j)                                   │
│  • EntityQualityReviewer                                   │
│  • TrendAnalyzer                                           │
└─────────────────────────────────────────────────────────────┘
```

#### 4.3.2 Procesamiento de Documentos para Grafo

- **Hybrid Processing**: Combina extracción de entidades y relaciones
- **Conceptual Processing**: Enfoque en citas e ideas interrelacionadas
- **Co-occurrence Analysis**: Análisis de co-ocurrencias optimizado
- **Temporal Analysis**: Detección de tendencias temporales

## 5. Interfaces de Usuario

### 5.1 Componente CommonChat (`src/components/CommonChat.tsx`)

#### 5.1.1 Gestión de Contexto

```typescript
interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
}
```

**Funcionalidades:**
- **Selector de Contexto**: Permite seleccionar documentos/colecciones
- **Upload de Archivos**: Integración directa con colecciones
- **Subida de Imágenes**: Soporte para contexto visual
- **Contexto Persistente**: Mantiene contexto entre mensajes

#### 5.1.2 WebSocket Integration

```typescript
useWebSocketContext() // Para updates en tiempo real
```

**Eventos Manejados:**
- `stream_start`, `stream_chunk`, `stream_end`: Para streaming de respuestas
- `tool_start`, `tool_end`: Para estado de herramientas
- `document_processing_*`: Para estado de procesamiento de documentos

### 5.2 Context Selector Button

- **Selección de Colecciones**: Interface para elegir collections como contexto
- **Preview de Documentos**: Vista previa de documentos en la colección
- **Filtros por Workspace**: Si aplica, filtrado por workspace

## 6. Características Avanzadas

### 6.1 Sistema de Permisos

#### 6.1.1 Roles de Workspace
- **owner**: Control total sobre el workspace y sus colecciones
- **editor**: Puede crear/editar colecciones y documentos
- **viewer**: Solo lectura de colecciones compartidas

#### 6.1.2 Verificación de Permisos
```python
async def check_workspace_permission(
    db: AsyncSession,
    workspace_uuid: uuid.UUID,
    account_uuid: uuid.UUID,
    required_roles: List[str]
)
```

### 6.2 Búsqueda y Filtrado Avanzado

#### 6.2.1 Filtros Múltiples
- **Por Workspace**: Filtrado por contexto de workspace
- **Por Topic**: Filtrado por colección específica
- **Por Tipo de Contenido**: `user_memories`, `user_documents`, `user_notes`
- **Por Categoría**: Categorización personalizada
- **Por Fecha**: Rangos temporales (via metadatos)

#### 6.2.2 Búsqueda Semántica
- **Embeddings Locales**: Usando modelos Ollama
- **Similarity Threshold**: Umbral configurable de similitud
- **Hybrid Search**: Combinación de semántica y FTS
- **Reranking**: Reordenamiento inteligente de resultados

### 6.3 Integración con Contactos

#### 6.3.1 Perfiles Vinculados
- **Many-to-Many**: Una colección puede tener múltiples contactos
- **Association Table**: `user_document_topic_contact_profiles_association`
- **Gestión API**: Endpoints para vincular/desvincular perfiles

### 6.4 Análisis y Insights

#### 6.4.1 Entity Quality Reviewer
```python
class EntityQualityReviewer:
    def review_all_entities(self, workspace_id: str)
    def apply_corrections(self, corrections: List[Dict], auto_apply: bool)
```

**Funcionalidades:**
- Detección de entidades mal clasificadas
- Identificación de duplicados
- Sugerencias de corrección automáticas

#### 6.4.2 Trend Analysis
```python
class TrendAnalyzer:
    def detect_trends(self, dataset_name: str, time_window: str)
    def analyze_temporal_patterns(self, dataset_name: str, analysis_types: List[str])
```

**Capacidades:**
- Detección de tendencias emergentes
- Análisis de patrones temporales
- Métricas de tendencias por dirección

## 7. Optimizaciones de Rendimiento

### 7.1 Columnas Directas en Embeddings
- **Sin JOINs**: Filtros directos en `langchain_pg_embedding`
- **Índices Optimizados**: Para búsquedas frecuentes
- **Batch Processing**: Procesamiento en lotes para embeddings

### 7.2 Cache y Session Management
```python
async def get_shared_dependencies():
    # Singleton instances para GraphDB y GraphIntegration
```

### 7.3 Concurrency Control
```python
DOCUMENT_PROCESSING_SEMAPHORE = asyncio.Semaphore(5)
```

## 8. Configuración y Dependencias

### 8.1 Variables de Entorno Clave
```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Embeddings
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_MODEL_PATH=/path/to/model

# Configuración RAG
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
HYBRID_SEARCH_BM25_WEIGHT=0.3
```

### 8.2 Extensiones de Base de Datos
- **pgvector**: Para embeddings vectoriales
- **pg_trgm**: Para búsqueda por similitud
- **tsvector**: Para búsqueda de texto completo

## 9. Flujo de Datos Completo

### 9.1 Creación de Colección
```
1. Usuario → API /collections (POST)
2. API → memory_manager.create_empty_collection()
3. memory_manager → DB UserDocumentTopic (INSERT)
4. API → Response con confirmación
```

### 9.2 Subida de Documento
```
1. Usuario → Frontend upload
2. Frontend → API /documents/upload-chat-document
3. API → memory_manager.process_document_for_rag()
4. memory_manager → Text splitting + embedding generation
5. memory_manager → langchain_pg_embedding (INSERT)
6. WebSocket → Frontend (progreso y finalización)
```

### 9.3 Búsqueda en Colección
```
1. Usuario → Frontend query
2. Frontend → API con filtros (workspace, topic, etc.)
3. API → memory_manager.get_relevant_memories()
4. memory_manager → Hybrid search (semantic + FTS)
5. memory_manager → Reranking (opcional)
6. API → Frontend (resultados formateados)
```

## 10. Limitaciones y Consideraciones

### 10.1 Limitaciones Actuales
- **Escalabilidad**: Procesamiento de documentos en lotes puede ser lento para archivos muy grandes
- **Memoria**: Embeddings de modelos grandes pueden consumir memoria significativa
- **Búsqueda**: FTS en español podría mejorarse con stemming específico

### 10.2 Consideraciones de Seguridad
- **Validación de Permisos**: Verificación en cada endpoint
- **Sanitización**: Limpieza de metadatos de documentos
- **Aislamiento de Datos**: Separación por account_id y workspace_id

## 11. Recomendaciones de Mejora

### 11.1 Optimizaciones Técnicas
1. **Cache de Embeddings**: Cachear embeddings para documentos similares
2. **Índices Adicionales**: Índices compuestos para consultas frecuentes
3. **Batch Operations**: Operaciones en lote para múltiples documentos
4. **Background Processing**: Jobs en background para procesamiento pesado

### 11.2 Mejoras de UX
1. **Preview de Colecciones**: Vista previa del contenido antes de seleccionar
2. **Drag & Drop**: Interface más intuitiva para subir documentos
3. **Bulk Operations**: Operaciones en lote para múltiples documentos
4. **Historial de Búsqueda**: Guardar búsquedas frecuentes

### 11.3 Funcionalidades Avanzadas
1. **Auto-tagging**: Etiquetado automático de documentos
2. **Duplicate Detection**: Detección automática de documentos duplicados
3. **Version Control**: Control de versiones para documentos
4. **Collaboration Features**: Comentarios y anotaciones colaborativas

## 12. Conclusiones

El sistema de colecciones de conocimientos de KognitoAI es una arquitectura sólida y bien diseñada que proporciona:

### 12.1 Fortalezas
- **Arquitectura Escalable**: Separación clara de responsabilidades
- **Flexibilidad**: Soporte para múltiples tipos de contenido y casos de uso
- **Rendimiento**: Optimizaciones para búsquedas eficientes
- **Integración**: Seamless integration con otros módulos del sistema
- **Multi-tenancy**: Soporte robusto para workspaces y permisos

### 12.2 Innovación
- **Búsqueda Híbrida**: Combinación inteligente de métodos de búsqueda
- **Grafo de Conocimiento**: Integración avanzada con análisis de entidades
- **Tiempo Real**: Updates via WebSocket para mejor UX
- **Universal ID**: Sistema de identidad independiente de plataforma

### 12.3 Impacto
Este sistema permite a los usuarios:
- Organizar eficientemente grandes volúmenes de documentos
- Realizar búsquedas inteligentes y contextuales
- Colaborar en espacios de trabajo compartidos
- Obtener insights avanzados a través del grafo de conocimiento
- Mantener un historial conversacional enriquecido

El sistema está bien preparado para escalar y adaptarse a futuras necesidades, con una base arquitectónica sólida que soporta tanto casos de uso simples como complejos.

---

**Fin del Informe**

*Este documento representa un análisis completo del sistema de colecciones de conocimientos de KognitoAI basado en la revisión exhaustiva del código fuente, APIs, modelos de datos, y funcionalidades implementadas.*