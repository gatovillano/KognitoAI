# Investigación Profunda: Arquitectura de Agentes, Sistema de Razonamiento y Memoria de KognitoAI

## Documento de Investigación Técnica

---

## 1. RESUMEN EJECUTIVO

KognitoAI implementa una arquitectura de agente híbrida que combina:
- **LangChain** como framework base (no LangGraph explícitamente en el módulo principal)
- **Memoria dual vectorial + grafo** (pgvector + Neo4j)
- **Razonamiento neuronal** sobre grafos de conocimiento con exploración latente
- **Gestión de memoria proactiva** con Write-Ahead Logging inspirado en el patrón Hal Stack
- **Protocolo MCP** (Model Context Protocol) como estándar emergente para conectividad

El sistema se distingue por su manejo manual del ciclo de memoria (carga → procesamiento → guardado), abandonando las clases de memoria de LangChain para obtener control total sobre el contexto.

---

## 2. ARQUITECTURA DE AGENTES

### 2.1 Agente Principal (`core/agent.py` - 4074 líneas)

El archivo `agent.py` constituye el núcleo del sistema. Su arquitectura se basa en los siguientes principios:

#### Manejo Manual de Memoria
A diferencia de los enfoques convencionales que usan `ConversationBufferMemory` o similares de LangChain, KognitoAI implementa un **ciclo explícito de memoria**:
1. Cargar historial de conversación desde PostgreSQL (`PostgresChatMessageHistory`)
2. Procesar el contexto del usuario
3. Guardar el historial actualizado
4. Limpiar mensajes antiguos según políticas de retención

Este enfoque manual permite control granular sobre qué contexto se inyecta en cada llamada al LLM, evitando la degradación de rendimiento por ventanas de contexto excesivas.

#### Prompt Dinámico Centralizado
Un único `SystemMessage` integra:
- Perfil del usuario (datos estructurados)
- Memorias relevantes recuperadas del sistema vectorial
- Prompt de personalidad del asistente
- Instrucciones de herramientas disponibles

La inyección de IDs (`account_id`, `telegram_id`) se realiza directamente en el `AgentExecutor` vía configuración, permitiendo aislamiento multi-tenant.

#### Inicialización de LLMs
El método `initialize_llms()` configura:
- **LiteLLM** para abstracción multi-proveedor
- **Semáforos** para paralelismo de herramientas (prevención de rate limiting)
- **Detección de modelos multimodales** (`is_multimodal_model()`) para Gemini, GPT-4o, Claude-3, Qwen-VL

#### Gestión de Hilos (Threads)
El sistema implementa un modelo de hilos persistentes por cuenta:
- `create_thread_for_account()` - Crea hilos dedicados
- `get_or_create_heartbeat_thread()` - Hilo de mantenimiento autónomo
- `force_update_thread_title()` / `force_update_all_thread_titles()` - Actualización dinámica de títulos
- Semáforos de concurrencia para operaciones paralelas seguras

#### Sistema de Skills
Resolución explícita por tags con mapeo flexible de nombres. Las skills se cargan dinámicamente y se resuelven al momento de la ejecución del agente.

### 2.2 Nodos de Razonamiento (`core/agents/`)

#### DeepResearcher
Un agente especializado en investigación profunda que:
- Lee archivos del proyecto
- Busca contexto relevante en la base de datos vectorial
- Realiza búsquedas web complementarias
- Sintetiza hallazgos en respuestas estructuradas

#### GapDeveloper
Agente especializado en identificar y desarrollar gaps funcionales en el sistema, utilizando análisis de código y comparación con patrones establecidos.

---

## 3. SISTEMA DE MEMORIA

### 3.1 Arquitectura Dual: Vectorial + Grafo

KognitoAI implementa una arquitectura de memoria de dos capas complementarias:

#### Capa 1: Memoria Vectorial (pgvector)
**Ubicación:** `core/memory_manager.py` (2630 líneas)

- **Almacenamiento:** PostgreSQL con extensión `pgvector` para embeddings
- **Modelo de embeddings:** OllamaEmbeddings (modelos locales)
- **Chunking:** `RecursiveCharacterTextSplitter` con parámetros configurables
- **Búsqueda semántica:** Distancia L2 (coseno) con umbral de similitud configurable
- **Filtrado multi-dimensional:**
  - Por `account_id` (aislamiento multi-tenant)
  - Por `workspace_id` (aislamiento de espacios de trabajo)
  - Por `content_type` (user_memories, user_documents, user_notes)
  - Por `topic` y `category`
  - Por `document_ids` explícitos

**Funciones clave:**
- `get_relevant_memories()` - Recuperación semántica con re-ranking
- `add_memory_to_vector_db()` - Ingesta de nuevos fragmentos
- `_run_semantic_search()` - Búsqueda vectorial optimizada con reuso de sesión

#### Capa 2: Grafo de Conocimiento (Neo4j)
**Ubicación:** `knowledge_graph/`

- **Base de datos:** Neo4j (graph database)
- **Conexión:** `GraphDB` - Singleton con reconnect automático y retry logic
- **Schema:** Refrescado dinámicamente con caché interna
- **Operaciones:** Consultas Cypher asíncronas con serialización de tipos Neo4j

**Estructura del Grafo:**
- **Nodos:** Entidades con propiedades `name`, `description`, `dataset_name`, `account_id`, `type`
- **Relaciones:** Tipos como `RELATED_TO`, `MENTIONS`, `HAS_PART` con propiedades `weight`, `trust_score`, `is_current`
- **Filtrado:** Por `account_id`, `workspace_id`, `dataset_name`, `trust_score` mínimo

### 3.2 EnhancedMemoryManager
**Ubicación:** `core/enhanced_memory_manager.py`

Integra ambas capas (vectorial + grafo) para proporcionar contexto enriquecido:

1. **Contexto tradicional** (embeddings): Recuperación semántica estándar
2. **Contexto del grafo:**
   - Búsqueda en grafo de memorias del agente (dataset: "Agent Memories")
   - Búsqueda en grafo de documentos (dataset: workspace-specific)
3. **Combinación:** Fusión de contextos con priorización de relevancia

**Optimización:** Desactivación automática de búsqueda en grafo para consultas >100 palabras (evita latencia en respuestas de herramientas extensas).

### 3.3 Memoria Proactiva (WAL Protocol)

Aunque no implementado explícitamente como un módulo separado en el código actual, el sistema de KognitoAI incorpora principios del **Write-Ahead Logging (WAL)**:

- **Persistencia inmediata:** Los insights del grafo se guardan como `AnalysisTask` en PostgreSQL de forma asíncrona (no bloqueante)
- **Título contextualizado:** Los análisis se titulan automáticamente basándose en los conceptos encontrados
- **Metadatos ricos:** Cada insight incluye `result_payload` con resumen, data neuronal, query del usuario, conceptos y diagrama Mermaid

---

## 4. SISTEMA DE RAZONAMIENTO

### 4.1 GraphReasoningNode
**Ubicación:** `knowledge_graph/graph_reasoning_node.py`

El nodo de razonamiento sobre grafo implementa el concepto de **"Pensamiento Neuronal"** (Neural Thinking):

#### Flujo de Razonamiento:
1. **Extracción de conceptos clave:**
   - Heurística de frecuencia de palabras (0ms) con stopwords personalizadas
   - Fallback a LLM para extracción semántica si la heurística no produce ≥2 conceptos
   - Filtro de stopwords en español (más de 50 términos)

2. **Búsqueda en paralelo en Neo4j:**
   - **Búsqueda de camino más corto** entre los dos primeros conceptos (`shortestPath` con profundidad 1-4)
   - **Expansión de vecindario** para cada concepto (profundidad 1-2)
   - Todo ejecutado en paralelo con `asyncio.gather()`

3. **Ranking de relevancia:**
   - Puntuación por superposición de conceptos en los caminos encontrados
   - Selección de los top 15 resultados

4. **Síntesis neuronal (en segundo plano):**
   - Prompt que pide al LLM analizar las relaciones encontradas
   - Ejecución asíncrona no bloqueante (`asyncio.create_task()`)
   - Persistencia como `AnalysisTask` si cumple filtros de relevancia

5. **Generación de diagrama Mermaid:**
   - Visualización automática del subgrafo resultante

#### Características de Seguridad:
- Filtro de workspace_id para aislamiento multi-tenant
- Filtro de trust_score mínimo (default: 0.5)
- Exclusión de queries de heartbeat/ping/status del análisis persistente
- Longitud mínima de query (≥15 caracteres) para persistencia

### 4.2 GraphDatabase
**Ubicación:** `knowledge_graph/graph_database.py`

- **Patrón Singleton:** Una única instancia por proceso
- **Reconexión automática:** Retry logic con 3 intentos y backoff exponencial
- **Serialización de tipos Neo4j:** Conversión de `DateTime`, `Date`, `Time`, `Duration`, `Node`, `Relationship`, `Path` a tipos Python estándar
- **Schema caching:** Refresco bajo demanda con invalidación en error

---

## 5. ANÁLISIS COMPARATIVO CON EL SECTOR

### 5.1 Framework: LangChain vs LangGraph

| Aspecto | Enfoque KognitoAI | LangGraph (estándar) |
|---------|-------------------|---------------------|
| **Gestión de memoria** | Manual explícito (ciclo carga-procesamiento-guardado) | Clases de memoria abstractas (ConversationBufferMemory, etc.) |
| **Control de contexto** | Total: prompt dinámico centralizado con inyección de IDs | Parcial: depende de la configuración del memory object |
| **Flexibilidad** | Alta: abandono de abstracciones de LangChain para control total | Media-alta: abstracciones simplifican pero limitan |
| **Complejidad** | Mayor: requiere implementar manualmente el ciclo de memoria | Menor: las clases de memoria manejan el ciclo automáticamente |

**Análisis:** KognitoAI sacrifica la conveniencia de LangChain a cambio de control total. Esta decisión es consistente con la filosofía de Anthropic (ver sección 5.3): "start by using LLM APIs directly" y solo aumentar complejidad cuando sea necesario.

### 5.2 Memoria Vectorial vs Grafo: El Debate Actual

El sector debate activamente entre:
- **Enfoques vectoriales puros (RAG tradicional):** Simples, escalables, pero sin comprensión relacional
- **Enfoques de grafo (Knowledge Graph RAG):** Ricos en relaciones, pero más complejos de mantener
- **Enfoques híbridos (como KognitoAI):** Combinan lo mejor de ambos mundos

**Posición de KognitoAI:** El sistema `EnhancedMemoryManager` representa un enfoque híbrido maduro que:
1. Usa embeddings vectoriales para búsqueda semántica rápida
2. Usa el grafo para descubrir relaciones latentes entre conceptos
3. Combina ambos contextos con un pipeline de enriquecimiento

**Debate actual del sector:**
- **A favor del grafo:** Los grafos capturan relaciones estructuradas que los embeddings no pueden (ej: "empresa X adquirió empresa Y" vs similitud semántica)
- **A favor de vectors:** Los embeddings son más flexibles y manejan mejor la ambigüedad y la variación lingüística
- **Síntesis:** Los sistemas más exitosos (como KognitoAI) usan ambos, delegando al grafo el descubrimiento de relaciones y a vectors la recuperación por similitud

### 5.3 Arquitecturas de Agentes: El Debate Actual

Basándose en la investigación de Anthropic ("Building Effective Agents", diciembre 2024) y el paper CodeAct (ICML 2024):

#### Principales Patrones de Agentes:

| Patrón | Descripción | Uso en KognitoAI |
|--------|-------------|------------------|
| **Prompt Chaining** | Secuencia de LLM calls con salida de una alimentando la siguiente | Parcialmente en el flujo de investigación del grafo |
| **Routing** | Clasificación de input y delegación a handlers especializados | Skills-based routing (plan-creation, web-tools, etc.) |
| **Parallelization** | Ejecución simultánea de subtareas | `asyncio.gather()` en GraphReasoningNode para queries paralelas |
| **Orchestrator-Workers** | LLM central descompone tareas y delega | DeepResearcher como orquestador de investigación |
| **Evaluator-Optimizer** | Un LLM genera, otro evalúa en loop | No implementado explícitamente en el código actual |

#### El Debate: Simplicidad vs Complejidad

**Anthropic (2024):** "Success in the LLM space isn't about building the most sophisticated system. It's about building the *right* system for your needs."

**KognitoAI** adopta una postura intermedia:
- Usa componentes sofisticados (grafo, embeddings, razonamiento neuronal) cuando aportan valor demostrable
- Mantiene la simplicidad en el agente principal (manejo manual de memoria, sin frameworks de agentes complejos)
- Sigue el principio de **Complejidad Solo Cuando Es Necesaria**

### 5.4 Model Context Protocol (MCP)

Anunciado por Anthropic (noviembre 2024), MCP es un estándar abierto para conectar AI assistants a fuentes de datos:

**Relevancia para KognitoAI:**
- MCP podría reemplazar o complementar el sistema actual de integración de herramientas
- Proporciona un protocolo universal en lugar de integraciones custom por cada fuente de datos
- Los servidores MCP pre-construidos (Google Drive, Slack, GitHub, Postgres, Puppeteer) podrían integrarse directamente

**Estado actual en KognitoAI:** No hay implementación explícita de MCP, pero la arquitectura de skills y herramientas es conceptualmente compatible con el modelo MCP.

### 5.5 CodeAct: Acciones de Código Ejecutable

El paper "Executable Code Actions Elicit Better LLM Agents" (ICML 2024, arXiv:2402.01030) propone consolidar acciones de agentes en código Python ejecutable:

**Resultados clave:**
- CodeAct supera alternativas establecidas en hasta un 20% en tasa de éxito
- Permite revisión dinámica de acciones previas
- Facilita la auto-depuración del agente

**Relevancia para KognitoAI:**
- El uso de `python_executor` (kernel Jupyter) ya permite ejecución de código
- La integración de CodeAct como paradigma de herramientas podría mejorar significativamente las capacidades del sistema
- El enfoque de acciones como código es complementario al sistema actual de herramientas basadas en JSON

---

## 6. SISTEMA DE HEARTBEAT Y MONITOREO

### 6.1 Heartbeat Autónomo

El sistema implementa un **heartbeat proactivo** inspirado en el patrón Hal Stack:

- **Hilo dedicado:** `platform='heartbeat'` con `get_or_create_heartbeat_thread()`
- **Mantenimiento automático:** Actualización de títulos de hilos, verificación de salud del sistema
- **Persistencia de estado:** Los resultados del heartbeat se guardan como `AnalysisTask` en PostgreSQL

### 6.2 Sistema de Alertas

El `GraphReasoningNode` implementa alertas contextuales:
- Log de conceptos clave identificados
- Alertas de "no se encontraron conexiones relevantes"
- Tracking de análisis neuronales guardados

---

## 7. ARQUITECTURA TÉCNICA DETALLADA

### 7.1 Flujo de una Petición del Usuario

```
Usuario envía mensaje
    │
    ▼
1. PostgresChatMessageHistory - Cargar historial
    │
    ▼
2. Sistema de Memoria - get_relevant_memories()
    ├── Búsqueda vectorial en pgvector
    └── Búsqueda en grafo (si aplica)
    │
    ▼
3. GraphReasoningNode - Pensamiento Neuronal
    ├── Extracción de conceptos clave
    ├── Queries Cypher paralelas a Neo4j
    ├── Ranking de resultados
    └── Síntesis neuronal (background task)
    │
    ▼
4. Prompt Dinámico Centralizado
    ├── SystemMessage con perfil + memorias + personalidad + herramientas
    └── Inyección de account_id y telegram_id
    │
    ▼
5. AgentExecutor (LangChain)
    ├── LiteLLM con semáforos
    ├── Ejecución de herramientas
    └── PostgresChatMessageHistory - Guardar historial
    │
    ▼
6. Respuesta al Usuario
```

### 7.2 Componentes Clave y Sus Responsabilidades

| Componente | Responsabilidad | Archivo |
|-----------|----------------|---------|
| `agent.py` | Orquestación principal del agente | `/core/agent.py` |
| `memory_manager.py` | Memoria vectorial (pgvector) | `/core/memory_manager.py` |
| `enhanced_memory_manager.py` | Fusión vectorial + grafo | `/core/enhanced_memory_manager.py` |
| `graph_reasoning_node.py` | Razonamiento sobre Neo4j | `/knowledge_graph/graph_reasoning_node.py` |
| `graph_database.py` | Conexión y operaciones Neo4j | `/knowledge_graph/graph_database.py` |
| `llm_manager.py` | Gestión de modelos LLM | `/core/llm_manager.py` |
| `citation_models.py` | Modelos de fuentes y citas | `/core/citation_models.py` |
| `reranker.py` | Re-ranking de resultados | `/core/reranker.py` |

---

## 8. DEBATES ACTUALES DEL SECTOR Y POSICIÓN DE KOGNITOAI

### 8.1 Memoria a Largo Plazo: Vectorial vs Grafo vs Híbrida

**Debate:** ¿Es mejor almacenar memoria como embeddings vectoriales o como relaciones de grafo?

**Posición KognitoAI:** Híbrida. El `EnhancedMemoryManager` demuestra que ambos enfoques son complementarios:
- Vectors para búsqueda por similitud semántica (rápida, flexible)
- Grafo para descubrimiento de relaciones estructurales (profunda, contextual)

### 8.2 RAG vs KG-RAG

**Debate:** ¿Es suficiente RAG tradicional o se necesita Knowledge Graph RAG?

**Posición KognitoAI:** KG-RAG añade valor significativo para dominios con relaciones complejas. El sistema de "Pensamiento Neuronal" demuestra que la exploración de relaciones latentes produce insights que la búsqueda vectorial pura no puede encontrar.

### 8.3 Agentes Autónomos vs Workflows Predefinidos

**Debate:** ¿Deben los agentes tener control total o seguir flujos predefinidos?

**Posición KognitoAI:** Modelo mixto. El agente principal sigue un flujo relativamente estructurado (carga de memoria → procesamiento → guardado), pero delega tareas complejas a agentes especializados (DeepResearcher) con mayor autonomía.

### 8.4 Frameworks de Agentes: Necesidad vs Complejidad

**Debate:** ¿Son necesarios frameworks como LangGraph, CrewAI, AutoGen?

**Posición KognitoAI:** Coherente con Anthropic: los frameworks pueden ser útiles para empezar, pero KognitoAI ha optado por construir sobre LangChain con implementaciones custom que priorizan control y transparencia sobre abstracción.

### 8.5 El Futuro: MCP y Estándares Abiertos

**Debate:** ¿Hacia dónde va la integración de herramientas y datos?

**Posición KognitoAI:** La arquitectura actual de skills y herramientas está alineada con la dirección del MCP. La adopción de MCP proporcionaría:
- Estandarización de la conectividad con fuentes de datos
- Reducción de código de integración custom
- Acceso a un ecosistema creciente de conectores pre-construidos

---

## 9. CONCLUSIONES Y RECOMENDACIONES

### Fortalezas de la Arquitectura KognitoAI:
1. **Control total sobre memoria:** El manejo manual del ciclo de memoria evita las limitaciones de los abstractions de LangChain
2. **Arquitectura híbrida madura:** La combinación vectorial + grafo es técnicamente sofisticada y bien implementada
3. **Razonamiento neuronal:** La exploración latente de relaciones en el grafo produce insights únicos
4. **Multi-tenant robusto:** Aislamiento por account_id y workspace_id en todos los niveles
5. **Rendimiento optimizado:** Paralelismo en queries Cypher, semáforos para LLM, ejecución asíncrona no bloqueante

### Áreas de Mejora Potencial:
1. **Adopción de MCP:** Integrar el Model Context Protocol para estandarizar conectividad
2. **Evaluator-Optimizer:** Implementar un ciclo de retroalimentación para mejorar respuestas iterativamente
3. **CodeAct:** Adoptar el paradigma de acciones como código ejecutable para herramientas más flexibles
4. **Compresión de contexto:** Implementar compresión automática de historial para ventanas de contexto largas
5. **Memoria episódica explícita:** Añadir un sistema dedicado de memoria episódica (eventos, interacciones) separado de la memoria semántica

### Recomendaciones de Investigación Futura:
- Evaluar la integración de MCP como reemplazo del sistema custom de skills
- Experimentar con CodeAct para herramientas que requieran composición de múltiples operaciones
- Implementar el patrón Evaluator-Optimizer para tareas de alta complejidad
- Explorar técnicas de compresión de contexto basadas en LLM para gestión de ventanas largas

---

## REFERENCIAS

1. Anthropic. "Building Effective Agents." (diciembre 2024). https://www.anthropic.com/engineering/building-effective-agents
2. Anthropic. "Introducing the Model Context Protocol." (noviembre 2024). https://www.anthropic.com/news/model-context-protocol
3. Wang, X. et al. "Executable Code Actions Elicit Better LLM Agents." ICML 2024. arXiv:2402.01030. https://arxiv.org/abs/2402.01030
4. KognitoAI Codebase. `/core/agent.py`, `/core/memory_manager.py`, `/knowledge_graph/graph_reasoning_node.py`, `/knowledge_graph/graph_database.py`
5. Hal Labs. "Proactive Agent v3.0.0." Part of the Hal Stack. https://github.com/halthelobster/proactive-agent
6. Model Context Protocol. https://modelcontextprotocol.io

---

*Documento generado como parte de la investigación de arquitectura de agentes de KognitoAI.*
*Fecha: 2026*
