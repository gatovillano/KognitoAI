# Guía Técnica: Implementación de Grafos de Conocimiento

## 🔧 Arquitectura Técnica Detallada

### Estructura de Directorios

```
kognito-ai/
├── knowledge_graph/
│   ├── __init__.py
│   ├── graph_database.py          # Clase GraphDB para Neo4j
│   ├── knowledge_models.py        # Modelos Pydantic
│   └── cognee_integration.py      # Integración con Cognee
├── core/
│   ├── tools/
│   │   └── knowledge_graph_tool.py # Herramienta base
│   └── config.py                  # Configuración actualizada
├── tools/
│   ├── text_to_knowledge_graph_tool.py    # Herramienta híbrida
│   └── mindmap_to_graph_tool.py           # Mapa mental + grafo
└── test_knowledge_graph_tools.py          # Script de pruebas
```

### Modelos de Datos

#### Node (knowledge_models.py)

```python
class Node(BaseModel):
    """Modelo base para nodos en el grafo."""
    label: str = Field(..., description="Etiqueta del nodo")
    properties: Dict[str, Any] = Field(..., description="Propiedades del nodo")

class Concept(Node):
    """Nodo específico para conceptos."""
    label: str = "Concepto"
    properties: Dict[str, Any] = Field(...)

class Persona(Node):
    """Nodo específico para personas."""
    label: str = "Persona"
    properties: Dict[str, Any] = Field(...)
```

#### Relationship (knowledge_models.py)

```python
class Relationship(BaseModel):
    """Modelo para relaciones entre nodos."""
    type: str = Field(..., description="Tipo de relación")
    start_node_label: str = Field(...)
    start_node_property_name: str = Field(...)
    start_node_property_value: Any = Field(...)
    end_node_label: str = Field(...)
    end_node_property_name: str = Field(...)
    end_node_property_value: Any = Field(...)
    properties: Optional[Dict[str, Any]] = Field(None)
```

### Clase GraphDB

#### Métodos Principales

```python
class GraphDB:
    def __init__(self, uri: str, user: str, password: str)
    def connect(self) -> None
    def close(self) -> None
    def verify_connection(self) -> None
    def create_node(self, node: Node) -> Any
    def get_node(self, label: str, property_name: str, property_value: Any) -> Any
    def update_node(self, label: str, property_name: str, property_value: Any, new_properties: Dict) -> Any
    def delete_node(self, label: str, property_name: str, property_value: Any) -> None
    def create_relationship(self, ...) -> Any
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]
```

#### Ejemplo de Uso

```python
# Inicializar conexión
graph_db = GraphDB(
    uri="bolt://neo4j_db:7687",
    user="neo4j",
    password="password"
)

# Conectar
graph_db.connect()

# Crear nodo
node = Node(
    label="Concept",
    properties={
        "name": "Machine Learning",
        "description": "AI subset focused on learning from data",
        "category": "technology"
    }
)
created_node = graph_db.create_node(node)

# Crear relación
graph_db.create_relationship(
    node1_label="Concept",
    node1_property_name="name",
    node1_property_value="Machine Learning",
    relationship_type="IS_PART_OF",
    node2_label="Concept",
    node2_property_name="name",
    node2_property_value="Artificial Intelligence"
)

# Cerrar conexión
graph_db.close()
```

## 🛠️ Implementación de Herramientas

### TextToKnowledgeGraphTool

#### Flujo de Procesamiento

1. **Análisis de Texto**: Usa `AdvancedTextAnalyzer`
2. **Extracción de Entidades**: Convierte análisis a entidades/relaciones
3. **Almacenamiento**: Persiste en Neo4j con metadatos
4. **Integración Cognee**: Opcional para procesamiento avanzado

#### Métodos Clave

```python
async def _arun(self, text: str, workspace_id: str, graph_name: str, 
                create_graph: bool, use_cognee: bool) -> str:
    # 1. Análisis de texto
    analysis_result = await text_analyzer.analyze_single_text(text)
    
    # 2. Crear grafo si se solicita
    if create_graph:
        if use_cognee:
            graph_result = await self._create_graph_with_cognee(...)
        else:
            graph_result = await self._create_graph_direct(...)
    
    return self._format_final_result(result)

async def _create_graph_direct(self, analysis_result, graph_name, workspace_id):
    # Convertir análisis a entidades
    entities_relations = await extract_entities_from_text_analysis(analysis_dict)
    
    # Almacenar en Neo4j
    self.graph_db.connect()
    try:
        for entity in entities_relations.get("entities", []):
            node = Node(label=entity.get("type"), properties={...})
            self.graph_db.create_node(node)
        
        for relation in entities_relations.get("relationships", []):
            self.graph_db.create_relationship(...)
    finally:
        self.graph_db.close()
```

### MindmapToGraphTool

#### Flujo de Procesamiento

1. **Extracción de Conceptos**: Usa `extract_concepts_from_document`
2. **Generación de Mapa**: Crea estructura visual
3. **Creación de Grafo**: Convierte estructura a nodos/relaciones
4. **Detección de Relaciones**: Encuentra conexiones semánticas

#### Algoritmo de Relaciones

```python
def _concepts_are_related(self, concept1: Dict, concept2: Dict) -> bool:
    """Determina si dos conceptos están relacionados."""
    name1 = concept1.get("name", "").lower()
    name2 = concept2.get("name", "").lower()
    
    # Palabras compartidas
    words1 = set(word for word in name1.split() if len(word) > 2)
    words2 = set(word for word in name2.split() if len(word) > 2)
    
    if words1.intersection(words2):
        return True
    
    # Misma categoría
    if concept1.get("category") == concept2.get("category"):
        return True
    
    return False
```

## 🔌 Integración con Cognee

### Endpoints API

```python
# Endpoints principales de Cognee
POST /cognee/add        # Añadir documentos
POST /cognee/cognify    # Procesar y crear grafo
GET  /cognee/search     # Buscar en el grafo
POST /cognee/prune      # Limpiar datos
GET  /cognee/status     # Estado del servicio
```

### Implementación

```python
async def _process_with_cognee(self, documents: List[Dict], graph_name: str) -> Dict:
    """Envía documentos a Cognee para crear el grafo."""
    async with httpx.AsyncClient() as client:
        # 1. Añadir documentos
        add_response = await client.post(
            f"{self.cognee_url}/cognee/add",
            json={"data": documents, "dataset_name": graph_name}
        )
        
        # 2. Procesar y crear grafo
        cognify_response = await client.post(
            f"{self.cognee_url}/cognee/cognify",
            json={"dataset_name": graph_name}
        )
        
        return cognify_response.json()
```

## 📊 Esquemas de Base de Datos

### Neo4j Schema

#### Nodos Principales

```cypher
-- Crear índices para rendimiento
CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);
CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id);
CREATE INDEX account_workspace IF NOT EXISTS FOR (n) ON (n.account_id, n.workspace_id);

-- Constraints para integridad
CREATE CONSTRAINT concept_unique IF NOT EXISTS FOR (c:Concept) REQUIRE (c.name, c.account_id, c.workspace_id) IS UNIQUE;
```

#### Estructura de Propiedades

```json
// Nodo Concept
{
  "name": "Machine Learning",
  "description": "AI subset for learning from data",
  "category": "technology",
  "importance": 0.8,
  "workspace_id": "research_project",
  "account_id": "user123",
  "graph_name": "ai_concepts",
  "created_at": "2024-01-09T10:30:00Z",
  "source": "text_analysis"
}

// Relación RELATED_TO
{
  "relationship_type": "semantic",
  "confidence": 0.7,
  "workspace_id": "research_project",
  "account_id": "user123",
  "graph_name": "ai_concepts",
  "created_at": "2024-01-09T10:30:00Z"
}
```

### PostgreSQL Extensions

#### Tabla de Metadatos de Grafos

```sql
CREATE TABLE knowledge_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    workspace_id VARCHAR(255) NOT NULL,
    document_ids TEXT[], -- Array de IDs de documentos fuente
    node_count INTEGER DEFAULT 0,
    relationship_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Índices
CREATE INDEX idx_kg_account_workspace ON knowledge_graphs(account_id, workspace_id);
CREATE INDEX idx_kg_graph_name ON knowledge_graphs(graph_name);
CREATE INDEX idx_kg_status ON knowledge_graphs(status);
```

## 🧪 Testing y Validación

### Script de Pruebas

El script `test_knowledge_graph_tools.py` incluye:

1. **test_neo4j_connection()**: Verifica conectividad básica
2. **test_text_to_knowledge_graph()**: Prueba extracción de texto
3. **test_mindmap_to_graph()**: Prueba generación de mapas mentales
4. **test_graph_queries()**: Verifica consultas Cypher
5. **cleanup_test_data()**: Limpia datos de prueba

### Casos de Prueba

```python
# Texto de prueba para análisis
test_text = """
La inteligencia artificial es una rama de la informática que se centra en crear 
sistemas capaces de realizar tareas que normalmente requieren inteligencia humana. 
Incluye subcampos como el aprendizaje automático, el procesamiento de lenguaje 
natural y la visión por computadora.
"""

# Documento de prueba para mapa mental
test_document = """
El cambio climático es uno de los desafíos más importantes de nuestro tiempo. 
Las principales causas incluyen las emisiones de gases de efecto invernadero, 
la deforestación y la industrialización.
"""
```

### Métricas de Validación

```python
# Verificar creación exitosa
assert result["status"] == "success"
assert result["nodes_created"] > 0
assert result["relationships_created"] > 0

# Verificar estructura del grafo
query = "MATCH (n) WHERE n.account_id = $account_id RETURN count(n) as node_count"
node_count = graph_db.execute_query(query, {"account_id": "test_user"})[0]["node_count"]
assert node_count > 0
```

## 🔧 Configuración Avanzada

### Optimización de Neo4j

```cypher
-- Configuración de memoria (neo4j.conf)
dbms.memory.heap.initial_size=1G
dbms.memory.heap.max_size=2G
dbms.memory.pagecache.size=1G

-- Configuración de conexiones
dbms.connector.bolt.thread_pool_min_size=5
dbms.connector.bolt.thread_pool_max_size=400
```

### Configuración de Cognee

```yaml
# docker-compose.yml - Configuración avanzada
cognee:
  image: cognee/cognee-mcp:main
  environment:
    COGNEE_API_URL: ${COGNEE_API_URL}
    COGNEE_LOG_LEVEL: INFO
    COGNEE_MAX_WORKERS: 4
    COGNEE_TIMEOUT: 300
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```

### Variables de Entorno Adicionales

```bash
# Configuración avanzada de Neo4j
NEO4J_dbms_memory_heap_initial__size=1G
NEO4J_dbms_memory_heap_max__size=2G
NEO4J_dbms_memory_pagecache_size=1G

# Configuración de timeouts
NEO4J_CONNECTION_TIMEOUT=30
COGNEE_REQUEST_TIMEOUT=60

# Configuración de logging
KNOWLEDGE_GRAPH_LOG_LEVEL=INFO
NEO4J_LOG_LEVEL=WARN
```

## 🚀 Deployment y Producción

### Consideraciones de Seguridad

1. **Credenciales**: Usar secretos seguros para Neo4j
2. **Red**: Configurar firewall para puertos 7474/7687
3. **Backup**: Implementar backup automático de grafos
4. **Monitoreo**: Configurar alertas para servicios

### Escalabilidad

```yaml
# Configuración para múltiples instancias
neo4j:
  deploy:
    replicas: 3
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
  volumes:
    - neo4j_data_1:/data
    - neo4j_logs_1:/logs
```

### Monitoreo

```python
# Métricas personalizadas
from prometheus_client import Counter, Histogram

nodes_created = Counter('kg_nodes_created_total', 'Total nodes created')
query_duration = Histogram('kg_query_duration_seconds', 'Query duration')

# Uso en código
nodes_created.inc()
with query_duration.time():
    result = graph_db.execute_query(query)
```

## 🔍 Debugging y Troubleshooting

### Logs Detallados

```python
# Configuración de logging para debugging
import logging

# Logger principal
logger = logging.getLogger('knowledge_graph')
logger.setLevel(logging.DEBUG)

# Handler para archivo
file_handler = logging.FileHandler('knowledge_graph.log')
file_handler.setLevel(logging.DEBUG)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
```

### Problemas Comunes y Soluciones

#### 1. Error de Conexión Neo4j

```python
# Problema: ConnectionError o AuthError
# Solución: Verificar configuración
try:
    graph_db.connect()
except Exception as e:
    logger.error(f"Error de conexión: {e}")
    # Verificar:
    # - Servicio Neo4j corriendo
    # - Credenciales correctas
    # - Puerto accesible
```

#### 2. Timeout en Cognee

```python
# Problema: httpx.TimeoutException
# Solución: Aumentar timeout
async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.post(url, json=data)
```

#### 3. Memoria Insuficiente

```bash
# Problema: OutOfMemoryError en Neo4j
# Solución: Aumentar heap size
NEO4J_dbms_memory_heap_max__size=4G
```

### Herramientas de Diagnóstico

```python
# Script de diagnóstico
async def diagnose_system():
    """Ejecuta diagnósticos del sistema de grafos."""

    # 1. Verificar Neo4j
    try:
        graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        graph_db.connect()
        result = graph_db.execute_query("RETURN 1 as test")
        print("✅ Neo4j: Conectado")
        graph_db.close()
    except Exception as e:
        print(f"❌ Neo4j: Error - {e}")

    # 2. Verificar Cognee
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.cognee_api_url}/health")
            if response.status_code == 200:
                print("✅ Cognee: Disponible")
            else:
                print(f"⚠️ Cognee: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Cognee: Error - {e}")

    # 3. Verificar herramientas
    try:
        tool = TextToKnowledgeGraphTool(account_id="diagnostic")
        print("✅ TextToKnowledgeGraphTool: Inicializada")
    except Exception as e:
        print(f"❌ TextToKnowledgeGraphTool: Error - {e}")
```

## 📈 Optimización de Rendimiento

### Índices Neo4j

```cypher
-- Índices para consultas frecuentes
CREATE INDEX concept_account_workspace IF NOT EXISTS
FOR (c:Concept) ON (c.account_id, c.workspace_id);

CREATE INDEX document_created_at IF NOT EXISTS
FOR (d:Document) ON (d.created_at);

CREATE INDEX relationship_confidence IF NOT EXISTS
FOR ()-[r:RELATED_TO]-() ON (r.confidence);

-- Índices de texto completo
CREATE FULLTEXT INDEX concept_search IF NOT EXISTS
FOR (c:Concept) ON EACH [c.name, c.description];
```

### Consultas Optimizadas

```cypher
-- Consulta optimizada para buscar conceptos relacionados
MATCH (c1:Concept {account_id: $account_id})-[r:RELATED_TO]-(c2:Concept)
WHERE c1.name CONTAINS $search_term
AND r.confidence > 0.5
RETURN c1, r, c2
ORDER BY r.confidence DESC
LIMIT 20;

-- Consulta para análisis de centralidad
MATCH (c:Concept {account_id: $account_id})
OPTIONAL MATCH (c)-[r]-()
WITH c, count(r) as degree
WHERE degree > 0
RETURN c.name, degree
ORDER BY degree DESC
LIMIT 10;
```

### Batch Processing

```python
# Procesamiento en lotes para grandes volúmenes
async def create_nodes_batch(self, nodes: List[Node], batch_size: int = 100):
    """Crea nodos en lotes para mejor rendimiento."""

    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]

        # Crear query batch
        query = """
        UNWIND $nodes as node_data
        CREATE (n)
        SET n = node_data.properties
        SET n:Concept
        """

        # Preparar datos
        batch_data = [{"properties": node.properties} for node in batch]

        # Ejecutar batch
        self.graph_db.execute_query(query, {"nodes": batch_data})

        logger.info(f"Procesado lote {i//batch_size + 1}: {len(batch)} nodos")
```

## 🔄 Migración y Versionado

### Schema Migrations

```python
# migrations/001_initial_schema.py
def upgrade():
    """Crear esquema inicial de Neo4j."""
    queries = [
        "CREATE CONSTRAINT concept_unique IF NOT EXISTS FOR (c:Concept) REQUIRE (c.name, c.account_id) IS UNIQUE",
        "CREATE INDEX concept_workspace IF NOT EXISTS FOR (c:Concept) ON (c.workspace_id)",
        "CREATE INDEX node_created_at IF NOT EXISTS FOR (n) ON (n.created_at)"
    ]

    for query in queries:
        graph_db.execute_query(query)

def downgrade():
    """Revertir cambios del esquema."""
    queries = [
        "DROP CONSTRAINT concept_unique IF EXISTS",
        "DROP INDEX concept_workspace IF EXISTS",
        "DROP INDEX node_created_at IF EXISTS"
    ]

    for query in queries:
        graph_db.execute_query(query)
```

### Versionado de Datos

```python
# Añadir versión a nodos
node_properties = {
    "name": "Machine Learning",
    "description": "AI subset",
    "schema_version": "1.0",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}
```

## 🔐 Seguridad y Permisos

### Control de Acceso

```cypher
-- Crear roles en Neo4j
CREATE ROLE reader;
CREATE ROLE writer;
CREATE ROLE admin;

-- Asignar permisos
GRANT MATCH {*} ON GRAPH * TO reader;
GRANT MATCH {*}, CREATE ON GRAPH * TO writer;
GRANT ALL ON GRAPH * TO admin;
```

### Filtrado por Cuenta

```python
# Siempre filtrar por account_id en consultas
def secure_query(self, base_query: str, account_id: str, params: Dict = None):
    """Ejecuta consulta con filtro de seguridad."""

    # Añadir filtro de account_id
    if "WHERE" in base_query.upper():
        secure_query = base_query.replace(
            "WHERE",
            f"WHERE n.account_id = '{account_id}' AND "
        )
    else:
        secure_query = base_query + f" WHERE n.account_id = '{account_id}'"

    return self.graph_db.execute_query(secure_query, params)
```

## 📊 Métricas y Monitoreo

### Métricas Personalizadas

```python
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class GraphMetrics:
    """Métricas del sistema de grafos."""
    nodes_created: int = 0
    relationships_created: int = 0
    queries_executed: int = 0
    avg_query_time: float = 0.0
    errors_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "nodes_created": self.nodes_created,
            "relationships_created": self.relationships_created,
            "queries_executed": self.queries_executed,
            "avg_query_time": self.avg_query_time,
            "errors_count": self.errors_count
        }

# Singleton para métricas globales
graph_metrics = GraphMetrics()

# Decorator para medir tiempo de consultas
def measure_query_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            graph_metrics.queries_executed += 1
            return result
        except Exception as e:
            graph_metrics.errors_count += 1
            raise
        finally:
            execution_time = time.time() - start_time
            # Actualizar promedio
            total_time = graph_metrics.avg_query_time * (graph_metrics.queries_executed - 1)
            graph_metrics.avg_query_time = (total_time + execution_time) / graph_metrics.queries_executed

    return wrapper
```

### Dashboard de Métricas

```python
# Endpoint para métricas
@app.get("/metrics/knowledge-graph")
async def get_graph_metrics():
    """Retorna métricas del sistema de grafos."""

    # Métricas de Neo4j
    neo4j_stats = graph_db.execute_query("""
        MATCH (n)
        RETURN
            count(n) as total_nodes,
            count(distinct labels(n)) as node_types,
            size(()-[]->()) as total_relationships
    """)[0]

    # Métricas por workspace
    workspace_stats = graph_db.execute_query("""
        MATCH (n)
        WHERE n.workspace_id IS NOT NULL
        RETURN n.workspace_id as workspace, count(n) as nodes
        ORDER BY nodes DESC
        LIMIT 10
    """)

    return {
        "system_metrics": graph_metrics.to_dict(),
        "neo4j_stats": neo4j_stats,
        "workspace_stats": workspace_stats,
        "timestamp": datetime.now().isoformat()
    }
```

---

**Nota**: Esta guía técnica debe mantenerse actualizada con los cambios en la implementación.
**Versión**: 1.0
**Última Actualización**: 2025-01-09
