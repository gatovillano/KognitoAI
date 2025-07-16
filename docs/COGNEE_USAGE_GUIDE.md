# 🧠 Guía de Uso de Cognee en KognitoAI

## 📋 Índice
1. [¿Qué es Cognee?](#qué-es-cognee)
2. [Configuración Inicial](#configuración-inicial)
3. [Uso Básico](#uso-básico)
4. [Herramienta del Agente](#herramienta-del-agente)
5. [Ejemplos Prácticos](#ejemplos-prácticos)
6. [Visualización](#visualización)
7. [Solución de Problemas](#solución-de-problemas)

## 🤔 ¿Qué es Cognee?

Cognee es una biblioteca de Python que permite crear **grafos de conocimiento** automáticamente a partir de documentos de texto. En KognitoAI, Cognee:

- 📄 **Procesa documentos** y extrae entidades y relaciones
- 🔗 **Crea grafos de conocimiento** en Neo4j
- 🔍 **Permite búsquedas semánticas** avanzadas
- 💡 **Genera insights** y patrones de conocimiento
- 🧠 **Integra con LLMs** para análisis inteligente

## ⚙️ Configuración Inicial

### 1. Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```bash
# Neo4j (requerido para Cognee)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password_aqui

# Google API (ya configurado)
GOOGLE_API_KEY=tu_google_api_key
```

### 2. Iniciar Servicios

```bash
# Iniciar Neo4j
docker-compose up -d neo4j

# Iniciar el servicio core
docker-compose up -d core
```

### 3. Verificar Instalación

```bash
# Ejecutar script de prueba
python scripts/test_cognee.py
```

## 🚀 Uso Básico

### Desde Python

```python
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool

# Crear la herramienta
tool = CogneeKnowledgeGraphTool()

# Procesar documentos
result = await tool._arun(
    action="process_documents",
    account_id="usuario123",
    documents=[
        {
            "id": "doc1",
            "title": "Mi Documento",
            "content": "Contenido del documento...",
            "metadata": {"author": "Juan", "year": 2024}
        }
    ],
    dataset_name="mi_dataset"
)
```

### Desde el Agente de IA

Simplemente habla con tu agente:

```
"Procesa estos documentos y crea un grafo de conocimiento"
"Busca información sobre machine learning en mi grafo"
"¿Qué insights puedes obtener sobre inteligencia artificial?"
```

## 🛠️ Herramienta del Agente

La herramienta `cognee_knowledge_graph` tiene tres acciones principales:

### 1. **process_documents**
Procesa documentos y crea el grafo de conocimiento.

**Parámetros:**
- `documents`: Lista de documentos con `id`, `title`, `content`, `metadata`
- `dataset_name`: Nombre del dataset (opcional)
- `account_id`: ID de la cuenta del usuario

### 2. **search_graph**
Busca información específica en el grafo.

**Parámetros:**
- `query`: Consulta de búsqueda en lenguaje natural
- `dataset_name`: Nombre del dataset
- `account_id`: ID de la cuenta del usuario

### 3. **get_insights**
Obtiene insights y patrones del grafo.

**Parámetros:**
- `query`: Tema para obtener insights
- `dataset_name`: Nombre del dataset
- `account_id`: ID de la cuenta del usuario

## 📚 Ejemplos Prácticos

### Ejemplo 1: Documentos de Investigación

```python
# Ejecutar ejemplos completos
python examples/cognee_usage_examples.py
```

### Ejemplo 2: Documentos Empresariales

```python
documents = [
    {
        "id": "strategy_2024",
        "title": "Estrategia Digital 2024",
        "content": "Nuestra estrategia se enfoca en IA, automatización...",
        "metadata": {"department": "Strategy", "year": 2024}
    }
]

result = await tool._arun(
    action="process_documents",
    account_id="empresa_xyz",
    documents=documents,
    dataset_name="estrategia_empresarial"
)
```

### Ejemplo 3: Búsqueda Inteligente

```python
# Buscar información específica
result = await tool._arun(
    action="search_graph",
    account_id="empresa_xyz",
    query="¿Cuáles son nuestras iniciativas de IA?",
    dataset_name="estrategia_empresarial"
)
```

## 👁️ Visualización

### Neo4j Browser

1. Abre http://localhost:7474 en tu navegador
2. Conecta con:
   - **URI**: `bolt://localhost:7687`
   - **Usuario**: `neo4j`
   - **Contraseña**: tu password del .env

### Consultas Cypher Útiles

```cypher
// Ver todos los nodos
MATCH (n) RETURN n LIMIT 25

// Ver nodos por dataset
MATCH (n) WHERE n.dataset_name = "mi_dataset" RETURN n

// Ver relaciones
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10

// Buscar por contenido
MATCH (n) WHERE n.content CONTAINS "inteligencia artificial" RETURN n
```

## 🔧 Solución de Problemas

### Error: "Configuración de Neo4j incompleta"

**Solución:**
```bash
# Verifica tu archivo .env
cat .env | grep NEO4J

# Asegúrate de tener:
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password
```

### Error: "No se pudo conectar a Neo4j"

**Solución:**
```bash
# Verifica que Neo4j esté corriendo
docker ps | grep neo4j

# Si no está corriendo:
docker compose up -d neo4j

# Verifica los logs
docker logs kognito_neo4j
```

### Error: "GOOGLE_API_KEY no configurada"

**Solución:**
```bash
# Agrega tu API key de Google al .env
echo "GOOGLE_API_KEY=tu_api_key_aqui" >> .env
```

### Error: "Failed to import Cognee"

**Solución:**
```bash
# Instalar Cognee en el contenedor
docker exec -it kognito_core pip install cognee

# O reconstruir el contenedor
docker compose build core
```

## 💡 Consejos y Mejores Prácticas

### 1. **Organización de Datasets**
- Usa nombres descriptivos: `investigacion_ia`, `estrategia_2024`
- Separa por cuenta: automáticamente se agrega `_{account_id}`
- Agrupa documentos relacionados en el mismo dataset

### 2. **Estructura de Documentos**
```python
{
    "id": "identificador_único",
    "title": "Título descriptivo",
    "content": "Contenido principal del documento",
    "metadata": {
        "author": "Autor",
        "date": "2024-01-01",
        "category": "Categoría",
        "tags": ["tag1", "tag2"]
    }
}
```

### 3. **Consultas Efectivas**
- Usa lenguaje natural: "¿Qué dice sobre machine learning?"
- Sé específico: "Estrategias de IA para 2024"
- Combina conceptos: "Relación entre transformers y BERT"

### 4. **Monitoreo**
- Revisa los logs del contenedor core
- Usa Neo4j Browser para verificar el grafo
- Prueba consultas simples antes de las complejas

## 🔄 Integración con Otras Herramientas

Cognee se integra perfectamente con otras herramientas de KognitoAI:

- **📄 Documentos**: Procesa documentos existentes del sistema
- **🔍 Búsqueda**: Combina con herramientas de búsqueda web
- **💭 Memoria**: Complementa el sistema de memoria vectorial
- **📊 Análisis**: Enriquece análisis con grafos de conocimiento

## 📈 Próximos Pasos

1. **Experimenta** con tus propios documentos
2. **Integra** Cognee en tu flujo de trabajo
3. **Combina** con otras herramientas del sistema
4. **Visualiza** los grafos en Neo4j Browser
5. **Optimiza** las consultas según tus necesidades
