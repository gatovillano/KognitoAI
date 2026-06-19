# Documentación Completa de KognitoAI
**Un proyecto de Kognito AI Labs**

Este documento ofrece una explicación exhaustiva sobre las funciones, estructura, lógica y espíritu del proyecto KognitoAI, actualizado a su estado actual en 2026. KognitoAI es un sistema modular de **Inteligencia Aumentada (IAu)** diseñado para integrar diversas funcionalidades de inteligencia artificial, gestión de conocimiento profundo y soberanía de datos a través de múltiples plataformas, como Telegram y una aplicación web moderna. El objetivo de esta documentación es detallar la arquitectura del proyecto, sus componentes clave, la lógica operativa detrás de su construcción y la visión que impulsa su desarrollo.

## Espíritu de KognitoAI

KognitoAI se fundamenta en los principios de **Soberanía Cognitiva**, modularidad e independencia de plataforma. El sistema centraliza la gestión de datos del usuario —que incluye notas, agendas, documentos, memorias vectoriales y grafos de conocimiento— y expone estas funcionalidades a través de una API robusta basada en FastAPI.

La visión detrás de KognitoAI es crear un **"Exocerebro Digital"** seguro, escalable y centrado en el usuario que no solo recuerde interacciones previas, sino que sea capaz de conectar ideas complejas de forma proactiva. Un elemento clave de esta visión es el concepto de **Identidad Universal** (a través de un `account_id` único) y el **"Second Me"**, una instancia de IA personalizada que replica el razonamiento y estilo del usuario basándose en su propio historial de conocimiento.

## Características Principales Actualizadas

*   📋 **Documentación del Sistema de Agentes**: Ver [`SISTEMA_AGENTES_ACTUAL.md`](SISTEMA_AGENTES_ACTUAL.md) para detalles completos sobre arquitectura, implementaciones y uso de agentes.
*   📘 **Manual de Usuario y Guía Funcional**: Ver [`Manual_Usuario_y_Funcional_KognitoAI.md`](Manual_Usuario_y_Funcional_KognitoAI.md) para una explicación exhaustiva módulo por módulo sobre para qué sirve cada vista y cómo se utiliza.
*   🏢 **Dossier Corporativo y Propuesta de Valor**: Ver [`Propuesta_Valor_y_Funcionalidades_Corporativas_KognitoAI.md`](Propuesta_Valor_y_Funcionalidades_Corporativas_KognitoAI.md) para una evaluación comercial, retorno de inversión (ROI), gobernanza de TI y modelos de despliegue orientados a la adquisición del software por parte de una empresa.
*   **Identidad Universal y "Second Me"**: Gestión de datos coherente en Telegram y WebApp mediante un UUID único y alineación profunda de la IA con el usuario.
*   **Grafo de Conocimiento Neuronal (Neo4j)**: Modelado de relaciones complejas entre entidades y conceptos, permitiendo el descubrimiento de conexiones invisibles y razonamiento relacional.
*   **Memoria a Largo Plazo y RAG 2.0**: Implementación avanzada de *Retrieval-Augmented Generation* usando **PostgreSQL + pgvector**, proporcionando respuestas con citas exactas al documento fuente.
*   **Agentes de Investigación Profunda (Deep Research)**: Agentes autónomos que planifican y ejecutan tareas de investigación multietapa en internet y bases de datos internas.
*   **Ecosistema de Módulos 360°**: Gestión integrada de Workspaces, Agenda inteligente, Tablas dinámicas y Centro de Análisis.
*   **Procesamiento Multimodal**: Capacidades de visión (OCR avanzado con Mistral Vision) y voz (transcripción con Whisper y análisis emocional con emotion2vec).
*   **Extensibilidad MCP**: Conectividad dinámica con sistemas externos (ERP, CRM, GitHub) mediante el *Model Context Protocol*.
*   **Seguridad Empresarial**: Integración con AWS IAM/OIDC y soporte para despliegues locales (On-Premise) y "Air-Gapped".

## Estructura del Proyecto

El proyecto KognitoAI está organizado en directorios específicos, cada uno con un rol definido en el sistema general.

### Archivos del Directorio Raíz
*   `.env.example`: Plantilla de configuración para claves de API, credenciales de bases de datos y ajustes de LLM.
*   `docker-compose.yml`: Define la orquestación de microservicios: `db` (Postgres), `core` (API), `frontend` (Next.js), `neo4j`, `redis` y `telegram_client`.
*   `Dockerfile.core.hybrid`, `Dockerfile.frontend`, `Dockerfile.telegram`: Configuraciones Docker optimizadas para cada componente, incluyendo soporte para GPU NVIDIA.
*   `run_api.py`, `run_telegram_bot.py`: Scripts de inicio para el servidor central y el bot de Telegram.
*   `nginx.conf`: Configuración del proxy inverso para el enrutamiento seguro de tráfico.
*   `kai.py`: Script principal de orquestación y utilidades de alto nivel.

### Directorio Core (`core/`)
Contiene la lógica de negocio principal e independiente de la interfaz.
*   [`agent.py`](core/agent.py): Define el grafo de ejecución del agente de IA usando LangGraph.
*   [`config.py`](core/config.py): Gestión centralizada de configuraciones y validación de entorno.
*   [`database.py`](core/database.py): Capa de persistencia relacional y vectorial (SQLAlchemy + pgvector).
*   [`memory_manager.py`](core/memory_manager.py): Gestión de memorias vectoriales y recuperación semántica.
*   [`llm_manager.py`](core/llm_manager.py): Orquestación multi-modelo (Gemini, OpenAI, Anthropic, Ollama).
*   [`notes_manager.py`](core/notes_manager.py), [`agenda_manager.py`](core/agenda_manager.py): Lógica para notas estructuradas y eventos.
*   `agents/`: Subdirectorio con agentes especializados como el `DeepResearcher`.

### Directorio de Grafo de Conocimiento (`knowledge_graph/`)
Lógica especializada para el procesamiento relacional.
*   [`graph_database.py`](knowledge_graph/graph_database.py): Interfaz de bajo nivel con Neo4j.
*   [`conceptual_graph_processor.py`](knowledge_graph/conceptual_graph_processor.py): Extracción de conceptos mediante LLMs.
*   [`graph_reasoning_node.py`](knowledge_graph/graph_reasoning_node.py): Nodo de razonamiento neuronal para el grafo.

### Directorio de API (`api/`)
Endpoints de FastAPI que exponen las capacidades del sistema.
*   [`main.py`](api/main.py): Inicialización de la aplicación y montaje de routers.
*   [`chat.py`](api/chat.py): Manejo de streaming de chat y WebSockets.
*   [`knowledge_graph.py`](api/knowledge_graph.py): Endpoints para visualización de grafos.
*   [`workspaces.py`](api/workspaces.py), [`notes.py`](api/notes.py): Gestión de módulos específicos.

### Directorio de Herramientas (`tools/`)
Herramientas LangChain que el agente utiliza para interactuar con el mundo.
*   [`knowledge_search_tool.py`](tools/knowledge_search_tool.py): Búsqueda semántica en la memoria organizacional.
*   [`graph_cypher_generator_tool.py`](tools/graph_cypher_generator_tool.py): Consultas dinámicas a Neo4j.
*   [`deep_research_tool.py`](tools/deep_research_tool.py): Ejecutor de investigaciones autónomas.

### Directorio Frontend (`src/`)
Aplicación web construida con Next.js y Tailwind CSS.
*   `src/app/(dashboard)/`: Layouts y páginas para chat, RAG, grafos y configuración.
*   `src/components/`: Componentes de UI (AppShell, GraphVisualization, MarkdownRenderer).
*   `src/lib/`: Cliente de API (`api.ts`) y modelos de datos.

### Directorio Telegram Client (`telegram_client/`)
Interfaz conversacional específica para Telegram.
*   [`bot_manager.py`](telegram_client/bot_manager.py): Gestión del bot y coordinación de handlers.
*   `handlers/`: Lógica para procesar comandos, voz e imágenes.

## Lógica y Construcción del Sistema

La arquitectura de KognitoAI es **desacoplada y basada en grafos de estado**. La API Core actúa como el orquestador central, mientras que los servicios de datos proporcionan la infraestructura de persistencia y razonamiento.

### Gestión de Datos del Usuario
Todos los datos están vinculados a un `account_id` universal. El sistema utiliza un pipeline de **Refinamiento Cognitivo** gestionado por el `NoteService`, que fragmenta, clasifica y versiona el conocimiento para mantener la coherencia relacional.

### Agente de IA y Motor de Planes
El corazón de la inteligencia es un grafo de estados (LangGraph) que permite al asistente planificar misiones complejas, ejecutar herramientas dinámicamente mediante el `OperationParser` y generar respuestas basadas en contexto profundo.

### Flujo de Datos y Comunicación
1.  **Entrada**: El usuario interactúa vía Telegram o WebApp (Texto, Voz, Imagen).
2.  **Identificación**: El sistema asocia la entrada al `account_id` y recupera el perfil del "Second Me".
3.  **Razonamiento**: El agente consulta la memoria vectorial (RAG) y el grafo (Neo4j) para obtener contexto histórico y relacional.
4.  **Acción**: El agente invoca herramientas (búsqueda web, ejecución de código, etc.) según el plan generado.
5.  **Respuesta**: Se genera una respuesta enriquecida con citas y evidencia, enviada en tiempo real vía WebSockets.

## Tecnologías y Despliegue

*   **Backend**: Python 3.9+, FastAPI, SQLAlchemy, LangChain, LangGraph.
*   **Bases de Datos**: PostgreSQL (pgvector), Neo4j (Cypher), Redis (Caching).
*   **IA**: LiteLLM, Google Gemini 2.0, Whisper (Voz), Mistral Vision.
*   **Frontend**: Next.js 14+, TypeScript, Tailwind CSS, Framer Motion.
*   **Despliegue**: Docker, Docker Compose, Nginx, soporte para AWS EKS.

## Conclusión

KognitoAI representa la vanguardia de la **Inteligencia Aumentada**. Su arquitectura modular, su capacidad de razonamiento neuronal y su enfoque inquebrantable en la soberanía de los datos lo convierten en una solución única para organizaciones que buscan escalar su capacidad intelectual de forma segura y eficiente.

---
Documentación generada para KognitoAI - © 2026