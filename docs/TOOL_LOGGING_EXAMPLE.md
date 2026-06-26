# 🔧 Logging Mejorado de Herramientas - Ejemplos

## ✅ **Mejoras Implementadas**

Ahora el callback muestra **exactamente qué parámetros** se envían a cada herramienta, estructurados de manera clara.

### 📊 **Antes (menos claro):**
```
🔧 [TOOL START] web_search | Session: abc12345...def67890
🔨 [TOOL INPUT]: {"query": "capital de Francia", "num_results": 5}
```

### 🎯 **Después (mucho más claro):**
```
🔧 [TOOL START] web_search | Session: abc12345...def67890
🔨 [TOOL CALL] web_search(
    query='capital de Francia'
    num_results=5
)
```

## 📝 **Ejemplos de Diferentes Herramientas**

### 1. **Búsqueda Web**
```
🔧 [TOOL START] web_search | Session: abc12345...def67890
🔨 [TOOL CALL] web_search(
    query='últimas noticias inteligencia artificial'
    num_results=3
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Encontré 3 resultados sobre inteligencia artificial...
```

### 2. **Búsqueda en Memoria**
```
🔧 [TOOL START] memory_search_optimized | Session: abc12345...def67890
🔨 [TOOL CALL] memory_search_optimized(
    query='proyectos de IA del usuario'
    k=5
    workspace_id='workspace-123'
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Encontré 3 memorias relevantes sobre proyectos de IA...
```

### 3. **Análisis de Documentos**
```
🔧 [TOOL START] get_document_content | Session: abc12345...def67890
🔨 [TOOL CALL] get_document_content(
    document_id='doc-456'
    workspace_id='workspace-123'
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Documento recuperado: "Manual de Python - Capítulo 1..."
```

### 4. **Herramienta con Parámetros Largos**
```
🔧 [TOOL START] comprehensive_web_analyzer | Session: abc12345...def67890
🔨 [TOOL CALL] comprehensive_web_analyzer(
    query='análisis completo sobre machine learning en 2024 incluyendo tendencias, herramientas...[TRUNCATED]...y aplicaciones prácticas'
    max_results=10
    include_analysis=True
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Análisis completo realizado. Encontré 15 fuentes relevantes sobre machine learning...[TRUNCATED]...con aplicaciones en diversos sectores.
```

### 5. **Actualización de Perfil**
```
🔧 [TOOL START] update_user_profile | Session: abc12345...def67890
🔨 [TOOL CALL] update_user_profile(
    field='intereses'
    value='machine learning, deep learning, computer vision'
    workspace_id='workspace-123'
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Perfil actualizado exitosamente. Campo 'intereses' modificado.
```

### 6. **Análisis de Conversación**
```
🔧 [TOOL START] conversation_context_analyzer_tool | Session: abc12345...def67890
🔨 [TOOL CALL] conversation_context_analyzer_tool(
    analysis_type='interests_and_preferences'
    workspace_id='workspace-123'
)
✅ [TOOL END] Session: abc12345...def67890
🔧 [TOOL OUTPUT]: Análisis completado. Identificados intereses en: IA, programación, análisis de datos...
```

## 🔍 **Información Capturada**

### **Para cada herramienta verás:**
1. **🔧 [TOOL START]** - Nombre de la herramienta y sesión
2. **🔨 [TOOL CALL]** - Llamada estructurada con parámetros
3. **✅ [TOOL END]** - Finalización de la herramienta
4. **🔧 [TOOL OUTPUT]** - Resultado de la herramienta

### **Parámetros mostrados:**
- ✅ **query** - La consulta o pregunta
- ✅ **workspace_id** - ID del workspace (si aplica)
- ✅ **k** - Número de resultados
- ✅ **document_id** - ID de documentos
- ✅ **field/value** - Para actualizaciones
- ✅ **analysis_type** - Tipo de análisis
- ✅ **Cualquier otro parámetro** específico de la herramienta

## 🎯 **Beneficios**

### **Antes:**
- ❌ Difícil de entender qué parámetros se enviaban
- ❌ JSON crudo poco legible
- ❌ No se veía claramente la estructura de la llamada

### **Después:**
- ✅ **Parámetros claros** y estructurados
- ✅ **Fácil de leer** y entender
- ✅ **Formato consistente** para todas las herramientas
- ✅ **Truncado inteligente** para parámetros largos
- ✅ **Debugging más eficiente**

## 🚀 **Cómo usar**

1. **Ejecuta el monitor de logs:**
   ```bash
   python scripts/monitor_llm_logs.py
   ```

2. **Envía un mensaje** que use herramientas (ej: "busca información sobre IA")

3. **Observa los logs** con el nuevo formato mejorado

4. **Verifica** que los parámetros sean los esperados

## 🔧 **Casos de debugging**

### **Problema: La herramienta no encuentra resultados**
**Antes:** Difícil saber qué query se envió exactamente
**Después:** Puedes ver exactamente: `query='mi consulta específica'`

### **Problema: Workspace incorrecto**
**Antes:** No se veía el workspace_id
**Después:** Claramente visible: `workspace_id='workspace-123'`

### **Problema: Parámetros incorrectos**
**Antes:** JSON difícil de leer
**Después:** Estructura clara con cada parámetro en su línea

¡Ahora tienes visibilidad completa de todas las llamadas a herramientas! 🎉
