# Knowledge Graph Module

## 📋 Descripción

Este módulo implementa la funcionalidad de grafos de conocimiento para KognitoAI, proporcionando una arquitectura híbrida que combina bases de datos relacionales (PostgreSQL), bases de datos de grafos (Neo4j) y procesamiento semántico avanzado (Cognee MCP).

## 🏗️ Estructura del Módulo

```
knowledge_graph/
├── __init__.py                 # Inicialización del módulo
├── graph_database.py           # Clase GraphDB para interacción con Neo4j
├── knowledge_models.py         # Modelos Pydantic para nodos y relaciones
├── cognee_integration.py       # Integración con Cognee MCP
└── README.md                   # Este archivo
```

## 📁 Archivos Principales

### `graph_database.py`

Contiene la clase `GraphDB` que maneja todas las operaciones con Neo4j:

```python
from knowledge_graph.graph_database import GraphDB

# Inicializar conexión
graph_db = GraphDB(uri, user, password)
graph_db.connect()

# Crear nodo
node = Node(label="Concept", properties={"name": "AI"})
graph_db.create_node(node)

# Crear relación
graph_db.create_relationship(...)

# Ejecutar consulta personalizada
results = graph_db.execute_query("MATCH (n) RETURN n LIMIT 10")

graph_db.close()
```

**Métodos principales**:
- `connect()` / `close()`: Gestión de conexiones
- `create_node(node)`: Crear nodos
- `get_node()` / `update_node()` / `delete_node()`: CRUD de nodos
- `create_relationship()`: Crear relaciones
- `execute_query()`: Consultas Cypher personalizadas

### `knowledge_models.py`

Define los modelos Pydantic para estructurar datos:

```python
from knowledge_graph.knowledge_models import Node, Concept, Persona, Relationship

# Crear nodo genérico
node = Node(
    label="Entity",
    properties={"name": "Example", "type": "test"}
)

# Crear concepto específico
concept = Concept(
    properties={"name": "Machine Learning", "description": "AI subset"}
)

# Crear relación
relationship = Relationship(
    type="RELATED_TO",
    start_node_label="Concept",
    start_node_property_name="name",
    start_node_property_value="AI",
    end_node_label="Concept",
    end_node_property_name="name",
    end_node_property_value="Machine Learning"
)
```

**Modelos disponibles**:
- `Node`: Modelo base para nodos
- `Concept`: Nodo específico para conceptos
- `Persona`: Nodo específico para personas
- `Lugar`: Nodo específico para lugares
- `Relationship`: Modelo para relaciones entre nodos

### `cognee_integration.py`

Maneja la integración con Cognee MCP para procesamiento semántico avanzado:

```python
from knowledge_graph.cognee_integration import CogneeIntegration

# Inicializar integración
cognee = CogneeIntegration(cognee_api_url, graph_db)

# Convertir grafo a PDDL
pddl_data = cognee.convert_graph_to_pddl("domain_name")

# Ejecutar plan
plan_result = cognee.execute_plan(domain_file, problem_file)

# Integrar resultados
cognee.integrate_cognee_results(plan_result)
```

**Funcionalidades**:
- Conversión de grafos a formato PDDL
- Ejecución de planes en Cognee
- Integración de resultados en Neo4j
- Comunicación HTTP con API de Cognee

## 🔧 Configuración

### Variables de Entorno Requeridas

```bash
# Neo4j
NEO4J_URI=bolt://neo4j_db:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Kn0wl3dg3Gr4ph2024!

# Cognee
COGNEE_API_URL=http://cognee_service:8000
```

### Dependencias

```python
# requirements.txt
neo4j>=5.0.0
pydantic>=2.0.0
httpx>=0.24.0
requests>=2.28.0
```

## 🚀 Uso Básico

### Ejemplo Completo

```python
import asyncio
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node, Concept
from core.config import settings

async def ejemplo_basico():
    # 1. Inicializar conexión
    graph_db = GraphDB(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password
    )
    
    try:
        # 2. Conectar
        graph_db.connect()
        
        # 3. Crear conceptos
        ai_concept = Concept(
            properties={
                "name": "Inteligencia Artificial",
                "description": "Campo de la informática",
                "category": "technology",
                "account_id": "user123",
                "workspace_id": "research"
            }
        )
        
        ml_concept = Concept(
            properties={
                "name": "Machine Learning",
                "description": "Subcampo de IA",
                "category": "technology",
                "account_id": "user123",
                "workspace_id": "research"
            }
        )
        
        # 4. Crear nodos
        graph_db.create_node(ai_concept)
        graph_db.create_node(ml_concept)
        
        # 5. Crear relación
        graph_db.create_relationship(
            node1_label="Concept",
            node1_property_name="name",
            node1_property_value="Machine Learning",
            relationship_type="IS_PART_OF",
            node2_label="Concept",
            node2_property_name="name",
            node2_property_value="Inteligencia Artificial",
            properties={
                "confidence": 0.9,
                "account_id": "user123"
            }
        )
        
        # 6. Consultar resultados
        query = """
        MATCH (c1:Concept)-[r:IS_PART_OF]->(c2:Concept)
        WHERE c1.account_id = $account_id
        RETURN c1.name as subconcept, c2.name as parent_concept, r.confidence
        """
        
        results = graph_db.execute_query(query, {"account_id": "user123"})
        
        for result in results:
            print(f"{result['subconcept']} es parte de {result['parent_concept']} "
                  f"(confianza: {result['confidence']})")
    
    finally:
        # 7. Cerrar conexión
        graph_db.close()

# Ejecutar ejemplo
if __name__ == "__main__":
    asyncio.run(ejemplo_basico())
```

## 🧪 Testing

### Ejecutar Pruebas

```bash
# Desde el directorio raíz del proyecto
python test_knowledge_graph_tools.py
```

### Pruebas Unitarias

```python
# Ejemplo de prueba unitaria
import unittest
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.knowledge_models import Node

class TestGraphDatabase(unittest.TestCase):
    
    def setUp(self):
        self.graph_db = GraphDB("bolt://localhost:7687", "neo4j", "password")
        self.graph_db.connect()
    
    def tearDown(self):
        # Limpiar datos de prueba
        self.graph_db.execute_query(
            "MATCH (n {test: true}) DETACH DELETE n"
        )
        self.graph_db.close()
    
    def test_create_node(self):
        node = Node(
            label="TestNode",
            properties={"name": "Test", "test": True}
        )
        
        created_node = self.graph_db.create_node(node)
        self.assertIsNotNone(created_node)
    
    def test_query_execution(self):
        result = self.graph_db.execute_query("RETURN 1 as test")
        self.assertEqual(result[0]["test"], 1)

if __name__ == "__main__":
    unittest.main()
```

## 📊 Monitoreo

### Métricas Importantes

```python
# Obtener estadísticas del grafo
stats_query = """
MATCH (n)
WHERE n.account_id = $account_id
RETURN 
    count(n) as total_nodes,
    count(distinct labels(n)) as node_types,
    size(()-[]->()) as total_relationships
"""

stats = graph_db.execute_query(stats_query, {"account_id": "user123"})
print(f"Nodos: {stats[0]['total_nodes']}")
print(f"Tipos: {stats[0]['node_types']}")
print(f"Relaciones: {stats[0]['total_relationships']}")
```

### Health Check

```python
def health_check():
    """Verifica el estado del sistema de grafos."""
    try:
        graph_db = GraphDB(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        graph_db.connect()
        
        # Prueba básica
        result = graph_db.execute_query("RETURN 1 as health")
        
        graph_db.close()
        return result[0]["health"] == 1
    
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
```

## 🔍 Debugging

### Logging

```python
import logging

# Configurar logging para el módulo
logger = logging.getLogger('knowledge_graph')
logger.setLevel(logging.DEBUG)

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)
```

### Consultas de Diagnóstico

```cypher
-- Ver todos los nodos de un usuario
MATCH (n) 
WHERE n.account_id = "user123"
RETURN labels(n), count(n)

-- Ver relaciones más comunes
MATCH ()-[r]->()
RETURN type(r), count(r)
ORDER BY count(r) DESC

-- Ver nodos sin relaciones
MATCH (n)
WHERE NOT (n)--()
RETURN n
```

## 📚 Recursos Adicionales

### Documentación

- [Guía de Usuario](../docs/knowledge-graphs-user-guide.md)
- [Guía Técnica](../docs/knowledge-graphs-technical-guide.md)
- [Documentación de Integración](../docs/knowledge-graphs-integration.md)

### Enlaces Externos

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Cognee Documentation](https://docs.cognee.ai/)

---

**Versión**: 1.0  
**Última Actualización**: 2025-01-09  
**Mantenedor**: KognitoAI Development Team
