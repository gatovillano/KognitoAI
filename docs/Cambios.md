## 09-02-26 Corrección de Errores de UUID y URL en Compartir Análisis 🔧

Se han solucionado cuatro errores críticos en la funcionalidad de compartir análisis: errores de UUID, una URL incorrecta, comparación de tipos incorrecta y conversión redundante de UUID.

- **Error 1: UUID en SQLAlchemy/psycopg**
  - **Causa**: El código utilizaba `UUID` de SQLAlchemy (que es un tipo de columna) en lugar del módulo `uuid` de Python para convertir strings a objetos UUID. Esto causaba el error `psycopg.ProgrammingError: cannot adapt type 'UUID' using placeholder '%s' (format: AUTO)`.
  - **Solución (`api/analysis_share.py`)**:
    - Se reemplazaron todas las instancias de `from sqlalchemy.dialects.postgresql import UUID` y `analysis_uuid = UUID(...)` por `import uuid` y `analysis_uuid = uuid.UUID(...)`.
    - Esto afecta a 5 funciones: [`create_share_analysis_link`](api/analysis_share.py:84), [`list_share_analysis_links`](api/analysis_share.py:166), [`revoke_share_analysis_link`](api/analysis_share.py:225), [`access_shared_analysis`](api/analysis_share.py:277) y [`get_shared_analysis_info`](api/analysis_share.py:368).
    - Ahora los objetos UUID de Python se pasan correctamente a SQLAlchemy, que se encarga de la conversión automática para PostgreSQL.

- **Error 2: URL Incorrecta en Enlaces Compartidos**
  - **Causa**: El backend generaba URLs con el dominio hardcoded "<https://kognito.ai>" que no existe, en lugar de usar el dominio actual de la aplicación.
  - **Solución**:
    - **Backend (`api/analysis_share.py`)**: Se eliminó la generación de URLs completas en el backend. Ahora solo se devuelve el token, siguiendo el mismo patrón que los álbumes de fotos.
    - **Frontend (`src/components/ShareAnalysisDialog.tsx`)**: Se actualizó para construir la URL usando `window.location.origin`, que obtiene dinámicamente el dominio actual del navegador.
    - Esto asegura que los enlaces funcionen correctamente tanto en desarrollo como en producción, usando el dominio correcto de la aplicación.

- **Error 3: Comparación de Tipos Incorrecta en account_id**
  - **Causa**: El `current_account_id` es un string, pero `AnalysisTask.account_id` es un UUID en la base de datos. La comparación directa fallaba porque PostgreSQL no podía comparar un string con un UUID.
  - **Solución (`api/analysis_share.py`)**:
    - Se agregó la conversión de `current_account_id` a UUID antes de compararlo con `AnalysisTask.account_id`.
    - Esto afecta a 3 funciones: [`create_share_analysis_link`](api/analysis_share.py:84), [`list_share_analysis_links`](api/analysis_share.py:166) y [`revoke_share_analysis_link`](api/analysis_share.py:225).
    - Ahora la consulta SQL compara correctamente dos UUIDs, resolviendo el error 404 "Analysis not found or you don't have permission to share it."

- **Error 4: Conversión Redundante de UUID en shared_link.analysis_id**
  - **Causa**: `shared_link.analysis_id` ya es un UUID (viene de la base de datos), pero el código intentaba convertirlo de nuevo a UUID con `uuid.UUID(shared_link.analysis_id)`, causando el error `'UUID' object has no attribute 'replace'`.
  - **Solución (`api/analysis_share.py`)**:
    - Se agregó una verificación de tipo antes de convertir: `analysis_uuid = shared_link.analysis_id if isinstance(shared_link.analysis_id, uuid.UUID) else uuid.UUID(shared_link.analysis_id)`.
    - Esto afecta a 2 funciones: [`access_shared_analysis`](api/analysis_share.py:277) y [`get_shared_analysis_info`](api/analysis_share.py:368).

---

## 15-02-26 Corrección de Conflicto de Dependencias en Docker Build 🔧

Se ha solucionado el error de conflicto de dependencias de langchain que impedía el build de Docker.

- **Error: Dependency Resolution Impossible**
  - **Causa**: Los constraints muy restrictivos en las dependencias de langchain entraban en conflicto. Además, langchain-community 0.3.28+ requiere específicamente langchain >= 0.3.27.
  - **Solución (`requirements.txt`)**:
    - Se especificaron versiones mínimas exactas: langchain>=0.3.27 y langchain-community>=0.3.27 para asegurar compatibilidad.
    - Se mantuvieron los límites superiores (<0.4.0) para mantener la serie 0.3.x.
    - Cambios específicos:
      - `langchain>=0.3.0,<0.4.0` → `langchain>=0.3.27,<0.4.0`
      - `langchain-community>=0.3.0,<0.3.28` → `langchain-community>=0.3.27,<0.4.0`
      - `langchain-google-genai>=4.2.0` → `langchain-google-genai>=4.0.0`
      - `langchain-google-vertexai>=3.2.2` → `langchain-google-vertexai>=2.0.0`
      - `langchain-openai>=1.1.9` → `langchain-openai>=1.0.0`
      - `langchain-postgres==0.0.16` → `langchain-postgres>=0.0.1`
      - `litellm==1.81.10` → `litellm>=1.0.0`
      - `langgraph==1.0.8` → `langgraph>=1.0.0`
      - `tavily-python==0.7.21` → `tavily-python>=0.5.0`
      - `requests>=2.32.3` → `requests>=2.0.0`
    - Se agregó `requests>=2.32.5` en el Dockerfile.core.hybrid para forzar actualización de requests antes de instalar dependencias, ya que la imagen base tiene requests==2.32.3.

---

## 11-02-26 Corrección de Errores en Deep Research: Fuentes y Accesos a Diccionarios 🔧

Se han corregido múltiples errores en el sistema de Deep Research que causaban que las fuentes no se renderizaran correctamente.

- **Problema 1: Acceso Incorrecto a Objeto Diccionario**
  - **Causa**: En [`comprehensive_web_analysis_tool.py`](tools/comprehensive_web_analysis_tool.py:113), el código intentaba acceder a `search_results_obj.context_for_llm` pero `search_results_obj` es un diccionario retornado por `web_search_tool.py` (usando `.model_dump()`).
  - **Solución**: Se cambió `return search_results_obj.get('context_for_llm', '')` por `return search_results_obj.get('context_for_llm', '')`.

- **Problema 2: Tipo de Parámetro Incorrecto en _extract_urls**
  - **Causa**: El método `_extract_urls` tenía un type hint `List[Source]` pero recibía una lista de diccionarios del resultado de búsqueda.
  - **Solución**: Se cambió a `List[Dict]` y se añadió el import de `Dict` desde typing.

- **Problema 3: Retorno del Tool Sin Fuentes**
  - **Causa**: El `comprehensive_web_analysis_tool.py` guardaba las fuentes en la base de datos pero no las incluía en el retorno del tool, por lo que el `deep_researcher.py` no podía procesarlas.
  - **Solución**: Se modificó el retorno del tool para incluir un diccionario con `report`, `sources` y `formatted_sources`:

    ```python
    return {
        "report": final_report,
        "sources": urls_to_scrape_accumulated,
        "formatted_sources": formatted_sources
    }
    ```

  - Esto permite que el `deep_researcher.py` extraiga correctamente las fuentes en las líneas 658-660.

---

## 09-02-26 Corrección de Fuentes Vacías en Investigación Profunda 🔍

Se ha corregido el problema por el cual las fuentes no llegaban en los reportes de investigación profunda (`sources: []`).

- **Problema 1: Regex incompatible con formato Tavily**
  - **Causa**: La regex en [`compress_research`](core/agents/deep_researcher.py:920) buscaba `Content:` pero Tavily devuelve `SUMMARY:`.
  - **Solución**: Se actualizó la regex para buscar ambos formatos: `(?:SUMMARY|Content):`.

- **Problema 2: Debugging insuficiente**
  - **Causa**: No había suficiente logging para diagnosticar problemas de extracción de fuentes.
  - **Solución**: Se agregó logging extensivo en:
    - [`compress_research`](core/agents/deep_researcher.py:874-952): Para mostrar conteo de mensajes, nombres de herramientas encontradas, URLs y títulos extraídos.
    - [`supervisor_tools`](core/agents/deep_researcher.py:676-681): Para mostrar el total de fuentes retornadas.
    - [`final_report_generation`](core/agents/deep_researcher.py:353-359): Para mostrar las fuentes recibidas antes de la deduplicación.

- **Problema 3: Posible pérdida de fuentes en el retorno del supervisor**
  - **Causa**: Las fuentes podían no propagarse correctamente desde el subgrafo del supervisor.
  - **Solución**: Se aseguró que [`supervisor_tools`](core/agents/deep_researcher.py:676-681) siempre incluya `sources` en el payload de retorno, incluso si está vacío.

- **Mejora: Manejo robusto de fuentes sin URL**
  - **Causa**: Si una fuente no tenía URL, la deduplicación podía fallar.
  - **Solución**: Se cambió `source['url']` a `source.get('url')` en la deduplicación para evitar errores cuando falta la URL.

---

## 09-02-26 Implementada funcionalidad para compartir análisis por enlace 🔗

Se ha implementado la funcionalidad completa para compartir informes de análisis a través de enlaces compartibles. Los usuarios ahora pueden generar enlaces que permiten visualizar análisis sin necesidad de iniciar sesión.

- **Modelo de Base de Datos (`core/database.py`)**:
  - Añadido nuevo modelo `SharedAnalysisLink` para almacenar los enlaces de análisis compartidos
  - Incluye campos para: token único, hash de contraseña, fecha de expiración, y permisos de descarga

- **API Backend (`api/analysis_share.py`)**:
  - **Endpoint `POST /api/analysis/share/create`**: Crea un nuevo enlace compartido para un análisis
  - **Endpoint `GET /api/analysis/share/list`**: Lista todos los enlaces compartidos de un análisis
  - **Endpoint `DELETE /api/analysis/share/{token}`**: Revoca un enlace compartido
  - **Endpoint `POST /api/analysis/share/access/{token}`**: Accede a un análisis compartido (con soporte de contraseña)
  - **Endpoint `GET /api/analysis/share/info/{token}`**: Obtiene información básica del análisis compartido
  - Características: protección con contraseña opcional, fecha de expiración configurable (1-365 días), control de descarga PDF

- **Frontend - Diálogo de Compartir (`src/components/ShareAnalysisDialog.tsx`)**:
  - Nuevo componente React para generar enlaces de compartir
  - Opciones para establecer contraseña y fecha de expiración
  - Botón para copiar enlace al portapapeles
  - Integración con el flujo existente de análisis

- **Frontend - Página de Visualización (`src/app/share/analysis/[token]/page.tsx`)**:
  - Nueva página de aplicación Next.js para visualizar análisis compartidos
  - Diseño a pantalla completa similar a los diálogos de resultados
  - Soporte para protección con contraseña
  - Visualización del resumen y datos del análisis
  - Indicadores de fecha de creación y tipo de análisis

- **Integración en Diálogos Existentes**:
  - **`AnalysisDetailDialog.tsx`**: Añadido botón de compartir y componente `ShareAnalysisDialog`
  - **`DeepResearchDetailDialog.tsx`**: Añadido botón de compartir y componente `ShareAnalysisDialog`

- **Flujo de Usuario**:
  1. Usuario abre un análisis completado
  2. Hace clic en el botón de compartir (icono de enlace)
  3. Configura opciones: contraseña opcional y fecha de expiración
  4. Genera el enlace compartido
  5. Copia el enlace y lo comparte con otros
  6. Los destinatarios acceden al enlace y ven el análisis a pantalla completa

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
  - **Lógica de Autoscroll Optimizada**: El chat ahora detecta si el usuario ha subido manually para leer mensajes anteriores, desactivando temporalmente el autoscroll para no interrumpir la lectura.
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

Se ha completado la migración de todas las herramientas y utilidades críticas para eliminar las llamadas directas a los modelos de Google (Gemin) a través de `langchain_google_genai`, unificando toda la gestión de modelos bajo **LiteLLM**. Esto resuelve errores de compatibilidad y asegura un comportamiento agnóstico al proveedor.

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
  - Se modificó la lógica de manejo de errores en `invoke_structured_output`.
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

## 09-02-26 Mejorada la Página de Análisis Compartido con Componentes Visuales y Diálogos 🎨

Se ha mejorado significativamente la página de análisis compartido para mostrar los análisis con una visualización rica similar a los diálogos originales, incluyendo diálogos interactivos para brechas de conocimiento, conceptos y citas de temas.

- **Reducción de Ancho de Página**:
  - Se cambió el ancho máximo de `max-w-6xl` a `max-w-4xl` para una visualización más concentrada y legible en `src/app/share/analysis/[token]/page.tsx`.

- **Visualización Rica de Contenido**:
  - Se implementó una función `renderRichContent` que procesa diferentes tipos de contenido (strings, arrays, objetos) y los renderiza con formato markdown apropiado.
  - Los datos de `full_data` y `result_payload` ahora se muestran en tarjetas separadas con estilos por tipo de análisis.
  - Se excluyen campos redundantes como `summary` y `executive_summary` para evitar duplicación.

- **Diálogos Interactivos Agregados**:
  - **`ConceptDetailDialog`**: Muestra detalles de conceptos con nombre y definición en formato markdown.
  - **`ThemeQuotesDialog`**: Presenta citas relacionadas con temas específicos encontrados en los documentos.
  - **`QuestionSliderDialog`**: Integrado desde `@/components/QuestionSliderDialog` para explorar y desarrollar brechas de conocimiento.

- **Integración de `SourcesTab`**:
  - Se añadió el componente `SourcesTab` para mostrar las fuentes del análisis de manera visual y navegable.

- **Colores por Tipo de Análisis**:
  - Sistema de esquemas de color (`getAnalysisColorScheme`) que aplica estilos visuales coherentes según el tipo de análisis (documento, colección, semántico, código, etc.).

- **Flujo de Usuario Mejorado**:
  1. Usuario accede al enlace compartido
  2. Ve el análisis con formato visual rico
  3. Puede interactuar con conceptos, temas y brechas de conocimiento
  4. Explora las fuentes utilizadas
  5. Comparte el enlace si lo desea

Se han solucionado dos errores de validación críticos en el agente `DeepResearcher` que causaban la caída del servicio `kognito_core` y, como consecuencia, la pérdida de conexión del bot de Telegram.

- **Error 1: `KnowledgeSearchInput` (Entrada de Búsqueda de Conocimiento)**
  - **Causa**: El LLM generaba un texto con formato de lista (ej. `'["ley"]'`) para el filtro `filter_topics`, pero la herramienta esperaba una lista real (`['ley']`), causando un error de validación.
  - **Solución (`tools/knowledge_search_tool.py`)**: Se añadió un validador de Pydantic al modelo de entrada. Este validador ahora convierte automáticamente el texto en una lista antes de la validación, haciendo la herramienta más robusta frente a las inconsistencias de formato del LLM.

- **Error 2: `WebSearchTool` (Herramienta de Búsqueda Web)**
  - **Causa**: La herramienta `WebSearchTool` era instanciada con un `account_id` que no era de tipo `string` (probablemente `None`), lo que provocaba un error de validación.

---

## 09-02-26 Transformación de Datos para Componentes de Análisis Compartido 🔧

Se ha implementado la transformación de datos en la página de análisis compartido para que los componentes especializados (`SemanticAnalysis`, `CollectionAnalysis`, `DocumentAnalysis`, `CodeAnalysis`, `NoteAnalysis`, etc.) reciban los datos en el formato correcto según el tipo de análisis.

- **Problema**: El `result_payload` de la API puede tener una estructura anidada diferente a la esperada por los componentes especializados. Por ejemplo, para análisis semántico, los datos pueden estar en `semantic_analysis` en lugar de directamente en el objeto raíz.
- **Solución (`src/app/share/analysis/[token]/page.tsx`)**:

Se ha corregido la página de análisis compartido para que transforme correctamente los datos del `result_payload` según el tipo de análisis, permitiendo que los componentes especializados (`SemanticAnalysis`, `CollectionAnalysis`, etc.) rendericen correctamente el contenido en lugar de mostrarlo como texto plano.

- **Problema**: Los componentes especializados esperan una estructura de datos específica (ej. `collection_summary`, `temas_transversales`, etc.), pero el `result_payload` de la API puede tener una estructura diferente (ej. `semantic_analysis`, `collection_analysis`, etc.).
- **Solución (`src/app/share/analysis/[token]/page.tsx`)**:

Se ha corregido la página de análisis compartido para que muestre los análisis utilizando los mismos componentes especializados que se usan en el diálogo de análisis, incluyendo el componente `SourcesTab` para las fuentes. Antes, los análisis se mostraban como texto plano/JSON.

- **Problema**: La página `src/app/share/analysis/[token]/page.tsx` iteraba sobre `result_payload` y convertía cada campo a `JSON.stringify`, mostrando los datos como texto plano en lugar de usar los componentes ricos de visualización.
- **Solución**:
  - **Importación de componentes específicos**: Se importaron todos los componentes de análisis especializados (`SemanticAnalysis`, `CollectionAnalysisComponent`, `DocumentAnalysisComponent`, `CodeAnalysisComponent`, `NoteCollectionAnalysisComponent`, `NoteAnalysisComponent`, `DeepResearchAnalysis`, `ProactiveInsightAnalysis`, `ComprehensiveWebAnalysis`, `ScopedRagAnalysis`, `NeuralInsightAnalysis`).
  - **Función `renderTypeSpecificContent`**: Se implementó una función que selecciona el componente apropiado según el tipo de análisis (`analysis.analysis.type`), pasando los datos en el formato esperado (`full_data` o `result`).
  - **Integración de `SourcesTab`**: Se añadió el componente `SourcesTab` para mostrar las fuentes de manera enriquecida con tarjetas, filtros y búsqueda, solo cuando hay fuentes disponibles.
  - **Funciones auxiliares**: Se copiaron las funciones `getAnalysisColorScheme`, `getAnalysisTypeBadgeColor` y `getAnalysisTypeLabel` desde `analysis-detail-dialog.tsx` para mantener la consistencia visual.
  - **Soporte de TTS**: Se implementó un hook `useSimpleTTS` simple para permitir la síntesis de voz en la página compartida, manteniendo la funcionalidad de escuchar el resumen.
  - **Estructura de datos**: Se preparan los datos de fuentes desde `result_payload.sources` al formato esperado por `SourcesTab` (con `id`, `title`, `snippet`, `url`, `type`, `metadata`).
- **Archivos modificados**:
  - `src/app/share/analysis/[token]/page.tsx`: Reescrito completamente para usar el sistema de componentes específicos.
  - **Solución (`tools/web_search_tool.py`)**: Se modificó la herramienta para que el `account_id` sea opcional y se añadió una verificación al inicio de su ejecución. Si el `account_id` no es válido, la herramienta ahora devuelve un mensaje de error controlado en lugar de fallar.

- **Impacto General**: Al resolver estos errores, se estabiliza el servicio `kognito_core`, lo que a su vez garantiza que la conexión WebSocket con el `telegram_client` se mantenga activa, restaurando la funcionalidad del bot de Telegram.

---

## 08-02-26 Corrección de `UnboundLocalError` en la Generación del Informe Final del Agente Investigador 📄✍️

Se ha solucionado un error `UnboundLocalError` que ocurría durante la generación del informe final en el agente `DeepResearcher`.

- **Causa del Error**: La variable `final_report` se referenciaba antes de ser asignada en el bloque `try/except`, causando un error cuando la generación del informe fallaba.
- **Solución (`core/agents/deep_researcher.py`)**:
  - Se inicializó `final_report` con un valor por defecto antes del bloque `try/except`.
  - Se mejoró el manejo de errores para capturar y registrar excepciones durante la generación del informe.
  - Se añadió un mensaje de error descriptivo cuando la generación del informe falla.

---

## 09-02-26 Corrección de Renderizado de Fuentes en Diálogo de Investigación Profunda 🔧

Se ha solucionado el problema donde las fuentes no se renderizaban correctamente en el diálogo de detalles de Investigación Profunda.

- **Causa del Problema**: El mapeo de fuentes en [`deep-research-detail-dialog.tsx`](src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx:34-47) realizaba un cast inseguro del tipo `string` a `Source['type']`. Si el valor no coincidía con los tipos válidos ('web', 'document', 'memory', 'code', 'database', 'graph', 'note', 'github'), las fuentes no se renderizaban correctamente.

- **Solución Implementada (Frontend)**:
  - **Función de Normalización de Tipos**: Se creó la función `normalizeSourceType` que valida y normaliza el tipo de fuente.
  - **Validación de Tipos Válidos**: La función verifica si el tipo es uno de los valores válidos antes de asignarlo.
  - **Mapeo de Tipos Comunes**: Se implementó un mapeo de tipos comunes que podrían venir del backend (ej. 'url' → 'web', 'file' → 'document', 'repo' → 'github').
  - **Fallback a Tipo por Defecto**: Si el tipo no es reconocido, se asigna 'web' como valor por defecto.
  - **Mejora en Logging**: Se añadieron logs de depuración para rastrear el proceso de normalización de tipos.

- **Archivos Modificados (Frontend)**:
  - [`src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx`](src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx:34-83): Implementación de la función `normalizeSourceType` y mejora del mapeo de fuentes.

---

## 09-02-26 Corrección de Extracción de Fuentes en Backend para Investigación Profunda 🔧

Se ha solucionado el problema donde las fuentes no se guardaban en el informe final de Investigación Profunda debido a que el backend no las extraía correctamente.

- **Causa del Problema**: En la función `compress_research` en [`deep_researcher.py`](core/agents/deep_researcher.py:876-925), el código estaba extrayendo las fuentes SOLO de los mensajes de herramienta con nombre `"tavily_search"`, cuando el nombre real de la herramienta es `"tavily_search_tool"`. Además, solo buscaba fuentes de una herramienta específica, ignorando otras herramientas de búsqueda como `web_search`, `ddg_search_tool`, y `multi_query_search`.

- **Solución Implementada (Backend)**:
  - **Lista de Herramientas de Búsqueda**: Se creó una lista `search_tool_names` que incluye todos los nombres de herramientas de búsqueda disponibles:
    - `tavily_search_tool`
    - `web_search`
    - `ddg_search_tool`
    - `multi_query_search`
    - `tavily_search` (por compatibilidad con versiones anteriores)
  - **Extracción de Fuentes Multi-Herramienta**: Se modificó la condición para buscar fuentes de todas las herramientas de búsqueda en la lista, no solo de una específica.
  - **Mejora en Logging**: Se actualizó el mensaje de error para incluir el nombre de la herramienta que causó el error, facilitando la depuración.

- **Archivos Modificados (Backend)**:
  - [`core/agents/deep_researcher.py`](core/agents/deep_researcher.py:876-925): Implementación de la lista de herramientas de búsqueda y modificación de la lógica de extracción de fuentes.

---

Se ha solucionado un error `UnboundLocalError` que ocurría en la etapa final de la generación de informes del agente `DeepResearcher`.

- **Causa del Error**: La función `final_report_generation` intentaba acceder a una variable local `findings` para construir el informe, pero esta variable nunca se inicializaba. Los resultados de la investigación se encontraban en el estado del agente (`state`), pero no se estaban cargando en la variable local.
- **Solución (`core/agents/deep_researcher.py`)**: Se añadió una línea al principio de la función `final_report_generation` para inicializar la variable `findings`. Esta línea recupera las notas de investigación (`state.get("notes", [])`) del estado del agente y las une en un único texto, asegurando que los hallazgos estén disponibles para la creación del informe final y evitando el error.

---

## 08-02-26 Fallo en `json_mode` para Salida Estructurada 🛠️

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

## 09-02-26 Carga Dinámica de Modelos desde Proveedores LLM 🌍🔄

Se ha implementado la carga dinámica de modelos directamente desde las APIs de todos los proveedores de LLM, eliminando listas hardcodeadas y asegurando que los usuarios vean los modelos realmente disponibles.

- **API de Modelos (`api/llm.py`)**: [UPDATE]
  - **Proveedor OpenRouter**: Implementación de llamada directa a `/api/v1/models` para obtener modelos actualizados.
  - **Proveedor OpenAI**: Integración con `/v1/models` para listar modelos GPT disponibles.
  - **Proveedor Anthropic**: Conexión con `/v1/models` con manejo de endpoint no disponible (usa lista conocida como fallback).
  - **Proveedor Google/Gemini**: Uso de Google Generative Language API para obtener modelos Gemini en tiempo real.
  - **Proveedor DeepSeek**: Integración con API compatible con OpenAI para listar modelos.
  - **Proveedor Mistral**: Conexión con `/v1/models` para modelos Mistral.
  - **Proveedor Groq**: Uso de `/openai/v1/models` para modelos de Groq.
  - **Proveedor Cerebras**: Integración con `/v1/models` para modelos de Cerebras.
  - **Proveedor Ollama**: Detección automática de modelos locales vía `/api/tags` con fallback a comunes.
  - **Proveedor Azure**: Configuración para Azure OpenAI endpoints.
  - **Proveedor HuggingFace**: Lista de modelos Inference API comunes.
  - **Proveedor Vertex AI**: Configuración para Google Cloud Vertex AI.

- **Gestor de LLMs (`core/llm_manager.py`)**: [UPDATE]
  - **Configuración Dinámica de Proveedores**: Actualizada la inicialización de LLMs (principal, rápido, visión) para detectar automáticamente el proveedor según el formato del modelo (`anthropic/`, `groq/`, `deepseek/`, `mistral/`, `cerebras/`, `vertex/`, `azure/`).
  - **Proveedores Soportados**: Anthropic, Groq, DeepSeek, Mistral, Cerebras, Vertex AI, Azure además de los ya existentes (OpenAI, Gemini, OpenRouter).
  - **Log Mejorado**: Mensajes de log específicos por proveedor para mejor trazabilidad.

- **Características de Seguridad y Rendimiento**:
  - **Caché de Modelos**: Implementación de caché en memoria (TTL: 1 hora) para evitar llamadas excesivas a las APIs.
  - **Credenciales del Usuario**: Uso de API keys del usuario (desde secretos encriptados) en lugar de globales cuando están disponibles.
  - **Fallbacks Robustos**: Listas conocidas como respaldo cuando las APIs no responden.

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

---

## 08-02-26 Rediseño Premium de Tarjetas de Fuentes de Investigación 🎨✨

Se ha implementado un rediseño completo del componente `SourcesTab.tsx`, elevando la experiencia de visualización de fuentes en "Investigaciones Profundas" a un nivel premium y altamente funcional.

- **Nueva Interfaz "Glassmorphism"**:
  - Se han sustituido las tarjetas básicas por componentes `Card` con efectos de translucidez, bordes sutiles y sombras suaves, alineados con una estética moderna y elegante.
  - Las transiciones de entrada y salida ahora están animadas con `framer-motion`, proporcionando una sensación de fluidez y respuesta inmediata.

- **Funcionalidades Avanzadas**:
  - **Búsqueda en Tiempo Real**: Se ha incorporado una barra de búsqueda que permite filtrar fuentes instantáneamente por título, contenido o URL.
  - **Filtrado por Categoría**: Pestañas de navegación intuitivas para alternar entre tipos de fuentes (Web, Documentos, GitHub, etc.), facilitando la gestión de grandes volúmenes de referencias.
  - **Acciones Rápidas**: Nuevos botones interactivos para copiar URLs y abrir fuentes externamente, con feedback visual (tooltips y cambios de icono).

- **Visualización de Datos Mejorada**:
  - **Indicadores de Relevancia**: Se han añadido gráficos circulares (anillos) para mostrar el porcentaje de similitud/relevancia de cada fuente de manera visual y atractiva.
  - **Etiquetado Inteligente**: Badges con colores distintivos para cada tipo de fuente (ej. Azul para Web, Índigo para GitHub, Púrpura para Memorias), mejorando la escaneabilidad del contenido.
  - **Scroll Interno**: Los fragmentos de texto (snippets) largos ahora cuentan con un área de scroll dedicada, manteniendo el diseño de la tarjeta limpio y uniforme.

---

## 08-02-26 Corrección de `TypeError` en `create_github_source` por argumento `file_path` inesperado 🛠️

Se ha solucionado un `TypeError` en `tools/github_repo_tool.py` que ocurría al llamar a `create_github_source()` con un argumento `file_path` inesperado.

- **Causa del Error**: La función `create_github_source` en `core/citation_models.py` no acepta un argumento `file_path`. Sin embargo, `tools/github_repo_tool.py` lo estaba pasando en las llamadas a esta función, lo que resultaba en un `TypeError`. Además, el `source_id` se estaba pasando como `node_id=None`, lo cual no era correcto.
- **Solución (`tools/github_repo_tool.py`)**:
  - Se eliminó el argumento `file_path` de las llamadas a `create_github_source` en las funciones `_run` y `_arun`.
  - Se generó un `source_id` único utilizando un hash SHA256 de la `full_url` del repositorio, asegurando que cada fuente tenga un identificador válido.
  - El `file_path` y `repo_url` ahora se pasan dentro del diccionario `metadata` de la fuente, que es el lugar adecuado para metadatos adicionales.
  - Esto garantiza que la función `create_github_source` sea llamada con los argumentos correctos, resolviendo el `TypeError`.

---

## 08-02-26 Corrección de `UnboundLocalError` en `proactive_memory_node` 🐛

Se ha solucionado un `UnboundLocalError` en la función `proactive_memory_node` de `core/agent.py` que impedía el correcto funcionamiento de la memoria proactiva.

- **Causa del Error**: La variable `HumanMessage` se utilizaba en la función `proactive_memory_node` antes de que se ejecutara su importación local dentro de la misma función. Esto provocaba un `UnboundLocalError`.
- **Solución (`core/agent.py`)**:
  - `HumanMessage` ya estaba importado globalmente al principio del archivo, por lo que eliminar la importación local resuelve el conflicto de alcance y permite que la función acceda correctamente a la clase `HumanMessage`.

---

---

## 25-02-26 Optimización de la Experiencia de Usuario en Investigación Profunda 🤫🎨

Se ha mejorado la fluidez del chat durante investigaciones profundas al silenciar los mensajes de progreso intermedios, manteniendo una visualización premium y coherente.

- **Filtrado de Mensajes en Chat (`src/components/CommonChat.tsx`)**:
  - Se modificó la lógica de recepción de mensajes WebSocket para ignorar la creación de burbujas de "Usando herramienta..." y notificaciones de completado para `deep_research`.
  - Esto evita que el historial de chat se llene de mensajes redundantes, permitiendo que el usuario se concentre en el **DeepResearchVisualizer** interactivo.
  - Se mantuvieron activos los eventos de progreso para alimentar el visualizador en tiempo real sin generar ruido textual.

- **Consistencia de Datos en API (`api/deep_research.py`)**:
  - Se actualizaron los endpoints `run_deep_research` y `clarify_deep_research` para incluir siempre el campo `visual_schema`.
  - Esto asegura que el esquema visual (HTML/CSS) generado por el agente esté disponible de forma consistente en todas las vistas de respuesta, eliminando discrepancias entre la generación del agente y la entrega de la API.

- **Mejoras Visuales y de UX**:
  - Desactivación de toasts de éxito/error para la herramienta de investigación, eliminando interrupciones visuales repetitivas mientras el proceso sigue en curso en segundo plano.

- **Frontend (`src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx`)**:
  - Se añadió un botón "Exportar a PDF" en el encabezado del diálogo de detalles.
  - Se implementó la lógica para llamar al nuevo endpoint y abrir el PDF generado en una nueva pestaña.
  - Se añadió un estado de carga (`Loader2`) para mejorar la experiencia de usuario durante la generación.

---

## 08-02-26 Implementación de Exportación a PDF en Investigación Profunda 📄🚀

Se ha implementado la funcionalidad para exportar los resultados de una Investigación Profunda a un archivo PDF profesional.

- **Backend (`api/deep_research.py`)**:
  - Se creó un nuevo endpoint `POST /deep_research/export_pdf`.
  - Este endpoint utiliza un LLM para formatear el contenido de la investigación en HTML semántico y luego invoca la herramienta `CreatePDFTool` para generar el archivo PDF.
  - Se añadió el modelo `DeepResearchPDFExportRequest` para validar los datos de entrada.

- **Frontend (`src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx`)**:
  - Se añadió un botón "Exportar a PDF" en el encabezado del diálogo de detalles.
  - Se implementó la lógica para llamar al nuevo endpoint y abrir el PDF generado en una nueva pestaña.
  - Se añadió un estado de carga (`Loader2`) para mejorar la experiencia de usuario durante la generación.

---

## 08-02-26 Solución de `TimeoutError` en Streaming con LiteLLM 🔧🕒

Se ha solucionado un `TimeoutError` crítico que interrumpía la generación de respuestas largas o complejas durante el streaming del agente, causado por el uso de valores por defecto en el cliente HTTP subyacente.

- **Configuración de Timeout Explícito (`core/llm_manager.py`)**:
  - Se modificaron las funciones `get_llm_for_user` e `initialize_llms` para inyectar explícitamente el parámetro `timeout` al instanciar `ChatLiteLLM`.
  - El valor del timeout ahora se toma directamente de `settings.llm_request_timeout` (configurable vía variable de entorno `LLM_REQUEST_TIMEOUT`, por defecto 120s).
  - Esto asegura que `liteLLM` propague correctamente el tiempo de espera a la capa de transporte (`aiohttp`/`httpx`), evitando cortes prematuros en la conexión cuando el modelo tarda en responder.

---

## 08-02-26 Aumento del Timeout para Solicitudes LLM ⏳

Se ha aumentado el tiempo de espera predeterminado para las solicitudes a los modelos de lenguaje (LLM) para evitar `TimeoutException` en respuestas largas o complejas.

- **Punto 1**: Se modificó la configuración en `core/config.py` para establecer el valor por defecto de `LLM_REQUEST_TIMEOUT` de 120 a 300 segundos.
- **Punto 2**: Este cambio se propaga a `core/llm_manager.py`, donde `ChatLiteLLM` utiliza `settings.llm_request_timeout` para configurar el timeout de las solicitudes.
- **Impacto**: El sistema ahora esperará hasta 5 minutos por una respuesta del LLM antes de lanzar un error de tiempo de espera, mejorando la robustez en escenarios de alta latencia o respuestas extensas.

---

## 09-02-26 Transformación de Datos para Componentes de Análisis Compartido 🔧

Se ha implementado la transformación de datos en la página de análisis compartido para que los componentes especializados (`SemanticAnalysis`, `CollectionAnalysis`, `DocumentAnalysis`, `CodeAnalysis`, `NoteAnalysis`, etc.) reciban los datos en el formato correcto según el tipo de análisis.

- **Problema**: El `result_payload` de la API puede tener una estructura anidada diferente a la esperada por los componentes especializados. Por ejemplo, para análisis semántico, los datos pueden estar en `semantic_analysis` en lugar de directamente en el objeto raíz.
- **Solución (`src/app/share/analysis/[token]/page.tsx`)**:

---

## 08-02-26 Corrección de Visualización de Razonamiento Nativo en Frontend 🧠

Se ha solucionado un problema que impedía que el razonamiento nativo de los LLMs se mostrara en la interfaz de usuario.

- **Punto 1: Mejora en la Detección de Modelos (`core/llm_manager.py`)**: Se amplió la lista de palabras clave para detectar modelos con capacidad de razonamiento, incluyendo "claude-3.5-sonnet" y "gemma-2", y se añadieron logs más explícitos para verificar la activación del razonamiento.
- **Punto 2: Persistencia del Razonamiento en el Agente (`core/agent.py`)**: Se corrigió la construcción del mensaje final de la IA para asegurar que el `full_reasoning_content` se incluya siempre en los `additional_kwargs` del mensaje.
- **Punto 3: Propagación del Razonamiento al Frontend (`src/components/CommonChat.tsx`)**: Se modificó el manejador de eventos `stream_end` del WebSocket para que el campo `reasoning` se conserve en el estado del mensaje final, permitiendo que el componente `ChatMessage` lo renderice correctamente.

---

## 09-02-26 Corrección de Error de Validación de Pydantic en KognitoPGVectorRetriever 🔧

Se ha corregido un error de validación de Pydantic que causaba fallos en la búsqueda de memorias cuando `workspace_id` no era un string válido.

- **Causa del Error**: El validador de Pydantic esperaba que `workspace_id` fuera un string, pero podía recibir otros tipos de datos (como `None` u otros objetos), causando el error `str type expected (type=type_error.str)`.
- **Solución (`core/memory_manager.py`)**:
  - Se añadió un import de `validator` desde `pydantic`.
  - Se agregaron validadores `@validator('workspace_id', pre=True, always=True)` a las clases `KognitoPGVectorRetriever` y `KognitoFTSRetriever`.
  - Los validadores normalizan el valor de `workspace_id` para que siempre sea `None` o un string válido.
- **Solución (`utils/multi_query_retriever.py`)**:
  - Se eliminaron los parámetros inválidos `team_id` y `visibility_teams` de la llamada fallback a `get_relevant_memories` en la función `search_with_multiple_queries`.
- **Impacto**: El sistema ahora puede manejar correctamente valores de `workspace_id` de cualquier tipo, evitando errores de validación y permitiendo que la búsqueda de memorias funcione correctamente.

---

## 09-02-26 Documentación de Sistema de IA Anticipatoria para KognitoAI 🚀

Se ha creado una guía completa para implementar un sistema anticipatorio que genera insights y predice necesidades del usuario antes de que se soliciten explícitamente.

- **Concepto de IA Anticipatoria**:
  - El sistema va más allá del modelo reactivo tradicional, monitorizando patrones en el comportamiento del usuario, prediciendo necesidades futuras basándose en datos históricos y contexto actual, y generando insights proactivamente.

- **Arquitectura en Capas**:
  - **Capa de Interfaz**: WebSocket, notificaciones y dashboard de insights.
  - **Capa de Insights**: Generador de patrones, motor de predicciones, alertador inteligente y generador de recomendaciones.
  - **Capa de Contexto**: Graph de conocimiento, memoria mejorada, perfil de usuario y contexto temporal.
  - **Capa de Datos**: PostgreSQL, Neo4j, VectorDB y memoria conversacional.

- **Componentes Principales Implementados (`docs/anticipatory_ai_system.md`)**:
  - **Pattern Recognition Engine** (`core/anticipation/pattern_recognition.py`): Detecta patrones temporales, de contenido y de consulta en el historial del usuario.
  - **Prediction Engine** (`core/anticipation/prediction_engine.py`): Genera predicciones sobre próximas necesidades, brechas de información, deadlines y oportunidades.
  - **Proactive Insight Generator** (`core/anticipation/insight_generator.py`): Convierte predicciones en insights accionables categorizados.
  - **Anticipation Scheduler** (`core/anticipation/anticipation_scheduler.py`): Planifica y ejecuta tareas proactivas según triggers configurados.

- **Tipos de Predicciones**:
  - **NEXT_NEED**: Predice qué necesitará el usuario a continuación.
  - **INFORMATION_GAP**: Detecta temas consultados sin documentación guardada.
  - **DEADLINE_APPROACHING**: Notifica tareas con fecha de entrega próxima.
  - **OPPORTUNITY**: Identifica nuevas oportunidades basadas en intereses.

- **Categorías de Insights**:
  - PATTERN_DISCOVERY, CORRELATION, TREND, RECOMMENDATION, WARNING, OPPORTUNITY.

- **Integración con Agente Existente**:
  - `AnticipatoryAgent` extiende el agente base para incluir capacidades anticipatorias.
  - Los insights se incluyen automáticamente en las respuestas del agente.
  - API REST para acceder a insights y manejar acciones del usuario.

- **Métricas y Monitoreo**:
  - Sistema de métricas para evaluar engagement y precisión de predicciones.
  - Registro de interacciones con insights (generados, actuados, descartados).

- **Beneficios Principales**:
  - Respuestas proactivas en lugar de solo reactivas.
  - Personalización avanzada basada en comportamiento histórico.
  - Detección temprana de oportunidades y riesgos.
  - Mejora continua mediante métricas de engagement.

El documento completo incluye ejemplos de código para todos los componentes, API de integración y ejemplo de flujo de uso
---

## 11-02-26 Corrección de Extracción de Fuentes en Investigación Profunda 🕵️‍♂️

Se ha solucionado un error fundamental que impedía la extracción de fuentes en los informes de investigación profunda. La causa era un método de parsing frágil basado en expresiones regulares que no era compatible con el formato de salida estructurado (JSON) de las herramientas de búsqueda.

- **Causa del Error**: La función `compress_research` en `core/agents/deep_researcher.py` intentaba parsear el resultado de las herramientas de búsqueda (que es una lista de diccionarios en formato JSON) como si fuera texto plano, usando expresiones regulares. Esto fallaba silenciosamente, resultando en una lista de fuentes vacía.
- **Solución Implementada**:
  - **Parsing Robusto de JSON**: Se ha reemplazado completamente la lógica de expresiones regulares por un método de parsing de JSON robusto.
  - **Manejo de Múltiples Formatos**: El nuevo código primero verifica si el contenido del resultado de la herramienta ya es un objeto de Python (una lista). Si es una cadena de texto, intenta decodificarla como JSON.
  - **Extracción Estructurada**: Una vez que tiene la lista de diccionarios, itera sobre ella y extrae de forma segura los campos `url`, `title` y `snippet` de cada fuente.
  - **Mejora de Logs**: Se han añadido logs más claros para diagnosticar si la extracción de una fuente fue exitosa (`✅`) o si el formato del contenido no era el esperado (`⚠️`).
- **Impacto**: Este cambio asegura que las fuentes se extraigan de manera fiable independientemente de pequeños cambios en el formato de salida de las herramientas de búsqueda, solucionando el problema de raíz y garantizando que los informes de investigación profunda siempre incluyan sus referencias. 🚀

---

## 11-02-26 Corrección de TypeError en el Filtrado de Fuentes 🛡️

Se ha solucionado un error `TypeError: Cannot read properties of undefined (reading 'toLowerCase')` que ocurría en el componente `SourcesTab.tsx` al intentar filtrar las fuentes para la búsqueda.

- **Causa del Error**: La lógica de filtrado intentaba acceder a las propiedades `source.title`, `source.snippet` y `source.url` sin verificar si existían. Si alguna de estas propiedades era `null` o `undefined` en los datos de una fuente, la llamada a `.toLowerCase()` provocaba un error que rompía la aplicación.
- **Solución Implementada**:
  - **Manejo Seguro de Nulos**: Se ha modificado la lógica de filtrado en `src/components/SourcesTab.tsx` para utilizar "optional chaining" (`?.`) y el "nullish coalescing operator" (`?? ''`).
  - **Lógica Actualizada**: La comprobación ahora es `(source.title?.toLowerCase() ?? '').includes(query)`. Esto asegura que si `source.title` (o `snippet`, o `url`) es nulo o indefinido, se trate como una cadena vacía para la comparación, en lugar de lanzar un error.
- **Impacto**: El componente de filtrado de fuentes ahora es más robusto y puede manejar datos de fuentes incompletos sin fallar, mejorando la estabilidad de la página de análisis compartido y otros lugares donde se utiliza `SourcesTab`.

---

## 11-02-26 Corrección de ProgrammingError: Columna `tts_provider` no existe 🛠️

Se ha solucionado el `ProgrammingError` que indicaba que la columna `accounts.tts_provider` no existía en la base de datos, a pesar de estar definida en el modelo `Account`. Este error impedía la correcta inicialización de las herramientas programadas.

- **Causa del Error**: El esquema de la base de datos no estaba sincronizado con el modelo `Account` en `core/database.py`, donde se definen las columnas `tts_provider`, `tts_model`, `tts_voice` y `tts_speed`.
- **Solución Implementada**:
  - Se generó una nueva migración de Alembic (`eeedefc8932c_add_tts_configuration_to_account_model.py`) para añadir las columnas faltantes a la tabla `accounts`.
  - Se aplicó la migración a la base de datos utilizando `alembic upgrade head` dentro del contenedor `kognito_core`.
- **Impacto**: La base de datos ahora está sincronizada con el modelo `Account`, resolviendo el `ProgrammingError` y permitiendo que la aplicación funcione correctamente con las configuraciones de TTS.

---

## 11-02-26 Reimplementación de TTS con Configuración de Usuario y Abstracción de Servicio 🗣️⚙️

Se ha reimplementado la funcionalidad de Text-to-Speech (TTS) para permitir que el usuario configure su servicio TTS preferido desde el panel de Settings del frontend. Se ha introducido una arquitectura más modular y extensible.

- **Abstracción de Servicio TTS (`core/tts_manager.py`)**: [NEW]
  - Se creó una interfaz `TTSService` (clase abstracta` que define los métodos `synthesize_speech` y `synthesize_speech_streaming`.
  - Se implementó `GoogleTTSService` que hereda de `TTSService` y encapsula la lógica existente de Google Cloud TTS.
  - Se introdujo `TTSServiceFactory` para obtener dinámicamente la implementación de TTS según el proveedor seleccionado.
  - La clase `TTSCache` (para el almacenamiento en caché de audios) y las funciones de conveniencia `generate_speech` y `generate_speech_streaming` fueron movidas y adaptadas a este nuevo módulo.

- **Eliminación de Código Redundante (`utils/google_tts.py`)**: [DELETED]
  - El archivo `utils/google_tts.py` fue eliminado, ya que toda su funcionalidad fue migrada a `core/tts_manager.py`.

- **Actualización de la API de Chat (`api/chat.py`)**: [UPDATED]
  - Se eliminaron las importaciones antiguas de `utils.google_tts`.
  - Se importaron `generate_speech_streaming` y `get_tts_client` desde `core/tts_manager`.
  - El modelo `TextToSpeechRequest` fue modificado para incluir un campo `provider` (por defecto "google"), permitiendo al frontend especificar el servicio TTS.
  - La función `text_to_speech` fue actualizada para:
    - Aceptar `current_account_id` y `db: AsyncSession` como dependencias.
    - Si el `provider` en la solicitud es el valor por defecto ("google"), consulta la base de datos (`Account`) para obtener la configuración de TTS del usuario (`tts_provider`, `tts_voice`, `tts_speed`).
    - Utiliza la configuración del usuario (si existe) o los valores por defecto para generar el audio.
  - Las funciones `get_tts_cache_stats` y `clear_tts_cache` fueron adaptadas para usar el nuevo `get_tts_client` (que ahora utiliza la fábrica) y aceptan un parámetro `provider` para gestionar el caché por servicio.

- **Actualización de la API de Usuarios (`api/users.py`)**: [UPDATED]
  - Los modelos `UserSettingsResponse` y `UserSettingsUpdateRequest` fueron modificados para incluir los campos `tts_provider`, `tts_model`, `tts_voice`, y `tts_speed`.
  - Las funciones `get_user_settings` y `update_user_settings` fueron actualizadas para manejar estos nuevos campos, permitiendo que el frontend los muestre y actualice en la configuración del usuario.

- **Impacto**: Esta reimplementación proporciona una arquitectura de TTS más flexible y extensible, permitiendo a los usuarios personalizar su experiencia de voz y facilitando la integración de futuros proveedores de TTS.

---

## 11-02-26 Integración de Azure TTS en el Sistema 🗣️☁️

Se ha añadido soporte completo para Azure Text-to-Speech (TTS) en el sistema, permitiendo a los usuarios seleccionar Azure como proveedor de voz y configurar sus credenciales y región desde el panel de configuración.

- **Backend (`core/tts_manager.py`)**:
  - **Nueva Clase `AzureTTSService`**: Implementación de la interfaz `TTSService` para interactuar con la API de Azure Cognitive Services Speech.
  - **Actualización de `TTSServiceFactory`**: Modificado para instanciar `AzureTTSService` cuando el proveedor es "azure", gestionando la API Key y la región de forma segura a través de `SecretRepository` y `settings.azure_speech_region`.
  - **Importaciones Necesarias**: Añadidas las importaciones de `uuid`, `core.config`, `core.repositories.secret_repository`, `core.database` y `azure.cognitiveservices.speech` para el correcto funcionamiento.
  - **Funciones Asíncronas**: `get_tts_client` y `TTSServiceFactory.get_service` se hicieron asíncronas para permitir la obtención segura de claves API y la interacción con la base de datos.

- **Frontend (`src/app/(dashboard)/settings/page.tsx`)**:
  - **Actualización de `TTS_PROVIDERS`**: Añadido "azure" a la lista de proveedores de TTS disponibles.
  - **Voces de Azure**: Incluidas voces representativas de Azure en `TTS_VOICES_BY_PROVIDER`.
  - **Campo de Región en UI**: Añadido un campo de entrada para que el usuario pueda especificar la región de Azure TTS.
  - **Lógica de Guardado Mejorada**: Actualizada la inicialización de `localTTS` para incluir `tts_region` y modificada la función `handleSaveAllSettings` para enviar `tts_region` al backend solo si el proveedor seleccionado es Azure.
  - **Manejo de Claves API**: La función `handleSaveKey` fue actualizada para identificar y guardar correctamente `AZURE_TTS_KEY` como clave de entorno para Azure TTS.

- **Impacto**: Los usuarios ahora tienen una opción adicional y robusta para la síntesis de voz, con la flexibilidad de configurar sus preferencias de Azure TTS directamente desde la interfaz de usuario.

---

## 11-02-26 Implementación de Sistema de Embeddings Configurable por Usuario 🧠✨

Se ha implementado un sistema de embeddings flexible que permite a los usuarios seleccionar su proveedor y modelo de embeddings preferido, así como configurar las claves API y bases de URL directamente desde la interfaz de usuario. Esto mejora la personalización y la capacidad de integración con diversos servicios de embeddings.

- **Abstracción de Servicio de Embeddings (`core/embedding_manager.py`)**:
  - Se creó una interfaz `EmbeddingService` (clase abstracta) que define los métodos `aembed_query` y `aembed_documents`.
  - Se implementó `KognitoInternalEmbeddingService` que hereda de `EmbeddingService` y encapsula la lógica para el modelo `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, con soporte para `fp16`.
  - Se introdujo `EmbeddingServiceFactory` para obtener dinámicamente la implementación de embeddings según el proveedor seleccionado por el usuario.
  - La fábrica utiliza `SecretRepository` para obtener las claves API de forma segura si se configuran.

- **Actualización de Utilidades de Embeddings (`utils/embeddings.py`)**:
  - Se refactorizó `utils/embeddings.py` para usar la nueva arquitectura de `EmbeddingService` y `EmbeddingServiceFactory`.
  - La variable global `_embedding_model` fue reemplazada por `_embedding_service` de tipo `Optional[EmbeddingService]`.
  - La función `initialize_embeddings` ahora utiliza `EmbeddingServiceFactory.get_service()` para obtener la instancia del servicio de embeddings, pasando la configuración del usuario (proveedor, modelo, API key name, API base) y el `account_id`.
  - Las funciones `get_embedding_model` (renombrada a `get_embedding_service`) y `aembed_query` fueron adaptadas para interactuar con la interfaz `EmbeddingService`.
  - Se añadió una nueva función `aembed_documents` para generar embeddings para una lista de textos.

- **Actualización de la API de Usuarios (`api/users.py`)**:
  - Los modelos `UserSettingsResponse` y `UserSettingsUpdateRequest` fueron modificados para incluir los campos `embedding_provider`, `embedding_model`, `embedding_api_key_name`, y `embedding_api_base`.
  - Las funciones `get_user_settings` y `update_user_settings` fueron actualizadas para manejar estos nuevos campos, permitiendo que el frontend los muestre y actualice en la configuración del usuario.

- **Actualización del Frontend (`src/contexts/UserSettingsContext.tsx`, `src/app/(dashboard)/settings/page.tsx`)**:
  - La interfaz `UserSettings` en `src/contexts/UserSettingsContext.tsx` fue actualizada para incluir los campos de embeddings.
  - En `src/app/(dashboard)/settings/page.tsx`, se añadió la UI para la configuración de embeddings en `LLMSettingsForm`, incluyendo constantes para proveedores y modelos, estados locales y lógica de guardado y carga de secretos para las API Keys de Embeddings.

- **Impacto**: Esta implementación proporciona una solución robusta y extensible para la gestión de embeddings, permitiendo a los usuarios personalizar su experiencia y facilitando la integración de futuros proveedores de embeddings.

---

## 12-02-26 Mejora Integral en la Renderización y Recolección de Fuentes de Investigación Profunda 🔍✨

Se ha corregido y mejorado el flujo de recolección de fuentes en el backend y su visualización en el frontend para los módulos de Deep Research y Gap Development.

- **Frontend - Unificación y Diseño Premium**:
  - **Componentes Actualizados**: `DeepResearchAnalysis.tsx`, `GapDevelopmentDialog.tsx` y `DeepResearchDetailDialog.tsx`.
  - **Normalización**: Implementación de `collectSourcesFromMessage` para asegurar que todas las fuentes tengan un formato consistente (web, graph, github, etc.).
  - **Citas Interactivas**: Uso de `processMessageWithCitations` y `MarkdownRenderer` para que las referencias `[1]` en el texto del informe sean clicables y funcionales.
  - **Visualización Rica**: Integración del componente `SourcesTab` para mostrar las fuentes con búsqueda, filtros y tarjetas de diseño premium.
  - **Sección de Referencias**: Se añadió una sección de fuentes al final de los informes para mejorar la trazabilidad, similar a la interfaz de chat.

- **Backend - Recolección Robusta de Fuentes (`core/agents/deep_researcher.py`)**:
  - **Soporte de Herramientas Extendido**: Se amplió la extracción de fuentes para incluir herramientas como `brave_search_tool`, `comprehensive_web_analyzer`, `arxiv_search` y el grafo de conocimiento.
  - **Flexibilidad de Datos**: El agente ahora procesa tanto listas de diccionarios como listas simples de URLs (strings) y reconoce diversos nombres de campos de metadatos (`href`, `link`, `header`, `snippet`).
  - **Deduplicación**: Implementación de lógica de deduplicación basada en URL a nivel de investigador para evitar fuentes redundantes.
  - **IDs Secuenciales**: Asegurada la asignación de IDs numéricos secuenciales para garantizar la correspondencia exacta con las citas en el texto generado por los modelos de lenguaje.

---

## 12-02-26 Flexibilización de Dependencias de LangChain ⛓️

Se ha solucionado un conflicto de dependencias entre `langchain` y `langchain-community` eliminando las versiones fijas en el archivo `requirements.txt`.

- **Problema**: Las versiones fijas de `langchain` y `langchain-community` tenían requisitos incompatibles para el paquete `langchain-core`, lo que impedía la instalación de las dependencias.
- **Solución**: Se eliminaron los especificadores de versión (ej. `==0.2.10`) para `langchain` y `langchain-community`. Esto permite que `pip` resuelva automáticamente las versiones compatibles, mejorando la flexibilidad y robustez del proceso de instalación.

---

## 12-02-26 Resolución de Conflictos de Dependencias y Limpieza de CrewAI 🧹📦

Se ha realizado una limpieza profunda del proyecto para resolver conflictos críticos de dependencias entre `openai`, `litellm` y `crewai`, permitiendo la actualización a versiones más modernas de las librerías de IA.

- **Eliminación de Conflictos de Dependencias (`requirements.txt`)**:
  - Se eliminó **`crewai==1.9.3`**, la cual bloqueaba la versión de `openai` a la serie 1.x (1.83.0), impidiendo el uso de la nueva serie 2.x requerida por versiones actuales de `litellm`.
  - Se eliminó **`langchain-mcp-adapters==0.1.7`** tras verificar que no se utilizaba activamente en el proyecto y generaba conflictos adicionales con `langchain-core 1.x`.

- **Limpieza de Código y Agentes (`core/agents/`, `tools/`)**:
  - Eliminado el agente investigador basado en CrewAI: `core/agents/crewai_researcher.py`.
  - Eliminado el archivo de pruebas asociado: `core/agents/test_crewai_researcher.py`.
  - Eliminada la herramienta de investigación que dependía de CrewAI: `tools/crew_research_tool.py`.

- **Refactorización del Ensamblaje de Herramientas (`core/tools.py`)**:
  - Se eliminaron todas las referencias a `CrewResearchTool`, incluyendo su importación dinámica, su lógica especial de instanciación con `account_id` y su inclusión en la lista global de herramientas de la toolbox del agente.

- **Resultado**: El sistema ahora es compatible con la serie **`openai 2.x`** y versiones modernas de **`litellm` (1.81.x)**, simplificando el mantenimiento y mejorando la estabilidad del entorno Docker.

---

## 15-02-26 Corrección de Compatibilidad NumPy y LangChain 🔧

Se solucionaron errores críticos que impedían el inicio de los servicios `core` y `telegram_client`.

- **Punto 1: Compatibilidad NumPy**:
  - **Causa**: Conflicto entre módulos compilados con NumPy 1.x y la versión 2.x instalada por defecto en la imagen base.
  - **Solución (`requirements.txt`, Dockerfile)**: Se forzó la instalación de `numpy<2` para asegurar compatibilidad con las librerías existentes.

- **Punto 2: Importación Obsoleta en Telegram Client**:
  - **Causa**: `ImportError` al intentar cargar `LiteLLMEmbeddings` desde `langchain_community.embeddings`, que ha sido deprecado o reestructurado en versiones recientes. Además, la importación de `OllamaEmbeddings` causaba fallos en cascada en la inicialización del paquete.
  - **Solución (`core/embedding_manager.py`)**:
    - Se eliminaron las importaciones problemáticas de `langchain_community.embeddings`.
    - Se migró a una implementación directa usando `litellm` para mayor estabilidad y menor dependencia de la estructura interna de LangChain.

---

## 15-02-26 Corrección de Importación de Modelos 🔧

Se corrigió un `ModuleNotFoundError` crítico que impedía el inicio del servicio `kognito_core`. El error se debía a intentos de importar la clase `Account` y otros modelos desde `core.models`, un módulo que no existe, en lugar de su ubicación correcta en `core.database`.

- **utils/embeddings.py**:
  - **Causa**: Intentaba importar `Account` desde `core.models`.
  - **Solución**: Se actualizó la importación para obtener `Account` desde `core.database`.

- **scripts/migrate_workspace_owners.py**:
  - **Causa**: Intentaba importar `Workspace`, `WorkspacePermission` y `DATABASE_URL` desde ubicaciones incorrectas o con nombres erróneos.
  - **Solución**:
    - Se corrigió la importación de modelos a `core.database`.
    - Se corrigió la importación de `DATABASE_URL` (que es `database_url` en minúsculas en `core.database`).

- **Verificación**:
  - Se reinició el servicio `kognito_core` y se verificó en los logs que el error de importación ha desaparecido y el servicio inicia correctamente, aplicando los parches de estabilidad.

---

## 16-02-26 Corrección de AttributeError en API de Usuarios

Se solucionó un error crítico en el endpoint `get_user_settings` que impedía obtener la configuración del usuario debido a la falta del atributo `tts_region` en el modelo `Account`. Además, se actualizaron los esquemas de la API para incluir campos de configuración de TTS y Embeddings que faltaban.

- **core/database.py**:
  - Se añadió el campo `tts_region` al modelo `Account` para reflejar la estructura esperada por la API y corregir el `AttributeError`.

- **api/schemas.py**:
  - Se actualizaron los modelos Pydantic `UserSettingsResponse` y `UserSettingsUpdateRequest` para incluir los campos `tts_provider`, `tts_model`, `tts_voice`, `tts_speed`, `tts_region`, así como los campos de configuración de embeddings (`embedding_provider`, `embedding_model`, `embedding_api_key_name`, `embedding_api_base`). Esto asegura que la API pueda recibir y devolver correctamente estos ajustes.

---

## 16-02-26 Corrección de Extracción de Fuentes en Investigador Profundo 🕵️‍♂️

Se ha solucionado el problema por el cual las fuentes no llegaban a los informes finales de investigación profunda.

- **Causa**: Las herramientas de investigación (como `web_search` y `comprehensive_web_analysis`) devolvían diccionarios o objetos que, al ser convertidos a cadena en `ToolMessage`, utilizaban comillas simples. Esto provocaba que `compress_research` fallara al intentar parsear el contenido como JSON, resultando en la pérdida de las fuentes extraídas.
- **Solución (`core/agents/deep_researcher.py`)**:
  - Se actualizó la función `researcher_tools` para detectar y manejar correctamente las observaciones que son diccionarios (además de objetos `ToolOutputWithSources`).
  - Se implementó una serialización explícita a JSON (`json.dumps`) para asegurar que el contenido del `ToolMessage` sea siempre un JSON válido en herramientas nuevas.
  - **Mejora Crítica**: Se añadió un mecanismo de **Regex Fallback** en `compress_research` para extraer fuentes de herramientas que devuelven texto plano (como Tavily o búsquedas internas), evitando que se pierdan fuentes si el contenido no es un JSON válido.
  - **Corrección Final (`tools/deep_research_tool.py`)**: Se implementó el desempaquetado de fuentes compatible con el formato `{"type": "override", "value": [...]}` de LangGraph. Anteriormente, la herramienta intentaba iterar sobre el diccionario de control en lugar de la lista de fuentes, resultando en una lista vacía en el reporte final.
  - Esto garantiza que `sources` llegue correctamente poblado al agente principal y, por ende, al frontend.

---

## 16-02-26 Corrección de Compatibilidad de Modelos Nativos de OpenRouter 🏷️

Se ha solucionado el problema que impedía utilizar modelos nativos de OpenRouter como "aurora-alpha" o "pony-alpha" debido a la adición automática e incorrecta del prefijo "openrouter/".

- **core/llm_manager.py**:
  - Se implementó la función `normalize_openrouter_model_name` para manejar inteligentemente el prefijo `openrouter/`, evitando que se añada a modelos que no lo requieren.
  - Se creó una lista de excepciones para modelos nativos de OpenRouter (`aurora-alpha`, `pony-alpha`, etc.) que actúan como modelos "propios" de la plataforma.
  - Se refactorizó `get_llm_for_user` para utilizar esta nueva lógica de normalización centralizada.
- **Mantenimiento del Sistema**:
  - Se identificó y resolvió un conflicto de puertos causado por una instancia duplicada/zombie del contenedor `kognito_core`.
  - Se realizó una limpieza de contenedores y reinicio exitoso del servicio `core`.

---

## 16-02-26 Mejora de la Memoria Conceptual del Agente (Ideas de Gran Envergadura)

Se ha implementado una mejora en el sistema de memoria del agente para capturar ideas de mayor envergadura y conceptos estratégicos a partir de la conversación, elevando el nivel de razonamiento del sistema.

- **Actualización del Prompt de Extracción**: Se ha rediseñado el prompt en `knowledge_graph/knowledge_extraction_node.py` para incluir una visión macro que identifique "Ideas Maestras" y conclusiones estratégicas, además de entidades granulares.
- **Persistencia de Conceptual Insights**: Se ha actualizado la lógica de persistencia para capturar el campo `conceptual_insights` y registrar los nodos en Neo4j con la etiqueta `CONCEPTUAL_QUOTE`.
- **Interoperabilidad Semántica**: Al alinear las etiquetas de memoria con las del procesamiento de documentos, el agente puede conectar ahora pensamientos del chat con información técnica previa de forma fluida.
- **Metadatos Enriquecidos**: Se han incorporado atributos de importancia, categoría y texto completo para mejorar la precisión de las futuras búsquedas conceptuales.

---

## 16-02-26 Formato de Investigación Profunda en Página Compartida 📊

Se ha implementado el formato de Investigación Profunda para la página de análisis compartidos, mostrando las investigaciones profundas y brechas de conocimiento con el mismo diseño que en DeepResearchDetailDialog.

- **Cambio 1: Imports necesarios**
  - Se añadieron los imports de los componentes necesarios: MarkdownRenderer, SourceButton, SourcesTab, y las funciones de utilidad processMessageWithCitations y collectSourcesFromMessage
  - Ubicación: [`src/app/share/analysis/[token]/page.tsx`](src/app/share/analysis/[token]/page.tsx:1)

- **Cambio 2: Función helper de detección**
  - Se creó la función isDeepResearchOrGapDevelopment para detectar si el tipo de análisis es 'deep_research' o 'gap_development'
  - Se creó la función getDeepResearchData para extraer los datos correctos dependiendo del tipo de análisis

- **Cambio 3: Componente DeepResearchContent**
  - Se creó el nuevo componente DeepResearchContent que renderiza el contenido con el formato de pestañas (Resumen, Hallazgos, Fuentes, Acciones)
  - Utiliza MarkdownRenderer para renderizar el contenido con citas
  - Incluye el componente SourceButton para mostrar las fuentes citadas al final del resumen
  - Incluye la pestaña de Fuentes con SourcesTab
  - Incluye la pestaña de Acciones con las recomendaciones

- **Cambio 4: Integración en la página**
  - Se modificó el renderizado principal para usar el componente DeepResearchContent cuando el tipo de análisis sea 'deep_research' o 'gap_development'
  - Mantiene el formato original para los demás tipos de análisis

---

## 16-02-26 Corrección de Error de Consola "Each child in a list should have a unique 'key' prop" 🐛

Se ha solucionado el error de consola que indicaba la falta de una prop `key` única en los elementos de la lista de `Collapsible` en `ContextSelectorButton.tsx`.

- **Causa del Error**: La propiedad `key` del componente `Collapsible` se basaba en `group.topic`, que podía ser `null` o `undefined` para múltiples grupos, lo que resultaba en claves duplicadas o inválidas.
- **Solución (`src/components/ContextSelectorButton.tsx`)**:
  - Se modificó la función `fetchDocuments` para asignar un `id` único a cada grupo (`group.id`) durante su construcción.
  - Se actualizó el componente `Collapsible` para usar este `group.id` como su `key`, garantizando la unicidad.
  - Se añadieron fallbacks a 'Sin categoría' para `col.topic` y `doc.topic` para asegurar que siempre sean strings.
  - Se actualizaron las interfaces de `handleSelectGroup` y `isGroupSelected` para reflejar la nueva propiedad `id` en el objeto `group`.

---

## 16-02-26 Corrección de TypeError: `collectSourcesFromMessage` no es una función 🐛

Se ha solucionado un error `TypeError` en `ChatMessage.tsx` que indicaba que `collectSourcesFromMessage` no era una función, probablemente debido a un problema de caché o de importación en el bundler.

- **Causa del Error**: A pesar de que la función estaba correctamente exportada en `src/lib/chatUtils.ts`, el bundler (Webpack) no la estaba resolviendo correctamente al importarla como un export nombrado.
- **Solución (`src/components/ChatMessage.tsx`)**:
  - Se modificó la estrategia de importación para importar todo el módulo como un espacio de nombres: `import * as chatUtils from '@/lib/chatUtils';`.
  - Se actualizaron las llamadas a las funciones para usar el nuevo espacio de nombres: `chatUtils.collectSourcesFromMessage(...)` y `chatUtils.processMessageWithCitations(...)`.
  - Este cambio fuerza al bundler a cargar el módulo completo, evitando problemas con la resolución de exports nombrados individuales.

---

## 21-02-26 Implementación de Renderizado HTML Premium en el Chat 💎🎨

Se ha habilitado la capacidad del agente para entregar respuestas directamente en formato HTML, permitiendo diseños premium, tablas complejas, gradientes y diagramación avanzada para mejorar la legibilidad de respuestas extensas.

- **Frontend (`src/components/MarkdownRenderer.tsx`)**:
  - Se modificó la configuración de `marked` para permitir el renderizado de HTML crudo (`raw HTML`).
  - Se eliminó la lógica de escapado de etiquetas HTML que impedía la visualización de diseños personalizados.
  - Se aseguró la compatibilidad con el sistema de citas y componentes de Mermaid existentes.
- **Experiencia de Usuario**:
  - El agente ahora puede utilizar etiquetas HTML de Tailwind CSS y estilos en línea para crear interfaces ricas y visualmente atractivas dentro de la burbuja del chat.
  - Se mantiene la compatibilidad con el modo oscuro y los estilos base del sistema.

---

## 21-02-26 Refuerzo de Instrucciones de Diseño y Soporte de Reportes Deep 💎🚀

Se ha reforzado el sistema de prompts para garantizar que las instrucciones de diseño HTML no sean omitidas por configuraciones de Workspace o por el motor de investigación profunda.

- **Backend (`core/prompt_manager.py`)**:
  - Se modificó el ensamblaje final del prompt del sistema para inyectar dinámicamente las reglas de diseño HTML (`HTML_DESIGN_PROMPT`) al final de cada interacción.
  - Esto evita que prompts personalizados de Workspace o de perfil de usuario sobrescriban o ignoren las capacidades visuales de KAI.
- **Deep Researcher (`core/agents/deep_researcher_prompts.py`)**:
  - Se actualizaron las instrucciones de generación de informes para permitir y fomentar el uso de HTML en secciones clave como el "Resumen Ejecutivo" y "Recomendaciones Estratégicas".
  - Se suavizó la regla de "prohibición de esquemas" para validar el uso de layouts HTML (grids, cards) como método de estructuración visual premium.
- **Consistencia de IA**:
  - Se creó una constante dedicada para centralizar las reglas de estilo, asegurando coherencia visual en toda la plataforma.

---

## 23-02-26 Corrección TypeError en Tool Calls en agent.py 🐛

Se ha solucionado el error `TypeError: unhashable type: 'dict'` en `core/agent.py` que impedía el correcto parseo de las llamadas a herramientas.

- **Punto 1**: Se identificó que la variable `name` en `_parse_tool_calls_from_text` recibía un diccionario cuando el LLM devolvía el bloque JSON con el formato anidado de OpenAI (`{"function": {"name": "...", "arguments": "..."}}`).
- **Punto 2**: Se añadió lógica para detectar si `name` es un diccionario y extraer correctamente el nombre de la herramienta, así como parsear sus argumentos desde JSON si vienen como string.
- **Punto 3**: La validación `name in tool_map` ahora se realiza de forma segura verificando `isinstance(name, str)`, recuperando la capacidad del agente de invocar herramientas en estos escenarios.

---

## 23-02-26 Extensividad y Profundidad Analítica en Diseño HTML 📝✨

Se ha añadido una directriz explícita para evitar que el uso de diseños de interfaz premium (HTML/CSS) reduzca la profundidad, detalle y extensividad de las respuestas del agente Kai.

- **Punto 1**: Se modificó `HTML_DESIGN_PROMPT` en `core/prompts.py` para incluir una nueva regla crítica ("4. EXTENSIVIDAD Y PROFUNDIDAD ANALÍTICA").
- **Punto 2**: Se estableció de forma innegociable que el diseño HTML debe servir únicamente para maquetar y organizar la información, pero que los textos y análisis contenidos en él deben mantener el mismo nivel de detalle, exhaustividad y sabiduría que caracteriza al agente, como si estuviera respondiendo en texto plano extenso.

---

## 23-02-26 Corrección Critica de Deep Research y Salida Estructurada 🚀🧠

Se han solucionado múltiples fallos que impedían la generación del resumen de investigación (Research Brief) y causaban errores de validación.

- **Estabilización de Salida Estructurada (`core/utils/llm_utils.py`)**:
  - Se modificó `invoke_structured_output` para deshabilitar el streaming y el razonamiento durante llamadas críticas de JSON, mejorando la fiabilidad.
  - Se implementó un detector de retornos `None` para forzar el fallback manual con prompts reforzados y ejemplos dinámicos.
- **Normalización de Modelos y OpenRouter (`core/llm_manager.py`)**:
  - Se corrigió la lógica de `normalize_openrouter_model_name` para evitar la duplicación del prefijo `openrouter/` (ej. `openrouter/openrouter/model`).
  - Se añadió la exportación explícita de `custom_llm_provider: "openrouter"` para evitar errores internos de LiteLLM.
  - Se deshabilitó el razonamiento nativo (`include_reasoning: False`) por defecto en modelos de OpenRouter al solicitar JSON, evitando que el texto de razonamiento ensucie el esquema.
- **Correcciones de Errores Críticos (NameError, UUID y TypeError)**:
  - **`core/llm_manager.py`**: Añadida importación faltante de `os`.
  - **`knowledge_graph/knowledge_extraction_node.py`**: Añadida importación faltante de `uuid` para evitar fallos en la extracción de entidades.
  - **`core/agents/deep_researcher.py`**: Corregido un `TypeError: can only concatenate list (not "str") to list` al generar el reporte final, asegurando que la clave `recommendations` que retorna `final_report_generation` sea siempre una lista (`List[str]`), en lugar de un `str`.
- **Mejoras en Frontend (`src/components/DeepResearchVisualizer.tsx`)**:
  - Se corrigieron errores de claves duplicadas en React usando índices y prefijos únicos, evitando cuelgues visuales durante el progreso.
- **Limpieza de Logs**: Se redujo el ruido de LiteLLM moviendo logs detallados a nivel `WARNING` para producción.

---

## 25-02-26 Persistencia de Esquemas Visuales en Investigación Profunda 📊🔍

Se ha implementado la persistencia del campo `visual_schema` en los resultados de las investigaciones profundas para asegurar que el frontend pueda renderizar los diagramas y esquemas generados por el agente.

- **Backend (`tools/deep_research_tool.py`)**:
  - Se modificó la lógica de guardado en la base de datos para extraer el campo `visual_schema` del estado final del grafo de investigación profunda.
  - Este campo ahora se incluye dentro del objeto `report` en el `result_payload` de la tabla `AnalysisTask`.
  - Como el campo de la base de datos es `JSONB`, no se requirió una migración estructural (ALTER TABLE) de SQL, pero se aseguró que los nuevos datos sigan el esquema esperado por el frontend.
- **Utilidad**: Esto permite que diagramas (Mermaid u otros formatos incluidos en etiquetas `<visual_schema>`) se almacenen permanentemente junto con el informe y las recomendaciones, mejorando la visualización enricher en los diálogos de detalles.

---

## 25-02-26 Acceso Contextual Completo del Agente a los Informes de Análisis 🧠💬

Se ha implementado una mejora crítica en el sistema de prompts que permite al agente de chat acceder y procesar todo el contenido de un informe de análisis (Deep Research, Análisis Semántico, etc.) cuando se inicia una conversación desde la vista de resultados.

- **Backend (`core/prompt_manager.py`)**:
  - Se actualizó el método `build_system_prompt` para manejar dinámicamente el contexto de tipo `analysis`.
  - El sistema ahora extrae y formatea automáticamente el **Resumen Ejecutivo**, **Hallazgos Clave**, **Informe Detallado** y **Recomendaciones** desde el snapshot del análisis enviado por el frontend.
  - Esto se inyecta en el prompt del sistema bajo la sección "--- CONTEXTO DE ANÁLISIS ACTIVO ---", proporcionando a la IA una base de conocimiento inmediata sobre la investigación que el usuario está consultando.
- **Frontend (`src/components/ContextualChat.tsx`)**:
  - Se confirmó que el componente ya enviaba el `snapshot` completo del análisis al backend, lo que permitió habilitar esta mejora sin cambios adicionales en el cliente.
- **Beneficio**: Los usuarios ya no necesitan copiar y pegar partes del informe en el chat; el agente ahora "sabe" todo lo que contiene la investigación y puede responder preguntas específicas de forma instantánea y precisa.

---

---

## 25-02-26 Refinamiento Estético de la Interfaz de Investigación y Consistencia de API 🎨🚀

Se han aplicado mejoras estéticas de alto nivel a la visualización de resultados y se ha garantizado la entrega del esquema visual en todos los endpoints de la API.

- **Frontend (`DeepResearchAnalysis.tsx`)**:
  - **Lienzo Visual Premium**: Rediseño de la pestaña "Esquema Visual" utilizando un fondo de cuadrícula técnica (canvas), sombreados profundos y efectos de desenfoque de fondo.
  - **Tipografía y Tablas**: Inyección de estilos CSS específicos para el contenido dinámico, mejorando la legibilidad de tablas, imágenes y encabezados dentro del esquema.
  - **Navegación**: Actualización de las pestañas con iconos dinámicos, badges informativos y transiciones animadas para una experiencia de usuario fluida.
- **Backend (`api/deep_research.py`)**:
  - **Consistencia de Datos**: Se corrigieron los endpoints `/deep_research/` y `/deep_research/clarify` para incluir el campo `visual_schema` en la respuesta JSON. Esto asegura que el esquema esté disponible incluso cuando la investigación se inicia directamente desde el Centro de Análisis.
- **Instrucciones del Agente (`deep_researcher_prompts.py`)**:
  - **Garantía de Generación**: Se verificó y reforzó la obligatoriedad de la generación del esquema visual en las instrucciones maestras del agente, asegurando que cada investigación incluya una representación gráfica estructurada.
