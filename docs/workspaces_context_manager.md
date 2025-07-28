# 🏢 Guía de Uso del Context Manager de Workspaces 🚀

## 📋 Índice
1.  [¿Qué es el Context Manager de Workspaces?](#qué-es-el-context-manager-de-workspaces)
2.  [Configuración](#configuración)
3.  [Uso Básico](#uso-básico)
4.  [Componentes Clave](#componentes-clave)
5.  [Flujo de Trabajo](#flujo-de-trabajo)
6.  [Solución de Problemas](#solución-de-problemas)
7.  [Consejos y Mejores Prácticas](#consejos-y-mejores-prácticas)

## 🤔 ¿Qué es el Context Manager de Workspaces? 💡

El Context Manager de Workspaces es un mecanismo en KognitoAI que permite aislar la memoria
de los usuarios por workspace. Esto significa que cada usuario, al interactuar con el sistema
dentro de un workspace específico, solo tendrá acceso a la información y los documentos
relevantes para ese workspace.

En KognitoAI, el Context Manager de Workspaces:

-   🔒 **Aísla la información** por workspace.
-   🛡️ **Garantiza la seguridad** y privacidad de los datos.
-   🚀 **Optimiza las búsquedas** al limitar el alcance a un contexto específico.
-   🧠 **Mejora la experiencia del usuario** al presentar solo información relevante.

## ⚙️ Configuración 🛠️

No se requiere una configuración especial para utilizar el Context Manager de Workspaces.
Simplemente, asegúrate de que tu aplicación esté utilizando las funciones y clases
correctas del `core/memory_manager.py` para crear y utilizar el contexto.

### 1. Dependencias

Asegúrate de tener las siguientes dependencias instaladas:

-   `core/memory_manager.py`
-   `api/workspaces.py`
-   Base de datos PostgreSQL con extensión pgvector

## 🚀 Uso Básico 🧑‍💻

El Context Manager de Workspaces se utiliza principalmente a través de las APIs y funciones
internas del sistema. Aquí te mostramos algunos ejemplos de cómo se utiliza:

### 1. Creación del Contexto

```python
from core.memory_manager import create_memory_context

account_id = "usuario123"
workspace_id = "workspace456"

context = await create_memory_context(account_id=account_id, workspace_id=workspace_id)
```

### 2. Búsqueda en el Contexto

```python
from core.memory_manager import create_memory_context

account_id = "usuario123"
workspace_id = "workspace456"
query = "¿Cuáles son las estrategias de IA?"

context = await create_memory_context(account_id=account_id, workspace_id=workspace_id)
results = await context.search_documents(query=query)

print(results)
```

## 🗂️ Almacenamiento y Filtrado de Datos 🛠️

El Context Manager de Workspaces utiliza las siguientes tablas para almacenar y filtrar los datos:

### 1. Tabla `workspaces`

Esta tabla almacena la información de los workspaces. Sus columnas principales son:

-   `id`: `UUID`, clave primaria del workspace.
-   `account_id`: `UUID`, clave foránea que relaciona el workspace con la tabla `accounts`.
-   `name`: `String`, nombre del workspace.
-   `system_prompt`: `Text`, prompt de sistema específico para este workspace.
-   `created_at`: `DateTime`, fecha de creación del workspace.

### 2. Tabla `UserDocumentTopic`

Esta tabla almacena las colecciones (temas) de documentos definidos por el usuario. Sus columnas principales son:

-   `id`: `UUID`, clave primaria de la colección.
-   `account_id`: `UUID`, clave foránea que relaciona la colección con la tabla `accounts`.
-   `workspace_id`: `UUID`, clave foránea que relaciona la colección con la tabla `workspaces` (opcional).
-   `team_id`: `UUID`, clave foránea que relaciona la colección con la tabla `teams` (opcional).
-   `name`: `String`, nombre de la colección.
-   `description`: `Text`, descripción de la colección.
-   `is_global`: `Boolean`, indica si la colección es global (accesible fuera de un workspace/equipo específico).

### 3. Tabla `langchain_pg_embedding`

Esta tabla almacena los embeddings de los documentos y las memorias. Sus columnas principales son:

-   `document`: `Text`, el contenido del documento o memoria.
-   `cmetadata`: `JSONB`, metadatos del documento o memoria (incluye `file_name`, `topic`, `type`, etc.).
-   `embedding`: `Vector`, el embedding vectorial del contenido.
-   `account_id`: `UUID`, clave foránea que relaciona el embedding con la tabla `accounts`.
-   `workspace_id`: `UUID`, clave foránea que relaciona el embedding con la tabla `workspaces` (opcional).
-   `team_id`: `UUID`, clave foránea que relaciona el embedding con la tabla `teams` (opcional).
-   `topic`: `String`, el tema/colección al que pertenece el documento.

### Filtrado por `workspace_id`

El filtrado por `workspace_id` se realiza en las siguientes funciones:

-   `list_user_collections` (en `core/memory_manager.py`):
    -   Busca en la tabla `UserDocumentTopic` y filtra por `account_id` y `workspace_id` (si se proporciona).
    -   Busca en la tabla `langchain_pg_embedding` y filtra por `account_id`, `workspace_id` (si se proporciona) y `cmetadata->>'type' = 'document_chunk'`.

-   `list_user_documents` (en `core/memory_manager.py`):
    -   Busca en la tabla `langchain_pg_embedding` y filtra por `account_id`, `workspace_id` (si se proporciona) y `cmetadata->>'type' = 'document_chunk'`.  Utiliza `DISTINCT ON (cmetadata->>'document_id')` para obtener solo un documento por cada `document_id`.

Este filtrado garantiza que solo se obtengan los datos relevantes para el workspace especificado.

 🧩

### 1. Clase `MemoryContext`

La clase `MemoryContext` (definida en `core/memory_manager.py`) es el componente
principal del Context Manager de Workspaces. Esta clase encapsula la información
necesaria para aislar la memoria del usuario por workspace.

**Atributos:**

-   `account_id`: El ID de la cuenta del usuario.
-   `workspace_id`: El ID del workspace actual (opcional).
-   `team_id`: El ID del team actual (opcional).
-   `user_teams`: Una lista de los IDs de los teams a los que pertenece el usuario.

**Métodos:**

-   `search_memories()`: Busca en las memorias del usuario dentro del contexto.
-   `search_documents()`: Busca en los documentos del usuario dentro del contexto.
-   `search_all()`: Busca en todas las fuentes de memoria dentro del contexto.

### 2. Función `create_memory_context()`

La función `create_memory_context()` (definida en `core/memory_manager.py`) se utiliza
para crear una instancia de la clase `MemoryContext`. Esta función recibe el `account_id`,
`workspace_id` y `team_id` como parámetros y devuelve un objeto `MemoryContext`
configurado con esta información.

### 3. Función `search_vector_db_optimized()`

La función `search_vector_db_optimized()` (definida en `core/memory_manager.py`) es
responsable de realizar la búsqueda vectorial optimizada en la base de datos. Esta
función utiliza la información de contexto proporcionada por el `MemoryContext` para
filtrar los resultados y garantizar que solo se devuelvan los datos relevantes para
el workspace actual.

## 🔄 Flujo de Trabajo ➡️

El flujo de trabajo general para utilizar el Context Manager de Workspaces es el siguiente:

1.  La API recibe una solicitud con el `account_id` y el `workspace_id` (si aplica).
2.  Se llama a la función `create_memory_context()` para crear una instancia de
    `MemoryContext` con la información proporcionada.
3.  Se utiliza el objeto `MemoryContext` para realizar búsquedas y otras operaciones
    en la base de datos.
4.  La función `search_vector_db_optimized()` utiliza la información de contexto para
    filtrar los resultados y garantizar el aislamiento de la memoria.
5.  Los resultados se devuelven a la API y, finalmente, al usuario.

## 🔧 Solución de Problemas 🐞

### Problema: No se están filtrando los resultados por Workspace

**Posible Solución:**

-   Verifica que estés utilizando la función `create_memory_context()` para crear el
    contexto.
-   Asegúrate de que estás pasando el `workspace_id` correcto a la función
    `create_memory_context()`.
-   Verifica que la función `search_vector_db_optimized()` esté utilizando la
    información de contexto para filtrar los resultados.

### Problema: Error al crear el `MemoryContext`

**Posible Solución:**

-   Verifica que las dependencias necesarias estén instaladas.
-   Asegúrate de que la base de datos esté configurada correctamente.
-   Revisa los logs para obtener más información sobre el error.

## 💡 Consejos y Mejores Prácticas ✅

### 1. Utiliza nombres descriptivos para los Workspaces

Esto facilitará la identificación y gestión de los workspaces.

### 2. Organiza tus documentos por Workspace

Esto garantizará que la información esté correctamente aislada y que los usuarios solo
tengan acceso a los datos relevantes para su contexto.

### 3. Utiliza el Context Manager de Workspaces en todas las operaciones

Para garantizar el aislamiento de la memoria, utiliza el Context Manager de Workspaces
en todas las operaciones que accedan a la base de datos.
