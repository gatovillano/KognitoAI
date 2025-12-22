# Implementación del Agente de Investigación Profunda

Este documento detalla la implementación del nuevo agente de investigación profunda en Kognito AI, que utiliza un enfoque basado en LangGraph para una investigación estructurada y la integración con la API de Tavily para búsquedas web avanzadas.

## Visión General

El agente de investigación profunda está diseñado para realizar investigaciones exhaustivas sobre un tema dado, descomponiendo la consulta en subpreguntas, ejecutando búsquedas y sintetizando los hallazgos en un informe coherente. La arquitectura se basa en un grafo de estados de LangGraph, que coordina un "Supervisor" y múltiples "Investigadores" especializados.

## Componentes Clave

### 1. `core/agents/deep_researcher_config.py`

Define la configuración del agente, incluyendo:
- `SearchAPI`: Enumeración de proveedores de API de búsqueda (actualmente Tavily, OpenAI, Anthropic).
- `MCPConfig`: Configuración para servidores del Protocolo de Contexto de Modelos (MCP).
- Parámetros generales: `max_structured_output_retries`, `allow_clarification`, `max_concurrent_research_units`.
- Parámetros de investigación: `search_api`, `max_researcher_iterations`, `max_react_tool_calls`.
- Configuración de modelos: `summarization_model`, `research_model`, `compression_model`, `final_report_model` y sus límites de tokens.
- `max_content_length`: Límite de caracteres para el contenido de la página web antes del resumen.

### 2. `core/agents/deep_researcher_state.py`

Define las clases `Pydantic` para los estados del grafo y los outputs estructurados:
- `ConductResearch`: Herramienta para delegar temas de investigación.
- `ResearchComplete`: Herramienta para señalar la finalización de la investigación.
- `Summary`: Output estructurado para resúmenes de investigación.
- `ClarifyWithUser`: Output estructurado para preguntas de clarificación al usuario.
- `ResearchQuestion`: Output estructurado para la pregunta de investigación principal.
- `AgentInputState`, `AgentState`, `SupervisorState`, `ResearcherState`, `ResearcherOutputState`: Tipos de `TypedDict` y `BaseModel` que definen la estructura de datos que fluye a través del grafo.

### 3. `core/agents/deep_researcher_prompts.py`

Contiene todos los prompts del sistema y plantillas de prompts utilizadas por los diferentes nodos del agente:
- `clarify_with_user_instructions`: Prompt para decidir si se necesita clarificación del usuario.
- `transform_messages_into_research_topic_prompt`: Prompt para convertir mensajes de usuario en un tema de investigación detallado.
- `lead_researcher_prompt`: Prompt para el supervisor, que guía la delegación de tareas.
- `research_system_prompt`: Prompt para los investigadores individuales, guiando el uso de herramientas de búsqueda y reflexión.
- `compress_research_system_prompt`: Prompt para comprimir y sintetizar los hallazgos de la investigación.
- `final_report_generation_prompt`: Prompt para generar el informe final completo.
- `summarize_webpage_prompt`: Prompt para resumir el contenido de páginas web.

### 4. `core/agents/deep_researcher_utils.py`

Contiene funciones de utilidad y herramientas personalizadas:
- `time_function`: Decorador para medir el tiempo de ejecución de funciones asíncronas.
- `tavily_search`: Herramienta de búsqueda web que utiliza la API de Tavily para buscar y resumir contenido.
- `tavily_search_async`: Ejecuta múltiples consultas de Tavily de forma asíncrona.
- `summarize_webpage`: Utiliza un LLM para resumir el contenido de páginas web.
- `think_tool`: Herramienta de reflexión para la planificación estratégica.
- `get_search_tool`: Configura y devuelve herramientas de búsqueda basadas en el proveedor `SearchAPI` seleccionado.
- `get_all_tools`: Ensambla el conjunto completo de herramientas disponibles para los investigadores.
- `get_notes_from_tool_calls`: Extrae notas de las llamadas a herramientas.
- `get_today_str`: Devuelve la fecha actual formateada.
- `get_config_value`: Extrae valores de la configuración, manejando enumeraciones.
- `get_tavily_api_key`: Obtiene la clave API de Tavily.
- `execute_tool_safely`: Ejecuta herramientas de forma segura con manejo de errores.

### 5. `core/agents/deep_researcher.py`

El archivo principal que define y compila el grafo de LangGraph.
- **Nodos del Grafo Principal**:
  - `clarify_with_user`: Nodo inicial para determinar si se requiere más información del usuario.
  - `write_research_brief`: Genera un resumen de la investigación a partir de los mensajes del usuario.
  - `research_supervisor`: El subgrafo principal que orquesta la investigación.
  - `final_report_generation`: Genera el informe final.
- **Subgrafo del Supervisor**:
  - `supervisor`: Decide la estrategia de investigación y delega tareas.
  - `supervisor_tools`: Ejecuta las herramientas llamadas por el supervisor (principalmente `ConductResearch`).
- **Subgrafo del Investigador**:
  - `researcher`: Realiza la investigación enfocada utilizando herramientas (como `tavily_search` y `think_tool`).
  - `researcher_tools`: Ejecuta las herramientas llamadas por el investigador.
  - `compress_research`: Comprime y sintetiza los hallazgos de la investigación.
- **Lógica de Transición**: Define las condiciones para la transición entre nodos (`should_continue_research`, `should_continue_supervision`, `should_start_research`).

## Flujo de Ejecución

1.  **Inicio**: El grafo comienza con el nodo `clarify_with_user`.
2.  **Clarificación**: Si se necesita clarificación, el agente formula una pregunta al usuario y termina la ejecución temporalmente. Si no, o si la clarificación está deshabilitada, procede.
3.  **Brief de Investigación**: `write_research_brief` crea un resumen detallado de la investigación.
4.  **Supervisión**: El control pasa al `research_supervisor`, que planifica la investigación y delega temas a investigadores individuales.
    - El supervisor utiliza `ConductResearch` para iniciar sub-investigadores en paralelo.
    - Utiliza `think_tool` para la reflexión estratégica.
    - Si la investigación es suficiente, llama a `ResearchComplete`.
5.  **Investigación Individual**: Cada sub-investigador (`researcher`) utiliza herramientas de búsqueda (`tavily_search`) y reflexión (`think_tool`) para recopilar información sobre su tema asignado.
6.  **Compresión**: Los hallazgos de cada investigador se comprimen y sintetizan en `compress_research`.
7.  **Informe Final**: Una vez que el supervisor considera que la investigación está completa, `final_report_generation` compila todos los hallazgos en un informe completo.

## Integración y Uso

- **Frontend**: El frontend (`src/components/CommonChat.tsx`) ha sido actualizado para mostrar un indicador visual cuando el agente de investigación profunda está activo (`isDeepResearchActive`).
- **API**: El agente se integra a través de la API, donde las llamadas al `deep_researcher` activan este flujo.
- **Variables de Entorno**: Requiere que `TAVILY_API_KEY` esté configurada para la funcionalidad de búsqueda web.

Esta implementación proporciona una base robusta y extensible para capacidades de investigación profunda en Kognito AI.