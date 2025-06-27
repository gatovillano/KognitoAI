# Documentación Completa de Kognito

## 1. Introducción y Visión General del Proyecto

### Nombre del Proyecto
Kognito

### Propósito y Objetivo Principal
Kognito es una plataforma avanzada de inteligencia artificial desarrollada específicamente para 'Puertos Monte y Sierra', con el propósito de abordar los desafíos críticos relacionados con la integración de datos y la toma de decisiones en un entorno portuario complejo. El objetivo principal de Kognito es centralizar datos provenientes de múltiples departamentos —como Mantenimiento, Operaciones, Comercial y Aduanas— y transformarlos en información accionable mediante el uso de tecnologías de procesamiento de lenguaje natural (PLN) y análisis predictivo.

El problema que Kognito resuelve es la fragmentación de datos y la falta de visibilidad integral en las operaciones portuarias. En un entorno donde los datos están dispersos en diferentes sistemas y formatos (bases de datos relacionales, documentos manuales, APIs externas), los gerentes y analistas enfrentan dificultades para obtener una visión unificada que les permita tomar decisiones informadas. Kognito elimina estos silos de datos al integrar información de diversas fuentes, permitiendo a los usuarios realizar consultas en lenguaje natural (por ejemplo, "¿Cuáles son los retrasos esperados en el muelle 3 debido al clima?") y recibir respuestas detalladas, informes personalizados y visualizaciones interactivas en dashboards. Esto no solo mejora la velocidad de la toma de decisiones, sino que también incrementa la precisión al basarse en datos consolidados y análisis de IA.

Además, Kognito automatiza procesos repetitivos como la generación de informes, la gestión de agendas y el envío de notificaciones, liberando tiempo valioso para que el personal se enfoque en tareas estratégicas. Su capacidad para ofrecer insights proactivos —como identificar patrones en fallos de equipos o vincular conocimiento entre documentos mediante herramientas como `proactive_knowledge_linker_tool.py`— añade un valor adicional al anticipar problemas antes de que se conviertan en crisis. Por ejemplo, Kognito puede alertar a un gerente de mantenimiento sobre un posible fallo en una grúa basándose en datos históricos y patrones detectados, permitiendo una intervención preventiva.

Kognito también se destaca por su enfoque en la personalización y la accesibilidad. Los usuarios pueden adaptar dashboards y consultas a sus necesidades específicas, mientras que la integración con Telegram permite recibir notificaciones y realizar consultas rápidas desde dispositivos móviles, ideal para personal operativo en campo. Este enfoque integral asegura que todos los niveles de la organización, desde gerentes hasta técnicos, puedan beneficiarse de la plataforma.

### Visión a Largo Plazo
La visión a largo plazo de Kognito es convertirse en una solución líder no solo para 'Puertos Monte y Sierra', sino para la industria portuaria y logística a nivel global. Se proyecta como una plataforma integral que impulse la digitalización y automatización de procesos operativos y administrativos en puertos de diferentes tamaños y contextos regulatorios. Entre los objetivos futuros se incluyen:

- **Expansión de Capacidades de IA**: Integrar modelos avanzados de aprendizaje automático para ofrecer predicciones más precisas, como mantenimiento predictivo de equipos portuarios (identificando fallos antes de que ocurran mediante análisis de datos históricos y en tiempo real), estimaciones de flujo de carga basadas en datos históricos y externos (como condiciones climáticas o tendencias de mercado), y optimización de rutas logísticas para minimizar costos y tiempos de espera.
- **Soporte Multilingüe**: Adaptar la interfaz y el procesamiento de lenguaje natural para soportar múltiples idiomas, facilitando su uso en puertos internacionales con personal diverso. Esto incluye la capacidad de procesar consultas en español, inglés, y otros idiomas relevantes para la industria marítima.
- **Adaptabilidad Regulatoria**: Incorporar módulos que permitan la personalización de flujos de trabajo y reportes para cumplir con regulaciones aduaneras y operativas de diferentes países. Por ejemplo, generar automáticamente documentación compatible con normativas específicas de la Unión Europea o de países asiáticos.
- **Integración con IoT y Sensores**: Conectar Kognito con dispositivos IoT en tiempo real (como sensores en grúas, contenedores o vehículos) para monitorear condiciones y actualizar datos dinámicamente, mejorando la capacidad de respuesta ante eventos imprevistos como fallos mecánicos o cambios en las condiciones climáticas.
- **Escalabilidad y Personalización**: Diseñar la arquitectura para manejar volúmenes crecientes de datos y usuarios, permitiendo a cada cliente personalizar la plataforma según sus necesidades específicas, ya sea un puerto pequeño con operaciones limitadas o una red logística internacional con múltiples puntos de operación.
- **Sostenibilidad y Eficiencia Energética**: Incorporar análisis de datos para optimizar el consumo energético en operaciones portuarias, como la gestión eficiente de grúas y vehículos, contribuyendo a los objetivos de sostenibilidad de la industria.
- **Colaboración Interorganizacional**: Desarrollar funcionalidades que permitan la colaboración segura entre diferentes entidades (puertos, proveedores, clientes) mediante el intercambio controlado de datos y reportes, fomentando una red logística más integrada.

Kognito aspira a ser una herramienta indispensable en la transformación digital de la industria marítima, promoviendo operaciones más eficientes, sostenibles y seguras mediante el uso de inteligencia artificial. Su visión incluye no solo la mejora operativa, sino también la creación de un ecosistema donde los datos se conviertan en un activo estratégico para la competitividad de sus usuarios.

### Público Objetivo
Kognito está diseñado para satisfacer las necesidades de una amplia gama de usuarios dentro y fuera de 'Puertos Monte y Sierra', cada uno con roles y requerimientos específicos que la plataforma aborda de manera personalizada:

- **Gerentes**: Responsables de la planificación estratégica y la supervisión general de las operaciones portuarias. Necesitan una visión integral de los datos para tomar decisiones basadas en métricas clave (KPIs) como tiempos de inactividad de equipos, volúmenes de carga procesados, costos operativos y cumplimiento normativo. Kognito les proporciona dashboards personalizados y respuestas rápidas a consultas complejas como "¿Qué impacto tendrá el pronóstico del clima en las operaciones de la próxima semana?".
- **Analistas**: Profesionales que trabajan con datos para identificar tendencias, patrones y anomalías. Requieren herramientas avanzadas de análisis y visualización para explorar datos en profundidad, generar informes detallados y proporcionar recomendaciones basadas en evidencia. Kognito les permite realizar análisis predictivos y acceder a herramientas como `analyze_text_for_insights_tool.py` para extraer insights de documentos extensos.
- **Desarrolladores e Ingenieros de Sistemas**: Encargados de integrar Kognito con sistemas existentes, personalizar funcionalidades y mantener la plataforma operativa. Necesitan documentación técnica detallada, acceso a APIs (como las definidas en `run_api.py`), y herramientas para extender las capacidades del sistema, como la integración con GitHub mediante `github_repo_tool.py`.
- **Usuarios Operativos**: Personal de departamentos específicos como Mantenimiento (técnicos que monitorean el estado de grúas y equipos), Operaciones (coordinadores de muelles que gestionan tiempos de carga/descarga), Comercial (gestores de contratos y relaciones con clientes) y Aduanas (inspectores que verifican documentación y cumplimiento). Utilizan Kognito para consultas diarias, como verificar el estado de equipos o documentos pendientes, y para recibir notificaciones en tiempo real a través de Telegram (`telegram_client/notification_scheduler.py`).
- **Stakeholders Externos**: Incluyen socios comerciales, clientes, proveedores y entidades reguladoras que pueden beneficiarse de informes generados por Kognito, como resúmenes de operaciones, certificaciones de cumplimiento o análisis de rendimiento. Kognito asegura que estos informes sean exportables en formatos estándar (PDF, CSV) para facilitar su uso en presentaciones o auditorías.

La plataforma está diseñada para ser intuitiva para usuarios no técnicos, mientras que ofrece profundidad técnica para aquellos con conocimientos avanzados, asegurando que todos los roles dentro de la organización puedan aprovechar sus capacidades al máximo.

### Beneficios Clave
Kognito ofrece una serie de beneficios que impactan directamente en la eficiencia operativa, la toma de decisiones y la competitividad de 'Puertos Monte y Sierra'. Estos beneficios se derivan de su arquitectura avanzada y de las tecnologías de IA integradas:

- **Integración de Datos sin Precedentes**: Unifica información de múltiples fuentes (bases de datos internas como PostgreSQL gestionadas por `core/database.py`, APIs externas como datos meteorológicos, documentos manuales subidos por usuarios) en una sola plataforma, eliminando silos de datos y proporcionando una visión holística de las operaciones portuarias. Esto permite, por ejemplo, correlacionar datos de mantenimiento con retrasos operativos para identificar causas raíz.
- **Toma de Decisiones Mejorada**: Transforma datos complejos y voluminosos en insights accionables mediante análisis de IA, permitiendo a los usuarios tomar decisiones informadas rápidamente. Por ejemplo, un gerente puede identificar cuellos de botella en tiempo real y reasignar recursos con un solo clic, basándose en respuestas generadas por el agente de IA en `core/agent.py`.
- **Eficiencia Operativa**: Automatiza tareas repetitivas como la generación de informes (mediante `tools/analyze_text_for_insights_tool.py`), la gestión de agendas (`core/agenda_manager.py`), y el envío de notificaciones (`telegram_client/notification_scheduler.py`), reduciendo significativamente el esfuerzo manual y los errores humanos. Esto permite al personal centrarse en actividades de mayor valor estratégico.
- **Interacción Intuitiva con PLN**: Gracias al procesamiento de lenguaje natural implementado en `core/agent.py` con modelos como Google Gemini (`gemini-2.0-flash`), los usuarios pueden interactuar con Kognito haciendo preguntas en un lenguaje cotidiano, sin necesidad de conocimientos técnicos avanzados. Esto democratiza el acceso a datos y análisis, permitiendo que incluso personal operativo pueda obtener información crítica sin formación especializada.
- **Personalización Avanzada**: Ofrece la capacidad de adaptar dashboards, consultas e informes a las necesidades específicas de cada usuario o departamento, asegurando que cada rol obtenga la información más relevante para su trabajo. Por ejemplo, un técnico de mantenimiento puede configurar un dashboard para monitorear solo el estado de equipos específicos, mientras que un gerente puede ver un resumen de todos los departamentos.
- **Insights Proactivos**: Mediante herramientas como `analyze_text_for_insights` y `proactive_knowledge_linker_tool.py`, Kognito identifica patrones y conexiones en los datos antes de que los usuarios las soliciten, anticipándose a problemas y sugiriendo soluciones. Por ejemplo, puede detectar una correlación entre fallos de equipos y condiciones climáticas pasadas, alertando al equipo de mantenimiento antes de que ocurra un problema similar.
- **Escalabilidad y Robustez**: Diseñado para manejar grandes volúmenes de datos y un número creciente de usuarios, Kognito puede adaptarse a las necesidades futuras de 'Puertos Monte y Sierra' sin comprometer el rendimiento. Su arquitectura basada en Docker (`docker-compose.yml`) y configuraciones para Kubernetes asegura que pueda escalar horizontalmente en entornos de producción.
- **Accesibilidad Multiplataforma**: Disponible tanto en interfaces web (con diseño responsivo para móvil y escritorio en `src/components/AppShell.tsx`) como a través de un bot de Telegram (`run_telegram_bot.py`), permitiendo a los usuarios acceder a información crítica desde cualquier lugar, ya sea en la oficina o en el campo. Esto es especialmente útil para personal operativo que necesita actualizaciones en tiempo real mientras está en los muelles.
- **Seguridad y Confidencialidad**: Implementa principios estrictos de seguridad, como autenticación mediante JWT (`core/config.py` con `jwt_secret_key`), encriptación de datos sensibles, y control de acceso basado en roles, asegurando que la información confidencial esté protegida y solo accesible para usuarios autorizados.
- **Mejora Continua del Contexto**: A través de la gestión de memoria en `core/memory_manager.py` y la sumarización de historiales en `core/agent.py` (`summarize_history_in_background`), Kognito aprende de las interacciones pasadas para ofrecer respuestas más relevantes y personalizadas con el tiempo, mejorando la experiencia del usuario de manera continua.

Estos beneficios posicionan a Kognito como una herramienta transformadora que no solo resuelve problemas operativos inmediatos, sino que también prepara a 'Puertos Monte y Sierra' para los desafíos futuros de la industria logística.

## 2. Arquitectura y Diseño del Sistema

### Componentes Principales
Kognito está estructurado como un sistema modular, donde cada componente tiene una función específica pero trabaja en conjunto para ofrecer una experiencia fluida y potente. La arquitectura está diseñada para ser escalable, mantenible y adaptable a las necesidades cambiantes de un entorno portuario. A continuación, se describen los módulos principales identificados a partir de la estructura del código en los directorios `core/`, `tools/`, `src/`, y otros, con referencias específicas a archivos y funcionalidades:

- **Módulo de Ingesta de Datos**:
  - **Función**: Recolecta datos de diversas fuentes internas y externas para centralizar la información en Kognito. Las fuentes internas incluyen bases de datos relacionales de departamentos como Mantenimiento (estado de equipos, historial de reparaciones), Operaciones (tiempos de carga/descarga, asignación de muelles), Comercial (contratos, volúmenes de carga, análisis de clientes) y Aduanas (documentación, cumplimiento normativo). Las fuentes externas abarcan APIs de terceros (por ejemplo, datos meteorológicos o de tráfico marítimo) y documentos manuales subidos por usuarios (PDF, DOCX, TXT).
  - **Implementación**: Utiliza conectores personalizados para bases de datos y APIs, así como herramientas de scraping web definidas en `tools/web_scraper_tool.py` (con clase `WebScraperTool` para extraer contenido de URLs específicas). Los documentos subidos se procesan mediante `utils/document_parser.py`, que extrae texto y metadatos para su posterior análisis. Los datos crudos se limpian y estructuran antes de ser almacenados en bases de datos optimizadas para búsqueda y análisis.
  - **Archivos Relevantes**: `utils/document_parser.py` (procesamiento de documentos), `tools/web_scraper_tool.py` (scraping de datos externos), `tools/web_search_tool.py` (búsqueda web para enriquecer datos con información externa mediante `Brave Search API` configurada en `core/config.py`).
  - **Detalles Técnicos**: La ingesta de datos es un proceso asíncrono que asegura un impacto mínimo en el rendimiento del sistema, permitiendo la actualización en tiempo real de datos críticos como el estado de equipos o retrasos operativos. La configuración de APIs externas, como `BRAVE_SEARCH_API_KEY` en `core/config.py`, permite integrar datos de búsqueda web cuando los datos internos no son suficientes para responder a una consulta.

- **Módulo de Procesamiento de Lenguaje Natural (PLN)**:
  - **Función**: Permite a los usuarios interactuar con Kognito mediante preguntas en lenguaje natural, traduciendo estas consultas a comandos estructurados que el sistema puede procesar. Genera respuestas comprensibles y contextuales, adaptadas al dominio portuario, asegurando que incluso usuarios no técnicos puedan obtener información compleja sin necesidad de aprender sintaxis o interfaces técnicas.
  - **Implementación**: Basado en modelos de IA como Google Gemini (`gemini-2.0-flash` configurado en `core/config.py` como `GOOGLE_MAIN_MODEL_NAME`), integrados en `core/agent.py` mediante funciones como `initialize_llms` (que carga los modelos al iniciar el servidor) y `create_and_run_agent` (que procesa las consultas de los usuarios). Utiliza contexto del usuario mediante `_get_user_context` para personalizar respuestas, incorporando información de perfil y memorias relevantes obtenidas de `core/memory_manager.py`. La biblioteca LangChain (`langchain_google_genai.ChatGoogleGenerativeAI`) es central para orquestar la interacción entre el modelo de lenguaje, las herramientas y la memoria.
  - **Archivos Relevantes**: `core/agent.py` (núcleo del procesamiento de consultas con `create_and_run_agent`), `core/config.py` (configuración de modelos de lenguaje y temperatura con `llm_temperature`), `tools/knowledge_analysis_tool.py` (análisis semántico de consultas mediante `KnowledgeAnalysisTool`).
  - **Detalles Técnicos**: El módulo de PLN utiliza un enfoque de "prompt dinámico centralizado" (como se describe en los comentarios de `core/agent.py`), donde un único `SystemMessage` se construye al inicio de cada interacción, integrando el perfil del usuario, memorias relevantes, instrucciones de identificación (`account_id`, `telegram_id`), y guías para el uso de herramientas. Esto asegura que las respuestas sean contextuales y precisas. Además, el sistema maneja errores de parsing (`handle_parsing_errors=True` en `AgentExecutor`) para garantizar robustez ante entradas inesperadas del usuario.

- **Módulo de Análisis y Generación de Informes**:
  - **Función**: Procesa datos ingeridos mediante algoritmos de análisis descriptivo (resúmenes históricos de operaciones), predictivo (predicciones de fallos de equipos o retrasos basados en patrones) y prescriptivo (recomendaciones de acción como reasignación de recursos). Produce informes detallados y personalizados que pueden exportarse a formatos como PDF o CSV para uso interno o externo.
  - **Implementación**: Incluye herramientas específicas como `analyze_text_for_insights_tool.py` (con clase `AnalyzeTextForInsightsTool` para análisis de texto y extracción de insights) y `proactive_knowledge_linker_tool.py` (con `ProactiveKnowledgeLinkerTool` para vincular conocimiento entre documentos y datos, utilizando umbrales de similitud definidos en `core/config.py` como `DUPLICITY_SIMILARITY_THRESHOLD` y `SYNERGY_SIMILARITY_THRESHOLD`). Los resultados se formatean para ser legibles y accionables mediante métodos como `_format_result` en `analyze_text_for_insights_tool.py`.
  - **Archivos Relevantes**: `tools/analyze_text_for_insights_tool.py` (análisis de texto), `utils/analyze_text_for_insights.py` (lógica subyacente de análisis), `tools/proactive_knowledge_linker_tool.py` (vinculación de conocimiento), `core/config.py` (parámetros de umbrales para análisis).
  - **Detalles Técnicos**: El análisis se realiza de manera asíncrona para manejar grandes volúmenes de datos sin bloquear la interfaz del usuario. Por ejemplo, `AnalyzeTextForInsightsTool` utiliza `_arun` para procesar texto de forma asíncrona y devolver resultados formateados. Los umbrales configurables en `core/config.py` permiten ajustar la sensibilidad del análisis, como detectar duplicidad (similitud > 0.90) o sinergia (similitud > 0.65), lo que asegura que los insights sean relevantes y no redundantes. La generación de informes puede integrarse con dashboards para visualización inmediata o exportarse para presentaciones.

- **Módulo de Dashboards e Interfaz de Usuario**:
  - **Función**: Proporciona una interfaz web intuitiva para visualizar datos, personalizar dashboards, realizar consultas en lenguaje natural y gestionar tareas operativas como notas y agendas. Soporta diseño responsivo para acceso desde dispositivos móviles y de escritorio, asegurando accesibilidad para todos los usuarios, ya sea en la oficina o en el campo.
  - **Implementación**: Construido con React y Next.js, con componentes clave como `AppShell.tsx` (estructura principal de la aplicación con un sidebar colapsable y header con toggle de tema en `src/components/AppShell.tsx`), `Sidebar.tsx` (navegación entre secciones como Agenda, Notas, RAG en `src/components/Sidebar.tsx`), y páginas específicas como `rag/page.tsx` (análisis de documentos y colecciones en `src/app/(dashboard)/rag/page.tsx`) y `chat/[id]/page.tsx` (interacción conversacional con IA en `src/app/(dashboard)/chat/[id]/page.tsx`). Utiliza Tailwind CSS para estilos (`tailwind.config.ts`) y componentes de `shadcn/ui` (`src/components/ui/`) para una experiencia de usuario consistente con elementos como botones, diálogos y tablas.
  - **Archivos Relevantes**: `src/components/AppShell.tsx` (estructura responsiva de la aplicación), `src/components/Sidebar.tsx` (navegación entre módulos), `src/app/(dashboard)/rag/page.tsx` (interfaz para análisis RAG), `src/app/(dashboard)/chat/[id]/page.tsx` (chat con IA), `tailwind.config.ts` (estilos).
  - **Detalles Técnicos**: La interfaz utiliza un diseño responsivo que adapta el layout según el tamaño de la pantalla (`useMediaQuery` en `AppShell.tsx` para detectar desktop vs móvil). En desktop, el sidebar es persistente y colapsable (`isSidebarCollapsed` toggle), mientras que en móvil se presenta como un menú deslizante (`Sheet` component). La integración con el backend se realiza mediante APIs RESTful (`src/lib/api.ts`), permitiendo la actualización en tiempo real de datos en dashboards. Componentes como `ThemeToggle` (`src/components/ThemeToggle.tsx`) permiten alternar entre temas claro y oscuro, mejorando la usabilidad en diferentes condiciones de iluminación.

- **Módulo de Integración con Telegram**:
  - **Función**: Permite notificaciones en tiempo real, recordatorios y consultas rápidas desde dispositivos móviles a través de un bot de Telegram, ideal para usuarios operativos en campo que no tienen acceso constante a la interfaz web. Esto asegura que el personal pueda recibir alertas críticas (como fallos de equipos) o responder a consultas simples sin necesidad de una computadora.
  - **Implementación**: Gestionado por `telegram_client/bot_manager.py` (orquestación del bot) y `telegram_client/notification_scheduler.py` (programación de notificaciones y recordatorios), con manejadores específicos para diferentes tipos de interacciones: comandos (`telegram_client/handlers/command_handlers.py`), mensajes de texto (`telegram_client/handlers/message_handlers.py`), y documentos (`telegram_client/handlers/document_handlers.py`). Las credenciales y configuraciones del bot se gestionan en `core/config.py` (`TELEGRAM_BOT_TOKEN`, `BOT_USERNAME`).
  - **Archivos Relevantes**: `telegram_client/handlers/message_handlers.py` (procesamiento de mensajes de usuarios), `telegram_client/handlers/command_handlers.py` (manejo de comandos como /start), `telegram_client/notification_scheduler.py` (envío de recordatorios), `run_telegram_bot.py` (script de inicio del bot).
  - **Detalles Técnicos**: La integración utiliza la biblioteca Telethon para interactuar con la API de Telegram, permitiendo funcionalidades como el envío de mensajes formateados y la gestión de callbacks (`telegram_client/handlers/callback_query_handler.py`). Los IDs de administrador (`ADMIN_TELEGRAM_IDS` en `core/config.py`) restringen ciertas funcionalidades a usuarios autorizados. La URL del panel web (`TELEGRAM_WEBAPP_URL`) permite a los usuarios acceder a la interfaz completa desde Telegram si necesitan más funcionalidades.

- **Módulo de Gestión de Base de Datos y Memoria**:
  - **Función**: Administra el almacenamiento, recuperación y búsqueda de datos estructurados (como agendas, notas, perfiles de usuario) y no estructurados (como textos de documentos y embeddings para búsqueda semántica). Mantiene el contexto de las interacciones del usuario para respuestas personalizadas, asegurando que Kognito "recuerde" conversaciones pasadas y preferencias.
  - **Implementación**: Utiliza bases de datos relacionales como PostgreSQL (definidas en `core/database.py` con modelos como `Account`, `Memory`, `Nota`, `AgendaEvent`, `ChatThread`) para datos estructurados, y bases de datos vectoriales como Pinecone o Weaviate para embeddings (`utils/embeddings.py`, configurado con `GOOGLE_EMBEDDING_MODEL_NAME` como `text-embedding-004` en `core/config.py`). Incluye funcionalidades como `memory_manager.py` para gestionar recuerdos y documentos (`get_relevant_memories` para buscar memorias relevantes, `process_document_for_rag` para procesar documentos para RAG). El historial de chat se almacena mediante `PostgresChatMessageHistory` en `core/agent.py`.
  - **Archivos Relevantes**: `core/database.py` (modelos de datos relacionales), `core/memory_manager.py` (gestión de contexto y documentos), `utils/embeddings.py` (generación de embeddings), `core/agent.py` (almacenamiento de historial con `PostgresChatMessageHistory`).
  - **Detalles Técnicos**: La base de datos PostgreSQL se configura mediante variables de entorno como `DATABASE_URL` en `core/config.py`, asegurando flexibilidad para diferentes entornos (desarrollo, producción). La gestión de memoria utiliza un enfoque de "manejo manual" (como se describe en `core/agent.py`), cargando y guardando explícitamente el historial para mayor control. Los embeddings permiten búsquedas semánticas rápidas, esenciales para funcionalidades como RAG (`tools/document_rag_tool.py`), donde los fragmentos de documentos más relevantes se recuperan basados en la similitud con la consulta del usuario (parámetros como `CHUNK_SIZE` y `CHUNK_OVERLAP` en `core/config.py` controlan la segmentación de textos).

- **Módulo de Herramientas y Agentes de IA**:
  - **Función**: Proporciona herramientas específicas para automatizar tareas y extender las capacidades de Kognito, como análisis de documentos, gestión de notas, integración con servicios externos (GitHub, búsqueda web), generación de imágenes, y programación de eventos. Estas herramientas son invocadas por el agente de IA para responder a consultas de usuarios de manera precisa y funcional.
  - **Implementación**: Definido en el directorio `tools/`, con clases como `BaseTool` extendidas para cada funcionalidad específica. Ejemplos incluyen `AddNoteTool` (`tools/add_note_tool.py`) para agregar notas, `DocumentRAGTool` (`tools/document_rag_tool.py`) para búsqueda y generación de respuestas basadas en documentos, `GitHubRepoTool` (`tools/github_repo_tool.py`) para interactuar con repositorios de GitHub, y `ImageGenerationTool` (`tools/image_generation_tool.py`) para crear imágenes basadas en texto. Estas herramientas son invocadas por agentes de IA en `core/agent.py` (`create_and_run_agent`), que utiliza LangChain para orquestar su uso (`get_all_langchain_tools` en `core/tools.py`).
  - **Archivos Relevantes**: `tools/add_note_tool.py` (gestión de notas), `tools/document_rag_tool.py` (RAG para documentos), `tools/github_repo_tool.py` (integración con GitHub), `tools/image_generation_tool.py` (generación de imágenes), `core/tools.py` (lista de herramientas disponibles), `core/agent.py` (ejecución de agentes).
  - **Detalles Técnicos**: Cada herramienta implementa métodos asíncronos (`_arun`) para garantizar un rendimiento óptimo, permitiendo operaciones no bloqueantes. Las herramientas reciben parámetros de identificación como `account_id` y `telegram_id` (pasados mediante `config` en `AgentExecutor` de `core/agent.py`) para asegurar que las operaciones sean específicas del usuario. La configuración de modelos de IA para herramientas específicas, como `GOOGLE_IMAGE_GENERATION_MODEL_NAME` (`imagegeneration@006` en `core/config.py`), asegura que cada tarea utilice el modelo más adecuado. El agente sigue una "instrucción crítica" de usar solo una herramienta por interacción (como se define en el prompt del sistema en `core/agent.py`), esperando la siguiente interacción del usuario antes de invocar otra herramienta, lo que evita respuestas sobrecargadas.

### Flujo de Datos
El flujo de datos en Kognito sigue un ciclo bien definido que asegura que la información se recolecte, procese, analice y presente de manera eficiente. Este flujo está diseñado para minimizar la latencia, maximizar la relevancia de las respuestas y mantener un contexto coherente para los usuarios. A continuación, se detalla cada etapa del flujo, con referencias a los componentes y archivos relevantes:

1. **Ingesta de Datos**:
   - **Descripción**: Los datos se recolectan de fuentes internas (bases de datos SQL de departamentos gestionadas por `core/database.py`, documentos subidos por usuarios) y externas (APIs de clima, tráfico marítimo, búsquedas web mediante `tools/web_search_tool.py`).
   - **Proceso**: Herramientas como `document_parser.py` procesan documentos en formatos variados (PDF, DOCX, TXT) para extraer texto y metadatos. Los conectores personalizados (implícitos en la arquitectura) acceden a bases de datos relacionales y APIs externas. Los datos crudos se limpian y estructuran para su almacenamiento, asegurando consistencia y calidad.
   - **Archivos Clave**: `utils/document_parser.py`, `tools/web_scraper_tool.py`, `tools/web_search_tool.py`.
   - **Detalles**: La ingesta puede ser en tiempo real (para datos de sensores o APIs) o por lotes (para documentos subidos), dependiendo de la fuente. La API key para búsqueda web (`BRAVE_SEARCH_API_KEY` en `core/config.py`) permite enriquecer datos internos con información externa cuando sea necesario.

2. **Almacenamiento y Procesamiento**:
   - **Descripción**: Los datos estructurados (eventos de agenda, notas, perfiles) se guardan en bases de datos relacionales, mientras que los datos no estructurados (textos de documentos, consultas de usuarios) se convierten en embeddings para búsqueda semántica.
   - **Proceso**: Los datos estructurados se almacenan en PostgreSQL (`core/database.py` con modelos como `Nota`, `AgendaEvent`), configurado mediante `DATABASE_URL` en `core/config.py`. Los datos no estructurados se procesan en embeddings mediante `utils/embeddings.py` (usando el modelo `text-embedding-004` definido en `core/config.py`) y se almacenan en bases de datos vectoriales. El contexto del usuario se mantiene mediante `memory_manager.py` (`add_memory_to_vector_db`, `get_relevant_memories`) para personalizar interacciones futuras.
   - **Archivos Clave**: `core/database.py`, `core/memory_manager.py`, `utils/embeddings.py`.
   - **Detalles**: La segmentación de textos para RAG se controla mediante parámetros como `CHUNK_SIZE` (1000 caracteres por defecto) y `CHUNK_OVERLAP` (200 caracteres) en `core/config.py`, asegurando que los fragmentos sean lo suficientemente grandes para mantener contexto pero lo suficientemente pequeños para búsquedas precisas. El almacenamiento de embeddings permite búsquedas semánticas rápidas, esenciales para responder consultas basadas en documentos.

3. **Análisis de Datos**:
   - **Descripción**: Los datos procesados se analizan mediante modelos de IA para identificar patrones, tendencias y predicciones, generando insights accionables.
   - **Proceso**: Herramientas como `analyze_text_for_insights_tool.py` extraen insights de textos largos (método `_arun` para análisis asíncrono), mientras que `proactive_knowledge_linker_tool.py` vincula información relacionada entre documentos y datos (usando umbrales de similitud como `DUPLICITY_SIMILARITY_THRESHOLD` de `core/config.py`). Los resultados del análisis se formatean para ser legibles, ya sea como texto narrativo, tablas o visualizaciones, mediante métodos como `_format_result`.
   - **Archivos Clave**: `tools/analyze_text_for_insights_tool.py`, `tools/proactive_knowledge_linker_tool.py`, `core/config.py`.
   - **Detalles**: El análisis predictivo puede identificar, por ejemplo, un aumento en fallos de grúas y sugerir mantenimiento preventivo. Los umbrales configurables permiten ajustar la sensibilidad del análisis (por ejemplo, detectar contradicciones con `CONTRADICTION_SENTIMENT_THRESHOLD` de 0.70), asegurando que los insights sean relevantes. El análisis se realiza de manera asíncrona para no bloquear la interfaz del usuario.

4. **Interacción del Usuario**:
   - **Descripción**: Los usuarios interactúan con Kognito a través de la interfaz web o el bot de Telegram, realizando consultas en lenguaje natural que son procesadas por el agente de IA.
   - **Proceso**: Las consultas se reciben mediante la interfaz web (`src/app/(dashboard)/chat/[id]/page.tsx`) o Telegram (`telegram_client/handlers/message_handlers.py`). El agente en `core/agent.py` (`create_and_run_agent`) procesa la consulta, invocando herramientas relevantes del directorio `tools/` (como `DocumentRAGTool` para búsqueda en documentos). Las respuestas se personalizan según el contexto del usuario almacenado en `memory_manager.py` (`get_relevant_memories`).
   - **Archivos Clave**: `core/agent.py`, `src/app/(dashboard)/chat/[id]/page.tsx`, `telegram_client/handlers/message_handlers.py`, `core/memory_manager.py`.
   - **Detalles**: El agente utiliza un prompt dinámico que incluye el contexto del usuario, instrucciones de identificación (`account_id`, `telegram_id`), y guías para herramientas (como se ve en `core/agent.py`). La interacción sigue un principio de "una herramienta por vez", esperando la siguiente entrada del usuario antes de invocar otra herramienta, lo que asegura claridad en las respuestas. El historial de chat se guarda mediante `PostgresChatMessageHistory` para mantener continuidad.

5. **Presentación de Resultados**:
   - **Descripción**: Los resultados del análisis y las respuestas del agente se presentan al usuario en formatos accesibles y personalizables.
   - **Proceso**: Los resultados se muestran en dashboards interactivos (`src/app/(dashboard)/rag/page.tsx` para análisis de documentos), informes exportables (PDF, CSV generados por herramientas como `analyze_text_for_insights`), o notificaciones push a través de Telegram (`telegram_client/notification_scheduler.py`). Los usuarios pueden personalizar visualizaciones y filtros desde la interfaz web para adaptar la información a sus necesidades.
   - **Archivos Clave**: `src/app/(dashboard)/rag/page.tsx`, `tools/analyze_text_for_insights_tool.py`, `telegram_client/notification_scheduler.py`.
   - **Detalles**: Los dashboards permiten arrastrar y soltar widgets para métricas clave (como KPIs de operaciones), mientras que las notificaciones de Telegram se programan mediante `set_simple_reminder` en `core/reminders_manager.py`. La exportación de informes es compatible con formatos estándar para facilitar su uso en presentaciones o auditorías.

6. **Retroalimentación y Mejora Continua**:
   - **Descripción**: Las interacciones del usuario se utilizan para mejorar el contexto y la precisión de futuras respuestas, creando un ciclo de aprendizaje continuo.
   - **Proceso**: Las interacciones (consultas, feedback implícito) se almacenan como recuerdos en `core/memory_manager.py` (`add_memory_to_vector_db`) para enriquecer el contexto. El historial de chat se resume periódicamente mediante `summarize_history_in_background` en `core/agent.py` para mantener el contexto sin sobrecargar el modelo de lenguaje (si los tokens exceden 3000, se genera un resumen). Los modelos de IA pueden reentrenarse con nuevos datos mediante pipelines en el backend (aunque no explícito en el código, es una práctica estándar).
   - **Archivos Clave**: `core/memory_manager.py`, `core/agent.py`.
   - **Detalles**: La sumarización del historial no elimina mensajes originales, preservando el historial completo para el frontend mientras usa resúmenes para el contexto del LLM (`core/agent.py`). Los títulos de hilos de chat se actualizan dinámicamente mediante `update_thread_title_if_needed` (por ejemplo, después de 5 mensajes si el título es "Nuevo Chat"), mejorando la organización de las conversaciones.

Este flujo de datos asegura que Kognito sea un sistema reactivo y adaptable, capaz de manejar consultas complejas y datos en tiempo real mientras mantiene un contexto coherente para cada usuario.

### Tecnologías Utilizadas
Kognito utiliza un stack tecnológico moderno y robusto, diseñado para maximizar el rendimiento, la escalabilidad y la facilidad de mantenimiento. La selección de tecnologías refleja un enfoque en la integración de IA avanzada con interfaces de usuario intuitivas y una infraestructura confiable. A continuación, se detalla el conjunto de herramientas, frameworks y servicios empleados, basado en la estructura de archivos y configuraciones observadas en el código:

- **Lenguajes de Programación**:
  - **Python**: Utilizado para el backend, herramientas de IA y procesamiento de datos. Es el lenguaje principal para módulos como `core/agent.py`, `tools/`, y `utils/`, debido a su amplio soporte para bibliotecas de machine learning y su facilidad para manejar tareas asíncronas.
  - **TypeScript/JavaScript**: Usado para el frontend con React y Next.js, proporcionando una interfaz de usuario dinámica y responsiva (`src/app/`, `src/components/`), con TypeScript añadiendo tipado estático para mayor robustez en el desarrollo.

- **Frameworks y Librerías**:
  - **Frontend**:
    - **Next.js**: Framework de React para aplicaciones web con renderizado del lado del servidor (SSR) y optimización de rutas (`next.config.mjs`, `src/app/`), permitiendo una carga rápida y SEO mejorado para la interfaz de Kognito.
    - **React**: Biblioteca para construir componentes de interfaz de usuario reutilizables (`src/components/` como `AppShell.tsx`), facilitando la creación de una experiencia de usuario interactiva y modular.
    - **Tailwind CSS**: Framework de estilos basado en utilidades para un diseño rápido y consistente (`tailwind.config.ts`, usado en todos los componentes de `src/`), permitiendo personalización de temas (claro/oscuro mediante `ThemeToggle`).
    - **shadcn/ui**: Conjunto de componentes UI personalizables para formularios, diálogos y tablas (`src/components/ui/`), asegurando una interfaz coherente y accesible con elementos como `Button`, `Dialog`, y `Table`.
  - **Backend**:
    - **FastAPI**: Framework de Python para construir APIs RESTful de alto rendimiento, utilizado como puente entre frontend y backend (`run_api.py`), permitiendo endpoints rápidos y documentados automáticamente para la comunicación con la interfaz web.
    - **Telethon**: Biblioteca de Python para interactuar con la API de Telegram, usada en `telegram_client/` para el bot y notificaciones, asegurando una integración robusta con Telegram para notificaciones y consultas móviles.
  - **IA y Machine Learning**:
    - **TensorFlow o PyTorch**: Frameworks probables para modelos de aprendizaje automático subyacentes, aunque no explícitamente visibles en el código, son estándar para tareas como la generación de embeddings en `utils/embeddings.py`.
    - **Hugging Face Transformers**: Biblioteca para modelos de lenguaje preentrenados, utilizada implícitamente en `core/agent.py` para PLN (`initialize_llms`), proporcionando capacidades de procesamiento de texto avanzadas.
    - **LangChain**: Framework para construir aplicaciones de IA conversacional, integrado en `core/agent.py` (`AgentExecutor`, `ChatPromptTemplate`) y `tools/document_rag_tool.py` para RAG (Retrieval-Augmented Generation), permitiendo la orquestación de modelos de lenguaje con herramientas y memoria.
    - **Google Generative AI**: Usado explícitamente en `core/agent.py` (`ChatGoogleGenerativeAI`) y `tools/knowledge_analysis_tool.py` (`get_interpreter_llm`) para análisis de conocimiento y generación de texto, con modelos como `gemini-2.0-flash` (configurado en `core/config.py` como `GOOGLE_MAIN_MODEL_NAME`) y `imagegeneration@006` para imágenes (`GOOGLE_IMAGE_GENERATION_MODEL_NAME`).

- **Bases de Datos**:
  - **PostgreSQL**: Base de datos relacional para datos estructurados como cuentas de usuario, notas, eventos de agenda y historial de chat (`core/database.py` con modelos como `Account`, `Nota`, `ChatThread`), configurada mediante `DATABASE_URL` en `core/config.py` para flexibilidad entre entornos.
  - **Bases de Datos Vectoriales (Pinecone, Weaviate o similar)**: Para almacenar embeddings y realizar búsquedas semánticas, gestionado por `utils/embeddings.py` y `core/memory_manager.py`, con el modelo de embeddings `text-embedding-004` (`GOOGLE_EMBEDDING_MODEL_NAME` en `core/config.py`), esencial para funcionalidades como RAG.

- **Infraestructura y Despliegue**:
  - **Docker**: Para contenerización de servicios, con múltiples Dockerfiles (`Dockerfile.core`, `Dockerfile.frontend`, `Dockerfile.telegram`) y configuración en `docker-compose.yml`, permitiendo un despliegue consistente y portátil de todos los componentes de Kognito.
  - **Kubernetes**: Recomendado para orquestación en producción, aunque no explícito en el código, es una práctica estándar para sistemas como Kognito con múltiples servicios, asegurando escalabilidad y alta disponibilidad mediante pods y balanceo de carga.
  - **NGINX**: Configurado como proxy inverso y balanceador de carga (`nginx.conf`), asegurando un acceso eficiente y seguro a la aplicación, con soporte para HTTPS y distribución de tráfico entre instancias.

- **Otras Herramientas y APIs**:
  - **GitHub API**: Integrada mediante `tools/github_repo_tool.py` (`GitHubRepoTool` con métodos como `_list_tree`, `_read_file`), permitiendo a desarrolladores interactuar con repositorios de código o documentación directamente desde Kognito.
  - **Brave Search API**: Configurada en `core/config.py` (`BRAVE_SEARCH_API_KEY`) y utilizada en `tools/web_search_tool.py` para búsquedas web, enriqueciendo respuestas con información externa cuando los datos internos no son suficientes.
  - **Herramientas de Generación de Imágenes**: Implementadas en `tools/image_generation_tool.py` (`ImageGenerationTool`), utilizando el modelo `imagegeneration@006` de Vertex AI (`GOOGLE_IMAGE_GENERATION_MODEL_NAME` en `core/config.py`), para crear visualizaciones basadas en texto, útil para diagramas o ilustraciones operativas.
  - **Ollama**: Configurado como alternativa para embeddings locales (`OLLAMA_EMBEDDING_MODEL` como `nomic-embed-text` y `OLLAMA_API_URL` en `core/config.py`), proporcionando una opción de procesamiento local para entornos con restricciones de nube.

Este stack tecnológico asegura que Kognito sea una plataforma de vanguardia, combinando lo mejor de la inteligencia artificial, interfaces de usuario modernas y una infraestructura escalable para satisfacer las demandas de un entorno portuario dinámico.

### Diagramas de Arquitectura (Descripción Textual)
Para facilitar la visualización de la arquitectura de Kognito, se describen dos diagramas conceptuales que pueden ser implementados con herramientas como Mermaid o software de diagramación. Estos diagramas no están codificados en el documento, pero se proporcionan instrucciones detalladas para su creación, con el objetivo de que los desarrolladores y stakeholders comprendan la estructura y el flujo del sistema.

- **Diagrama de Alto Nivel del Sistema**:
  - **Estructura**: Un diagrama de bloques que muestra los componentes principales de Kognito y sus interacciones, proporcionando una visión general de la arquitectura.
  - **Elementos**:
    - Un rectángulo central etiquetado como "Core de Kognito", dividido en submódulos: "Ingesta de Datos", "Procesamiento PLN", "Análisis y Reportes", "Interfaz de Usuario", "Integración Telegram", "Gestión de Datos". Cada submódulo representa un componente descrito anteriormente.
    - Flechas entrantes desde bloques externos etiquetados como "Fuentes de Datos Internas" (Bases de Datos Departamentales de Mantenimiento, Operaciones, Comercial, Aduanas; Documentos Subidos) y "Fuentes de Datos Externas" (APIs de Clima, Tráfico Marítimo, Búsqueda Web mediante `Brave Search API`) hacia el submódulo "Ingesta de Datos", indicando el flujo de entrada de información.
    - Flechas salientes desde "Core de Kognito" hacia bloques etiquetados como "Usuarios" (Gerentes, Analistas, Operativos, con subetiquetas para Interfaz Web y Telegram) y "Sistemas Externos" (Exportación de Informes PDF/CSV, Notificaciones Push), mostrando los canales de salida de datos procesados.
    - Nubes alrededor del "Core de Kognito" etiquetadas como "Infraestructura Docker/Kubernetes" (representando la contenerización y orquestación definida en `docker-compose.yml`) y "Seguridad (Autenticación JWT, Encriptación)" (reflejando configuraciones como `jwt_secret_key` en `core/config.py`), destacando los aspectos de despliegue y protección.
  - **Propósito**: Mostrar cómo Kognito actúa como un núcleo central que integra datos de múltiples fuentes y los entrega a diferentes usuarios y sistemas, con un enfoque en la infraestructura y seguridad que lo soportan. Este diagrama es útil para stakeholders no técnicos que necesitan entender el sistema a alto nivel.

- **Diagrama de Flujo de Datos**:
  - **Estructura**: Un diagrama de flujo lineal que ilustra el recorrido de los datos desde su ingesta hasta la presentación al usuario, detallando cada etapa del proceso descrito en la sección "Flujo de Datos".
  - **Elementos**:
    - Una secuencia lineal de rectángulos conectados por flechas: "Fuentes de Datos" (Internas y Externas) -> "Ingesta de Datos" (con referencia a `document_parser.py`, `web_scraper_tool.py`) -> "Almacenamiento y Procesamiento" (con subetiquetas para PostgreSQL en `database.py` y Embeddings en `embeddings.py`) -> "Análisis y Modelos de IA" (referenciando `analyze_text_for_insights_tool.py`, `proactive_knowledge_linker_tool.py`) -> "Interfaz de Usuario/Dashboards" (referenciando `AppShell.tsx`, `rag/page.tsx`) -> "Respuesta al Usuario" (Web y Telegram).
    - Ramificaciones en "Análisis y Modelos de IA" hacia nodos adicionales etiquetados como "Generación de Informes" (exportación PDF/CSV) y "Notificaciones Telegram" (mediante `notification_scheduler.py`), mostrando salidas alternativas de datos.
    - Un ciclo de retroalimentación desde "Respuesta al Usuario" de vuelta a "Almacenamiento y Procesamiento" etiquetado como "Memoria y Contexto" (referenciando `memory_manager.py`, `summarize_history_in_background` en `agent.py`), indicando cómo las interacciones del usuario enriquecen el contexto para futuras respuestas.
  - **Propósito**: Detallar el recorrido de los datos a través de Kognito, destacando los componentes y archivos clave en cada etapa. Este diagrama es útil para desarrolladores y analistas técnicos que necesitan entender cómo fluye la información y cómo se integran los diferentes módulos.

Estos diagramas, una vez implementados visualmente, proporcionarán una representación clara y comprensible de la arquitectura de Kognito, facilitando la comunicación entre equipos técnicos y no técnicos, y sirviendo como referencia para futuras expansiones o modificaciones del sistema.

## 3. Configuración y Despliegue (Setup and Deployment)

### Requisitos del Sistema
Kognito está diseñado para ser desplegado en entornos de desarrollo y producción, con requisitos de hardware y software que varían según el caso de uso y la escala de la implementación. A continuación, se detallan los requisitos mínimos y recomendados, basados en la estructura del proyecto y las configuraciones observadas:

- **Hardware**:
  - **Entorno de Desarrollo**:
    - **Mínimo**: 8 GB de RAM, CPU de 4 núcleos, 20 GB de almacenamiento SSD. Suficiente para ejecutar servicios básicos (frontend, backend, base de datos local) en una máquina de desarrollo.
    - **Recomendado**: 16 GB de RAM, CPU de 6 núcleos, 50 GB de almacenamiento SSD. Mejora el rendimiento al compilar el frontend (`npm run dev`) y ejecutar múltiples contenedores Docker.
  - **Entorno de Producción**:
    - **Mínimo**: 16 GB de RAM, CPU de 8 núcleos, 100 GB de almacenamiento SSD. Adecuado para un puerto pequeño con un volumen moderado de datos y usuarios concurrentes.
    - **Recomendado**: 32 GB de RAM, CPU de 16 núcleos, 500 GB de almacenamiento SSD (o más dependiendo del volumen de datos históricos y embeddings). Ideal para manejar grandes volúmenes de datos, múltiples usuarios concurrentes y alta disponibilidad en un entorno portuario como 'Puertos Monte y Sierra'.
    - **Notas**: En producción, se recomienda almacenamiento escalable (como discos adicionales o almacenamiento en la nube) para embeddings y documentos, ya que el tamaño de la base de datos vectorial puede crecer rápidamente.

- **Software**:
  - **Sistema Operativo**: Linux (Ubuntu 20.04 LTS o superior recomendado) para producción debido a su estabilidad y soporte para Docker. En desarrollo, se puede usar Windows con WSL2 (Windows Subsystem for Linux 2) o macOS con herramientas compatibles.
  - **Dependencias Principales**:
    - **Node.js y npm**: Versión 18 o superior, necesario para el frontend (`package.json` indica dependencias de Next.js y React). Se utiliza para compilar y ejecutar la interfaz web.
    - **Python y pip**: Versión 3.9 o superior, esencial para el backend y herramientas de IA (`requirements.txt`, `requirements.core.txt` listan dependencias como FastAPI, LangChain).
    - **Docker y Docker Compose**: Requerido para contenerización y despliegue simplificado (`docker-compose.yml`, múltiples `Dockerfile`s). Docker Compose es suficiente para desarrollo y pequeñas producciones, mientras que Kubernetes es recomendado para escalabilidad.
  - **Dependencias Específicas**: Ver `requirements.txt` (dependencias generales de Python), `requirements.core.txt` (dependencias específicas del core como LangChain), `requirements.webapp.txt` (si aplica), y `package.json` (dependencias de Node.js como React, Next.js, Tailwind CSS).
  - **Bases de Datos**: PostgreSQL (versión 12 o superior) para datos relacionales (`DATABASE_URL` en `core/config.py`). Para bases de datos vectoriales, se puede necesitar un servicio externo como Pinecone o Weaviate, aunque no está explícito en los requisitos locales.

- **Conexión a Internet**:
  - **Desarrollo**: Necesaria para descargar dependencias (`npm install`, `pip install`) y acceder a APIs externas durante las pruebas (como `GOOGLE_API_KEY` para modelos de IA).
  - **Producción**: Requerida para APIs externas (`BRAVE_SEARCH_API_KEY`, Google Generative AI) y notificaciones de Telegram (`TELEGRAM_BOT_TOKEN`). Se recomienda una conexión estable y de alta velocidad para minimizar latencia en respuestas de IA y notificaciones.

- **Notas Adicionales**: En entornos de producción, se recomienda hardware con soporte para virtualización (para Docker/Kubernetes) y redundancia (RAID para almacenamiento, múltiples nodos para alta disponibilidad). Además, se debe asegurar acceso a claves API válidas (`GOOGLE_API_KEY`, `BRAVE_SEARCH_API_KEY` en `core/config.py`) para funcionalidades de IA y búsqueda web.

### Instalación
La instalación de Kognito varía según el entorno (desarrollo o producción) y el método elegido (manual o con Docker). A continuación, se describen los pasos detallados para configurar el sistema, basados en los archivos y scripts disponibles en el proyecto.

#### Entorno de Desarrollo
El entorno de desarrollo está diseñado para permitir a los desarrolladores trabajar en Kognito, probar nuevas funcionalidades y depurar problemas. Requiere la instalación de dependencias y la configuración de servicios localmente.

1. **Clonar el Repositorio**:
   - Descargar el código fuente de Kognito desde el repositorio GitHub (si está disponible) o la fuente proporcionada por el equipo de desarrollo.
   - Ejecutar los siguientes comandos en la terminal:
     ```bash
     git clone https://github.com/usuario/kognito-ai.git
     cd kognito-ai
     ```
   - Esto crea una copia local del proyecto en el directorio `kognito-ai`.

2. **Configurar el Backend (Python)**:
   - Crear y activar un entorno virtual para aislar las dependencias de Python:
     ```bash
     python -m venv venv
     source venv/bin/activate  # En Windows: venv\Scripts\activate
     ```
   - Instalar las dependencias del backend definidas en los archivos de requisitos:
     ```bash
     pip install -r requirements.txt
     pip install -r requirements.core.txt
     ```
   - Esto instala paquetes como FastAPI, LangChain, y bibliotecas específicas para IA como `langchain_google_genai`.

3. **Configurar el Frontend (Next.js)**:
   - Navegar al directorio raíz del proyecto (donde está `package.json`) e instalar las dependencias de Node.js:
     ```bash
     npm install
     ```
   - Iniciar el servidor de desarrollo para la interfaz web:
     ```bash
     npm run dev
     ```
   - Esto compila y ejecuta el frontend en `http://localhost:3000` (o el puerto configurado en `next.config.mjs`).

4. **Configurar el Bot de Telegram (Opcional)**:
   - Editar las variables de entorno en `core/config.py` o crear un archivo `.env` con las credenciales necesarias (`TELEGRAM_BOT_TOKEN`, `BOT_USERNAME`, etc., como se define en `core/config.py`).
   - Ejecutar el script del bot para iniciarlo:
     ```bash
     python run_telegram_bot.py
     ```
   - Esto conecta el bot a Telegram, permitiendo pruebas de notificaciones y consultas móviles.

5. **Configurar la Base de Datos**:
   - Instalar PostgreSQL localmente si no está disponible, o usar un contenedor Docker para simplificar:
     ```bash
     docker run -d --name postgres-kognito -e POSTGRES_PASSWORD=yourpassword -p 5432:5432 postgres
     ```
   - Configurar la variable de entorno `DATABASE_URL` en un archivo `.env` o directamente en el sistema, siguiendo el formato en `core/config.py` (por ejemplo, `postgresql+psycopg://user:password@localhost:5432/dbname`).
   - Ejecutar scripts de inicialización para crear tablas, definidos en `core/database.py` (función `create_tables`):
     ```bash
     python -c "from core.database import create_tables; import asyncio; asyncio.run(create_tables())"
     ```

6. **Configurar Variables de Entorno**:
   - Crear un archivo `.env` en la raíz del proyecto con las variables necesarias, basadas en `core/config.py`. Ejemplo:
     ```
     GOOGLE_API_KEY=your-google-api-key
     TELEGRAM_BOT_TOKEN=your-telegram-bot-token
     DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/kognito
     BRAVE_SEARCH_API_KEY=your-brave-search-key
     ```
   - Asegurarse de que las claves API y credenciales estén correctamente configuradas para evitar errores al iniciar los servicios.

7. **Iniciar el Backend**:
   - Ejecutar el servidor API del backend para manejar solicitudes del frontend y Telegram:
     ```bash
     python run_api.py
     ```
   - Esto inicia FastAPI en el puerto configurado (por defecto 8080, como se infiere de `API_SERVER_URL` en `core/config.py`).

#### Entorno de Producción
El entorno de producción está optimizado para rendimiento, escalabilidad y alta disponibilidad, utilizando Docker para contenerización y, opcionalmente, Kubernetes para orquestación.

1. **Usar Docker Compose (Recomendado para Pequeñas Producciones o Pruebas)**:
   - Asegurarse de que Docker y Docker Compose estén instalados en el servidor.
   - Configurar variables de entorno en un archivo `.env` o directamente en el sistema, como se describió anteriormente.
   - Ejecutar el siguiente comando para construir y desplegar todos los servicios (frontend, backend, bases de datos, Telegram):
     ```bash
     docker-compose up --build -d
     ```
   - Esto construye imágenes basadas en `Dockerfile.core`, `Dockerfile.frontend`, `Dockerfile.telegram`, y las ejecuta en contenedores definidos en `docker-compose.yml`, asegurando que todos los servicios estén interconectados (por ejemplo, el backend en el puerto 8080, la base de datos en el puerto 5432).

2. **Configuración Manual (Para Entornos sin Docker o Personalizados)**:
   - Instalar dependencias como en el entorno de desarrollo (pasos 2 y 3 anteriores).
   - Configurar NGINX como proxy inverso usando el archivo `nginx.conf` proporcionado:
     ```bash
     sudo cp nginx.conf /etc/nginx/conf.d/kognito.conf
     sudo nginx -t && sudo systemctl reload nginx
     ```
   - Iniciar servicios manualmente:
     - Backend: `python run_api.py`
     - Frontend: `npm run build && npm start`
     - Bot de Telegram: `python run_telegram_bot.py`
   - Asegurarse de que PostgreSQL esté configurado y accesible mediante `DATABASE_URL`.

3. **Base de Datos en Producción**:
   - Usar un servicio gestionado de PostgreSQL (como AWS RDS, Google Cloud SQL) para mayor fiabilidad y backups automáticos.
   - Configurar `DATABASE_URL` con las credenciales del servicio gestionado, asegurando conexiones seguras mediante SSL si es necesario.

### Configuración Inicial
La configuración inicial asegura que Kognito esté listo para operar con los parámetros y credenciales correctos. Esto incluye la definición de variables de entorno y la personalización de archivos de configuración.

- **Archivos de Configuración**:
  - **`.env.local`**: Usado para variables de entorno del frontend (como endpoints de API), ubicado en la raíz del proyecto o definido en el entorno de desarrollo de Next.js. Ejemplo:
    ```
    NEXT_PUBLIC_API_URL=http://localhost:8080/api
    ```
  - **`core/config.py`**: Configuración central del backend, que lee variables de entorno para credenciales, modelos de IA, y parámetros de la aplicación. Aunque no se edita directamente, sus valores se definen mediante un archivo `.env` o variables de sistema.
  - **`tailwind.config.ts`**: Configuración de estilos para el frontend, permitiendo personalización de temas y colores si es necesario para adaptarse a la identidad visual de 'Puertos Monte y Sierra'.

- **Variables de Entorno**:
  - **Claves de IA y APIs**:
    - `GOOGLE_API_KEY`: Clave para acceder a modelos de Google Generative AI (`gemini-2.0-flash` para texto, `imagegeneration@006` para imágenes), definida en `core/config.py`.
    - `BRAVE_SEARCH_API_KEY`: Clave para búsqueda web mediante Brave Search, usada en `tools/web_search_tool.py`.
  - **Credenciales de Telegram**:
    - `TELEGRAM_BOT_TOKEN`: Token para autenticar el bot de Telegram, esencial para notificaciones.
    - `BOT_USERNAME`: Nombre de usuario del bot para identificación.
    - `ADMIN_TELEGRAM_IDS`: Lista de IDs de Telegram de administradores, separados por comas, para acceso restringido.
  - **Base de Datos**:
    - `DATABASE_URL`: URL de conexión a PostgreSQL (formato `postgresql+psycopg://user:password@host:port/dbname`), crítica para la persistencia de datos.
  - **Parámetros de IA y Análisis**:
    - `LLM_TEMPERATURE`: Temperatura para la generación de texto (0.4 por defecto en `core/config.py`), controlando la creatividad de las respuestas.
    - `CHUNK_SIZE` y `CHUNK_OVERLAP`: Parámetros para segmentación de textos en RAG (1000 y 200 por defecto), ajustables para optimizar búsquedas semánticas.
    - `DUPLICITY_SIMILARITY_THRESHOLD`, `SYNERGY_SIMILARITY_THRESHOLD`, etc.: Umbrales para análisis de conocimiento en `proactive_knowledge_linker_tool.py`.
  - **Seguridad**:
    - `JWT_SECRET_KEY`: Clave para firmar tokens JWT, usada en autenticación (`core/config.py`).
    - `ADMIN_SECRET`: Secreto para proteger endpoints de administración.
  - **Notas**: Estas variables deben definirse en un archivo `.env` en la raíz del proyecto o como variables de entorno del sistema. En Docker, se pueden pasar mediante `docker-compose.yml` o al iniciar contenedores.

- **Personalización del Prompt del Sistema**:
  - El prompt por defecto del sistema (`DEFAULT_SYSTEM_PROMPT` en `core/config.py`) define la identidad de KAI (Knowledge & Augmented Intelligence), sus principios (aumentación, memoria viva, neutralidad), y estilo de comunicación (Markdown simple, profesional pero cercano). Los usuarios avanzados pueden personalizar este prompt en el perfil del usuario (`system_prompt` en `Perfil` de `core/database.py`) para adaptar el tono o las instrucciones a necesidades específicas.

- **Validación de Configuración**:
  - Al iniciar, Kognito valida las configuraciones críticas mediante `_validate_config` en `core/config.py`, lanzando errores si faltan variables esenciales como `TELEGRAM_BOT_TOKEN` o `DATABASE_URL`, y emitiendo advertencias para configuraciones opcionales como `GOOGLE_API_KEY` o `BRAVE_SEARCH_API_KEY`. Esto asegura que el sistema no arranque en un estado inválido.

### Despliegue
El despliegue de Kognito en producción requiere consideraciones de escalabilidad, seguridad y alta disponibilidad. A continuación, se describen los pasos y mejores prácticas para implementar la plataforma en un entorno operativo, basados en los archivos de configuración y las tecnologías utilizadas.

- **Docker y Kubernetes**:
  1. **Construcción de Imágenes**:
     - Construir imágenes Docker para cada servicio usando los Dockerfiles proporcionados:
       ```bash
       docker build -f Dockerfile.core -t kognito-core .
       docker build -f Dockerfile.frontend -t kognito-frontend .
       docker build -f Dockerfile.telegram -t kognito-telegram .
       ```
     - Etiquetar y subir las imágenes a un registro (como Docker Hub o un registro privado) si se despliega en múltiples servidores.
  2. **Despliegue con Docker Compose (Pequeñas Escalas)**:
     - Usar `docker-compose.yml` para entornos pequeños o de prueba, asegurando que las variables de entorno estén definidas:
       ```bash
       docker-compose up -d
       ```
     - Esto despliega todos los servicios (core, frontend, Telegram, base de datos) en una sola máquina con redes internas configuradas.
  3. **Despliegue con Kubernetes (Producción a Gran Escala)**:
     - Definir pods para cada servicio (core, frontend, Telegram, PostgreSQL) en archivos YAML de Kubernetes, basados en las imágenes construidas.
     - Configurar servicios de tipo `ClusterIP` para comunicación interna y `LoadBalancer` para acceso externo al frontend y API.
     - Usar ConfigMaps y Secrets para manejar variables de entorno sensibles (`GOOGLE_API_KEY`, `DATABASE_URL`).
     - Ejecutar el despliegue:
       ```bash
       kubectl apply -f kognito-core.yaml -f kognito-frontend.yaml -f kognito-telegram.yaml -f kognito-postgres.yaml
       ```
     - Configurar autoescalado basado en métricas de uso (CPU, memoria) para manejar picos de tráfico.

- **Servidores Específicos (Cloud Providers)**:
  - **AWS (Amazon Web Services)**:
    - Usar ECS (Elastic Container Service) para manejar contenedores Docker, con Fargate para una gestión sin servidores.
    - Configurar una base de datos RDS (Relational Database Service) para PostgreSQL, asegurando backups automáticos y escalabilidad.
    - Usar Elastic Load Balancer (ELB) para distribuir tráfico entre instancias de frontend y backend.
    - Configurar autoescalado en ECS basado en métricas de CloudWatch (uso de CPU, número de solicitudes).
  - **Azure**:
    - Desplegar contenedores en AKS (Azure Kubernetes Service), utilizando los YAML de Kubernetes descritos anteriormente.
    - Usar Azure Database for PostgreSQL para la base de datos relacional, con opciones de alta disponibilidad.
    - Configurar Azure Load Balancer para acceso externo y Application Gateway para seguridad adicional (WAF).
  - **Google Cloud Platform (GCP)**:
    - Usar GKE (Google Kubernetes Engine) para orquestación de contenedores, integrándose con servicios de Google como Vertex AI (para modelos de IA configurados en `core/config.py` con `GOOGLE_PROJECT_ID` y `GOOGLE_PROJECT_LOCATION`).
    - Configurar Cloud SQL para PostgreSQL, asegurando conexiones seguras y backups.
    - Usar Cloud Load Balancing para distribuir tráfico y autoescalado basado en métricas.

- **Dominio y SSL**:
  - Configurar un dominio personalizado (por ejemplo, `kognito.puertosmontesierra.cl`) con registros DNS apuntando a la IP del servidor o al balanceador de carga (AWS ELB, Azure Load Balancer, GCP Cloud Load Balancing).
  - Usar Certbot o un servicio de certificados gestionado (como AWS Certificate Manager) para obtener e instalar certificados SSL:
    ```bash
    sudo certbot --nginx -d kognito.puertosmontesierra.cl
    ```
  - Configurar NGINX (`nginx.conf`) para redirigir tráfico HTTP a HTTPS, asegurando conexiones seguras.

- **Consideraciones de Alta Disponibilidad**:
  - Desplegar múltiples réplicas de cada servicio (frontend, backend, Telegram) en diferentes zonas de disponibilidad (si se usa un proveedor de nube) para garantizar redundancia.
  - Configurar backups automáticos de la base de datos PostgreSQL y almacenamiento de embeddings, usando herramientas del proveedor (AWS S3, Azure Blob Storage) o scripts personalizados.
  - Implementar monitoreo con herramientas como Prometheus y Grafana (integrables con Docker Compose o Kubernetes) para detectar caídas de servicios o picos de uso, configurando alertas basadas en métricas.

- **Notas de Seguridad**:
  - Asegurarse de que las variables de entorno sensibles (`GOOGLE_API_KEY`, `TELEGRAM_BOT_TOKEN`) no estén hardcodeadas en el código ni en archivos de configuración públicos, usando Secrets en Kubernetes o servicios de gestión de secretos en la nube.
  - Configurar firewalls (como AWS Security Groups, Azure Network Security Groups) para restringir el acceso a puertos no necesarios (por ejemplo, solo permitir 80 y 443 para NGINX, 5432 para PostgreSQL desde IPs específicas).
  - Implementar autenticación robusta mediante JWT (`JWT_SECRET_KEY` y `JWT_EXPIRY_DAYS` en `core/config.py`), asegurando que solo usuarios autorizados accedan a la plataforma.

Este proceso de despliegue asegura que Kognito esté operativo en un entorno de producción, con capacidad para manejar las demandas de 'Puertos Monte y Sierra' y escalar según sea necesario.

## 4. Uso y Funcionalidades

### Guía de Usuario
Kognito está diseñado para ser intuitivo y accesible, permitiendo a usuarios de diferentes niveles técnicos interactuar con la plataforma de manera eficiente. A continuación, se describen los pasos básicos para usar Kognito, desde el acceso inicial hasta la realización de consultas y personalización de dashboards.

- **Acceso a la Plataforma**:
  - **Interfaz Web**: Acceder a la URL configurada (por ejemplo, `http://kognito.puertosmontesierra.cl` o `http://localhost:3000` en desarrollo) e iniciar sesión en la página de login (`/login` en `src/app/login/page.tsx`) con credenciales proporcionadas por el administrador. La autenticación utiliza JWT (`JWT_SECRET_KEY` en `core/config.py`) para seguridad.
  - **Bot de Telegram**: Enviar un mensaje al bot de Telegram (identificado por `BOT_USERNAME` en `core/config.py`) o usar el comando `/start` para iniciar la interacción. Esto es ideal para usuarios en campo que necesitan acceso rápido sin una computadora.
  - **Notas**: Los usuarios deben tener un `account_id` asignado (gestionado en `core/database.py` como `Account`) para personalizar su experiencia y mantener el contexto de sus interacciones.

- **Consultas en Lenguaje Natural**:
  - Navegar a la sección de chat en la interfaz web (`/chat/[id]` en `src/app/(dashboard)/chat/[id]/page.tsx`) o enviar un mensaje al bot de Telegram.
  - Escribir preguntas en lenguaje natural, como "¿Cuál es el estado del mantenimiento de grúas esta semana?" o "¿Hay retrasos en el muelle 3?". El agente de IA (`core/agent.py`) procesará la consulta y responderá con información relevante, invocando herramientas como `DocumentRAGTool` si es necesario.
  - Las respuestas pueden incluir datos de dashboards, fragmentos de documentos, o insights generados por herramientas como `analyze_text_for_insights_tool.py`.

- **Navegación por Dashboards**:
  - Usar el `Sidebar` (`src/components/Sidebar.tsx`) en la interfaz web para acceder a secciones específicas:
    - **Agenda** (`/agenda` en `src/app/(dashboard)/agenda/page.tsx`): Ver y gestionar eventos y recordatorios.
    - **Notas** (`/notes` en `src/app/(dashboard)/notes/page.tsx`): Crear, editar y revisar notas personales o de equipo.
    - **Análisis RAG** (`/rag` en `src/app/(dashboard)/rag/page.tsx`): Explorar documentos, colecciones y análisis de conocimiento.
  - Cada sección permite personalizar la visualización de datos mediante filtros y widgets, adaptándose a las necesidades del usuario.

- **Personalización de Dashboards**:
  - En secciones como RAG o dashboards generales, seleccionar métricas y filtros relevantes (por ejemplo, rango de fechas, departamento) para crear visualizaciones personalizadas.
  - Arrastrar y soltar widgets para reorganizar la información, como gráficos de volumen de carga o tablas de estado de equipos, asegurando que los datos más importantes estén siempre visibles.
  - Guardar configuraciones personalizadas para acceso rápido en futuras sesiones (almacenadas como parte del perfil del usuario en `core/memory_manager.py`).

- **Gestión de Documentos y Conocimiento**:
  - Subir documentos para análisis mediante `upload-document-dialog.tsx` (`src/app/(dashboard)/rag/upload-document-dialog.tsx`), procesados por `process_document_for_rag` en `core/memory_manager.py`.
  - Ver y analizar documentos en la sección RAG, usando diálogos como `preview-document-dialog.tsx` y `analysis-result-dialog.tsx` para explorar contenido y obtener insights.
  - Crear colecciones de documentos relacionados mediante `create-collection-dialog.tsx`, facilitando la organización del conocimiento.

- **Notificaciones y Recordatorios**:
  - Recibir notificaciones automáticas en Telegram para eventos críticos (como fallos de equipos) o recordatorios programados (`set_simple_reminder` en `core/reminders_manager.py`).
  - Configurar recordatorios personalizados desde la interfaz web o Telegram, especificando texto y tiempo en lenguaje natural (por ejemplo, "Recuérdame revisar el informe de aduanas mañana a las 9 AM").

- **Soporte Multiplataforma**:
  - Cambiar entre la interfaz web y Telegram sin perder contexto, ya que el historial y las memorias se sincronizan mediante `PostgresChatMessageHistory` y `memory_manager.py` usando el `account_id` único del usuario.
  - Usar la interfaz web para análisis profundos y dashboards, y Telegram para actualizaciones rápidas y notificaciones en movimiento.

Esta guía proporciona una base para interactuar con Kognito, pero la plataforma es altamente personalizable, permitiendo a los usuarios adaptar su uso según sus roles y necesidades específicas.

### Ejemplos de Consultas
Kognito permite a los usuarios realizar consultas en lenguaje natural, adaptadas a diferentes roles dentro de 'Puertos Monte y Sierra'. A continuación, se presentan ejemplos prácticos de preguntas que los usuarios pueden hacer, junto con las respuestas esperadas y las herramientas internas que las generan:

- **Pregunta de Gerente**: "¿Qué retrasos se esperan en las operaciones de carga debido al clima?"
  - **Respuesta Esperada**: "Basado en datos meteorológicos obtenidos mediante búsqueda web y análisis de operaciones actuales, se esperan retrasos de 4 horas en el muelle 3 mañana debido a fuertes vientos (probabilidad de 80% de lluvia intensa). Recomiendo reasignar recursos al muelle 5, que tiene condiciones más favorables. Ver informe detallado en el dashboard de Operaciones."
  - **Herramientas Involucradas**: `web_search_tool.py` (para datos meteorológicos mediante `BRAVE_SEARCH_API_KEY`), `analyze_text_for_insights_tool.py` (para correlacionar clima con operaciones), `DocumentRAGTool` (si hay documentos relevantes sobre reasignación de recursos).
  - **Notas**: La respuesta combina datos externos e internos, proporcionando una recomendación accionable que el gerente puede implementar de inmediato.

- **Pregunta de Analista**: "Analiza las tendencias de fallos en equipos de mantenimiento de los últimos 3 meses."
  - **Respuesta Esperada**: "Se detectó un aumento del 15% en fallos de grúas tipo A en los últimos 3 meses, con un pico en el mes pasado (8 incidentes frente a 5 en el mes anterior). Los datos sugieren una correlación con el aumento de carga procesada (+20% en el mismo período). Se sugiere implementar mantenimiento predictivo para las grúas tipo A antes del próximo ciclo de alta demanda. Ver informe detallado en el dashboard de Mantenimiento, con gráficos de tendencias y recomendaciones específicas."
  - **Herramientas Involucradas**: `analyze_text_for_insights_tool.py` (análisis de datos históricos de mantenimiento), `proactive_knowledge_linker_tool.py` (identificación de correlaciones entre carga y fallos).
  - **Notas**: La respuesta incluye análisis predictivo y prescriptivo, ayudando al analista a anticipar problemas y planificar soluciones.

- **Pregunta Operativa (Mantenimiento)**: "¿Cuál es el estado actual de la grúa número 7?"
  - **Respuesta Esperada**: "La grúa número 7 está operativa, con su último mantenimiento realizado hace 10 días (según el registro del 15 de junio). No se reportan fallos recientes. El próximo mantenimiento programado es en 20 días. Puedes ver el historial completo en la sección de Mantenimiento del dashboard."
  - **Herramientas Involucradas**: `DocumentRAGTool` (búsqueda en registros de mantenimiento), `get_document_content_tool.py` (si se necesita contenido específico de un informe).
  - **Notas**: La respuesta es directa y específica, ideal para un técnico que necesita información inmediata para actuar.

- **Pregunta Operativa (Aduanas)**: "¿Cuáles son los documentos aduaneros pendientes para el cargamento XYZ-123?"
  - **Respuesta Esperada**: "Hay 3 documentos pendientes para el cargamento XYZ-123: Declaración de Importación (falta firma), Certificado de Origen (no subido), y Permiso Sanitario (en revisión). Puedes revisarlos y subir los faltantes en la sección RAG bajo 'Documentos Aduaneros'."
  - **Herramientas Involucradas**: `get_document_list_tool.py` (listado de documentos asociados al cargamento), `DocumentRAGTool` (búsqueda de estado específico).
  - **Notas**: La respuesta proporciona una lista clara y accionable, con instrucciones para resolver el problema.

- **Pregunta de Desarrollo**: "¿Puedes mostrarme el código del archivo principal del repositorio GitHub de Kognito?"
  - **Respuesta Esperada**: "He accedido al repositorio de GitHub proporcionado. Aquí está el contenido del archivo principal `run_api.py` (mostrando las primeras 50 líneas para referencia). Si necesitas más detalles o navegar a otro archivo, indícalo. [Código formateado en bloque Markdown]."
  - **Herramientas Involucradas**: `github_repo_tool.py` (`GitHubRepoTool` con método `_read_file`).
  - **Notas**: Esta funcionalidad es útil para desarrolladores que necesitan revisar código o documentación sin salir de Kognito.

Estos ejemplos ilustran cómo Kognito adapta sus respuestas al rol del usuario y al contexto de la consulta, utilizando herramientas específicas para garantizar precisión y utilidad.

### Funcionalidades Clave
Kognito ofrece un conjunto de funcionalidades diseñadas para abordar las necesidades específicas de 'Puertos Monte y Sierra', integrando datos de múltiples departamentos y proporcionando herramientas avanzadas de análisis y automatización. A continuación, se describen las funcionalidades más importantes, con referencias a los componentes que las soportan:

- **Integración de Datos por Departamento**:
  - **Mantenimiento**:
    - **Descripción**: Centraliza datos sobre el estado de equipos (grúas, vehículos, infraestructura), historial de reparaciones, y programación de mantenimiento. Permite análisis predictivo para anticipar fallos (por ejemplo, aumento de incidentes en grúas tipo A).
    - **Implementación**: Datos almacenados en PostgreSQL (`core/database.py`) y analizados mediante `analyze_text_for_insights_tool.py`. Los usuarios pueden consultar el estado de equipos específicos mediante RAG (`DocumentRAGTool`).
    - **Beneficio**: Reduce tiempos de inactividad al anticipar problemas y optimizar la programación de mantenimiento.
  - **Operaciones**:
    - **Descripción**: Gestiona datos sobre tiempos de carga/descarga, asignación de muelles, retrasos operativos y uso de recursos. Permite identificar cuellos de botella y reasignar recursos en tiempo real.
    - **Implementación**: Dashboards personalizados en `src/app/(dashboard)/page.tsx` y análisis mediante `proactive_knowledge_linker_tool.py` para correlacionar retrasos con factores como clima o volumen.
    - **Beneficio**: Mejora la eficiencia operativa al optimizar el uso de muelles y recursos.
  - **Comercial**:
    - **Descripción**: Integra datos de contratos, volúmenes de carga procesados, análisis de clientes y tendencias de mercado. Facilita la generación de informes para negociaciones y planificación.
    - **Implementación**: Informes generados por `analyze_text_for_insights_tool.py`, con datos accesibles mediante dashboards y consultas en lenguaje natural.
    - **Beneficio**: Apoya la toma de decisiones comerciales con datos consolidados y análisis predictivo de demanda.
  - **Aduanas**:
    - **Descripción**: Gestiona documentación aduanera, estado de cumplimiento normativo y alertas de irregularidades. Permite rastrear documentos pendientes y asegurar conformidad con regulaciones.
    - **Implementación**: Herramientas como `get_document_list_tool.py` y `update_document_metadata_tool.py` para gestionar documentos, con análisis RAG en `src/app/(dashboard)/rag/page.tsx`.
    - **Beneficio**: Reduce riesgos de multas y retrasos al garantizar cumplimiento normativo.

- **Análisis RAG (Retrieval-Augmented Generation)**:
  - **Descripción**: Permite cargar, analizar y vincular documentos para responder consultas basadas en contenido específico. Los usuarios pueden subir documentos (`upload-document-dialog.tsx`), analizarlos (`analysis-result-dialog.tsx`), y organizar colecciones (`create-collection-dialog.tsx`).
  - **Implementación**: Basado en `tools/document_rag_tool.py` (`DocumentRAGTool`) para búsqueda y generación de respuestas, con procesamiento de documentos en `core/memory_manager.py` (`process_document_for_rag`). La interfaz está en `src/app/(dashboard)/rag/page.tsx`.
  - **Beneficio**: Mejora la precisión de las respuestas al basarse en documentos reales, ideal para consultas técnicas o normativas.
  - **Detalles**: Utiliza embeddings (`utils/embeddings.py`) para búsqueda semántica, con parámetros como `CHUNK_SIZE` (1000) y `CHUNK_OVERLAP` (200) configurados en `core/config.py` para segmentar textos. Herramientas como `proactive_knowledge_linker_tool.py` vinculan conocimiento entre documentos, detectando duplicidad o sinergia.

- **Gestión de Notas y Agenda**:
  - **Descripción**: Permite crear, editar y gestionar notas (`note-dialog.tsx`) y eventos de agenda (`event-dialog.tsx`), con recordatorios integrados para no perder fechas importantes.
  - **Implementación**: Notas gestionadas por `core/notes_manager.py` (`add_note`, `update_note`), agenda por `core/agenda_manager.py` (`schedule_event`, `get_agenda_for_day`), y recordatorios por `core/reminders_manager.py` (`set_simple_reminder`). Interfaces en `src/app/(dashboard)/notes/page.tsx` y `src/app/(dashboard)/agenda/page.tsx`.
  - **Beneficio**: Mejora la organización personal y de equipo, asegurando que tareas y eventos críticos no se pasen por alto.

- **Notificaciones Telegram**:
  - **Descripción**: Envía alertas y resúmenes diarios a dispositivos móviles mediante Telegram, ideal para personal en campo que necesita actualizaciones inmediatas.
  - **Implementación**: Gestionado por `telegram_client/notification_scheduler.py` y `core/reminders_manager.py`, con configuraciones en `core/config.py` (`TELEGRAM_BOT_TOKEN`).
  - **Beneficio**: Mantiene a los usuarios informados en tiempo real, mejorando la capacidad de respuesta ante eventos críticos como fallos de equipos o cambios en la agenda.

- **Generación de Imágenes y Visualizaciones**:
  - **Descripción**: Crea imágenes o diagramas basados en texto para apoyar la comunicación visual, como esquemas de operaciones o ilustraciones de informes.
  - **Implementación**: Mediante `tools/image_generation_tool.py` (`ImageGenerationTool`), usando el modelo `imagegeneration@006` de Vertex AI configurado en `core/config.py`.
  - **Beneficio**: Facilita la comprensión de conceptos complejos mediante representaciones visuales, útil para presentaciones o formación.

- **Integración con GitHub**:
  - **Descripción**: Permite a desarrolladores acceder y navegar por repositorios de GitHub directamente desde Kognito, útil para revisar código o documentación técnica.
  - **Implementación**: Mediante `tools/github_repo_tool.py` (`GitHubRepoTool` con métodos como `_list_tree`, `_read_file`), invocable desde el agente de IA.
  - **Beneficio**: Agiliza el trabajo de desarrollo al integrar herramientas de código en la misma plataforma.

Estas funcionalidades clave aseguran que Kognito sea una solución integral para las necesidades operativas, analíticas y administrativas de 'Puertos Monte y Sierra', con un enfoque en la personalización y la automatización.

### Generación de Informes y Dashboards
Kognito ofrece herramientas avanzadas para la creación, personalización y exportación de informes y dashboards, permitiendo a los usuarios visualizar y compartir datos de manera efectiva.

- **Creación de Informes**:
  - **Proceso**: Desde la interfaz web (secciones como `/rag` o dashboards generales en `src/app/(dashboard)/page.tsx`), seleccionar datos por departamento (Mantenimiento, Operaciones, etc.) o tema (retrasos, cumplimiento). Aplicar filtros como rango de fechas o tipo de análisis (descriptivo, predictivo) y generar el informe mediante herramientas como `analyze_text_for_insights_tool.py`.
  - **Formatos**: Los informes se generan en formatos exportables como PDF (para presentaciones) y CSV (para análisis en hojas de cálculo), asegurando compatibilidad con herramientas externas.
  - **Ejemplo**: Un gerente puede generar un informe sobre "Retrasos Operativos en el Último Mes", incluyendo gráficos y recomendaciones basadas en análisis de IA.

- **Personalización de Dashboards**:
  - **Proceso**: En la interfaz web, arrastrar y soltar widgets para métricas clave (KPIs), como tiempo de inactividad de equipos, volumen de carga procesado, o estado de documentos aduaneros. Seleccionar filtros dinámicos (por fecha, departamento) para adaptar la visualización.
  - **Guardado**: Las configuraciones personalizadas se guardan en el perfil del usuario (`core/memory_manager.py`), permitiendo acceso rápido en sesiones futuras.
  - **Ejemplo**: Un analista puede crear un dashboard con gráficos de tendencias de fallos de equipos y tablas de retrasos operativos, actualizándose en tiempo real con datos del backend.

- **Exportación de Datos**:
  - **Proceso**: Desde cualquier dashboard o informe, usar opciones de exportación para descargar datos subyacentes como hojas de cálculo (CSV) o visualizaciones como imágenes (PNG, JPEG), útiles para presentaciones o auditorías.
  - **Integración**: Los informes exportados pueden enviarse automáticamente a stakeholders externos mediante notificaciones de Telegram o correo (si configurado).
  - **Ejemplo**: Un informe de cumplimiento aduanero puede exportarse como PDF y compartirse con reguladores directamente desde Kognito.

- **Detalles Técnicos**: La generación de informes utiliza análisis de IA (`analyze_text_for_insights_tool.py`) para incluir insights narrativos junto con datos numéricos, mientras que los dashboards se actualizan mediante APIs RESTful (`src/lib/api.ts`) conectadas al backend FastAPI (`run_api.py`). Esto asegura que la información sea siempre actual y relevante.

Estas capacidades de informes y dashboards convierten a Kognito en una herramienta poderosa para la visualización de datos, permitiendo a los usuarios de 'Puertos Monte y Sierra' tomar decisiones basadas en información clara y accesible.

## 5. Mantenimiento y Operaciones

### Monitoreo
El monitoreo continuo de Kognito es esencial para garantizar su rendimiento, detectar problemas antes de que afecten a los usuarios y mantener la salud general del sistema. A continuación, se describen las estrategias y herramientas para monitorear la plataforma:

- **Rendimiento del Sistema**:
  - **Herramientas**: Usar Prometheus y Grafana (integrables mediante Docker Compose o Kubernetes) para monitorear métricas clave como latencia de API (tiempo de respuesta de endpoints en `run_api.py`), uso de CPU y RAM de los contenedores (`kognito-core`, `kognito-frontend`), y volumen de consultas por usuario.
  - **Configuración**: Configurar Prometheus para recolectar métricas de los servicios expuestos (por ejemplo, endpoints de salud en FastAPI) y Grafana para visualizarlas en dashboards personalizados.
  - **Ejemplo de Métrica**: Monitorear el tiempo de respuesta del endpoint `/api/chat` para detectar cuellos de botella en el procesamiento de consultas de IA (`core/agent.py`).

- **Salud del Sistema**:
  - **Endpoints de Salud**: Configurar endpoints de salud en el backend (`run_api.py`) para verificar la disponibilidad de servicios clave (base de datos, modelos de IA, conexión a Telegram). Ejemplo:
    ```bash
    curl http://localhost:8080/health
    ```
  - **Alertas**: Configurar alertas en Grafana o servicios de nube (AWS CloudWatch, Azure Monitor) para notificar a los administradores si un servicio falla o si hay errores recurrentes en los logs.
  - **Ejemplo**: Alertar si la conexión a PostgreSQL (`DATABASE_URL`) falla, indicando un problema de red o credenciales.

- **Logs y Diagnóstico**:
  - **Acceso a Logs**: Acceder a logs detallados en contenedores Docker mediante:
    ```bash
    docker logs kognito-core
    ```
  - **Archivos de Logs**: En configuraciones manuales, revisar logs generados por `logging` en Python (`logger` en `core/agent.py`, `core/config.py`) para diagnosticar errores específicos.
  - **Ejemplo**: Buscar errores relacionados con `GOOGLE_API_KEY` en los logs si las respuestas de IA fallan, indicando problemas de autenticación con Google Generative AI.

- **Notas**: El monitoreo debe ser proactivo, con revisiones regulares de métricas y logs para identificar tendencias (como aumento en latencia durante picos de uso) y configurar alertas basadas en umbrales (por ejemplo, latencia > 5 segundos). En producción, integrar herramientas de monitoreo con notificaciones a administradores mediante Telegram o correo.

### Resolución de Problemas (Troubleshooting)
Kognito incluye mecanismos para identificar y resolver problemas comunes que pueden surgir durante su operación. A continuación, se describen errores frecuentes y sus soluciones, basados en la arquitectura y configuraciones del sistema:

- **Error de Conexión a Base de Datos**:
  - **Síntoma**: Mensajes de error como "Connection to database failed" en los logs de `kognito-core` o fallos al guardar datos (notas, historial de chat).
  - **Causa Posible**: Variable `DATABASE_URL` incorrecta o servicio PostgreSQL no disponible.
  - **Solución**:
    1. Verificar `DATABASE_URL` en variables de entorno o archivo `.env`, asegurando que el formato sea correcto (`postgresql+psycopg://user:password@host:port/dbname`).
    2. Comprobar que el servicio PostgreSQL esté activo:
       ```bash
       docker ps | grep postgres
       ```
    3. Reiniciar el contenedor de la base de datos si es necesario:
       ```bash
       docker restart postgres-kognito
       ```
    4. Revisar logs de PostgreSQL para errores específicos:
       ```bash
       docker logs postgres-kognito
       ```

- **Respuestas Incorrectas o Incompletas de IA**:
  - **Síntoma**: Respuestas irrelevantes, incompletas, o errores como "Failed to invoke LLM" en los logs.
  - **Causa Posible**: Problemas con `GOOGLE_API_KEY`, modelo no disponible, o datos de entrada de baja calidad.
  - **Solución**:
    1. Verificar que `GOOGLE_API_KEY` esté correctamente configurada en `core/config.py` o `.env`.
    2. Comprobar la disponibilidad del modelo (`gemini-2.0-flash`) mediante logs de inicialización en `core/agent.py` (`initialize_llms`).
    3. Revisar la calidad de los datos de entrada (documentos, consultas) y ajustar parámetros como `LLM_TEMPERATURE` (en `core/config.py`) si las respuestas son demasiado creativas o imprecisas.
    4. Si el problema persiste, verificar embeddings en `utils/embeddings.py` y memorias relevantes en `core/memory_manager.py` para asegurar que el contexto sea adecuado.

- **Frontend No Carga o Muestra Errores**:
  - **Síntoma**: La interfaz web (`http://localhost:3000`) no carga, muestra errores de JavaScript en la consola del navegador, o no se conecta al backend.
  - **Causa Posible**: Problemas de compilación de Next.js, backend no disponible, o configuración incorrecta de API URL.
  - **Solución**:
    1. Comprobar la consola del navegador (F12) para errores de JavaScript y verificar que `NEXT_PUBLIC_API_URL` esté correctamente configurada en `.env.local`.
    2. Asegurarse de que el backend esté corriendo (`python run_api.py`) y accesible en el puerto configurado (por defecto 8080, como `API_SERVER_URL` en `core/config.py`).
    3. Recompilar el frontend si hay cambios recientes:
       ```bash
       npm run build && npm start
       ```
    4. Revisar logs del frontend para errores de conexión:
       ```bash
       docker logs kognito-frontend
       ```

- **Bot de Telegram No Responde**:
  - **Síntoma**: El bot no responde a mensajes o comandos como `/start`, o no envía notificaciones.
  - **Causa Posible**: `TELEGRAM_BOT_TOKEN` incorrecto, servicio del bot no iniciado, o problemas de red.
  - **Solución**:
    1. Confirmar que `TELEGRAM_BOT_TOKEN` y `BOT_USERNAME` estén correctamente configurados en `core/config.py` o `.env`.
    2. Verificar que el servicio del bot esté corriendo:
       ```bash
       docker ps | grep kognito-telegram
       ```
    3. Reiniciar el servicio si es necesario:
       ```bash
       docker restart kognito-telegram
       ```
    4. Revisar logs del bot para errores específicos:
       ```bash
       docker logs kognito-telegram
       ```

- **Errores de Autenticación o Acceso**:
  - **Síntoma**: Usuarios no pueden iniciar sesión, o reciben errores de "Unauthorized" al acceder a ciertas funcionalidades.
  - **Causa Posible**: Problemas con `JWT_SECRET_KEY` o credenciales de usuario no válidas.
  - **Solución**:
    1. Asegurarse de que `JWT_SECRET_KEY` esté correctamente configurada y sea consistente entre servicios (`core/config.py`).
    2. Verificar que las credenciales del usuario estén registradas en la base de datos (`Account` en `core/database.py`).
    3. Revisar logs del backend para errores de autenticación:
       ```bash
       docker logs kognito-core | grep "JWT"
       ```

- **Notas**: Para problemas no cubiertos, revisar los logs detallados de cada servicio (`docker logs` o archivos de log locales) y consultar la documentación de las bibliotecas utilizadas (como LangChain, FastAPI). Si el problema persiste, contactar a los administradores del sistema o al equipo de desarrollo con los logs relevantes
