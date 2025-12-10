# 🔬 Deep Research con LiteLLM - Guía de Integración

## 📋 Resumen

Este documento explica cómo **Open Deep Research** se integra con **Kognito AI** usando **LiteLLM**, evitando la duplicación de configuración de modelos y aprovechando la infraestructura existente.

---

## 🔄 Diferencias entre versiones

### **Versión Original** (`deep_research_tool.py`)

```python
# ❌ Problemas:
# 1. Usa init_chat_model de LangChain (no LiteLLM)
# 2. Hardcodea el modelo: "openai:gpt-4.1"
# 3. No aprovecha la configuración de Kognito
# 4. Requiere API keys separadas

run_config = {
    "configurable": {
        "research_model": settings.google_main_model_name,  # Hardcoded
    }
}
```

### **Versión LiteLLM** (`deep_research_tool_litellm.py`)

```python
# ✅ Ventajas:
# 1. Usa ChatLiteLLM de Kognito
# 2. Lee modelos de .env (LLM_MODEL, FAST_LLM_MODEL)
# 3. Aprovecha toda la configuración existente
# 4. Usa las mismas API keys de Kognito

config = self._create_litellm_compatible_config()
# Automáticamente usa get_main_llm() y get_fast_llm()
```

---

## 🛠️ Cómo funciona la integración

### **1. Mapeo de Modelos**

La nueva versión convierte automáticamente los modelos de LiteLLM al formato de LangChain:

```python
# LiteLLM (Kognito)
LLM_MODEL = "openrouter/anthropic/claude-3.5-sonnet"

# Se convierte automáticamente a:
# LangChain (Open Deep Research)
research_model = "anthropic:claude-3.5-sonnet"
```

**Mapeo soportado:**

| Formato LiteLLM | Formato LangChain |
|----------------|-------------------|
| `openrouter/openai/gpt-4` | `openai:gpt-4` |
| `openrouter/anthropic/claude-3.5-sonnet` | `anthropic:claude-3.5-sonnet` |
| `openrouter/google/gemini-pro` | `google:gemini-pro` |
| `openai/gpt-4` | `openai:gpt-4` |

### **2. Asignación de Modelos por Tarea**

```python
# Modelo Principal (Main LLM) - Para tareas complejas
- Research Model: Conducir investigación
- Final Report Model: Generar informe final

# Modelo Rápido (Fast LLM) - Para tareas simples
- Compression Model: Comprimir hallazgos
- Summarization Model: Resumir resultados de búsqueda
```

### **3. Configuración Automática**

```python
config = {
    "configurable": {
        # Modelos (automáticamente desde Kognito)
        "research_model": "anthropic:claude-3.5-sonnet",
        "compression_model": "openai:gpt-4o-mini",
        
        # API Keys (heredadas de settings)
        "api_key": settings.openrouter_api_key,
        "tavily_api_key": settings.tavily_api_key,
        
        # Configuración de investigación
        "max_researcher_iterations": 6,
        "max_concurrent_research_units": 3,
        "max_react_tool_calls": 10,
        
        # Tokens
        "research_model_max_tokens": 10000,
        "compression_model_max_tokens": 8192,
    }
}
```

---

## 🚀 Uso

### **Opción 1: Usar la nueva versión directamente**

```python
from tools.deep_research_tool_litellm import create_deep_research_tool_litellm
from tools.web_search_tool import get_web_search_tool
from tools.add_web_to_rag_tool import AddWebToRAGTool

# Crear herramientas
web_search = get_web_search_tool()
add_to_rag = AddWebToRAGTool()

# Crear Deep Research Tool con LiteLLM
deep_research = create_deep_research_tool_litellm(
    web_search_tool=web_search,
    add_web_to_rag_tool=add_to_rag
)

# Usar la herramienta
result = await deep_research._run(
    query="Investiga el impacto de la IA en la educación",
    max_iterations=6,
    max_concurrent_units=3
)
```

### **Opción 2: Integrar en el agente principal**

```python
# core/agent.py

from tools.deep_research_tool_litellm import create_deep_research_tool_litellm

async def initialize_tools():
    tools = []
    
    # ... otras herramientas ...
    
    # Añadir Deep Research con LiteLLM
    deep_research = create_deep_research_tool_litellm(
        web_search_tool=web_search,
        add_web_to_rag_tool=add_to_rag
    )
    
    if deep_research:
        tools.append(deep_research)
    
    return tools
```

---

## ⚙️ Configuración en `.env`

```bash
# === LLM Configuration (LiteLLM) ===
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet
FAST_LLM_MODEL=openrouter/openai/gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_API_BASE=https://openrouter.ai/api/v1

# === API Keys ===
OPENROUTER_API_KEY=sk-or-v1-xxxxx
TAVILY_API_KEY=tvly-xxxxx

# === Deep Research Configuration (Opcional) ===
# Estos valores se pueden sobrescribir en tiempo de ejecución
DEEP_RESEARCH_MAX_ITERATIONS=6
DEEP_RESEARCH_MAX_CONCURRENT_UNITS=3
DEEP_RESEARCH_MAX_TOOL_CALLS=10
```

---

## 🔧 Parámetros Configurables

### **En tiempo de ejecución:**

```python
result = await deep_research._run(
    query="Tu consulta de investigación",
    max_iterations=8,          # Default: 6
    max_concurrent_units=5     # Default: 3
)
```

### **Significado de los parámetros:**

| Parámetro | Descripción | Valor Recomendado |
|-----------|-------------|-------------------|
| `max_iterations` | Máximo de iteraciones del supervisor | 6-8 |
| `max_concurrent_units` | Investigadores en paralelo | 3-5 |
| `max_react_tool_calls` | Llamadas a herramientas por investigador | 10 |

**⚠️ Nota sobre concurrencia:**

- Más unidades concurrentes = Más rápido pero más costoso
- Cuidado con rate limits de las APIs
- Recomendado: 3-5 para uso normal, 1-2 para pruebas

---

## 📊 Flujo de Ejecución

```
Usuario solicita investigación
         │
         ▼
┌─────────────────────────┐
│ DeepResearchToolLiteLLM │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Obtener LLMs de Kognito│
│ - get_main_llm()        │
│ - get_fast_llm()        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Convertir formato       │
│ LiteLLM → LangChain     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Crear configuración     │
│ para el grafo           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Ejecutar grafo de       │
│ investigación           │
│ (Open Deep Research)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Guardar resultado       │
│ en RAG                  │
└─────────────────────────┘
```

---

## 🐛 Troubleshooting

### **Error: "Main LLM not initialized"**

```python
# Solución: Asegúrate de que los LLMs estén inicializados
from core.llm_manager import initialize_llms

await initialize_llms()
```

### **Error: "No se pudo mapear el modelo"**

```python
# Verifica el formato del modelo en .env
# Debe ser: "provider/model" o "openrouter/provider/model"

# ✅ Correcto:
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet

# ❌ Incorrecto:
LLM_MODEL=claude-3.5-sonnet
```

### **Error: "Token limit exceeded"**

```python
# Reduce el número de iteraciones o unidades concurrentes
result = await deep_research._run(
    query="...",
    max_iterations=4,          # Reducido de 6
    max_concurrent_units=2     # Reducido de 3
)
```

---

## 🔄 Migración desde la versión original

### **Paso 1: Actualizar imports**

```python
# Antes
from tools.deep_research_tool import DeepResearchTool

# Después
from tools.deep_research_tool_litellm import create_deep_research_tool_litellm
```

### **Paso 2: Actualizar inicialización**

```python
# Antes
deep_research = DeepResearchTool(
    web_search_tool=web_search,
    add_web_to_rag_tool=add_to_rag
)

# Después
deep_research = create_deep_research_tool_litellm(
    web_search_tool=web_search,
    add_web_to_rag_tool=add_to_rag
)
```

### **Paso 3: Uso (sin cambios)**

```python
# El uso es idéntico
result = await deep_research._run(query="...")
```

---

## ✅ Ventajas de la nueva versión

1. **✅ Configuración centralizada** - Todo en `.env`
2. **✅ Sin duplicación** - Usa los mismos LLMs que el resto de Kognito
3. **✅ Flexibilidad** - Cambia de modelo sin tocar código
4. **✅ Consistencia** - Mismo comportamiento en toda la app
5. **✅ Mantenibilidad** - Un solo lugar para configurar modelos
6. **✅ Costos optimizados** - Usa modelo rápido para tareas simples

---

## 📝 Ejemplo Completo

```python
import asyncio
from tools.deep_research_tool_litellm import create_deep_research_tool_litellm
from tools.web_search_tool import get_web_search_tool
from tools.add_web_to_rag_tool import AddWebToRAGTool
from core.llm_manager import initialize_llms

async def main():
    # 1. Inicializar LLMs de Kognito
    await initialize_llms()
    
    # 2. Crear herramientas
    web_search = get_web_search_tool()
    add_to_rag = AddWebToRAGTool()
    
    # 3. Crear Deep Research Tool
    deep_research = create_deep_research_tool_litellm(
        web_search_tool=web_search,
        add_web_to_rag_tool=add_to_rag
    )
    
    # 4. Ejecutar investigación
    result = await deep_research._run(
        query="Analiza las tendencias de IA generativa en 2024",
        max_iterations=6,
        max_concurrent_units=3
    )
    
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔗 Referencias

- **Open Deep Research**: `/external_agents/open_deep_research/`
- **LLM Manager**: `/core/llm_manager.py`
- **Configuración**: `/core/config.py`
- **Herramienta Original**: `/tools/deep_research_tool.py`
- **Herramienta LiteLLM**: `/tools/deep_research_tool_litellm.py`
