# Propuesta de Sofisticación del Agente Kognito AI

Esta propuesta detalla una evolución arquitectónica para el agente de Kognito AI, aprovechando las capacidades de **LangGraph** para implementar patrones de razonamiento avanzados, **RAG (Retrieval-Augmented Generation)** contextual y el uso profundo de **Grafos de Conocimiento**.

## 1. Objetivos

*   **Mejorar el Razonamiento**: Pasar de un bucle simple de ejecución a patrones cognitivos como *Plan-and-Solve*, *Reflection* y *Self-Correction*.
*   **Maximizar el Contexto RAG**: Implementar estrategias de recuperación activa y evaluación de relevancia (*Self-RAG*).
*   **Potenciar el Grafo de Conocimiento**: Utilizar el grafo no solo como base de datos, sino como herramienta de razonamiento y exploración activa.

## 2. Arquitectura Propuesta: "Cognitive Graph Agent"

Actualmente, el agente opera en un ciclo `Call Model -> Tool -> Call Model`. La propuesta transforma esto en un grafo de estados más rico con nodos especializados.

### 2.1. Nuevo Estado del Agente (`AgentState`)

El estado debe evolucionar para soportar planificación y crítica:

```python
class AgentState(TypedDict):
    messages: List[BaseMessage]
    account_id: str
    # ... (campos existentes)
    
    # Nuevos campos para razonamiento avanzado
    plan: Optional[List[str]]          # Lista de pasos planificados
    current_step: int                  # Paso actual del plan
    reasoning_trace: List[str]         # Traza de pensamientos/razonamientos intermedios
    critique: Optional[str]            # Crítica de la última generación
    retrieved_docs: List[Document]     # Documentos recuperados (para evaluación)
    graph_paths: List[Dict]            # Caminos del grafo explorados
```

### 2.2. Nodos Especializados

En lugar de un solo LLM que hace todo, dividimos la responsabilidad en nodos:

1.  **Planner Node (Planificador)**:
    *   **Función**: Analiza la solicitud compleja del usuario y la descompone en pasos lógicos.
    *   **Uso de Grafo**: Consulta el esquema del grafo para entender qué conceptos están disponibles antes de planificar.

2.  **Retriever Node (Recuperador Híbrido)**:
    *   **Función**: Ejecuta búsquedas tanto vectoriales como en el grafo.
    *   **Mejora**: Implementa *Query Expansion* usando el grafo para encontrar sinónimos o conceptos relacionados antes de buscar.

3.  **Graph Explorer Node (Explorador de Grafo)**:
    *   **Función**: Navega activamente por el grafo (saltos de 1-2 niveles) para encontrar conexiones no obvias entre entidades mencionadas en la consulta.
    *   **Salida**: "Reasoning Paths" (caminos explicativos) que conectan A con B.

4.  **Grader Node (Evaluador)**:
    *   **Función**: Evalúa la relevancia de los documentos/caminos recuperados.
    *   **Acción**: Si la información es irrelevante, solicita reescritura de la búsqueda (*Query Rewriting*).

5.  **Reasoner/Generator Node (Razonador)**:
    *   **Función**: Genera la respuesta final sintetizando la información validada.
    *   **Prompting**: Utiliza *Chain-of-Thought* (CoT) explícito inyectado en el prompt.

6.  **Reflector/Critic Node (Reflexión)**:
    *   **Función**: Revisa la respuesta generada antes de enviarla al usuario. Busca alucinaciones o falta de completitud.
    *   **Ciclo**: Si la crítica es negativa, devuelve el flujo al *Planner* o *Reasoner* para corregir.

## 3. Flujos de Trabajo (Workflows)

### A. Flujo de Investigación Profunda (Deep Research)
Ideal para preguntas complejas ("¿Cómo se relacionan X e Y en el contexto de Z?").

1.  **Start** -> **Planner**: Descompone la pregunta.
2.  **Planner** -> **Graph Explorer**: Busca conceptos clave y relaciones.
3.  **Graph Explorer** -> **Retriever**: Busca detalles específicos en documentos (chunks).
4.  **Retriever** -> **Grader**: ¿Es suficiente la información?
    *   *No*: -> **Query Rewriter** -> **Retriever** (Loop).
    *   *Sí*: -> **Reasoner**.
5.  **Reasoner** -> **Critic**: ¿La respuesta es sólida?
    *   *No*: -> **Reasoner** (con feedback).
    *   *Sí*: -> **End**.

### B. Flujo de Chat Rápido (Fast Chat)
Para interacciones simples, manteniendo la latencia baja.

1.  **Start** -> **Router**: Clasifica la intención (Simple vs Compleja).
2.  **Router (Simple)** -> **Simple LLM Call** -> **End**.
3.  **Router (Compleja)** -> **Deriva al Flujo A**.

## 4. Integración Técnica con Kognito AI

### 4.1. Mejoras en `knowledge_graph/`
*   **Graph Schema Injection**: Inyectar dinámicamente el esquema del grafo (tipos de nodos y relaciones) en el prompt del sistema para que el LLM "sepa lo que sabe".
*   **Algoritmos de Grafos**: Exponer algoritmos como *Shortest Path* o *Community Detection* como herramientas para el agente.

### 4.2. Mejoras en `core/agent.py`
*   Refactorizar `call_model_node` para que sea solo uno de los muchos nodos.
*   Implementar `conditional_edges` en LangGraph para manejar los bucles de corrección y planificación.

## 5. Beneficios Esperados

1.  **Menos Alucinaciones**: El paso de *Grader* y *Critic* filtra información incorrecta.
2.  **Respuestas Más Profundas**: El uso activo del grafo permite "unir puntos" que la búsqueda vectorial pierde.
3.  **Transparencia**: El usuario puede ver el "Plan" y los "Caminos del Grafo" usados para generar la respuesta.
4.  **Robustez**: El agente puede recuperarse de búsquedas fallidas reintentando con diferentes estrategias.

---
**Siguientes Pasos Sugeridos:**
1.  Crear una rama experimental.
2.  Implementar el `Planner Node` y el estado extendido.
3.  Probar el flujo de *Self-Correction* con preguntas difíciles.
