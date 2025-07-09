# Documentación de Herramientas del Sistema Kognito

## Introducción

El sistema Kognito utiliza una arquitectura modular de herramientas basada en LangChain que permite al agente de IA realizar una amplia variedad de tareas especializadas. Cada herramienta está diseñada siguiendo el patrón `BaseTool` de LangChain y se integra de manera robusta con el sistema de agentes.

## Arquitectura General

### Estructura Base
- **Ubicación**: `/core/tools.py` (ensamblador principal) y `/tools/` (implementaciones individuales)
- **Patrón**: Cada herramienta hereda de `langchain_core.tools.BaseTool`
- **Esquemas**: Utilizan Pydantic para validación de entrada (`args_schema`)
- **Ejecución**: Métodos `_run()` (síncrono) y `_arun()` (asíncrono)
- **Manejo de errores**: Sistema robusto con logging detallado

### Función de Ensamblaje
La función `get_all_langchain_tools()` en `/core/tools.py` actúa como el punto central de recolección, instanciando todas las herramientas disponibles con manejo de errores individual para garantizar que el sistema funcione aunque alguna herramienta falle.

## Categorías de Herramientas

### 1. Gestión de Memoria y Conocimiento

#### MemoryAddTool
- **Funcionalidad**: Guarda información valiosa en la memoria vectorial a largo plazo
- **Estrategia**: Utiliza embeddings para almacenar contenido en base de datos vectorial
- **Lugar en el sistema**: Componente central para la personalización y aprendizaje continuo
- **Parámetros**: `content`, `account_id`, `type`, `workspace_id`, `category`

#### MemorySearchOptimizedTool
- **Funcionalidad**: Búsqueda optimizada en la base de conocimiento del usuario
- **Estrategia**: Búsqueda semántica con filtros por cuenta, workspace y categoría
- **Lugar en el sistema**: Motor de recuperación de información personalizada
- **Parámetros**: `query`, `account_id`, `workspace_id`, `max_results`

#### VectorDBSearchTool
- **Funcionalidad**: Consultas directas a la base de datos vectorial
- **Estrategia**: Acceso de bajo nivel para búsquedas específicas y debugging
- **Lugar en el sistema**: Herramienta de diagnóstico y consulta avanzada
- **Parámetros**: `query`, `account_id`, `collection_filter`

#### NaturalQueryInterpreterTool
- **Funcionalidad**: Interpreta consultas en lenguaje natural y extrae parámetros
- **Estrategia**: Utiliza LLM para analizar intención y extraer metadatos automáticamente
- **Lugar en el sistema**: Capa de interpretación entre usuario y herramientas especializadas
- **Parámetros**: `user_query`, `account_id`

### 2. Análisis y Procesamiento de Conocimiento

#### KnowledgeAnalysisTool
- **Funcionalidad**: Análisis proactivo de patrones en la base de conocimiento
- **Estrategia**: Procesamiento por lotes con análisis temporal y temático
- **Lugar en el sistema**: Motor de insights proactivos y descubrimiento de patrones
- **Parámetros**: `user_request`, `account_id`

#### ComprehensiveWebAnalysisTool
- **Funcionalidad**: Investigación web integral con síntesis de múltiples fuentes
- **Estrategia**: Orquesta búsqueda web, scraping y análisis cruzado con conocimiento personal
- **Lugar en el sistema**: Herramienta de investigación avanzada para consultas complejas
- **Parámetros**: `query`, `account_id`, `workspace_id`

#### AnalyzeTextForInsightsTool
- **Funcionalidad**: Análisis profundo de texto para extraer insights
- **Estrategia**: Procesamiento de NLP para identificar conceptos clave y relaciones
- **Lugar en el sistema**: Procesador de contenido para análisis semántico
- **Parámetros**: `text_content`, `analysis_focus`, `account_id`

#### ScopedRagAnalysisTool
- **Funcionalidad**: Análisis RAG focalizado en documentos específicos
- **Estrategia**: Combina recuperación vectorial con análisis contextual
- **Lugar en el sistema**: Herramienta especializada para análisis de documentos
- **Parámetros**: `query`, `document_scope`, `account_id`

### 3. Gestión de Documentos

#### DocumentRAGTool
- **Funcionalidad**: Procesa documentos y los añade a la base de conocimiento
- **Estrategia**: Chunking inteligente, embedding y almacenamiento vectorial
- **Lugar en el sistema**: Ingesta principal de documentos al sistema RAG
- **Parámetros**: `document_content`, `filename`, `topic`, `account_id`

#### GetDocumentListTool
- **Funcionalidad**: Lista documentos disponibles en el sistema
- **Estrategia**: Consulta a metadatos de documentos con filtros
- **Lugar en el sistema**: Interfaz de navegación de documentos
- **Parámetros**: `account_id`, `workspace_filter`, `category_filter`

#### AddWebToRAGTool
- **Funcionalidad**: Añade contenido web directamente a la base de conocimiento
- **Estrategia**: Combina scraping web con procesamiento RAG en una sola operación
- **Lugar en el sistema**: Herramienta de ingesta rápida de contenido web
- **Parámetros**: `url`, `topic`, `account_id`

### 4. Búsqueda y Scraping Web

#### WebSearchTool (Brave Search)
- **Funcionalidad**: Búsqueda web con API de Brave Search
- **Estrategia**: Búsqueda estructurada con formateo de resultados para el agente
- **Lugar en el sistema**: Motor de búsqueda principal para información actualizada
- **Parámetros**: `query`

#### DDGSearchTool (DuckDuckGo)
- **Funcionalidad**: Búsqueda web alternativa con DuckDuckGo
- **Estrategia**: Búsqueda distribuida en el tiempo para evitar límites de rate
- **Lugar en el sistema**: Motor de búsqueda secundario y para análisis web
- **Parámetros**: `query`, `account_id`, `max_results`

#### WebScraperTool
- **Funcionalidad**: Extracción de contenido de páginas web específicas
- **Estrategia**: Scraping robusto con manejo de diferentes formatos web
- **Lugar en el sistema**: Herramienta de extracción de contenido detallado
- **Parámetros**: `url`

### 5. Productividad Personal

#### Gestión de Notas
- **AddNoteTool**: Crear notas personales
- **GetNotesTool**: Recuperar notas existentes
- **UpdateNoteTool**: Modificar notas
- **DeleteNoteTool**: Eliminar notas
- **Estrategia**: CRUD completo para gestión de notas personales
- **Lugar en el sistema**: Sistema de notas integrado con memoria vectorial

#### Gestión de Agenda
- **ScheduleEventTool**: Programar eventos
- **GetAgendaTool**: Consultar agenda
- **CancelEventTool**: Cancelar eventos
- **SetReminderTool**: Configurar recordatorios
- **Estrategia**: Gestión temporal integrada con notificaciones
- **Lugar en el sistema**: Asistente personal para organización temporal

### 6. Generación de Contenido

#### ImageGenerationTool
- **Funcionalidad**: Generación de imágenes a partir de descripciones textuales
- **Estrategia**: Integración con Vertex AI para generación visual
- **Lugar en el sistema**: Herramienta de creación de contenido visual
- **Parámetros**: `prompt`, `account_id`, `telegram_id`

#### MindmapGeneratorTool
- **Funcionalidad**: Generación de mapas mentales visuales y dinámicos
- **Estrategia**: Análisis de conceptos y generación de datos para renderizado frontend
- **Lugar en el sistema**: Herramienta de visualización de conocimiento
- **Parámetros**: `document_content`, `topic_hint`, `concept_query`, `account_id`

#### ImageBackgroundEraserTool
- **Funcionalidad**: Procesamiento de imágenes para eliminar fondos
- **Estrategia**: Integración con APIs de procesamiento de imágenes
- **Lugar en el sistema**: Herramienta de edición visual
- **Parámetros**: `image_data`, `account_id`

### 7. Integración y Automatización

#### GitHubRepoTool
- **Funcionalidad**: Interacción con repositorios de GitHub
- **Estrategia**: API de GitHub para análisis y gestión de código
- **Lugar en el sistema**: Herramienta de desarrollo y análisis de código
- **Parámetros**: `repository_url`, `action`, `github_token`

#### ScheduleToolExecutionTool
- **Funcionalidad**: Programación de ejecución de herramientas
- **Estrategia**: Sistema de cron para automatización de tareas
- **Lugar en el sistema**: Motor de automatización y tareas programadas
- **Parámetros**: `tool_name`, `schedule_time`, `parameters`, `account_id`

## Metodología de Integración

### Patrón de Diseño
1. **Herencia de BaseTool**: Todas las herramientas extienden `langchain_core.tools.BaseTool`
2. **Esquemas Pydantic**: Validación robusta de entrada con `args_schema`
3. **Manejo de Errores**: Try-catch individual en el ensamblador
4. **Logging Estructurado**: Sistema de logging detallado para debugging
5. **Asincronía**: Soporte para operaciones asíncronas cuando es necesario

### Flujo de Ejecución
1. **Instanciación**: El ensamblador crea instancias con parámetros específicos del usuario
2. **Validación**: Pydantic valida los parámetros de entrada
3. **Ejecución**: Método `_run` o `_arun` ejecuta la lógica de negocio
4. **Resultado**: Retorna resultado estructurado para el agente
5. **Logging**: Registra operación para auditoría y debugging

## Consideraciones Técnicas

### Manejo de Estado
- **account_id**: Identificador universal para personalización
- **workspace_id**: Contexto de trabajo para organización
- **telegram_id**: Integración específica con Telegram

### Optimización
- **Singleton LLMs**: Reutilización de modelos para eficiencia
- **Caching**: Almacenamiento en caché para operaciones frecuentes
- **Rate Limiting**: Control de velocidad para APIs externas

### Seguridad
- **Validación de entrada**: Esquemas Pydantic estrictos
- **Sanitización**: Limpieza de datos de entrada
- **Autenticación**: Verificación de permisos por cuenta

## Documentación Detallada por Categorías

Para información más detallada sobre cada categoría de herramientas, consulta los siguientes documentos especializados:

### 📚 [Herramientas de Memoria y Conocimiento](./herramientas-memoria-conocimiento.md)
Documentación completa sobre el sistema de memoria vectorial, búsqueda semántica y gestión de conocimiento personal.

### 🔍 [Herramientas de Análisis y Procesamiento](./herramientas-analisis.md)
Guía detallada sobre las capacidades de análisis, generación de insights y procesamiento de información.

### 🌐 [Herramientas de Búsqueda Web y Scraping](./herramientas-web-busqueda.md)
Documentación sobre motores de búsqueda, scraping web y integración con fuentes externas.

### 🎯 [Herramientas de Productividad y Generación de Contenido](./herramientas-productividad-contenido.md)
Información sobre gestión personal, generación de contenido visual y automatización de tareas.

## Guías de Implementación

### Para Desarrolladores
- **Estructura de Herramientas**: Cada herramienta sigue el patrón `BaseTool` de LangChain
- **Esquemas Pydantic**: Validación robusta con esquemas tipados
- **Manejo de Errores**: Sistema de logging y recuperación de errores
- **Testing**: Pruebas unitarias y de integración para cada herramienta

### Para Administradores
- **Configuración**: Variables de entorno y configuración de APIs
- **Monitoreo**: Métricas de rendimiento y salud del sistema
- **Escalabilidad**: Consideraciones para despliegue en producción
- **Seguridad**: Mejores prácticas de seguridad y privacidad

## Conclusión

El sistema de herramientas de Kognito proporciona una arquitectura robusta y extensible que permite al agente de IA realizar tareas complejas de manera eficiente. La modularidad del diseño facilita el mantenimiento y la adición de nuevas funcionalidades, mientras que la integración con LangChain garantiza compatibilidad y estabilidad.

La documentación detallada en los documentos especializados proporciona la información necesaria para entender, implementar y mantener cada categoría de herramientas, asegurando que el sistema pueda evolucionar y adaptarse a las necesidades cambiantes de los usuarios.
