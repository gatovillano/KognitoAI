# Propuesta de Refactorización de Herramientas

Este documento detalla la propuesta de refactorización de las herramientas del agente de IA, con el objetivo de mejorar su selección, uso y eficiencia general.

### Resumen del Plan de Refactorización de Herramientas

1.  **Recopilación y Análisis Detallado**: Hemos revisado exhaustivamente cada herramienta, sus funciones y parámetros.
2.  **Identificación de Redundancias y Solapamientos**: Se detectó una notable redundancia en las herramientas de búsqueda interna y en las de activación de análisis en segundo plano.
3.  **Evaluación de Claridad y Precisión de Descripciones**: Se identificaron oportunidades para hacer las descripciones más claras y precisas, especialmente para guiar al LLM en la selección correcta.
4.  **Propuesta de Agrupación y Categorización**: Se estableció una categorización lógica de las herramientas para una mejor organización y comprensión del ecosistema.
5.  **Recomendaciones de Diseño y Uso**:
    *   **Consolidación de Búsqueda Interna**: Se recomienda crear una única herramienta `unified_knowledge_search` que integre y orqueste las funcionalidades de `NaturalQueryInterpreterTool`, `MultiQuerySearchTool`, `MemorySearchOptimizedTool`, `MemoryContextSearchTool`, `VectorDBSearchTool` y `VectorDBQueryTool`. Esto simplificará drásticamente la selección para el LLM.
    *   **Consolidación de Activación de Análisis**: Se propone una única herramienta `trigger_background_analysis` para iniciar los diversos procesos de análisis en segundo plano (`KnowledgeAnalysisTool`, `ProactiveKnowledgeLinkerTool`, `ConversationHistoryAnalyzerTool`, `ConversationContextAnalyzerTool`).
    *   **Clarificación de GitHub**: Optimizar la descripción de `GitHubRepoTool` para que sea más concisa y orientada a los casos de uso.
    *   **Mantenimiento de Herramientas Especializadas**: Las herramientas específicas de Notas, Agenda, Creación/Manipulación de Imágenes y Automatización se mantendrían como están, dado su propósito claro y su eficiencia actual.

---

**Diagrama de Arquitectura de Herramientas Propuesto (Mermaid):**

Este diagrama ilustra la estructura de herramientas más limpia y eficiente que proponemos:

```mermaid
graph TD
    A[Agente de IA (LLM)] --> B(Herramientas Simplificadas)

    B --> B1(unified_knowledge_search)
    B1 --> D1[Base de Conocimiento Interna]
    B1 --> D2[Documentos del Usuario]
    B1 --> D3[Memorias del Usuario]
    B1 --> D4[Historial de Conversaciones]
    B1 --> D5[Workspaces y Temas]

    B --> B2(trigger_background_analysis)
    B2 --> E1[Análisis Completo]
    B2 --> E2[Análisis Reciente]
    B2 --> E3[Análisis por Tema]
    B2 --> E4[Análisis de Historial de Conversación]
    B2 --> E5[Análisis de Contexto de Conversación]

    B --> B3(Notas y Agenda)
    B3 --> F1(add_note_tool)
    B3 --> F2(get_notes_tool)
    B3 --> F3(update_note_tool)
    B3 --> F4(delete_note_tool)
    B3 --> F5(schedule_event_tool)
    B3 --> F6(get_agenda_tool)
    B3 --> F7(cancel_event_tool)
    B3 --> F8(set_reminder_tool)

    B --> B4(Búsqueda Web Ampliada)
    B4 --> G1(web_search)
    B4 --> G2(web_scraper_tool)
    B4 --> G3(comprehensive_web_analyzer)

    B --> B5(Gestión GitHub)
    B5 --> H1(github_repository_explorer)

    B --> B6(Análisis de Contenido Específico)
    B6 --> I1(analyze_text_for_insights)
    B6 --> I2(analyze_code_for_insights)
    B6 --> I3(scoped_rag_analysis)

    B --> B7(Creación y Manipulación Visual)
    B7 --> J1(generate_image_tool)
    B7 --> J2(image_background_eraser)
    B7 --> J3(mindmap_generator_tool)

    B --> B8(Grafos de Conocimiento Cognee)
    B8 --> K1(cognee_conceptual_processing_tool)
    B8 --> K2(cognee_knowledge_graph_tool)

    B --> B9(Recuperación de Insights y Análisis Guardados)
    B9 --> L1(get_analysis_results_tool)
    B9 --> L2(get_proactive_insights_tool)

    B --> B10(Automatización y Programación)
    B10 --> M1(schedule_tool_execution)
    B10 --> M2(list_scheduled_tools)

    style B1 fill:#f9f,stroke:#333,stroke-width:2px
    style B2 fill:#f9f,stroke:#333,stroke-width:2px