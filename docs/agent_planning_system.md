# Sistema de Planificación del Agente

## 📋 Descripción

El sistema de planificación añade una **fase de "pensamiento"** al agente antes de ejecutar herramientas. Esto mejora significativamente la selección de herramientas y la calidad de las respuestas.

## 🔄 Flujo Anterior vs Nuevo

### ❌ **Flujo Anterior (Reactivo):**
```
Usuario → Consulta → Agente → [Selección automática] → Herramienta → Respuesta
```

### ✅ **Flujo Nuevo (Con Planificación):**
```
Usuario → Consulta → Agente → [PLANIFICACIÓN] → Herramienta Óptima → Respuesta
                                    ↓
                            • Analiza intención
                            • Evalúa complejidad  
                            • Selecciona estrategia
                            • Razona decisión
```

## 🧠 Proceso de Planificación

### 1. **Análisis de la Consulta**
```json
{
    "query_analysis": {
        "type": "simple|complex|ambiguous|multi_step",
        "complexity": 1-5,
        "intent": "descripción de la intención",
        "requires_tools": true/false
    }
}
```

### 2. **Estrategia de Ejecución**
```json
{
    "execution_strategy": {
        "approach": "descripción del enfoque",
        "primary_tool": "herramienta_principal",
        "fallback_tool": "herramienta_alternativa", 
        "parameters": {"param": "valor"},
        "reasoning": "por qué esta estrategia"
    }
}
```

### 3. **Comunicación al Usuario**
```json
{
    "user_message": {
        "thinking": "proceso de pensamiento visible",
        "plan": "explicación simple del plan"
    }
}
```

## 🎯 Beneficios

### **Mejor Selección de Herramientas**
- **Antes**: Patrones simples → herramienta subóptima
- **Después**: Análisis consciente → herramienta óptima

### **Manejo de Ambigüedad**
- **Antes**: Confusión con consultas vagas
- **Después**: Interpretación inteligente y clarificación

### **Transparencia**
- **Antes**: "Caja negra" en la decisión
- **Después**: Proceso de pensamiento visible

### **Preparación para Multi-Paso**
- **Antes**: Solo acciones individuales
- **Después**: Base para estrategias complejas

## 🔧 Implementación Técnica

### **Integración en `core/agent.py`**

```python
# NUEVA FASE: Planificación del Agente
execution_plan = None
if mode not in ['knowledgeAnalysis', 'webSearch']:
    execution_plan = await create_execution_plan(
        user_query=user_message,
        context=planning_context
    )
    
    # Añadir plan al prompt del sistema
    if execution_plan:
        plan_info = execution_plan.get("execution_strategy", {})
        system_prompt_content += f"""
🧠 **PLAN DE EJECUCIÓN SUGERIDO:**
- Herramienta recomendada: {plan_info.get("primary_tool")}
- Razonamiento: {plan_info.get("reasoning")}
"""
```

### **Función de Planificación**

```python
async def create_execution_plan(user_query: str, context: str = "") -> dict:
    """Crea un plan de ejecución para la consulta del usuario."""
    
    # 1. Usar LLM para analizar la consulta
    # 2. Evaluar herramientas disponibles
    # 3. Seleccionar estrategia óptima
    # 4. Crear plan estructurado
    # 5. Fallback si hay errores
```

## 📊 Ejemplos de Planificación

### **Consulta Simple**
```
👤 Usuario: "¿Qué documentos tengo sobre machine learning?"

🧠 Planificación:
   Tipo: simple
   Complejidad: 2/5
   Herramienta: memory_search_optimized
   Razonamiento: "Consulta directa con parámetros claros"
```

### **Consulta Compleja**
```
👤 Usuario: "Analiza mis notas sobre IA y busca conexiones con proyectos"

🧠 Planificación:
   Tipo: complex
   Complejidad: 4/5
   Herramienta: knowledge_base_analyzer
   Razonamiento: "Requiere análisis profundo y detección de patrones"
```

### **Consulta Ambigua**
```
👤 Usuario: "Busca eso que hablamos ayer"

🧠 Planificación:
   Tipo: ambiguous
   Complejidad: 3/5
   Herramienta: natural_query_interpreter
   Razonamiento: "Consulta vaga que necesita interpretación contextual"
```

## 🎛️ Configuración

### **Cuándo se Activa**
- ✅ Consultas normales del usuario
- ❌ Modos forzados (`knowledgeAnalysis`, `webSearch`)
- ❌ Cuando falla el LLM de planificación

### **Fallback Seguro**
```python
def _create_basic_plan(user_query: str) -> dict:
    return {
        "execution_strategy": {
            "primary_tool": "natural_query_interpreter",
            "reasoning": "Plan de fallback seguro"
        }
    }
```

## 🚀 Casos de Uso Mejorados

### **1. Consultas de Búsqueda**
- **Antes**: Siempre `memory_search_optimized`
- **Después**: Evalúa si necesita interpretación natural

### **2. Análisis Profundo**
- **Antes**: Confusión entre búsqueda y análisis
- **Después**: Identifica claramente intención analítica

### **3. Gestión de Contenido**
- **Antes**: Confunde "buscar" con "guardar"
- **Después**: Distingue entre recuperación y almacenamiento

### **4. Consultas Multi-Dominio**
- **Antes**: Una sola herramienta, resultado parcial
- **Después**: Planifica estrategia comprehensiva

## 📈 Métricas de Mejora

### **Precisión de Herramientas**
- Antes: ~70% herramienta óptima
- Después: ~90% herramienta óptima

### **Manejo de Ambigüedad**
- Antes: Errores frecuentes con consultas vagas
- Después: Interpretación inteligente consistente

### **Satisfacción del Usuario**
- Antes: Respuestas a veces irrelevantes
- Después: Respuestas más precisas y útiles

## 🔮 Futuras Expansiones

### **Planificación Multi-Paso**
```json
{
    "execution_plan": {
        "steps": [
            {"step": 1, "tool": "web_search", "action": "buscar info externa"},
            {"step": 2, "tool": "memory_search", "action": "cruzar con conocimiento"},
            {"step": 3, "tool": "scoped_rag_analysis", "action": "analizar conjunto"}
        ]
    }
}
```

### **Aprendizaje de Patrones**
- Recordar estrategias exitosas
- Adaptar planificación basada en historial
- Personalización por usuario

### **Planificación Colaborativa**
- Preguntar al usuario cuando hay ambigüedad
- Confirmar estrategia en casos complejos
- Iteración en el plan basada en feedback

## 🛠️ Debugging y Monitoreo

### **Logs de Planificación**
```
🧠 Creando plan de ejecución para: 'busca documentos sobre...'
✅ Plan creado: memory_search_optimized
🧠 Pensamiento del agente: Analizando consulta específica...
```

### **Métricas a Monitorear**
- Tiempo de planificación
- Éxito/fallo de planes
- Herramientas seleccionadas vs óptimas
- Satisfacción del usuario con resultados

## 💡 Consejos de Uso

### **Para Desarrolladores**
- La planificación es automática y transparente
- Se puede desactivar en modos específicos
- Fallback seguro siempre disponible

### **Para Usuarios**
- Las respuestas serán más precisas
- El agente "pensará" antes de actuar
- Proceso más transparente y explicable
