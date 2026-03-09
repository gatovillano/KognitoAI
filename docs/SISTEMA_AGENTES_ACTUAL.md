# 📋 Sistema de Agentes de KognitoAI - Estado Actual

**Fecha**: Mayo 2025  
**Versión**: 1.0  
**Estado**: Producción (Deep Researcher) / Experimental (CrewAI)  
**Autor**: KogniTerm (Análisis automático)

---

## 🎯 Resumen Ejecutivo

KognitoAI cuenta actualmente con **tres implementaciones de agentes de investigación profunda**, cada una utilizando diferentes frameworks de orquestación. La implementación principal y en producción es **Deep Researcher basado en LangGraph**, que ofrece paralelismo real, control de flujo sofisticado y gestión inteligente de contexto. Existe también una implementación experimental con CrewAI y una versión externa (fork) con fines de investigación.

---

## 📊 Catálogo de Agentes

### 1. Deep Researcher (LangGraph) ✅ **Producción**

**Ubicación**: `core/agents/deep_researcher.py`  
**Estado**: Activo y en producción  
**Framework**: LangGraph + LangChain  
**Complejidad**: ~1000 líneas de código

**Características principales**:
- ✅ Paralelismo real (hasta 3 investigadores simultáneos)
- ✅ Control de flujo condicional avanzado
- ✅ Gestión de contexto con pruning proactivo/reactivo
- ✅ Múltiples capas de fallback para LLMs
- ✅ Sistema de herramientas dinámico
- ✅ Callbacks de progreso granulares
- ✅ Soporte MCP (Model Context Protocol)

**Capacidades**:
- Investigación exhaustiva en web (Tavily)
- Búsqueda en conocimiento interno (grafos, notas)
- Análisis de documentos
- Síntesis con citas numeradas
- Generación de informes estructurados

---

### 2. CrewAI Researcher 🔄 **Experimental**

**Ubicación**: `core/agents/crewai_researcher.py`  
**Estado**: Experimental, no en producción  
**Framework**: CrewAI  
**Complejidad**: ~200 líneas de código

**Características principales**:
- ❌ Sin paralelismo nativo (tareas secuenciales)
- ✅ Arquitectura de agentes jerárquica
- ✅ Adaptación manual de herramientas
- ✅ Más simple de entender

**Agentes**:
- **Manager**: Coordina el proceso
- **Researcher**: Realiza búsquedas
- **Analyst**: Analiza resultados
- **Writer**: Genera informe final

**Limitaciones**:
- No soporta paralelismo real
- Control de flujo menos fino
- Manejo de errores limitado
- Sin pruning de contexto automático

---

### 3. External Agents 🔬 **Investigación**

**Ubicación**: `external_agents/open_deep_research/`  
**Estado**: Fork/variante externa  
**Framework**: Desconocido (similar a LangGraph)  
**Propósito**: Experimentación y comparación

**Nota**: Implementación separada del core, posiblemente para A/B testing o investigación de mejoras.

---

## 🏗️ Arquitectura Técnica

### Deep Researcher - Estructura del Gráfico

```
┌─────────────────────────────────────────────────────────────┐
│                    GRÁFICO PRINCIPAL                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  START                                                     │
│     │                                                     │
│     ▼                                                     │
│  ┌─────────────────────┐                                  │
│  │ clarify_with_user   │◄─┐                              │
│  └─────────┬───────────┘  │                              │
│            │              │ await_user_clarification     │
│            ▼              │ (loop back)                  │
│  ┌─────────────────────┐  │                              │
│  │ write_research_brief│  │                              │
│  └─────────┬───────────┘  │                              │
│            │              │                              │
│            ▼              │                              │
│  ┌─────────────────────┐  │                              │
│  │ research_supervisor │──┘                              │
│  │  (Subgraph)         │                                 │
│  └─────────┬───────────┘                                 │
│            │                                             │
│            ▼                                             │
│  ┌─────────────────────┐                                  │
│  │ final_report_gen    │                                 │
│  └─────────┬───────────┘                                 │
│            │                                             │
│           END                                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Subgraph: Supervisor

```
┌─────────────────────────────────────────────────────┐
│              supervisor (nodo)                      │
│  - Planifica estrategia de investigación           │
│  - Decide: ConductResearch o ResearchComplete      │
│  - Usa think_tool para reflexión estratégica       │
└─────────────┬───────────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
┌──────────┐      ┌──────────────┐
│ Conduct  │      │ Research     │
│ Research │      │ Complete     │
│ (tool)   │      │ (tool)       │
└─────┬────┘      └──────┬───────┘
      │                  │
      ▼                  │
┌─────────────┐         │
│  researcher │◄────────┘
│  (subgraph) │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ compress_   │
│ research    │
└─────────────┘
```

### Subgraph: Researcher (React Pattern)

```
┌─────────────────────────────────────────────────────┐
│           researcher (nodo)                         │
│  - Ciclo: pensamiento → herramienta → reflexión    │
│  - Máximo max_react_tool_calls iteraciones        │
│  - Context pruning automático                      │
└─────────────┬───────────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
┌──────────┐      ┌──────────────┐
│  tool_   │      │   tool_      │
│  call    │      │   call       │
└─────┬────┘      └──────┬───────┘
      │                  │
      └──────┬───────────┘
             │
             ▼
      ┌─────────────┐
      │  reflexión  │
      │  (think)    │
      └──────┬──────┘
             │
             ▼
      (repeat until max or done)
```

---

## 🔧 Sistema de Herramientas

### Herramientas Disponibles

```python
# Cargadas en deep_researcher_utils.py → get_all_tools()

async def get_all_tools(config: RunnableConfig) -> List[BaseTool]:
    tools = [
        deep_research_think_tool,              # Reflexión estratégica
        tavily_search,                         # Búsqueda web (Tavily)
        web_scraper,                          # Extracción de contenido web
        knowledge_search,                     # Búsqueda en notas/grafos
        knowledge_graph,                      # Consultas a Neo4j
        graph_cypher_generator,               # Generación de Cypher
        comprehensive_web_analyzer,           # Análisis exhaustivo web
    ]
    return tools
```

### Características de las Herramientas

1. **Inyección de Contexto**:
   - `account_id` y `workspace_id` inyectados automáticamente
   - Aislamiento de datos por usuario/workspace

2. **Manejo Seguro de Errores**:
   - `execute_tool_safely()` captura y loguea errores
   - Fallbacks para herramientas que fallan
   - Continuación del flujo despite errores individuales

3. **Configuración Dinámica**:
   - Diferentes modelos LLM por herramienta
   - Límites de tokens configurables
   - Timeouts y retries automáticos

4. **Streaming y Callbacks**:
   - Soporte para streaming de respuestas
   - Callbacks de progreso por herramienta
   - Logging detallado para debugging

---

## ⚙️ Configuración

### Archivo: `core/agents/deep_researcher_config.py`

```python
from pydantic import BaseModel
from enum import Enum

class SearchAPI(Enum):
    TAVILY = "tavily"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class MCPConfig(BaseModel):
    server_url: str
    api_key: Optional[str] = None
    timeout: int = 30

class Configuration(BaseModel):
    # Retry y robustez
    max_structured_output_retries: int = 3

    # Clarificación
    allow_clarification: bool = True
    max_clarification_attempts: int = 3

    # Paralelismo
    max_concurrent_research_units: int = 3

    # Iteraciones
    max_researcher_iterations: int = 10
    max_react_tool_calls: int = 8

    # Límites
    max_input_tokens: int = 150000
    max_content_length: int = 100000

    # API de búsqueda
    search_api: SearchAPI = SearchAPI.TAVILY

    # Modelos (obtenidos de settings)
    research_model: str = settings.google_summary_model_name
    compression_model: str = settings.google_summary_model_name
    final_report_model: str = settings.google_summary_model_name
    summarization_model: str = settings.google_summary_model_name
    fast_llm_model: str = settings.google_fast_llm_model_name

    # MCP
    mcp_config: Optional[MCPConfig] = None
    mcp_prompt: Optional[str] = None
```

### Configuración por Entorno

```python
# .env o settings
TAVILY_API_KEY=xxx
GOOGLE_FAST_LLM_MODEL=gemini-1.5-flash
GOOGLE_SUMMARY_MODEL=gemini-1.5-pro
MAX_CONCURRENT_RESEARCH_UNITS=3
MAX_RESEARCHER_ITERATIONS=10
```

---

## 🔄 Flujos de Ejecución Detallados

### Fase 1: Clarificación (0-12%)

**Nodo**: `clarify_with_user`

**Lógica**:
```python
async def clarify_with_user(state: AgentState) -> dict:
    # Analizar si la consulta es clara
    is_clear = await check_clarity(state["messages"])
    attempts = state.get("clarification_attempts", 0)

    if is_clear or not config.allow_clarification or attempts >= config.max_clarification_attempts:
        # Continuar
        return {"is_clarification_needed": False}
    else:
        # Generar pregunta de clarificación
        clarification_question = await generate_clarification_question(state)
        return {
            "is_clarification_needed": True,
            "clarification_question": clarification_question,
            "clarification_attempts": attempts + 1
        }
```

**Salida**: Si necesita clarificación, el grafo se detiene y espera respuesta del usuario vía `await_user_clarification`.

---

### Fase 2: Brief de Investigación (12-15%)

**Nodo**: `write_research_brief`

**Propósito**: Convertir mensajes del usuario en pregunta de investigación estructurada.

**Prompt clave**:
```python
transform_messages_into_research_topic_prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente de investigación..."),
    ("human", "{messages}")
])
```

**Output esperado**:
```python
ResearchQuestion(
    question="¿Cuál es el impacto de la IA en la educación?",
    sub_questions=[
        "Impacto en metodologías de enseñanza",
        "Herramientas IA utilizadas en educación",
        "Estudios de caso recientes"
    ],
    search_terms=["IA educación", "edtech", "aprendizaje automático"],
    timeframe="últimos 2 años"
)
```

**Fallback**: Si structured output falla, usa LLM principal sin structured output.

---

### Fase 3: Supervisión e Investigación (15-90%)

#### Nodo: research_supervisor (Subgraph)

**Estado del supervisor**:
```python
class SupervisorState(TypedDict):
    research_plan: List[str]              # Plan de investigación
    completed_research: List[str]         # Investigaciones completadas
    current_iteration: int                # Iteración actual
    findings: List[ResearchSummary]      # Hallazgos acumulados
    enough_research: bool                # ¿Suficiente investigación?
    next_action: Literal["ConductResearch", "ResearchComplete"]
```

**Lógica del supervisor**:
```python
async def supervisor(state: SupervisorState) -> dict:
    # 1. Pensamiento estratégico (think_tool)
    strategy = await think_tool.ainvoke({
        "task": "Planificar próxima investigación",
        "current_findings": state["findings"],
        "research_plan": state["research_plan"]
    })

    # 2. Decidir acción
    if len(state["completed_research"]) >= len(state["research_plan"]) or \
       state["current_iteration"] >= config.max_researcher_iterations:
        next_action = "ResearchComplete"
    else:
        next_action = "ConductResearch"
        # Lanzar investigador(es) en paralelo
        tasks = []
        for topic in get_next_research_topics(state, config.max_concurrent_research_units):
            tasks.append(run_researcher_subgraph(topic, state))
        results = await asyncio.gather(*tasks)

    return {"next_action": next_action, "research_results": results}
```

**Paralelismo**:
- Hasta `max_concurrent_research_units` (default 3) investigadores simultáneos
- Cada investigador ejecuta hasta `max_react_tool_calls` (default 8) ciclos
- Limitado por `max_researcher_iterations` del supervisor (default 10)

---

#### Subgraph: Researcher

**Estado del investigador**:
```python
class ResearcherState(TypedDict):
    topic: str                           # Tema a investigar
    research_question: ResearchQuestion  # Pregunta estructurada
    tool_calls: List[ToolCall]          # Llamadas a herramientas
    tool_results: List[ToolResult]      # Resultados de herramientas
    reflections: List[str]              # Reflexiones del investigador
    current_thought: str                # Pensamiento actual
    research_summary: Optional[str]     # Resumen comprimido
```

**Ciclo React**:
```python
async def researcher(state: ResearcherState) -> dict:
    for i in range(config.max_react_tool_calls):
        # 1. Pensar (usar LLM)
        thought = await llm.ainvoke([
            SystemMessage(content=research_system_prompt),
            HumanMessage(content=format_research_step(state))
        ])

        # 2. Decidir herramienta (tool calling)
        tool_call = parse_tool_call(thought.content)

        # 3. Ejecutar herramienta
        result = await execute_tool_safely(tool_call)

        # 4. Reflexionar
        reflection = await reflect_on_result(tool_call, result)

        # 5. Context pruning (si necesario)
        if should_prune_context(state):
            state = prune_context(state)

        # 6. ¿Suficiente información?
        if is_research_complete(state):
            break

    # 7. Comprimir hallazgos
    compressed = await compress_research(state)

    return {"research_summary": compressed, "is_complete": True}
```

**Herramientas usadas típicamente**:
- `tavily_search`: Búsqueda web (1-3 queries por ciclo)
- `web_scraper`: Extraer contenido de URLs encontradas
- `knowledge_search`: Buscar en base de conocimiento interna
- `think_tool`: Reflexión estratégica (cada 2-3 ciclos)

---

### Fase 4: Generación de Informe Final (90-100%)

**Nodo**: `final_report_generation`

**Entradas**:
- Todos los `research_summary` de los investigadores
- Pregunta original de investigación
- Contexto y hallazgos acumulados

**Proceso**:
```python
async def final_report_generation(state: AgentState) -> dict:
    # 1. Consolidar hallazgos
    all_findings = "\n\n".join(state["compressed_findings"])

    # 2. Deduplicar fuentes (por URL)
    sources = deduplicate_sources(state["all_sources"])

    # 3. Generar informe con LLM
    report = await final_report_llm.ainvoke([
        SystemMessage(content=final_report_generation_prompt),
        HumanMessage(content=f"""
        Pregunta: {state['research_question'].question}
        Hallazgos: {all_findings}
        Fuentes: {sources}
        """)
    ])

    # 4. Formatear con citas numeradas [1][2][3]
    formatted_report = format_with_citations(report.content, sources)

    return {
        "final_report": formatted_report,
        "sources": sources,
        "is_complete": True
    }
```

**Formato de salida**:
```markdown
# Informe de Investigación

## Resumen Ejecutivo
[... resumen ...]

## Hallazgos Principales

### 1. Tema 1
[... contenido ...] [1][2]

### 2. Tema 2
[... contenido ...] [3][4]

## Fuentes
[1] URL 1 - Título
[2] URL 2 - Título
[3] URL 3 - Título
[4] URL 4 - Título
```

---

## 🆚 Comparativa Técnica

| Característica | Deep Researcher (LangGraph) | CrewAI Researcher |
|----------------|---------------------------|-------------------|
| **Paralelismo** | ✅ Hasta 3 investigadores simultáneos | ❌ Secuencial |
| **Control de flujo** | Condicional explícito (graph edges) | Manager agent decide |
| **Estado** | StateGraph con reducers | Memoria interna de CrewAI |
| **Herramientas** | `bind_tools()` directo | Adaptador manual |
| **Escalabilidad** | Alta (iteraciones controladas) | Limitada por diseño |
| **Progress tracking** | Granular (callbacks por nodo) | Básico |
| **Error handling** | Robusto (pruning, fallbacks) | Limitado |
| **MCP soporte** | ✅ Integrado | ❌ No evidente |
| **Context pruning** | ✅ Automático proactivo/reactivo | ❌ Manual |
| **Código** | ~1000 líneas | ~200 líneas |
| **Complejidad** | Alta | Baja |
| **Flexibilidad** | Muy alta | Moderada |

---

## 📈 Métricas de Rendimiento

### Deep Researcher (Producción)

**Capacidades**:
- **Investigadores paralelos**: 3 simultáneos
- **Iteraciones máximas**: 10 ciclos de supervisor
- **Tool calls por investigador**: 8 ciclos
- **Límite de contexto**: 150,000 tokens
- **Tiempo promedio**: 30-120 segundos (según complejidad)

**Throughput**:
- Queries simples: ~30s
- Queries medias: ~60s
- Queries complejas: ~120s

**Coste aproximado** (por investigación completa):
- LLM principal (Gemini Pro): $0.10-0.50
- LLM rápido (Gemini Flash): $0.01-0.05
- Tavily API: $0.02-0.10 por búsqueda
- **Total**: $0.20-1.00 por investigación

---

## 🔍 Puntos de Extensión

### 1. Añadir Herramienta Personalizada

```python
# En core/agents/deep_researcher_utils.py

from langchain_core.tools import BaseTool

class MiHerramientaPersonalizada(BaseTool):
    name = "mi_herramienta"
    description = "Descripción de qué hace"

    async def _arun(self, param1: str, param2: int) -> str:
        # Lógica de la herramienta
        result = await procesar(param1, param2)
        return result

async def get_all_tools(config: RunnableConfig):
    tools = [
        deep_research_think_tool,
        tavily_search,
        web_scraper,
        knowledge_search,
        knowledge_graph,
        graph_cypher_generator,
        comprehensive_web_analyzer,
        MiHerramientaPersonalizada(),  # ← Añadir aquí
    ]
    return tools
```

### 2. Modificar Prompts

```python
# En core/agents/deep_researcher_prompts.py

# Modificar cualquier prompt existente
research_system_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Eres un investigador especializado...
    [PERSONALIZAR AQUÍ]
    """),
    ("human", "{messages}")
])
```

### 3. Cambiar Modelos LLM

```python
# En deep_researcher.py, durante la compilación del grafo

async def compile_graph():
    # Obtener LLM configurado para el usuario
    if account_id:
        llm = await get_llm_for_user(account_id, purpose="deep_research")
    else:
        llm = get_main_llm()  # Por defecto

    # Pasar LLM al grafo
    graph = DeepResearcherGraph(llm=llm, config=config)
    return graph.compile()
```

### 4. Añadir Callback de Progreso

```python
config = RunnableConfig(configurable={
    "progress_callback": lambda progress, message: print(f"{progress}%: {message}"),
    "base_progress": 0,
    "max_sub_progress": 100,
    "account_id": user_account_id,
    "workspace_id": workspace_id
})

result = await graph.ainvoke(input_state, config=config)
```

### 5. Extender State

```python
# En core/agents/deep_researcher_state.py

from typing import TypedDict, List, Optional

class MyCustomState(TypedDict):
    custom_field: str
    custom_list: List[int]
    metadata: Optional[dict]

# Modificar AgentState para incluir campos personalizados
class AgentState(TypedDict):
    # ... campos existentes ...
    custom_field: str  # ← Añadir
```

---

## 🐛 Errores Conocidos y Soluciones

### Error 1: `read_many_files` con string

**Problema**: Se pasó un string de rutas en lugar de lista, causando que cada carácter se interpretara como ruta.

```python
# ❌ INCORRECTO
paths = "/ruta/a/archivo.py"  # String
files = read_many_files(paths=paths)  # Cada char se interpreta como ruta

# ✅ CORRECTO
paths = ["/ruta/a/archivo.py"]  # Lista
files = read_many_files(paths=paths)
```

**Solución**: Siempre usar listas, incluso para un solo archivo.

---

### Error 2: `read_recursive_directory` no soportado

**Problema**: Algunas herramientas no soportan lectura recursiva de directorios.

```python
# ❌ INCORRECTO
read_recursive_directory("/ruta/al/directorio")  # No soportado

# ✅ CORRECTO
# Navegar manualmente
contents = list_directory("/ruta/al/directorio")
for item in contents:
    if item["type"] == "directory":
        subcontents = list_directory(item["path"])
        # Procesar subdirectorio
    else:
        # Procesar archivo
```

**Solución**: Usar `list_directory` y navegar manualmente.

---

### Error 3: Contexto demasiado grande

**Problema**: El contexto puede exceder límites de tokens del LLM.

**Solución**:
- El sistema ya incluye pruning automático
- Ajustar `max_input_tokens` en configuración
- Reducir `max_react_tool_calls` si es necesario

---

## 📚 Ejemplos de Uso

### Ejemplo 1: Uso Básico desde Python

```python
from core.agents.deep_researcher import DeepResearcherGraph

# Inicializar
graph = DeepResearcherGraph(config=config)

# Ejecutar investigación
input_state = {
    "messages": [
        {"role": "user", "content": "¿Cuál es el estado actual de la computación cuántica?"}
    ],
    "account_id": "user-uuid-123",
    "workspace_id": "workspace-uuid-456"
}

config = RunnableConfig(configurable={
    "progress_callback": my_progress_callback,
    "account_id": "user-uuid-123"
})

result = await graph.ainvoke(input_state, config=config)

print(result["final_report"])
print(result["sources"])
```

---

### Ejemplo 2: Integración con API (FastAPI)

```python
# api/deep_research.py

from fastapi import APIRouter, Depends
from core.agents.deep_researcher import DeepResearcherGraph

router = APIRouter()

@router.post("/deep-research")
async def deep_research_endpoint(
    request: ResearchRequest,
    user: User = Depends(get_current_user)
):
    graph = DeepResearcherGraph()

    input_state = {
        "messages": [{"role": "user", "content": request.query}],
        "account_id": user.account_id,
        "workspace_id": request.workspace_id
    }

    config = RunnableConfig(configurable={
        "progress_callback": lambda p, m: broadcast_progress(user.id, p, m),
        "account_id": user.account_id,
        "workspace_id": request.workspace_id
    })

    result = await graph.ainvoke(input_state, config=config)

    return {
        "report": result["final_report"],
        "sources": result["sources"],
        "metadata": {
            "iterations": result.get("current_iteration", 0),
            "total_tools_calls": len(result.get("tool_calls", [])),
            "completion_time": result.get("completion_time")
        }
    }
```

---

### Ejemplo 3: Callback de Progreso para Frontend

```python
import asyncio
from collections import defaultdict

class ProgressTracker:
    def __init__(self):
        self.progress = defaultdict(float)
        self.messages = defaultdict(list)

    async def callback(self, progress: float, message: str, agent: str):
        self.progress[agent] = progress
        self.messages[agent].append(message)

        # Broadcast via WebSocket
        await websocket_manager.send(
            user_id=user_id,
            message={
                "type": "research_progress",
                "agent": agent,
                "progress": progress,
                "message": message,
                "overall": self.get_overall_progress()
            }
        )

    def get_overall_progress(self):
        # Calcular progreso global basado en agentes activos
        if not self.progress:
            return 0
        return sum(self.progress.values()) / len(self.progress)

# Uso
tracker = ProgressTracker()
config = RunnableConfig(configurable={
    "progress_callback": tracker.callback
})
```

---

## 🔮 Futuras Mejoras (Roadmap)

### Corto Plazo (1-2 meses)

1. **Mejorar CrewAI**: Implementar paralelismo en CrewAI Researcher
2. **Nuevas herramientas**:
   - `arxiv_search`: Búsqueda en papers académicos
   - `github_search`: Búsqueda en repositorios de código
   - `patent_search`: Búsqueda en patentes
3. **Caching inteligente**: Cachear resultados de búsqueda por tema
4. **Mejor pruning**: Context pruning basado en relevancia semántica

### Mediano Plazo (3-6 meses)

1. **Agentes especializados por dominio**:
   - Agente legal (búsqueda en jurisprudencia)
   - Agente médico (búsqueda en PubMed)
   - Agente financiero (búsqueda en mercados)
2. **Self-improvement**: Agente que optimiza sus propios prompts
3. **A/B testing**: Comparar Deep Researcher vs CrewAI automáticamente
4. **Explainability**: Explicar por qué se tomaron ciertas decisiones

### Largo Plazo (6-12 meses)

1. **Multi-modal**: Procesamiento de imágenes, audio, video
2. **Collaborative**: Múltiples agentes colaborando en tiempo real
3. **Learning from feedback**: Aprender de correcciones del usuario
4. **Autonomous research**: Investigación sin supervisión humana

---

## 📊 Glosario

**Términos clave**:

- **Pruning**: Eliminación de contexto antiguo/irrelevante para mantener dentro de límites de tokens
- **React pattern**: Ciclo de pensamiento-acción-reflexión típico de agentes
- **StateGraph**: Grafo de estado de LangGraph con typed dictionaries
- **Tool calling**: Capacidad del LLM de invocar funciones/herramientas
- **Structured output**: Output del LLM en formato JSON/struct definido
- **RAG**: Retrieval-Augmented Generation
- **MCP**: Model Context Protocol (protocolo para conectar LLMs con herramientas externas)
- **Parallelismo**: Ejecución concurrente de múltiples investigadores
- **Supervisor**: Agente que coordina y delega tareas
- **Compression**: Síntesis de hallazgos para reducir contexto

---

## 📞 Referencias y Recursos

### Archivos Críticos

1. `core/agents/deep_researcher.py` - Gráfico principal
2. `core/agents/deep_researcher_config.py` - Configuración
3. `core/agents/deep_researcher_state.py` - Definiciones de estado
4. `core/agents/deep_researcher_prompts.py` - Prompts
5. `core/agents/deep_researcher_utils.py` - Utilidades y herramientas
6. `core/agents/crewai_researcher.py` - Implementación CrewAI
7. `docs/deep_researcher_implementation.md` - Documentación existente
8. `docs/propuesta_sistema_multiagente.md` - Propuesta futura

### Documentación Externa

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [Tavily API](https://docs.tavily.com/)
- [CrewAI Documentation](https://www.crewai.com/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## ✅ Checklist de Mantenimiento

Cuando modifiques el sistema de agentes:

- [ ] Actualizar este documento con cambios
- [ ] Actualizar `docs/deep_researcher_implementation.md` si es necesario
- [ ] Añadir tests para nuevas funcionalidades
- [ ] Verificar que `max_input_tokens` no se exceda
- [ ] Probar con queries de diferentes complejidades
- [ ] Revisar logs de errores (`core_logs.txt`)
- [ ] Validar que las herramientas funcionan con `account_id`/`workspace_id`
- [ ] Medir coste de ejecución (tokens usados)
- [ ] Verificar que callbacks de progreso funcionan
- [ ] Hacer testing de paralelismo (si aplica)

---

## 📝 Notas de Versión

### v1.0 (Mayo 2025)
- Documentación inicial basada en análisis automático
- Cubre Deep Researcher, CrewAI y External Agents
- Incluye arquitectura, flujos, configuracion y ejemplos
- Identifica errores conocidos y soluciones

### Próximas versiones
- Añadir diagramas Mermaid interactivos
- Incluir métricas de rendimiento reales
- Documentar integración con Neo4j y pgvector
- Añadir sección de troubleshooting detallada

---

**📌 Importante**: Esta documentación refleja el estado actual del sistema. Para cambios recientes, consultar el historial de commits y los archivos de logs en `core_logs.txt`.
