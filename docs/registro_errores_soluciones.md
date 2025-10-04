# 🐞 Registro de Errores y Soluciones

Este documento sirve como una bitácora para registrar los errores encontrados durante el desarrollo y las soluciones implementadas. El objetivo es mantener un historial que pueda servir como referencia para futuros problemas similares.

---

## 12-09-2025 - `ValueError` por tipo de dato incorrecto en `Reranker`

-   **Error**: Se produjo un `ValueError: text input must be of type 'str' (single example), 'list[str]' (batch or single pretokenized example) or 'list[list[str]]' (batch of pretokenized examples)` en `core/memory_manager.py` al llamar a la función `reranker.rerank`.
-   **Causa**: La función `rerank` en `core/reranker.py` esperaba recibir una lista de cadenas de texto (`list[str]`). Sin embargo, desde `core/memory_manager.py`, se le estaba pasando una lista de objetos `Document` de LangChain, lo que causaba un error de tipo en el tokenizador de Hugging Face.
-   **Solución**: Se implementó una solución en dos partes para corregir el flujo de datos y mantener la coherencia:
    1.  **En `core/reranker.py`**: Se modificó la función `rerank` para que acepte una lista de objetos `Document`. La función ahora extrae el atributo `page_content` de cada documento para pasarlo al tokenizador. Después de calcular las puntuaciones, las añade a los metadatos de cada objeto `Document` original bajo la clave `rerank_score` y devuelve la lista de documentos reordenada.
    2.  **En `core/memory_manager.py`**: Se actualizó la función `get_relevant_memories`. Al construir las fuentes para la citación, ahora busca la clave `rerank_score` (en lugar de la antigua `similarity_score`) en los metadatos del documento para reflejar la puntuación obtenida en el proceso de reordenamiento.

---

## 11-09-2025 - `NameError` y `ValidationError` en `core/memory_manager.py`

-   **Error**: Se produjeron dos errores en `core/memory_manager.py`:
    1.  `NameError: name 'similarity_threshold' is not defined` en la función `get_relevant_memories`.
    2.  `ValidationError: 1 validation error for ToolOutputWithSources` al instanciar `ToolOutputWithSources` en un bloque `except`.
-   **Causa**-
    1.  La variable `similarity_threshold` se utilizaba en la instanciación de `KognitoPGVectorRetriever` sin haber sido definida como parámetro en la función `get_relevant_memories`.
    2.  El modelo `ToolOutputWithSources` requiere el campo `context_for_llm`, pero en el bloque `except` se estaba intentando instanciar con un campo `content` que no existe en el modelo.
-   **Solución**:
    1.  Se añadió el parámetro `similarity_threshold: float = 0.7` a la firma de la función `get_relevant_memories` y se utilizó en la instanciación del `KognitoPGVectorRetriever`.
    2.  Se corrigió la instanciación de `ToolOutputWithSources` en el bloque `except` para que utilice el campo `context_for_llm` en lugar de `content`.

---

## 11-09-2025 - `ImportError` por refactorización de `memory_manager`

-   **Error**: Se produjeron múltiples errores `ImportError: cannot import name 'search_vector_db_optimized' from 'core.memory_manager'` en varias herramientas (`internal_knowledge_search_tool`, `memory_search_optimized_tool`, `natural_query_interpreter_tool`, `vector_db_search_tool`) y en `api/analysis.py`.
-   **Causa**: La función `search_vector_db_optimized` y otras funciones relacionadas fueron eliminadas de `core/memory_manager.py` y reemplazadas por una función más potente y moderna llamada `get_relevant_memories`. Las herramientas que dependían de las funciones antiguas no habían sido actualizadas.
-   **Solución**: Se refactorizaron todas las herramientas y utilidades (`utils/vector_db_query.py`) que usaban las funciones obsoletas para que utilizaran la nueva función `get_relevant_memories`. Esto implicó:
    1.  Actualizar las sentencias `import` en los archivos de las herramientas.
    2.  Adaptar las llamadas a la nueva firma de la función `get_relevant_memories`.
    3.  Ajustar el procesamiento de los resultados para manejar el objeto `ToolOutputWithSources` que devuelve la nueva función.
    4.  Se unificaron las herramientas `MemorySearchOptimizedTool`, `VectorDBQueryTool` y `VectorDBSearchTool` en una sola herramienta llamada `KnowledgeSearchTool` para eliminar redundancia.
    5.  Se actualizó `core/tools.py` para importar y usar la nueva herramienta unificada.
    6.  Se eliminó la importación innecesaria en `api/analysis.py`.

---

## 07-08-2025 - `ValueError` en `Tool` por falta de `account_id`

-   **Error**: Se produjo un `ValueError: "Tool" object has no field "account_id"` al intentar instanciar las herramientas `web_search` y `ddg_search_tool`.
-   **Causa**: Las herramientas `web_search_tool.py` y `ddg_search_tool.py` no estaban estandarizadas como las demás. Les faltaba el campo `account_id` y el `__init__` para recibirlo, lo que provocaba un error de validación en Pydantic al crear la herramienta.
-   **Solución**: Se modificaron `tools/web_search_tool.py` y `tools/ddg_search_tool.py` para que las clases `WebSearchTool` y `DuckDuckGoSearchTool` incluyeran el campo `account_id` y un método `__init__` que lo aceptara. Además, se actualizaron las funciones `get_web_search_tool` y `create_ddg_search_tool` para que pasaran el `account_id` al crear la instancia de la herramienta, alineándolas con el resto de las herramientas del proyecto.

---

## 2025-08-03 - Solución de `TypeError` en la Instanciación de Herramientas

-   **Error**: Se produjo un `TypeError: Can't instantiate abstract class ... with abstract method _run` al intentar instanciar `DocumentRAGTool` y `VectorDBSearchTool`.
-   **Causa**: Las clases `DocumentRAGTool` y `VectorDBSearchTool` heredan de `langchain_core.tools.BaseTool`, que es una clase abstracta que requiere la implementación del método síncrono `_run()`. Aunque estas herramientas utilizan `_arun()` para la lógica asíncrona, la ausencia de una implementación de `_run()` hacía que Python las considerara abstractas y no permitiera su instanciación.
-   **Solución**: Se añadió una implementación básica del método `_run()` a `tools/document_rag_tool.py` y `tools/vector_db_search_tool.py`. Esta implementación simplemente envuelve la llamada a `_arun()` utilizando `asyncio.run()`, permitiendo que las herramientas sean instanciadas correctamente y manteniendo el enfoque asíncrono del proyecto.

## 2025-08-03 - Solución de `KeyError` en `PromptTemplate` de LangChain

-   **Error**: Se produjo un `KeyError: "Input to PromptTemplate is missing variables {'id_instructions'}"` durante la ejecución del agente en `api/chat.py`.
-   **Causa**: La plantilla `REACT_PROMPT_TEMPLATE` esperaba la variable `{id_instructions}`, pero esta no se estaba proporcionando en el momento de formatear el prompt, resultando en un error de clave faltante.
-   **Solución**: Se modificó la función `create_and_run_agent_streaming` en `api/chat.py` para construir explícitamente la cadena `id_instructions` y parcializar el `PromptTemplate` con esta variable antes de crear el agente. Esto asegura que todas las variables requeridas por la plantilla estén presentes durante la ejecución.

## 2025-08-03 - Corrección de `AttributeError` en `PromptManager`

-   **Error**: Se produjo un `AttributeError: 'Perfil' object has no attribute 'get'` en `core/prompt_manager.py`.
-   **Causa**: La refactorización del sistema de prompts resultó en que el `PromptManager` tratara al objeto `user_profile` (una instancia de la clase `Perfil` de SQLAlchemy) como un diccionario, intentando usar el método `.get()` en lugar de acceder a los atributos directamente.
-   **Solución**: Se modificó el método `build_system_prompt` en `core/prompt_manager.py` para acceder a los atributos del objeto `user_profile` directamente (p. ej., `user_profile.nombre` en lugar de `user_profile.get("nombre")`), resolviendo así el error.

## 2025-08-03 - Solución de Errores en la Interfaz de Chat

Se solucionaron tres errores críticos que afectaban la experiencia del usuario en la interfaz de chat (`src/components/CommonChat.tsx`):

-   **Error de Clave Duplicada en React**: Se resolvió un error de `Encountered two children with the same key` que ocurría al renderizar la lista de mensajes. La clave (`key`) de cada componente `ChatMessage` se modificó para ser garantizadamente única, utilizando una combinación de un prefijo estático, el índice del mensaje y su marca de tiempo (`msg-${messageIndex}-${msg.created_at || 'temp'}`). Esto previene problemas de renderizado y asegura la correcta identidad de los componentes en las actualizaciones del DOM.

-   **Error de Conexión WebSocket**: Se abordó un error silencioso (`WebSocket error: {}`) donde la conexión fallaba sin un mensaje claro. Se mejoró el registro de errores en el manejador `onerror` del WebSocket para incluir la URL de conexión y un mensaje descriptivo, facilitando el diagnóstico de problemas de configuración de red o de la variable de entorno `NEXT_PUBLIC_API_URL`.

-   **Error de Referencia `EmptyChat`**: Se corrigió un `ReferenceError: EmptyChat is not defined` que ocurría al intentar renderizar el estado de un chat vacío. El problema se solucionó importando explícitamente el componente `EmptyChat` dentro de `CommonChat.tsx`.

---

## 03-08-2025 - Error de Validación en `ScopedRagAnalysisTool`

-   **Error**: Se produjo un `ValidationError` en la herramienta `scoped_rag_analysis` indicando que los campos `query`, `content_types` y `analysis_goal` eran requeridos, pero no se estaban recibiendo correctamente. El `tool_input` mostraba un formato incorrecto (`analysis_objective` en lugar de `analysis_goal`).
-   **Causa**: La descripción de la herramienta `ScopedRagAnalysisTool` en `tools/scoped_rag_analysis_tool.py` no era lo suficientemente explícita para que el LLM generara los argumentos correctos al invocar la herramienta.
-   **Solución**: Se actualizó la `description` de `ScopedRagAnalysisTool` en `tools/scoped_rag_analysis_tool.py` para detallar claramente los parámetros esperados (`query`, `content_types`, `analysis_goal`, `topic`, `keywords`), asegurando que el LLM genere la entrada correcta para la herramienta.

---

## 03-08-2025 - Corrección de Errores en la Gestión de Repositorios de GitHub en la Interfaz de Usuario

- **Punto 1**: Se eliminó la importación innecesaria de `useParams` en `src/app/(dashboard)/rag/repositories/page.tsx`. Esta página no es una ruta dinámica, y la importación estaba causando el error "Cannot assign to read only property 'params'".
- **Punto 2**: Se corrigió el error "A <Select.Item /> must have a value prop that is not an empty string" en `src/app/(dashboard)/rag/github-repo-dialog.tsx`. El `SelectItem` para "Personal (sin workspace)" ahora tiene un valor de "personal" en lugar de una cadena vacía, y la lógica de `onValueChange` se ajustó para manejar este nuevo valor, estableciendo `selectedWorkspace` en `null` cuando se selecciona "personal".

---

## 03-08-2025 - `TypeError` en `KnowledgeAnalysisTool` por `NoneType` en `timedelta`

-   **Error**: Se produjo un `TypeError: unsupported type for timedelta days component: NoneType` en `tools/knowledge_analysis_tool.py` al intentar calcular una fecha.
-   **Causa**: El LLM, al interpretar la solicitud del usuario para un análisis de documentos recientes, no especificó un número de días, lo que resultó en que el parámetro `days_ago` se estableciera como `None`. La función `datetime.timedelta` no puede operar con un valor `None` para su componente `days`.
-   **Solución**: Se modificó `tools/knowledge_analysis_tool.py` para asegurar que la variable `days` siempre sea un entero. Si `params.get("days_ago")` devuelve `None`, se asigna un valor por defecto de `7` días antes de usarlo en `datetime.timedelta`.

---

## 03-08-2025 - Notificación de Finalización de Análisis en Chat

-   **Error**: La herramienta `knowledge_analysis_tool` no notificaba al usuario en el chat cuando el análisis en segundo plano había finalizado.
-   **Causa**: La función `run_batch_analysis_job` se ejecutaba de forma asíncrona y no tenía un mecanismo para enviar mensajes de vuelta al hilo de chat específico desde donde se originó la solicitud.
-   **Solución**: 
    -   Se añadió un parámetro `thread_id: Optional[str] = None` a la función `run_batch_analysis_job` en `utils/proactive_knowledge_linker.py`.
    -   Al finalizar el análisis en `run_batch_analysis_job`, si `thread_id` está presente, se utiliza `PostgresChatMessageHistory` para añadir un `AIMessage` al historial del chat, informando al usuario que el análisis ha concluido.
    -   Se modificó la clase `KnowledgeAnalysisTool` en `tools/knowledge_analysis_tool.py` para que acepte `thread_id` como un campo.
    -   Se actualizó el método `_arun` de `KnowledgeAnalysisTool` para pasar `self.thread_id` a todas las llamadas a `run_batch_analysis_job`.
    -   Se modificó `get_all_langchain_tools` en `core/tools.py` para que acepte `thread_id` y lo pase a la inicialización de `KnowledgeAnalysisTool`.
    -   Finalmente, se actualizó `create_and_run_agent_streaming` en `api/chat.py` para pasar el `thread_id` a `get_all_langchain_tools`.

---

## 04-08-2025 - `NameError: name 'Optional' is not defined` en `core/tools.py`

-   **Error**: Se produjo un `NameError: name 'Optional' is not defined` en `core/tools.py`.
-   **Causa**: El tipo `Optional` se estaba utilizando en la firma de la función `get_all_langchain_tools` sin haber sido importado desde el módulo `typing`.
-   **Solución**: Se añadió la importación `from typing import List, Optional` al inicio del archivo `core/tools.py`.

---

## 04-08-2025 - `ValidationError` en `ComprehensiveWebAnalysisInput`

-   **Error**: Se produjo un `ValidationError: 1 validation error for ComprehensiveWebAnalysisInput` indicando que el campo `account_id` era requerido pero no estaba presente en el `tool_input`.
-   **Causa**: El `account_id` estaba definido como un campo requerido en el esquema `ComprehensiveWebAnalysisInput` de Pydantic, pero el agente no lo estaba pasando como parte del `tool_input` al invocar la herramienta. La herramienta ya tenía acceso al `account_id` a través de su propia instancia (`self.account_id`).
-   **Solución**: Se eliminó el campo `account_id` del esquema `ComprehensiveWebAnalysisInput` y de la firma del método `_arun` en `tools/comprehensive_web_analysis_tool.py`. La herramienta ahora accede al `account_id` directamente desde `self.account_id`, eliminando la redundancia y resolviendo el error de validación.

---

## 04-08-2025 - Corrección de Errores en la Interfaz de Chat

-   **Error 1: `useState` no implementado**: Se produjo un `Runtime Error: Function not implemented` en `src/components/EmptyChat.tsx`. 
-   **Causa**: El componente no estaba importando el hook `useState` desde React, lo que provocaba que se utilizara una función local defectuosa con el mismo nombre.
-   **Solución**: Se añadió la importación `import { useState } from 'react';` al inicio del archivo `src/components/EmptyChat.tsx`.

-   **Error 2 y 3: Fallo en la conexión WebSocket**: La conexión WebSocket desde `src/components/CommonChat.tsx` fallaba repetidamente.
-   **Causa**: Este error es de naturaleza ambiental, no de código. La causa más probable es que el servidor backend no se esté ejecutando o que la variable de entorno `NEXT_PUBLIC_API_URL` no esté configurada correctamente en el frontend, impidiendo que el cliente se conecte al servidor WebSocket.
-   **Solución**: Se verificó que el código de conexión en `CommonChat.tsx` es correcto. La solución requiere que el usuario se asegure de que el servidor backend esté activo y que la variable de entorno `NEXT_PUBLIC_API_URL` apunte a la URL correcta del API.
---

## 04-08-2025 - Errores de Renderizado de Hooks en React

-   **Error**: Se produjeron dos errores relacionados en `src/app/(dashboard)/chat/[id]/page.tsx`:
    1.  `TypeError: Cannot assign to read only property 'params' of object '#<Object>'`
    2.  `Error: React has detected a change in the order of Hooks called by ChatPage.`
-   **Causa**: El componente intentaba modificar los `searchParams` directamente y, lo que es más importante, tenía una llamada condicional a `useEffect`. Las reglas de React exigen que los Hooks se llamen en el mismo orden en cada renderizado, por lo que no pueden estar dentro de condicionales.
-   **Solución**: Se refactorizó el componente para eliminar el renderizado condicional y la llamada a `useEffect` que lo infringía. Se utilizó un único `useEffect` para manejar de forma segura la lógica que depende de `searchParams` y se introdujo un estado local (`initialMessage`, `initialRagContext`) para gestionar los valores extraídos de la URL. Esto asegura que todos los Hooks se ejecuten en cada renderizado, eliminando el error y haciendo que el manejo de los parámetros de la URL sea más robusto.
---

## 04-08-25 - Corrección de `TypeError` en `search_vector_db_optimized`

-   **Error**: Se produjo un `TypeError: search_vector_db_optimized() got an unexpected keyword argument 'topic'`.
-   **Causa**: La función `search_vector_db_optimized` esperaba un argumento `topics` (en plural y como lista), pero se le estaba pasando `topic` (en singular) en las llamadas desde `search_memories`, `search_documents` y `search_vector_db`.
-   **Solución**: Se modificaron las llamadas a `search_vector_db_optimized` en `core/memory_manager.py` para pasar el argumento `topic` como `topics=[topic] if topic else None`, asegurando que la firma de la función se respete correctamente.

---

## 04-08-2025 - Errores de Ubicación de Importaciones y Bloques de Código en Componentes React

-   **Error**: Se produjeron errores de compilación (`'import', and 'export' cannot be used outside de module code`) en `src/app/(dashboard)/admin/page.tsx` y `src/app/(dashboard)/admin/scheduled-tools/page.tsx`.
-   **Causa**: Las sentencias `import { useEffect, useCallback } from 'react';` estaban ubicadas incorrectamente dentro del cuerpo de la función del componente, en lugar de al principio del archivo. Además, en ambos archivos, el bloque `try...catch` de las funciones `fetchUsers` y `fetchData` estaba fuera de la definición de `useCallback`, causando errores de sintaxis.
-   **Solución**: Se movieron las sentencias `import` al inicio de los archivos `src/app/(dashboard)/admin/page.tsx` y `src/app/(dashboard)/admin/scheduled-tools/page.tsx`. Se reubicaron los bloques `try...catch` dentro de las definiciones de `useCallback` para `fetchUsers` y `fetchData` respectivamente, asegurando la correcta estructura del código y la resolución de los errores de compilación.
---

## 07-08-2025 - `ValueError` en `WebSearchTool` por falta de campos de contexto

-   **Error**: Se produjo un `ValueError: "WebSearchTool" object has no field "thread_id"` al intentar pasar el contexto de la conversación a la herramienta.
-   **Causa**: La herramienta `WebSearchTool` no estaba estandarizada para aceptar los campos de contexto (`workspace_id`, `telegram_id`, `thread_id`) que el sistema pasa a todas las herramientas, aunque no los necesite para su lógica interna. Esto provocaba un error de validación en Pydantic.
-   **Solución**: Se modificó la clase `WebSearchTool` en `tools/web_search_tool.py` para que incluya los campos `workspace_id`, `telegram_id` y `thread_id`. También se eliminó el `__init__` personalizado, ya que no era necesario. Esto alinea la herramienta con la estructura estándar del proyecto y evita el error de validación, permitiendo que el sistema le pase el contexto sin problemas.

---

## 07-08-2025 - `ValueError` en `DuckDuckGoSearchTool` por falta de campos de contexto

-   **Error**: Se produjo un `ValueError: "DuckDuckGoSearchTool" object has no field "thread_id"` al intentar pasar el contexto de la conversación a la herramienta.
-   **Causa**: La herramienta `DuckDuckGoSearchTool` no estaba estandarizada para aceptar los campos de contexto (`workspace_id`, `telegram_id`, `thread_id`) que el sistema pasa a todas las herramientas, aunque no los necesite para su lógica interna. Esto provocaba un error de validación en Pydantic.
-   **Solución**: Se modificó la clase `DuckDuckGoSearchTool` en `tools/ddg_search_tool.py` para que incluya los campos `workspace_id`, `telegram_id` y `thread_id`. También se eliminó el `__init__` personalizado, ya que no era necesario. Esto alinea la herramienta con la estructura estándar del proyecto y evita el error de validación, permitiendo que el sistema le pase el contexto sin problemas.

---

## 07-08-2025 - `ValidationError` en `WebSearchTool` y `DuckDuckGoSearchTool` por `workspace_id` requerido

-   **Error**: Se produjo un `ValidationError` en `WebSearchTool` y `DuckDuckGoSearchTool` indicando que el campo `workspace_id` era requerido pero no se estaba proporcionando.
-   **Causa**: Durante la estandarización de las herramientas, el campo `workspace_id` se definió erróneamente como `str` en lugar de `Optional[str] = None`, haciéndolo obligatorio. Esto causaba un error de validación cuando las herramientas se instanciaban solo con el `account_id`.
-   **Solución**: Se modificaron las clases `WebSearchTool` en `tools/web_search_tool.py` y `DuckDuckGoSearchTool` en `tools/ddg_search_tool.py` para que la definición del campo `workspace_id` sea `Optional[str] = None`. Esto lo convierte en un campo opcional y resuelve el error de validación, permitiendo que las herramientas se creen correctamente con o sin un `workspace_id`.

---

## 07-08-2025 - `TypeError` por objeto no serializable en herramientas de búsqueda

-   **Error**: Se produjo un `TypeError: Object of type ToolOutputWithSources is not JSON serializable` al procesar el resultado de las herramientas `WebSearchTool` y `DuckDuckGoSearchTool`.
-   **Causa**: Las herramientas devolvían una instancia del objeto `ToolOutputWithSources` de Pydantic. Este objeto no es directamente compatible con la serialización JSON que requiere el sistema para procesar los resultados de las herramientas.
-   **Solución**: Se modificaron los métodos `_arun` en `tools/web_search_tool.py` y `tools/ddg_search_tool.py`. En lugar de devolver el objeto `ToolOutputWithSources` directamente, ahora se utiliza el método `.model_dump()` de Pydantic para convertir el objeto en un diccionario antes de devolverlo. Los diccionarios son compatibles con la serialización JSON, lo que resuelve el `TypeError` y permite que el sistema procese los resultados correctamente.

---
## 11-08-2025 - `ProgrammingError` por `FieldInfo` en `ExtractDocumentTitlesTool`

-   **Error**: Se produjo un `psycopg.ProgrammingError: cannot adapt type 'FieldInfo' using placeholder '%s'` al ejecutar la herramienta `ExtractDocumentTitlesTool`.
-   **Causa**: La herramienta estaba intentando pasar objetos `FieldInfo` (metadatos de Pydantic) directamente como parámetros a una consulta SQL, en lugar de los valores de cadena esperados para `topic` y `collection_id`. Esto ocurría porque los atributos de la instancia de la herramienta (`self.topic`, `self.collection_id`) conservaban sus valores `FieldInfo` predeterminados si no se les asignaba explícitamente un valor de cadena.
-   **Solución**: Se modificó el método `_arun` en `tools/extract_document_titles_tool.py`. Ahora, antes de usar `self.topic` y `self.collection_id` en los parámetros de la consulta SQL, se verifica explícitamente si son instancias de `str`. Si no lo son (es decir, si son objetos `FieldInfo`), se tratan como `None` para la consulta. Además, se ajustó el log inicial para reflejar el valor correcto del tema. Esto asegura que solo valores de cadena o `None` sean pasados a la base de datos, resolviendo el error de adaptación de tipo.

---

## 12-08-2025 - `KeyError: 'content'` al añadir repositorios de GitHub

- **Error**: Se produjo un `KeyError: 'content'` en `tools/github_repo_tool.py` al intentar añadir un repositorio de GitHub que contenía enlaces simbólicos (symlinks).
- **Causa**: El código intentaba acceder a la clave `'content'` en la respuesta de la API de GitHub para cada archivo. Sin embargo, la respuesta para un enlace simbólico no contiene esta clave, lo que provocaba el error.
- **Solución**: Se modificó el método `_add_as_knowledge_collection` en `tools/github_repo_tool.py` para comprobar el tipo de archivo antes de procesarlo. Si el tipo es `'symlink'`, el archivo se omite y se registra un mensaje, evitando así el `KeyError`.

---

## 11-09-2025 - `UndefinedColumn` en `task_contact_profiles_association`

-   **Error**: Se produjo un `(psycopg.errors.UndefinedColumn) column task_contact_profiles_association_1.contact_profile_id does not exist` al intentar acceder a la tabla `task_contact_profiles_association`.
-   **Causa**: La columna `contact_profile_id` no existía en la tabla `task_contact_profiles_association` en la base de datos, a pesar de haber sido definida en el modelo de SQLAlchemy. Esto ocurre cuando los cambios en el esquema de la base de datos no se aplican correctamente (por ejemplo, falta una migración).
-   **Solución**: Se añadió manualmente la columna `contact_profile_id` a la tabla `task_contact_profiles_association` en la base de datos PostgreSQL mediante la siguiente sentencia SQL:
    ```sql
    ALTER TABLE task_contact_profiles_association
    ADD COLUMN contact_profile_id UUID NOT NULL;
    ```
    Esta acción asegura que el esquema de la base de datos coincida con la definición del modelo de SQLAlchemy, resolviendo el error de columna indefinida.

---
## 10-09-2025 - `AttributeError: 'str' object has no attribute 'get'` en `WebSearchTool`

-   **Error**: Se produjo un `AttributeError: 'str' object has no attribute 'get'` en `tools/web_search_tool.py` al procesar los resultados de una búsqueda.
-   **Causa**: La herramienta `BraveSearch` de LangChain, después de una actualización reciente, devuelve los resultados de la búsqueda como una cadena de texto en formato JSON en lugar de una lista de diccionarios de Python. El código intentaba iterar directamente sobre esta cadena, tratando cada carácter como un resultado individual y provocando el error al intentar acceder a sus "atributos".
-   **Solución**: Se modificó el método `_arun` en `tools/web_search_tool.py`. Ahora, la cadena JSON devuelta por `BraveSearch` se decodifica explícitamente en un objeto Python (una lista de diccionarios) usando `json.loads()`. Esto asegura que el método `_format_results` reciba los datos en el formato esperado, resolviendo el `AttributeError`. Se añadió también un manejo de errores para el caso de que la respuesta no sea un JSON válido.

---

## 03-10-2025 - `ReferenceError: CardFooter is not defined` en componente React

-   **Error**: Se produjo un `ReferenceError: CardFooter is not defined` en `src/app/(dashboard)/profiles/[id]/page.tsx`.
-   **Causa**: El componente `CardFooter` se estaba utilizando en el código JSX sin haber sido importado junto con los otros componentes de `Card` desde la librería de componentes UI (`@/components/ui/card`).
-   **Solución**: Se actualizó la sentencia `import` en la parte superior del archivo para incluir `CardFooter`, resolviendo así el error de referencia. La línea de importación corregida es: `import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';`.

---