## 03-02-26 Implementado Endpoint para Compartir Colecciones con Workspaces 🤝

Se ha implementado la funcionalidad completa para compartir (asignar) una colección a un workspace específico a través de la API.

- **Backend (`api/collections.py`)**:
  - **Endpoint `POST /api/collections/{topic}/share` mejorado**: Este endpoint ahora acepta un `workspace_id` en el cuerpo de la solicitud.
  - **Integración con `core/memory_manager.py`**: El endpoint utiliza la función `update_collection` para realizar la asignación de la colección al workspace en la base de datos.
  - **Corrección de error 404**: La implementación resuelve el error 404 que ocurría al intentar acceder a una ruta de compartir colección no definida.

---

## 18-01-26 Corregida Subida de Archivos Excel en Sección de Tablas 📊

Se ha solucionado el problema que impedía importar archivos Excel (.xlsx, .xls) a la sección de tablas debido a dependencias faltantes en el entorno Docker y un manejo de errores limitado.

- **Dependencias (`requirements.txt`)**: Se corrigió un error de sintaxis que combinaba `websockets` con `openpyxl`, permitiendo que la librería para Excel se instale correctamente.
- **Backend (`api/tables.py`)**:
  - Se optimizó el endpoint de importación para manejar `workspace_id` nulos o vacíos provenientes del frontend.
  - Se añadió captura específica de `ImportError` para informar si faltan librerías de procesamiento.
- **Frontend (`src/app/(dashboard)/rag/import-table-dialog.tsx`)**: Se mejoró la captura de errores para mostrar el mensaje específico devuelto por el servidor en la interfaz de usuario.
- **Verificación**: Se validó el funcionamiento directamente en el contenedor `kognito_core` mediante un script de prueba transaccional.

---

## 21-01-26 Investigación y Propuestas de Optimización de CPU para run_api.py 🔍

Se realizó un análisis exhaustivo del alto consumo de CPU (90-100%) en el contenedor kognito_core durante la ejecución de run_api.py, identificando causas principales y proponiendo soluciones detalladas.

- **Análisis de código**: Se revisaron run_api.py, api/main.py, schedulers y WebSockets para identificar bottlenecks.
- **Causas identificadas**: Recarga automática de Uvicorn, herramientas programadas intensivas, procesamiento de audio en tiempo real, inicialización de modelos IA y operaciones de BD.
- **Informe creado**: Se generó `informe_optimizacion_cpu.md` con análisis detallado y plan de implementación priorizado.
- **Propuestas principales**: Desactivar reload en producción, optimizar schedulers, limitar conexiones de audio, forzar uso de GPU para modelos IA.

---

## 21-01-26 Optimización de Uso de GPU y Corrección de Errores de Importación 🚀

Se implementaron mejoras significativas para asegurar la correcta utilización de la GPU por parte de los modelos de IA y se corrigieron errores de importación de la librería `logging`.

- **Activación de GPU para LLMs (`core/llm_manager.py`)**:
  - Se añadió lógica para detectar la disponibilidad de una GPU (`torch.cuda.is_available()`).
  - Se configuró `ChatLiteLLM` para utilizar `device="cuda"` en los modelos de lenguaje principal, rápido y de visión cuando la GPU está disponible, optimizando su rendimiento.
- **Activación de GPU para Modelo Whisper (`utils/audio_transcriber.py`)**:
  - Se implementó la detección de GPU para el modelo de transcripción Faster Whisper.
  - Se ajustó el `device` a `"cuda"` y el `compute_type` a `"float16"` para aprovechar la GPU, mejorando la eficiencia de la transcripción de audio.
- **Aclaración sobre Embeddings (`utils/embeddings.py`)**:
  - Se confirmó que el modelo de embeddings basado en Ollama no requiere cambios directos en el código de la aplicación para el uso de GPU, ya que su configuración de hardware se gestiona a nivel del servidor de Ollama.
- **Eliminación del Flag `--reload` (`docker-compose.yml`)**:
  - Se eliminó el flag `--reload` del comando del servicio `core` en `docker-compose.yml` para reducir el consumo innecesario de CPU en entornos de ejecución estables.
- **Corrección de Errores de Importación (`core/llm_manager.py`, `utils/audio_transcriber.py`)**:
  - Se añadió la declaración `import logging` en ambos archivos para resolver los errores `NameError` que impedían el correcto inicio de la aplicación.

---

## 26-01-26 Implementación de Sección de Calendario en Kogninotes 📅

Se ha integrado una sección completa de Calendario en la aplicación móvil Kogninotes, permitiendo la visualización de la agenda sincronizada de Kognito AI.

- **Backend / API (`kogninotes-app/src/api/agendaService.ts`)**: [NEW]
  - Creación del servicio para consumir los eventos desde `GET /agenda/events`.
  - Soporte para filtrado por workspace e inclusión de eventos pasados.

- **Frontend / UI (`kogninotes-app/src/screens/CalendarScreen.tsx`)**: [NEW]
  - Implementación de una interfaz de agenda agrupada por secciones de fecha.
  - Diseño premium con gradientes, compatibilidad con modo oscuro/claro y estados de carga/vacío.
  - Comprobaciones de seguridad para el parseo de fechas ISO y manejo de errores.

- **Navegación e Integración**:
  - **`kogninotes-app/src/navigation/index.tsx`**: Registro de la nueva pantalla y corrección de la propiedad obligatoria `id` en `Stack.Navigator` (v7).
  - **`kogninotes-app/src/screens/HomeScreen.tsx`**: Inclusión de botón de acceso directo al calendario en la cabecera.

- **Estado del Build**:
  - Lanzamiento de construcción de APK mediante EAS Build (`eas build -p android --profile preview`).
  - Resolución de error de "Bundle JavaScript" mediante la corrección de tipos en la navegación y validaciones en la pantalla de calendario.

---

## 29-01-26 Correción de Error `BadRequestError` en Agente `DeepResearcher` 🤖

Se ha solucionado un error `litellm.BadRequestError` que ocurría en el agente `DeepResearcher` debido a una incompatibilidad con proveedores de LLM que exigen `tool_choice="auto"`.

- **Causa del Error**: El agente intentaba forzar el uso de una herramienta de salida estructurada (`with_structured_output`) sin especificar `tool_choice="auto"`, lo cual no es soportado por ciertos proveedores de modelos (como "Z.AI").
- **Solución (`core/agents/deep_researcher.py`)**:
  - Se modificaron las funciones `clarify_with_user` y `write_research_brief`.
  - En todas las llamadas al método `with_structured_output`, se añadió el parámetro `tool_choice="auto"` para asegurar la compatibilidad.
  - Esto afecta a las llamadas que utilizan `fast_llm`, `main_llm` y `fallback_llm`, garantizando que el agente funcione correctamente con todos los proveedores configurados.

---

## 29-01-26 Corrección de `NameError` para Soporte Multimodal (Visión) 👁️

Se ha solucionado un `NameError` que impedía el funcionamiento del soporte para imágenes (multimodal) en el agente principal.

- **Causa del Error**: El agente intentaba utilizar la función `get_vision_llm()` para procesar imágenes, pero dicha función no estaba importada en el archivo `core/agent.py`.
- **Solución (`core/agent.py`)**:
  - Se ha añadido `get_vision_llm` a la lista de importaciones desde `core.llm_manager`.
  - La línea de importación se ha modificado para incluir la función necesaria: `from core.llm_manager import get_main_llm, get_fast_llm, get_vision_llm`.
  - Esto restaura la capacidad del agente para cambiar al modelo de visión cuando se detecta una imagen en la conversación.

---

## 01-02-26 Solución para Cambios en Archivo .env No Aplicados 🔧

Se ha solucionado el problema donde los cambios en el archivo `.env` (específicamente el modelo LLM) no se aplicaban después de reiniciar la aplicación.

- **Causa del Problema**: El archivo `.env` se copia al contenedor durante el build en [`Dockerfile.core.hybrid`](../Dockerfile.core.hybrid:52), pero no había un volumen que montara el archivo `.env` del host, por lo que los cambios en el host no se reflejaban en el contenedor.

- **Solución Implementada (`docker-compose.yml`)**:
  - Se agregó un volumen para montar el archivo `.env` del host en los servicios `core`, `telegram_client` y `telegram_panel`.
  - El volumen está configurado como solo lectura (`:ro`) para evitar que el contenedor modifique el archivo del host.
  - Líneas modificadas: 62 (core), 105 (telegram_client), 162 (telegram_panel).

- **Script de Automatización (`restart_core_with_new_env.sh`)**: [NEW]
  - Se creó un script para facilitar el reinicio del servicio `core` con los cambios en el archivo `.env`.
  - El script detiene, reconstruye e inicia el servicio `core` automáticamente.

- **Documentación (`docs/SOLUCION_CAMBIO_MODELO_ENV.md`)**: [NEW]
  - Se creó un documento detallado explicando el problema, la solución y cómo aplicar los cambios en el futuro.
  - Incluye instrucciones para verificar que los cambios se hayan aplicado correctamente y solución de problemas.

---

## 03-02-26 Optimización de Scroll, Layout y Experiencia de Chat 🚀✨

Se han implementado mejoras críticas en la interfaz del chat para asegurar una navegación fluida, un scroll "pegajoso" inteligente y la correcta visualización del área de entrada de mensajes.

- **Mejora del Sistema de Scroll (`src/components/CommonChat.tsx`)**:
  - **Scroll "Sticky" Inteligente**: Se implementó un sistema de anclaje mediante `messagesEndRef` y `scrollIntoView`, asegurando que la vista se mantenga al final de la conversación mientras la IA responde en streaming.
  - **Lógica de Autoscroll Optimizada**: El chat ahora detecta si el usuario ha subido manualmente para leer mensajes anteriores, desactivando temporalmente el autoscroll para no interrumpir la lectura.
  - **Fluidez Mejorada**: Se optimizaron las llamadas a `scrollToBottom` para evitar saturar el hilo principal durante el streaming de tokens.

- **Corrección de Layout y Visibilidad (`src/components/AppShell.tsx`, `src/components/CommonChat.tsx`)**:
  - **Eliminación del Scroll General**: Se modificó el `AppShell` para que el contenedor principal sea `overflow-hidden` cuando se visualiza un chat, eliminando el molesto "scroll doble".
  - **Fijación del Input Bar**: Se ajustó la estructura Flexbox para que el área de entrada de mensajes esté siempre visible y completa en la parte inferior de la pantalla, sin ser cortada por el viewport.
  - **Ajuste de Alturas**: Se cambió el uso de unidades `h-screen` por `h-full` en componentes anidados para permitir una adaptación perfecta al espacio disponible.

- **Limpieza de Estilos y Refactorización (`src/app/globals.css`, `src/components/MarkdownRenderer.tsx`)**:
  - **Eliminación de Efectos Experimentales**: Se removieron las animaciones de desenfoque (blur) que afectaban la legibilidad, dejando un renderizado de texto nítido y de alto rendimiento.
  - **Sincronización de Animaciones**: Se simplificó el uso de `framer-motion` en el renderizado de markdown para evitar conflictos con los estilos globales.
  - **Limpieza de CSS**: Se reescribió y optimizó el archivo `globals.css` para eliminar estilos redundantes y asegurar una base limpia para futuras mejoras visuales.

---

## 03-02-26 Integración y Mejora de Seguridad y Rendimiento de OnlyOffice 🚀🔐

Se ha realizado una refactorización completa de la implementación de OnlyOffice para hacerla funcional, segura y eficiente, resolviendo problemas de seguridad y optimizando la experiencia de edición de documentos.

- **Refactorización del Cliente (`utils/onlyoffice_client.py`)**:
  - Migración de `requests` a `httpx` para soportar peticiones asíncronas no bloqueantes.
  - Implementación de firma de peticiones salientes y verificación de tokens JWT entrantes.
  - Mejora en el manejo de errores de conexión y respuestas de la Conversion API.

- **Creación del Servicio Centralizado (`core/onlyoffice_service.py`)**: [NEW]
  - Implementación de `OnlyOfficeService` para desacoplar la lógica de negocio de la capa de API.
  - Gestión segura de la configuración del editor (Document Server).
  - Procesamiento de callbacks con validación de estado y descarga segura de documentos.
  - Extracción automática de texto desde archivos `.docx` usando `python-docx` para mantener la sincronía con la base de conocimientos de la IA.
  - Registro de auditoría y detección de intrusiones mediante el monitoreo de IPs en los callbacks.

- **Fortalecimiento de la API (`api/notes.py`)**:
  - Actualización del endpoint de configuración para delegar en el nuevo servicio.
  - Refactorización de `onlyoffice-callback` para soportar validación robusta de JWT y auditoría de red.
  - Mejora en el endpoint de descarga raw para servir documentos generados dinámicamente o físicos de forma eficiente.

- **Optimización de la Experiencia de Usuario (`src/app/(dashboard)/notes/onlyoffice/[id]/page.tsx`)**:
  - Implementación de un sistema de timeouts para la carga de scripts y configuración.
  - Diseño de estados de carga premium con indicadores visuales y desenfoque de fondo.
  - Gestión de errores detallada con posibilidad de reintento para el usuario.
  - Carga diferida del script de OnlyOffice para optimizar el bundle inicial y mejorar el rendimiento.

- **Calidad y Mantenibilidad**:
  - Creación de pruebas unitarias básicas en `tests/test_onlyoffice_service.py` para validar la lógica del servicio.
  - Eliminación de dependencias sincrónicas innecesarias en flujos de trabajo críticos de la API.

---

## 03-02-26 Implementación de Adaptador Universal para OpenRouter y Mejora del Proceso de Pensamiento 🧠🚀

Se ha creado un sistema de adaptación para modelos en OpenRouter (GLM 4.5 Air y GPT-OSS 120B) para habilitar y visualizar procesos de razonamiento complejos.

- **Adaptador Universal de Modelos (`core/llm_manager.py`)**: [NEW]
  - Creación de la función `apply_openrouter_model_specific_logic` que automatiza la activación de parámetros de razonamiento.
  - Soporte específico para **GLM 4.5 Air** (`thinking_mode`, `reasoning`) y **GPT-OSS 120B** (`reasoning_effort: high`, `thinking`).
  - Activación global de `include_reasoning: True` para todos los ruteos de OpenRouter.

- **Detección Dinámica de Razonamiento (`core/agent.py`)**:
  - Implementación de un sistema de "fallback" que escanea tanto `additional_kwargs` como `response_metadata` buscando patrones de pensamiento (`think`, `reason`, `thought`).
  - Asegura la captura del razonamiento incluso si el proveedor cambia el nombre del campo técnico en la respuesta.

- **Interfaz de Usuario Progresiva (`src/components/ChatMessage.tsx`)**:
  - Transformación del bloque de razonamiento en un componente **desplegable y animado**.
  - **Lógica de Auto-expansión**: El bloque se expande automáticamente durante el streaming si el modelo está pensando y aún no hay respuesta final.
  - Diseño *premium* con efectos de desenfoque, iconos dinámicos (`BrainCircuit`) y transiciones fluidas con `framer-motion`.

---

## 03-02-26 Optimización y Limpieza Profunda de Logs del Agente 🧹✨

Se ha implementado una mejora visual significativa y una limpieza exhaustiva de los logs del sistema para facilitar el monitoreo y debugging, eliminando el ruido innecesario y estilizando la salida crítica.

- **Sistema de Logging Estilizado (`core/utils/logging_utils.py`)**: [NEW]
  - Creación de la clase `AgentLogger` que introduce logs con colores ANSI y emojis semánticos (`🤖`, `🛠️`, `⟳`).
  - Métodos específicos como `.node_start()`, `.tool_call()` y `.model_start()` para estandarizar la salida visual.

- **Refactorización del Agente (`core/agent.py`)**:
  - Migración completa al nuevo `AgentLogger`.
  - **Reducción de Ruido**: Volcados pesados de JSON (respuestas completas de LLM, metadatos) movidos de `INFO` a `DEBUG`.
  - Logs de ejecución de nodos de LangGraph simplificados y movidos a segundo plano (`DEBUG`) para una consola más limpia.

- **Silenciamiento de Componentes Ruidosos**:
  - **Base de Datos (`core/memory_manager.py`)**: Todas las consultas SQL de depuración (Semantic Search, FTS) y métricas de Reranking se movieron al nivel `DEBUG`.
  - **Carga de Herramientas (`core/tools.py`)**: El ensamblaje de la toolbox y la inicialización de dependencias compartidas ahora son silenciosos por defecto.
  - **LiteLLM (`core/llm_manager.py`)**: Configuración agresiva para silenciar logs internos repetitivos ("Provider List", "completion") estableciendo el nivel a `WARNING`.

---

## 03-02-26 Corrección Critica de Codebase en api/chat.py 🛠️

Se ha restaurado la integridad del archivo `api/chat.py`, el cual presentaba errores de sintaxis (`IndentationError`) y código faltante debido a una edición manual incorrecta, impidiendo el inicio deservicio `kognito_core`.

- **Restauración de Función (`api/chat.py`)**:
  - Se reincorporó la definición de la clase `PaginatedChatMessagesResponse` y de la función asíncrona `get_chat_messages` que habían sido eliminadas.
  - Se reconstruyó la lógica de inicialización del historial de chat (`PostgresChatMessageHistory`) y la iteración sobre los mensajes.
- **Corrección de Sintaxis**:
  - Se alineó correctamente el bloque de código huérfano que procesaba `sources` y `reasoning`, eliminando el `IndentationError`.
  - Se verificó la integridad del archivo mediante compilación (`python3 -m py_compile`).

---

## 03-02-26 Deduplicación de Nodos en Knowledge Graph 🕸️✨

Se ha implementado una solución robusta para resolver la duplicación de nodos en el grafo de conocimiento, donde entidades idénticas (mismo nombre) se creaban como nodos separados debido a variaciones en su tipo/clasificación.

- **Generación Unificada de IDs (`knowledge_graph/neo4j_adapter.py`)**:
  - Se modificó `_generate_entity_id` para basar la identidad del nodo **exclusivamente en su nombre normalizado** (`entity_{normalized_name}`), ignorando el tipo detectado. Esto permite que "Elon Musk" (PERSON) y "Elon Musk" (ORG) se resuelvan al mismo ID.

- **Estrategia de Merge Mejorada (`knowledge_graph/neo4j_adapter.py`)**:
  - Se actualizó la lógica de inserción (`MERGE`) para utilizar una etiqueta base genérica (`Entity`) junto con el ID, en lugar de restringir el `MERGE` a una etiqueta específica.
  - Esto garantiza que si el nodo ya existe (independientemente de su etiqueta original), se reutiliza y se enriquece con la nueva información y etiquetas.

---

## 03-02-26 Corrección de TypeError en GraphDB Initialization 🛠️

Se ha solucionado un error crítico `TypeError` en la herramienta `graph_cypher_generator_tool` que impedía la ejecución de consultas Cypher debido a la falta de argumentos en la inicialización de `GraphDB`.

- **Corrección de Inicialización (`tools/graph_cypher_generator_tool.py`)**:
  - Se modificó la función `_get_graph_integration` para importar `settings` desde `core.config`.
  - Ahora se inicializa `GraphDB` pasando explícitamente `uri`, `user`, y `password` obtenidos de la configuración global (`settings.neo4j_uri`, `settings.neo4j_user`, `settings.neo4j_password`), resolviendo el error de argumentos faltantes.

---

## 03-02-26 Corrección de Serialización JSON en CypherTool 🛠️

Se ha corregido un error de serialización que provocaba el fallo de la herramienta `cypher_tool` cuando la consulta devolvía objetos complejos de Neo4j (nodos, relaciones o rutas).

- **Procesamiento de Resultados (`tools/cypher_tool.py`)**:
  - Implementación de un método recursivo `_process_results` para convertir objetos `Node`, `Relationship` y `Path` de Neo4j en diccionarios compatibles con JSON.
  - El método extrae automáticamente metadatos como `_id`, `_labels` y `_type`, además de las propiedades del nodo/relación.
  - Soporte añadido para la serialización de objetos de fecha y tiempo mediante `isoformat()`.
  - Esto garantiza que el agente reciba una respuesta JSON estructurada y legible independientemente de la complejidad de la consulta Cypher.

---

## 03-02-26 Reemplazo de Modelos Hardcoded por Modelos Dinámicos (Fast LLM) 🚀🤖

Se ha completado la migración de múltiples herramientas y configuraciones que utilizaban el modelo `gemini-2.5-flash` de forma estática (hardcoded) para que utilicen los modelos configurados dinámicamente en las variables de entorno (`LLM_MODEL` y `FAST_LLM_MODEL`).

- **Configuración Centralizada (`core/config.py`)**:
  - Implementación de la función `get_model_name_from_provider_format` para extraer el nombre del modelo de cadenas con formato 'provider/model' (ej. 'gemini/gemini-2.0-flash').
  - Actualización de `google_main_model_name` y `google_summary_model_name` para que se deriven automáticamente de `LLM_MODEL` y `FAST_LLM_MODEL`, garantizando que todas las herramientas utilicen los modelos actuales configurados por el usuario.

---

## 03-02-26 Migración total a LiteLLM y eliminación de dependencias directas de Gemini 🚀🦁

Se ha completado la migración de todas las herramientas y utilidades críticas para eliminar las llamadas directas a los modelos de Google (Gemini) a través de `langchain_google_genai`, unificando toda la gestión de modelos bajo **LiteLLM**. Esto resuelve errores de compatibilidad y asegura un comportamiento agnóstico al proveedor.

- **Unificación de Herramientas (`tools/`)**:
  - **`natural_query_interpreter_tool.py`**: Refactorizado para usar `get_llm_for_user`, eliminando la instanciación directa de `ChatGoogleGenerativeAI`. Esto corrige el error de `max_retries` al usar la configuración centralizada de LiteLLM.
  - **`internal_knowledge_search_tool.py`**: Actualizado para obtener el modelo de interpretación de forma dinámica a través del `llm_manager`.

---

## 03-02-26 Integración Resiliente de `CrewResearchTool` y Gestión de Dependencias 🚢🔍

Se ha habilitado la herramienta `CrewResearchTool` bajo un esquema de carga segura para garantizar la estabilidad del sistema y permitir el escalado de capacidades de investigación.

- **Resiliencia de Carga (`core/tools.py`)**:
  - Se refactorizó `_import_tool_class` para capturar errores de importación y evitar caídas críticas del sistema si faltan librerías externas.
  - Implementación de un filtro dinámico en `get_all_langchain_tools` que omite herramientas cuyas dependencias no estén instaladas, permitiendo que la API arranque normalmente.
- **Gestión de Dependencias (`requirements.txt`)**:
  - Se añadió `crewai>=0.100.0` a la lista de dependencias base para asegurar su instalación en el contenedor.
- **Integración del Agente y System Prompt (`core/prompt_manager.py`)**:
  - Se registró `CrewResearchTool` en la toolbox global, permitiendo al agente realizar investigaciones colaborativas profundas.
  - Se actualizó el **System Prompt** en `PromptManager` para incluir una descripción destacada de la capacidad de investigación multi-agente de CrewAI, incentivando al LLM a utilizarla en consultas complejas.
- **Resultado**: El sistema ahora es capaz de manejar dependencias opcionales de forma robusta y el cerebro de la IA es consciente de sus nuevas y potentes capacidades de investigación.

---

## 04-02-26 Optimización de Memoria Selectiva y Proactiva 🧠✨

Se han implementado mejoras significativas en el sistema de memoria del agente para optimizar la relevancia de la información almacenada y asegurar que las memorias proactivas sean utilizadas efectivamente.

- **Memoria Selectiva (Selective Memory)**:
  - Se modificó `knowledge_extraction_node` en `core/agent.py` para incluir una verificación de inteligencia artificial previa.
  - Ahora, cada turno se analiza con un modelo rápido para determinar si contiene "NUEVO CONOCIMIENTO PERMANENTE" antes de intentar extraer y guardar información en el Grafo de Conocimiento, evitando el procesamiento innecesario de interacciones triviales.

- **Recuperación de Memorias Proactivas**:
  - **Nuevo Nodo de Grafo**: Se añadió `retrieve_proactive_memories_node` en el flujo del agente (`core/agent.py`), que se ejecuta en paralelo con la búsqueda RAG estándar. Este nodo busca específicamente memorias generadas proactivamente (`user_memory_proactive_llm`).
  - **Inclusión en RAG Estándar**: Se actualizó `core/memory_manager.py` para incluir por defecto el tipo `user_memory_proactive_llm` en todas las búsquedas de memoria relevantes, solucionando el problema donde estas memorias eran ignoradas.

---

## 04-02-26 Solución al error de OpenRouter "No endpoints found that support tool use" 🛠️

Se ha solucionado un error crítico que impedía a modelos servidos a través de OpenRouter (como Llama 3.1, DeepSeek, etc.) ejecutar herramientas.

- **Punto 1: Forzado de `tool_choice="auto"` en `core/agent.py`**: Se modificó la vinculación de herramientas para que todos los modelos de OpenRouter y modelos OSS (Llama, DeepSeek, Mistral) incluyan el parámetro `tool_choice="auto"`. Esto actúa como un filtro para que OpenRouter solo redirija la petición a proveedores que soportan herramientas. 🚀
- **Punto 2: Adaptador específico en `core/llm_manager.py`**: Se actualizó `apply_openrouter_model_specific_logic` para incluir configuraciones de `plugins` en el cuerpo de la petición, asegurando una mejor negociación de capacidades con la API de OpenRouter. 🧠
- **Punto 3: Headers de Identificación**: Se añadieron los headers `HTTP-Referer` y `X-Title` en las peticiones a OpenRouter (tal como recomienda su documentación oficial) para mejorar el ruteo y la visibilidad de la aplicación. 🛡️
- **Punto 4: Mayor Resiliencia**: La lógica ahora detecta automáticamente si el modelo es de OpenRouter o un modelo especializado (no nativo de OpenAI/Gemini) para aplicar estas reglas de forma inteligente. ⚙️
- **Punto 5: Modo Prompt Tooling Fallback (NUEVO)**: Se implementó un sistema que detecta modelos gratuitos (:free) o de razonamiento que no soportan herramientas nativas. En estos casos, se evita enviar el parámetro `tools` a la API (evitando errores 404) y se inyecta la documentación de las herramientas directamente en el prompt del sistema. El parser híbrido captura las llamadas en texto para ejecutarlas. 🛠️✨
- **Punto 6: Blindaje de Prompts (Escapado de Llaves)**: Se implementó una estrategia de escape global en `PromptManager` y `agent.py` que convierte todas las llaves `{}` en `{{}}` antes de pasar el prompt a LangChain. Esto evita errores de "missing variables" (KeyError) causados por contenido JSON o documentación técnica dentro del prompt del sistema. 🛡️🔐
- **Punto 7: Optimización de Peticiones OpenRouter**: Se refinó `core/llm_manager.py` para eliminar parámetros de `extra_body` innecesarios (como `plugins: []`) en modelos gratuitos. Esto soluciona los errores `BadRequest 400` ("can only concatenate str to str") causados por APIs de proveedores sensibles que no aceptan diccionarios adicionales. 🚀🌐
- **Punto 8: Control Manual de Modo de Herramientas**: Se implementó un nuevo ajuste de usuario (`use_prompt_tooling`) que permite elegir manualmente entre el uso nativo de herramientas (`bind_tools`) o el modo de compatibilidad por prompt. Este ajuste se integró en la base de datos (incluyendo migración exitosa en Docker), la API y la lógica del agente para ofrecer un control total al usuario. 🎮🛠️🔐⚖️

---

## 05-02-26 Corrección de `AttributeError` en `NotesManager` 🐛

Se ha solucionado un `AttributeError: 'FieldInfo' object has no attribute 'lower'` que ocurría al crear o consultar notas sin un `workspace_id` específico.

- **Causa del Error**: El `workspace_id` se pasaba como un objeto `FieldInfo` de Pydantic en lugar de `None` cuando no se proporcionaba, y el código intentaba llamar al método `.lower()` sobre este objeto.
- **Solución (`core/notes_manager.py`)**:
  - Se ha modificado las funciones `add_note` y `get_notes_as_dicts`.
  - Se ha añadido una comprobación `isinstance(workspace_id, str)` antes de intentar procesar el `workspace_id`.
  - Si `workspace_id` no es una cadena de texto, se trata como `None`, evitando el error y asegurando que la lógica de negocio funcione como se espera.

---

## 05-02-26 La página de Grafos de Conocimientos ahora ocupa todo el ancho disponible ↔️

Se ha modificado la página de Grafos de Conocimientos para que ocupe todo el ancho disponible en la pantalla, mejorando la visualización del grafo.

- **Punto 1**: Se eliminaron las clases de Tailwind CSS `max-w-7xl` y `mx-auto` del `div` principal en `src/pages/KnowledgeGraphPage.tsx`. Estas clases estaban limitando el ancho máximo del contenido y centrándolo, impidiendo que la página utilizara todo el espacio horizontal disponible.

---

## 05-02-26 Ajuste de Altura en el Visor de Grafos de Conocimiento 📏

Se ha ajustado la altura del componente `KnowledgeGraphViewer` para que se adapte correctamente a su contenedor padre, lo que puede influir en la correcta visualización del ancho disponible.

- **Punto 1**: Se modificó la propiedad `height` de `100vh` a `100%` en la clase `.knowledge-graph-viewer` dentro de `src/components/KnowledgeGraph/KnowledgeGraphViewer.css`. Este cambio asegura que el visor del grafo utilice la altura completa de su elemento padre, permitiendo una mejor adaptación al layout general de la página.

---

## 07-02-26 Corrección de Renderizado de Fuentes GitHub y Grafo en Chat 🐙✨

Se ha solucionado el problema donde las fuentes de GitHub no se renderizaban correctamente o se confundían con las del Grafo de Conocimiento en la interfaz de chat.

- **Detección Inteligente de Fuentes (`src/lib/chatUtils.ts`)**:
  - Implementación de `normalizeSource` para detectar automáticamente URLs de GitHub (`github.com`) y asignarles el tipo `github` de forma prioritaria, independientemente de su origen (`ragContext` o `sources`).
  - Se añadieron prefijos específicos para diferenciar tipos (`graph://`, `analysis://`, `note://`), evitando colisiones.
  - Se unificó la generación de identificadores únicos (`tipo-url`) para garantizar que fuentes distintas no se oculten entre sí.

- **Mejora en Renderizado de Fuentes GitHub**:
  - Modificado `tools/github_repo_tool.py` (métodos `_run` y `_arun`) para devolver `ToolOutputWithSources`, permitiendo que el sistema capture y renderice metadatos de fuentes para repositorios y archivos de GitHub.
  - Corregido el nodo `tool_node` en `core/agent.py` para evitar la duplicación de fuentes en el estado del grafo, optimizando el rendimiento y la consistencia.
  - Corregido un error de linter en `src/components/ChatMessage.tsx` relacionado con hooks de React mal cerrados.
  - Añadido log de depuración en `ChatMessage.tsx` para verificar la recepción de fuentes.
- **Mejoras Visuales (`src/components/SourceButton.tsx`)**:
  - Actualización de los estilos para el tipo `github` con un color Índigo distintivo y vibrante, separándolo visualmente de los resultados de grafos (Cian).
  - **Visualización Rica en Snippets**: Habilitación del comportamiento de Popover para las fuentes de GitHub. Ahora los usuarios pueden ver un snippet detallado del contenido del repositorio (código, contexto) en lugar de un enlace simple, mejorando significativamente la experiencia de usuario.

- **Corrección de Citas (`src/components/ChatMessage.tsx`, `src/lib/chatUtils.ts`)**:
  - Refactorización de la lógica de citas para vincular correctamente los índices numéricos `[1]` con las fuentes procesadas, asegurando que las inyecciones en el texto funcionen incluso con IDs alfanuméricos complejos.
  - Actualización de `normalizeSource` en `chatUtils.ts` para capturar el campo `page_content`, estándar en documentos de LangChain, asegurando que el contenido real del código se muestre en el frontend.

---

## 07-02-26 Aumento de la Estabilidad del Agente (Recursion Limit) 🧠🛡️

Se ha incrementado el límite de recursión del motor de agentes LangGraph para prevenir interrupciones en tareas complejas y multi-paso.

- **Aumento de Límite de Recursión (`api/chat.py`)**:
  - Se configuró explícitamente el parámetro `recursion_limit` a **100** (aumentando desde el valor por defecto de 25) al invocar el grafo del agente.
  - Esto soluciona los errores `Recursion limit of 25 reached` reportados en logs, permitiendo que el agente ejecute cadenas de razonamiento largas, bucles de corrección y flujos de investigación profunda sin fallos prematuros.

---

## 08-02-26 Corrección de Error de `tool_choice` en OpenRouter para Salida Estructurada 🛠️

Se ha solucionado un error crítico que impedía a modelos servidos a través de OpenRouter (como Llama 3.1, DeepSeek, etc.) ejecutar herramientas.

- **Causa del Error**: La función `invoke_structured_output` intentaba usar `with_structured_output` y luego `json_mode`, pero ambos métodos fallaban porque internamente enviaban un parámetro `tool_choice` que ciertos modelos de OpenRouter no aceptan, resultando en un error 404.
- **Solución (`core/utils/llm_utils.py`)**:
  - Se ha modificado la lógica de manejo de errores en `invoke_structured_output`.
  - Ahora, cuando se detecta el error específico de `tool_choice` de OpenRouter, el sistema **salta directamente al método de fallback manual**.
  - Este método manual consiste en instruir al modelo a través del prompt para que devuelva un JSON y luego se parsea la respuesta, evitando por completo el uso del parámetro `tool_choice`.
  - Esto asegura que la generación de salida estructurada funcione de manera robusta con todos los modelos, incluidos los de OpenRouter que tienen esta limitación.
---

## 08-02-26 Mejora de la Robustez en la Generación de Salida Estructurada 🧠💪

Se ha mejorado la fiabilidad de la generación de salida estructurada (JSON) desde los modelos de lenguaje, especialmente los más pequeños o rápidos, que a veces fallaban en seguir las instrucciones.

- **Causa del Error**: El método de fallback manual en `invoke_structured_output` no era lo suficientemente explícito, causando que algunos LLMs devolvieran la definición del esquema en lugar de los datos solicitados, lo que resultaba en un error de validación (`Manual parsing failed`).
- **Solución (`core/utils/llm_utils.py`)**:
  - Se ha refactorizado el prompt del método de fallback manual.
  - Ahora, el prompt **genera dinámicamente un ejemplo de JSON** basado en el esquema Pydantic requerido.
  - Este ejemplo muestra al LLM exactamente qué formato se espera, incluyendo los nombres de los campos y tipos de datos de ejemplo.
  - Al proporcionar un ejemplo concreto, se reduce drásticamente la ambigüedad y se guía al modelo para que produzca una salida JSON válida y conforme al esquema, solucionando los errores de validación.
---

## 08-02-26 Estabilización del Agente Investigador y Conexión de Telegram 🕵️‍♂️🔌

Se han solucionado dos errores de validación críticos en el agente `DeepResearcher` que causaban la caída del servicio `kognito_core` y, como consecuencia, la pérdida de conexión del bot de Telegram.

- **Error 1: `KnowledgeSearchInput` (Entrada de Búsqueda de Conocimiento)**
  - **Causa**: El LLM generaba un texto con formato de lista (ej. `'["ley"]'`) para el filtro `filter_topics`, pero la herramienta esperaba una lista real (`['ley']`), causando un error de validación.
  - **Solución (`tools/knowledge_search_tool.py`)**: Se añadió un validador de Pydantic al modelo de entrada. Este validador ahora convierte automáticamente el texto en una lista antes de la validación, haciendo la herramienta más robusta frente a las inconsistencias de formato del LLM.

- **Error 2: `WebSearchTool` (Herramienta de Búsqueda Web)**
  - **Causa**: La herramienta `WebSearchTool` era instanciada con un `account_id` que no era de tipo `string` (probablemente `None`), lo que provocaba un error de validación.
  - **Solución (`tools/web_search_tool.py`)**: Se modificó la herramienta para que el `account_id` sea opcional y se añadió una verificación al inicio de su ejecución. Si el `account_id` no es válido, la herramienta ahora devuelve un mensaje de error controlado en lugar de fallar.

- **Impacto General**: Al resolver estos errores, se estabiliza el servicio `kognito_core`, lo que a su vez garantiza que la conexión WebSocket con el `telegram_client` se mantenga activa, restaurando la funcionalidad del bot de Telegram.
---

## 08-02-26 Corrección de `UnboundLocalError` en la Generación del Informe Final del Agente Investigador 📄✍️

Se ha solucionado un error `UnboundLocalError` que ocurría en la etapa final de la generación de informes del agente `DeepResearcher`.

- **Causa del Error**: La función `final_report_generation` intentaba acceder a una variable local `findings` para construir el informe, pero esta variable nunca se inicializaba. Los resultados de la investigación se encontraban en el estado del agente (`state`), pero no se estaban cargando en la variable local.
- **Solución (`core/agents/deep_researcher.py`)**: Se añadió una línea al principio de la función `final_report_generation` para inicializar la variable `findings`. Esta línea recupera las notas de investigación (`state.get("notes", [])`) del estado del agente y las une en un único texto, asegurando que los hallazgos estén disponibles para la creación del informe final y evitando el error.
---

## 08-02-26 Corrección de Fallo en `json_mode` para Salida Estructurada 🛠️

Se ha corregido un error en `core/utils/llm_utils.py` donde el fallback a `json_mode` fallaba con el mensaje `Received unsupported arguments {'method': 'json_mode'}`.

- **Causa del Error**: El argumento `method="json_mode"` se pasaba explícitamente a `llm.with_structured_output` en el bloque de fallback, pero el LLM subyacente no lo soportaba.
- **Solución (`core/utils/llm_utils.py`)**: Se eliminó el argumento `method="json_mode"` del fallback. Ahora, `llm.with_structured_output(schema)` se llama sin un método específico, permitiendo que el LLM utilice su mecanismo predeterminado para la salida estructurada. Si esto falla, el sistema recurrirá al parseo manual de JSON, que ya está implementado.

---

## 08-02-26 Mejora de la Robustez en la Generación de Salida Estructurada (Fallback Consolidado) 🧠💪

Se ha mejorado la fiabilidad de la generación de salida estructurada (JSON) consolidando la lógica de fallback.

- **Causa del Error**: La función `invoke_structured_output` tenía múltiples bloques `try-except` anidados, lo que hacía que el manejo de errores fuera menos directo y no garantizaba que el fallback manual de JSON fuera el último recurso para *cualquier* fallo en la salida estructurada.
- **Solución (`core/utils/llm_utils.py`)**: Se refactorizó la función `invoke_structured_output` para tener un único bloque `try-except` principal. Si el intento inicial de `llm.with_structured_output(schema)` falla por cualquier razón (incluyendo errores de servicio o de argumentos no soportados), el control pasa directamente a la lógica de parseo manual de JSON. Esto simplifica el flujo y asegura que el sistema siempre intentará el parseo manual como último recurso para obtener una salida estructurada.

---

## 08-02-26 Corrección de `ValidationError` en `WebSearchTool` por `account_id` 🛠️

Se ha solucionado un `ValidationError` en `WebSearchTool` que ocurría cuando el `account_id` no era una cadena de texto válida.

- **Causa del Error**: La herramienta `WebSearchTool` requiere un `account_id` de tipo `str`, pero en `ComprehensiveWebAnalysisTool` se estaba pasando un valor que no era una cadena (posiblemente `None` o un tipo inesperado), lo que provocaba un error de validación al intentar instanciar `WebSearchTool`.
- **Solución (`tools/comprehensive_web_analysis_tool.py`)**: Se añadió una verificación explícita del tipo de `effective_account_id` antes de llamar a `get_web_search_tool`. Ahora, si `effective_account_id` no es una cadena de texto válida o está vacío, se registra un error y se devuelve un mensaje de error al usuario, evitando la `ValidationError` y asegurando que `WebSearchTool` siempre reciba un `account_id` válido.

---

## 08-02-26 Corrección del Contador de Turnos para Memoria Proactiva 🔄

Se ha corregido el problema donde el contador de turnos (`turn_count`) para la memoria proactiva no se incrementaba correctamente, registrando cada turno como "1".

- **Causa del Error**: La variable `turn_count` en el `AgentState` estaba definida pero no se incrementaba explícitamente en el flujo del agente.
- **Solución (`core/agent.py`)**: Se añadió una línea al inicio de la función `call_model_node` para incrementar `state['turn_count']` en cada llamada. Esto asegura que el contador se actualice con cada ciclo de procesamiento de la IA para una entrada de usuario, lo cual es fundamental para la gestión de la memoria proactiva.

---

## 08-02-26 Conversión Explícita de `account_id` a String en `ComprehensiveWebAnalysisTool` 🛠️

Se ha solucionado un `ValidationError` en `WebSearchTool` que ocurría porque `account_id` no era una cadena de texto válida al ser pasado desde `ComprehensiveWebAnalysisTool`.

- **Causa del Error**: Aunque `ComprehensiveWebAnalysisTool` definía `account_id` como `Optional[str]`, en algunos casos, un objeto `UUID` (o similar) se asignaba a `self.account_id`. Cuando este valor se pasaba a `get_web_search_tool` (que espera un `str`), se producía un error de validación.
- **Solución (`tools/comprehensive_web_analysis_tool.py`)**: Se añadió una conversión explícita a `str` para `self.account_id` al asignarlo a `effective_account_id` dentro del método `_arun`. Esto garantiza que `effective_account_id` sea siempre una cadena de texto (o `None`), resolviendo el error de validación en `WebSearchTool`.

---
## 08-02-26 Corrección de `ValidationError` en `ToolMessage` por `tool_call_id` nulo 🛠️

Se ha solucionado un `ValidationError` en `ToolMessage` que ocurría en el agente `DeepResearcher` cuando el `tool_call_id` era `None`.

- **Causa del Error**: En la función `supervisor_tools` de `core/agents/deep_researcher.py`, al construir `ToolMessage`, el campo `tool_call_id` podía ser `None` si el LLM no lo proporcionaba o si había un problema en la estructura del `tool_call`. Esto generaba un error de validación en Pydantic.
- **Solución (`core/agents/deep_researcher.py`)**:
  - Se importó el módulo `uuid` para la generación de identificadores únicos.
  - Se modificó la función `supervisor_tools` para asegurar que `tool_call_id` siempre tenga un valor válido. Si `tc.get("id")` es `None`, se genera un UUID (`uuid.uuid4()`) y se utiliza como `tool_call_id`.
  - Este cambio se aplicó en tres puntos clave dentro de `supervisor_tools`:
    - Al procesar herramientas que no son `ConductResearch`.
    - Al procesar los resultados de las tareas `ConductResearch` ejecutadas en paralelo.
    - Al construir la lista final de `ToolMessages` en el orden original.
  - Esto garantiza que todas las `ToolMessage` creadas tengan un `tool_call_id` válido, evitando el `ValidationError`.