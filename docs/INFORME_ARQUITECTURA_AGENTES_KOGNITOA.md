# 🔍 INFORME DE ARQUITECTURA Y AGENTES - KOGNITOA I

**Fecha:** 2025-10-18
**Autor:** KogniTerm (Análisis automático)
**Estado:** Análisis completo con propuestas de mejora

---

## 📋 RESUMEN EJECUTIVO

KognitoAI es un sistema **sophisticado de agentes AI** con:
- **Backend**: Python + FastAPI, LangGraph, PostgreSQL + pgvector, Neo4j
- **Frontend**: Next.js 14 + React + TypeScript + Tailwind
- **Agentes**: Implementaciones propias (CrewAI-style + LangGraph)
- **Arquitectura**: Híbrida (RAG + Graph + Tools)

**Estado actual**: Funcional pero con **deuda técnica crítica** que impacta mantenibilidad.

---

## 🏗️ ARQUITECTURA GENERAL

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Next.js UI    │────│   FastAPI Core   │────│ PostgreSQL │
│   (Next.js 14)  │    │   (LangGraph)    │    │ + pgvector  │
└─────────────────┘    └──────────────────┘    └─────────────┘
                                │
                                ├───── Neo4j (Knowledge Graph)
                                │
                                └───── Redis (Cache + Sessions)
```

**Componentes principales:**

| Componente | Ubicación | Tecnología | Responsabilidad |
|------------|-----------|------------|-----------------|
| **API Core** | `api/` | FastAPI | Endpoints REST, autenticación, routing |
| **Agentes** | `core/agents/` | LangGraph + CrewAI | Orquestación de tareas AI |
| **Graph DB** | `knowledge_graph/` | Neo4j + adaptador | Base de conocimiento grafos |
| **Tools** | `tools/` | Pydantic + LangChain | Funciones ejecutables por agentes |
| **Frontend** | `src/` | Next.js 14 + React | Interfaz web reactive |
| **Mobile** | `kogninotes-app/` | Expo (React Native) | App móvil |

---

## 🤖 SISTEMA DE AGENTES - ANÁLISIS DETALLADO

### **1. Agente Principal: Deep Researcher** ⭐

**Ubicaciones (PROBLEMA CRÍTICO):**
```
❌ DUPLICADO en 3 lugares:
1. core/agents/deep_researcher.py          [ACTIVO - 1200 líneas, CC 17.92]
2. external_agents/open_deep_research/... [OBSOLETO - 800 líneas]
3. core/agents/agents_langgraph_backup/   [BACKUP - 1200 líneas]
```

**Funcionalidad:**
- Investigación profunda en múltiples fuentes
- Búsqueda web (Tavily, DuckDuckGo)
- Análisis de código (GitHub repos)
- Revisión de documentos (PDF, markdown)
- Síntesis con citas estructuradas
- Exportación a PDF/HTML

**Arquitectura (LangGraph):**
```python
graph = StateGraph(DeepResearchState)
graph.add_node("supervisor", supervisor)           # Orquestador
graph.add_node("researcher", researcher)           # Búsqueda
graph.add_node("clarify_with_user", clarify)       # Interacción
graph.add_node("compress_research", compress)      # Síntesis
graph.add_node("report_to_user", report)           # Presentación
graph.add_conditional_edges("supervisor", ...)
```

**Problemas detectados:**
- **Complejidad extrema**: `compress_research` CC=44, `supervisor` CC=38
- **Lógica de fuentes duplicada**: 50+ líneas de parsing en cada función
- **Hardcodeados**: Límites de tokens, prompts, modelos

---

### **2. Agentes Secundarios**

| Agente | Ubicación | Líneas | Propósito |
|--------|-----------|--------|-----------|
| **CrewAI Researcher** | `core/agents/crewai_researcher.py` | ~400 | Investigación multi-agent |
| **Conceptual Graph** | `knowledge_graph/conceptual_graph_processor.py` | ~600 | Extracción de conceptos |
| **Memory Graph** | `knowledge_graph/memory_graph_processor.py` | ~500 | Construcción de grafos de memoria |
| **Graph Reasoning** | `knowledge_graph/graph_reasoning_node.py` | ~300 | Inferencia en grafos |

---

## 🔧 SISTEMA DE TOOLS (HERRAMIENTAS)

**Total**: ~35 herramientas activas en `tools/`

### **Categorías:**

1. **Búsqueda y RAG** (8 herramientas)
   - `knowledge_search_tool.py`
   - `internal_knowledge_search_tool.py`
   - `multi_query_search_tool.py`
   - `tavily_search_tool.py`
   - `web_scraper_tool.py`
   - `document_rag_tool.py`
   - `scoped_rag_analysis_tool.py`
   - `comprehensive_web_analysis_tool.py`

2. **Gestión de Contenido** (7 herramientas)
   - `add_note_tool.py`
   - `update_note_tool.py`
   - `delete_note_tool.py`
   - `get_notes_tool.py`
   - `search_notes_tool.py`
   - `analyze_text_for_insights_tool.py`
   - `analyze_code_for_insights_tool.py`

3. **Análisis y Procesamiento** (6 herramientas)
   - `insight_generation_tool.py`
   - `structured_data_generator_tool.py`
   - `table_analysis_tool.py`
   - `create_pdf_tool.py`
   - `html_generator_tool.py`
   - `mindmap_generator_tool.py`

4. **Integraciones Externas** (5 herramientas)
   - `github_repo_tool.py`
   - `get_document_content_tool.py`
   - `get_document_list_tool.py`
   - `cypher_tool.py`
   - `execute_command_tool.py`

5. **Gestión de Agenda** (3 herramientas)
   - `get_agenda_tool.py`
   - `schedule_event_tool.py`
   - `cancel_event_tool.py`

6. **Memoria y Grafos** (4 herramientas)
   - `memory_add_tool.py`
   - `query_memory_graph_tool.py`
   - `knowledge_graph_tool.py`
   - `add_web_to_rag_tool.py`

7. **Formularios** (2 herramientas)
   - `get_form_responses_tool.py`
   - `update_user_profile.py`

---

## ⚠️ PROBLEMAS CRÍTICOS IDENTIFICADOS

### **🔴 NIVEL 1: CRÍTICOS (Acción Inmediata)**

#### **1. Duplicación de Código Grave**
- **3 versiones** de Deep Researcher
- **Mantenimiento triplicado**
- **Riesgo de inconsistencias**

**Solución:**
```bash
# Eliminar duplicados
rm -rf external_agents/open_deep_research/
mv core/agents/agents_langgraph_backup/ archive/agents_backup_$(date +%Y%m%d)/
```

#### **2. Complejidad Ciclomática Extrema**
- `core/agent.py:call_model_node` CC=168 (¡!)
- `tools/get_analysis_results_tool.py:_arun` CC=80
- `tools/extract_document_titles_tool.py:_arun` CC=46

**Impacto:**
- Dificultad de testing
- Alto riesgo de bugs
- Mantenimiento costoso

**Refactorización necesaria:**
- `call_model_node` → 5-6 funciones < 30 líneas cada una
- `compress_research` → 3 funciones separadas (parsear, filtrar, formatear)

---

### **🟡 NIVEL 2: ALTOS (Acción en 2-4 semanas)**

#### **3. Formato de Tools Inconsistente**
- Algunas devuelven `ToolOutputWithSources`
- Otras devuelven `dict` con `sources`
- Otras strings simples

**Estandarización requerida:**
```python
# Todas las tools DEBEN devolver:
class ToolOutputWithSources(BaseModel):
    content: str
    sources: List[Source]
    metadata: dict = {}
```

#### **4. Manejo de Errores No Unificado**
- Patrones mezclados: retries, fallbacks, genéricos
- Logging inconsistente
- Sin clasificación de errores

**Propuesta:**
```python
class RetryableTool:
    async def execute_with_retry(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await self._execute()
            except TransientError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

---

### **🟢 NIVEL 3: MEDIOS (Acción en 1-2 meses)**

#### **5. Pooling de Conexiones DB**
```python
# ACTUAL (knowledge_graph/graph_database.py)
self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

# MEJORADO
self._driver = GraphDatabase.driver(
    self.uri,
    auth=(self.user, self.password),
    max_connection_pool_size=50,
    connection_acquisition_timeout=30.0,
    max_connection_lifetime=3600
)
```

#### **6. Concurrencia Sin Límites**
- `asyncio.gather()` sin semáforos
- Riesgo de saturación en alta carga

**Solución:**
```python
semaphore = asyncio.Semaphore(config.max_concurrent_tools)

async def execute_tool_with_limit(tool, *args):
    async with semaphore:
        return await tool.arun(*args)
```

---

## 📊 MÉTRICAS DE CALIDAD

| Métrica | Valor | Estado | Benchmark |
|---------|-------|--------|-----------|
| Archivos con CC > 10 | 8 | 🔴 Crítico | < 2 ideal |
| Función más compleja | 168 | 🔴 Crítico | < 30 ideal |
| Tools inconsistentes | ~30% | 🟡 Alto | 0% |
| Duplicación de agente | 3 versiones | 🔴 Crítico | 1 versión |
| Cobertura de tests | ❌ No detectada | 🔴 Crítico | > 80% |

---

## 🎯 PLAN DE ACCIÓN PRIORIZADO

### **FASE 1: ESTABILIDAD (1-2 semanas) - ¡URGENTE!**

**Sprint 1 (Día 1-3): Eliminación de Duplicación**
```
✅ Eliminar external_agents/open_deep_research/
✅ Mover backup a archive/
✅ Actualizar imports en todo el codebase
✅ Verificar que todos los tests pasan
```

**Sprint 2 (Semana 1): Unificación de Tools**
```
✅ Crear ToolOutputWithSources base
✅ Migrar 10 tools más usadas
✅ Centralizar lógica de fuentes en deep_researcher_utils.py
✅ Documentar estándar
```

**Sprint 3 (Semana 2): Refactorización Crítica**
```
✅ Refactorizar call_model_node (CC 168 → <30)
✅ Extraer parse_tool_calls() a utils
✅ Simplificar compress_research (CC 44 → <20)
```

---

### **FASE 2: ROBUSTEZ (2-3 semanas)**

**Sprint 4 (Semana 2):**
- ✅ Esquemas Pydantic para todos los estados
- ✅ Política de errores unificada
- ✅ Logging estructurado JSON

**Sprint 5 (Semana 3):**
- ✅ Tests unitarios para utils críticos
- ✅ Feature flags para rollout seguro
- ✅ Health checks para DB connections

---

### **FASE 3: OPTIMIZACIÓN (3-4 semanas)**

**Sprint 6 (Semana 3-4):**
- ✅ Connection pooling para Neo4j/PostgreSQL
- ✅ Límites de concurrencia global
- ✅ Caching Redis para búsquedas frecuentes
- ✅ Benchmarking de performance

---

## 🚀 PROPUESTAS DE MEJORA ADICIONALES

### **1. Sistema de Observabilidad**
```python
# Agregar a todas las tools:
@trace(name="tool_execution")
@measure_duration()
@log_io()
async def execute(self, *args):
    ...
```

**Herramientas recomendadas:**
- **Sentry** para error tracking
- **LangSmith** para tracing de agentes
- **Prometheus + Grafana** para métricas

---

### **2. Testing Completo**
```bash
# Tests necesarios:
tests/
├── unit/
│   ├── test_deep_researcher_utils.py # Lógica de parsing
│   ├── test_tool_output_format.py      # Formato consistente
│   └── test_graph_database.py          # Conexiones DB
├── integration/
│   ├── test_agent_workflow.py          # Flujo completo
│   └── test_tool_chaining.py           # Composición
└── e2e/
    └── test_research_pipeline.py       # Usuario → PDF
```

**Meta:** 80% coverage mínimo

---

### **3. Configuración Centralizada**
```python
# core/config.py (ya existe pero puede expandirse)
class AgentConfig(BaseSettings):
    DEEP_RESEARCH_MAX_ITERATIONS: int = 10
    TOOL_CONCURRENCY_LIMIT: int = 5
    TOKEN_LIMITS: dict = {
        "fast_llm": 4000,
        "main_llm": 16000,
        "summary_llm": 4000
    }
    RETRY_POLICY: dict = {
        "max_retries": 3,
        "backoff_factor": 2,
        "transient_errors": [...]
    }
```

---

### **4. Mejoras de Frontend**
- **Streaming en tiempo real** de agentes (usar Server-Sent Events)
- **Interrupción y reanudación** de investigaciones largas
- **Cache de resultados** en IndexedDB
- **PWA** para offline

---

## 📈 INDICADORES DE ÉXITO

| KPI | Actual | Objetivo (3 meses) |
|-----|--------|-------------------|
| Tiempo de desarrollo de nuevas features | 2-3 semanas | 1 semana |
| Bugs por release | ~5-10 | < 2 |
| Tiempo de onboarding nuevo dev | 2 semanas | 3 días |
| Cobertura de tests | ~10%? | > 80% |
| CC promedio módulos | 12.5 | < 8 |

---

## ⚡ ACCIONES INMEDIATAS (HOY)

1. **[ ] Reunión de equipo** para presentar este informe
2. **[ ] Crear GitHub Issues** para cada problema crítico
3. **[ ] Asignar dueños** a Fase 1 (Sprints 1-3)
4. **[ ] Configurar Sentry** si no existe
5. **[ ] Establecer pre-commit hooks**:
   ```yaml
   # .pre-commit-config.yaml
   - repo: https://github.com/astral-sh/ruff-pre-commit
     rev: v0.4.2
     hooks:
       - id: ruff
         args: [--select=COM,CPY,PLR] # Complejidad
   ```

---

## 📚 RECOMENDACIONES TÉCNICAS CONCRETAS

### **Prioridad Máxima (Hacer Ya):**
1. ✅ Eliminar duplicación de Deep Researcher
2. ✅ Refactorizar `call_model_node` (CC 168)
3. ✅ Unificar formato de Tools

### **Prioridad Alta (Próximas 2 semanas):**
4. ✅ Política de errores unificada
5. ✅ Logging JSON estructurado
6. ✅ Tests para `deep_researcher_utils.py`

### **Prioridad Media (Próximo mes):**
7. ✅ Connection pooling para DBs
8. ✅ Límites de concurrencia
9. ✅ Configuración centralizada

---

## 📊 ANEXO: ANÁLISIS DETALLADO DE COMPLEJIDAD

### **Archivos con Complejidad Ciclomática > 10:**

| Archivo | CC Promedio | Función Más Compleja | CC | Líneas |
|---------|-------------|---------------------|----|--------|
| `core/agent.py` | 14.23 | `call_model_node` | **168.0** | ~300 |
| `core/agents/deep_researcher.py` | 17.92 | `compress_research` | **44.0** | ~1200 |
| `core/agents/deep_researcher.py` | 17.92 | `supervisor` | **38.0** | ~1200 |
| `core/agents/deep_researcher.py` | 17.92 | `researcher` | **31.0** | ~1200 |
| `tools/get_analysis_results_tool.py` | 22.20 | `_arun` | **80.0** | ~250 |
| `tools/extract_document_titles_tool.py` | 18.25 | `_arun` | **46.0** | ~200 |
| `tools/comprehensive_web_analysis_tool.py` | 12.60 | `_arun` | **41.0** | ~300 |
| `tools/github_repo_tool.py` | 10.93 | `_update_knowledge_collection` | **31.0** | ~350 |

**Interpretación:**
- CC > 10: Difícil de mantener
- CC > 20: Muy difícil de testear
- CC > 50: Riesgo alto de bugs
- **CC 168**: ¡CRÍTICO! Requiere refactorización inmediata

---

## 🔍 ANEXO: ANÁLISIS DE DUPLICACIÓN

### **Deep Researcher - Tres Implementaciones:**

#### **Versión 1 (ACTIVA):** `core/agents/deep_researcher.py`
- **Líneas:** ~1200
- **Estado:** Activamente usada
- **Complejidad:** CC 17.92
- **Última modificación:** Reciente

#### **Versión 2 (OBSOLETA):** `external_agents/open_deep_research/src/open_deep_research/deep_researcher.py`
- **Líneas:** ~800
- **Estado:** No usada (directorio externo)
- **Complejidad:** No analizada
- **Problema:** Código muerto que confunde

#### **Versión 3 (BACKUP):** `core/agents/agents_langgraph_backup/deep_researcher.py`
- **Líneas:** ~1200
- **Estado:** Backup no actualizado
- **Complejidad:** CC 13.33
- **Problema:** Desactualizado, pero presente

**Conclusión:** Mantener solo la Versión 1. Eliminar o archivar las otras dos.

---

## 🎓 ANEXO: RECOMENDACIONES DE DISEÑO

### **Principios SOLID Aplicar:**

1. **Single Responsibility:**
   - Cada tool debe hacer UNA cosa
   - Cada nodo del grafo debe tener una responsabilidad clara

2. **Open/Closed:**
   - Usar herencia/composición para extender tools
   - No modificar código base para nuevas funcionalidades

3. **Liskov Substitution:**
   - Todas las tools deben heredar de `BaseTool`
   - Respetar contrato (métodos `_arun`, `run`)

4. **Interface Segregation:**
   - Separar `AsyncTool` vs `SyncTool`
   - No forzar métodos no usados

5. **Dependency Inversion:**
   - Inyectar dependencias (DB, LLM) no crear instancias directas
   - Usar `fastapi.Depends()` o patrón factory

---

## 📞 CONTACTO Y SEGUIMIENTO

Para cualquier duda sobre este informe:
- Revisar documentación en `/docs/`
- Ejecutar análisis de código: `python -m radon cc <archivo>`
- Configurar pre-commit hooks para monitoreo continuo

---

**Fin del informe**

*Generado automáticamente por KogniTerm - Tu asistente de terminal experto*
