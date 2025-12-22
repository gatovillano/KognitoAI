# Documentación Técnica: Sistema de Grafo de Conocimiento (KG)

## 1. Introducción y Propósito
El Sistema de Grafo de Conocimiento (KG) es el "cerebro relacional" del proyecto. Su propósito es transformar datos no estructurados en una base de conocimientos estructurada y semántica. A diferencia de un sistema RAG (Retrieval-Augmented Generation) tradicional que solo busca fragmentos de texto, el KG permite:
- **Descubrir conexiones ocultas** entre documentos aparentemente inconexos.
- **Realizar razonamiento multihop**, permitiendo al agente responder preguntas que requieren conectar varios puntos de información.
- **Visualizar la estructura del conocimiento** para el usuario final.
- **Mantener una memoria persistente y relacional** de las interacciones y aprendizajes del sistema.

---

## 2. Arquitectura de Archivos y Conectividad

El sistema está distribuido en cuatro capas principales que interactúan entre sí:

### A. Capa de Procesamiento (`knowledge_graph/`)
Es el motor donde ocurre la "magia" de la extracción.
- **`hybrid_graph_processor.py`**: El procesador estándar. Utiliza modelos locales (spaCy/GLiNER) para extraer entidades y relaciones rápidamente. Se conecta con `embeddings.py` para la deduplicación semántica.
- **`conceptual_graph_processor.py`**: Utiliza LLMs para extraer conceptos de alto nivel y citas textuales, creando un grafo más "filosófico" y menos taxonómico.
- **`memory_graph_processor.py`**: Actúa como un puente entre la memoria episódica (conversaciones) y la memoria semántica (grafo).
- **`neo4j_adapter.py`**: La única vía de comunicación con la base de datos Neo4j. Traduce objetos Python a comandos Cypher.

### B. Capa de Orquestación y Utilidades (`utils/`)
Gestionan la lógica de negocio y el flujo de datos.
- **`knowledge_graph_service.py`**: El "Facade" o punto de entrada para la mayoría de las operaciones. Coordina la extracción, el análisis y la visualización.
- **`proactive_knowledge_linker.py`**: Un proceso inteligente que se ejecuta post-extracción para encontrar vínculos semánticos entre el nuevo contenido y el grafo existente.
- **`knowledge_graph_analysis.py`**: Maneja las tareas pesadas en segundo plano (Background Tasks) para no bloquear la API.

### C. Capa de Interfaz de Agente (`tools/`)
Permite que el Agente de IA "use" el grafo.
- **`knowledge_graph_tool.py`**: Herramienta de alto nivel que usa razonamiento basado en grafos para responder al usuario.
- **`graph_cypher_generator_tool.py`**: Permite al agente realizar consultas técnicas y precisas sobre la base de datos.

### D. Capa de API (`api/`)
Expone las funcionalidades al frontend (Next.js) y a clientes externos.
- **`api/knowledge_graph.py`**: Define los endpoints para obtener datos de visualización, estadísticas y disparar nuevos procesamientos.

---

## 3. Flujo del Proceso y de la Información

### Paso 1: Ingesta y Disparo
Cuando un usuario sube un documento o crea una nota, el sistema puede disparar el procesamiento del grafo de dos formas:
1. **Automática**: Configurada como parte del pipeline de ingesta.
2. **Manual**: A través del endpoint `/process-knowledge-graph-optimized`.

### Paso 2: Extracción (El Pipeline Híbrido)
1. **Limpieza**: El texto se normaliza.
2. **NER (Reconocimiento de Entidades)**: Se identifican personas, lugares, organizaciones y conceptos técnicos.
3. **Generación de Relaciones**: Se analizan las oraciones para encontrar verbos y conectores que unan las entidades (ej: "A" *desarrolló* "B").
4. **Embeddings**: Cada entidad se convierte en un vector numérico para comparar su significado con entidades ya existentes en el grafo.

### Paso 3: Persistencia en Neo4j
El `Neo4jAdapter` ejecuta una serie de comandos `MERGE`. Si una entidad ya existe (según su nombre y tipo), se actualiza; si no, se crea. Cada nodo se etiqueta con:
- `account_id`: Para multi-inquilino.
- `workspace_id`: Para organizar el conocimiento por proyectos.
- `source_id`: Para rastrear de qué documento proviene la información.

### Paso 4: Vinculación Proactiva
Una vez guardado, el `ProactiveKnowledgeLinker` analiza los nuevos nodos. Si detecta que un concepto en el Documento A es semánticamente muy cercano a un concepto en el Documento B, crea una relación de tipo `SEMANTICALLY_RELATED_TO`, uniendo islas de conocimiento.

### Paso 5: Consumo y Visualización
1. **Frontend**: Solicita datos a `/api/knowledge_graph/data`, recibe un JSON de nodos y aristas, y los renderiza usando `react-force-graph` o `vis.js`.
2. **Agente**: Durante un chat, si el usuario pregunta algo complejo, el agente llama a `knowledge_graph_tool`, que consulta el grafo y devuelve una respuesta enriquecida.

---

## 4. Importancia en el Proyecto

El Grafo de Conocimiento no es solo una base de datos adicional; es el componente que permite la **escalabilidad del entendimiento**. 
- **Contexto Infinito**: A diferencia de una ventana de contexto de LLM limitada, el grafo puede almacenar millones de relaciones y entregar solo las relevantes.
- **Transparencia**: El usuario puede ver *por qué* el sistema conectó dos ideas, explorando visualmente los nodos.
- **Inteligencia Proactiva**: Permite que el sistema le diga al usuario: "Oye, esto que acabas de escribir se relaciona con este otro proyecto en el que trabajaste hace tres meses".

---
*Documentación generada por KogniTerm - Asistente Experto en Terminal* 🚀