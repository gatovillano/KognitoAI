# 🧱 Estructura del Directorio `/core` ⚙️

El directorio `/core` contiene la lógica principal de la aplicación KognitoAI. Define la
estructura de la base de datos, gestiona la memoria del usuario, implementa el agente de
IA y proporciona la configuración de la aplicación.

## 📋 Índice
1.  [Descripción General](#descripción-general)
2.  [Archivos Clave](#archivos-clave)
3.  [Interacciones entre Archivos](#interacciones-entre-archivos)

## 1. Descripción General ℹ️

El directorio `/core` es el corazón de la aplicación KognitoAI. Contiene los módulos
esenciales para el funcionamiento del sistema, incluyendo la gestión de la base de datos,
la memoria del usuario, el agente de IA y la configuración de la aplicación. Los módulos
en este directorio están diseñados para ser reutilizables y modulares, lo que facilita
el mantenimiento y la extensión de la aplicación.

## 2. Archivos Clave 🔑

### `notes_manager.py` 📝

Gestiona la creación, lectura, actualización y eliminación de notas del usuario.

### `reminders_manager.py` ⏰

Gestiona la creación, lectura, actualización y eliminación de recordatorios del usuario.

### `websocket_manager.py` 📡

Gestiona las conexiones WebSocket para la comunicación en tiempo real entre el servidor y
los clientes. Permite enviar actualizaciones y notificaciones a los usuarios en tiempo real.

### `memory_manager.py` 🧠

Gestiona la memoria a largo plazo y el perfil del usuario. Incluye la interacción con la
base de datos vectorial para almacenar y recuperar información relevante para el usuario.
Este módulo también implementa el Context Manager de Workspaces para aislar la memoria
por workspace.

### `enhanced_memory_manager.py` ✨

(Descripción pendiente) Parece ser una versión mejorada del `memory_manager.py` o un
módulo relacionado con la gestión de memoria.

### `config.py` ⚙️

Define la configuración de la aplicación, incluyendo las variables de entorno y la
configuración de la base de datos. Utiliza la biblioteca `pydantic` para validar y
gestionar la configuración.

### `agent.py` 🤖

Define la lógica del agente de IA, incluyendo la creación de hilos de chat y la
interacción con el modelo de lenguaje. Utiliza las herramientas definidas en `tools.py`
para realizar acciones específicas.

### `citation_models.py` 📚

Define modelos relacionados con citas o referencias bibliográficas. Se utiliza para
estructurar y gestionar la información de las citas.

### `database.py` 🗄️

Define la estructura de la base de datos utilizando SQLAlchemy, incluyendo los modelos
ORM y la configuración de la conexión. Define las tablas principales de la aplicación,
como `Account`, `Workspace`, `Nota`, `Recordatorio`, etc.

### `agenda_manager.py` 🗓️

Gestiona los eventos de la agenda del usuario. Permite crear, leer, actualizar y
eliminar eventos de la agenda.

### `llm_manager.py` 🗣️

Gestiona la interacción con los modelos de lenguaje (LLMs), incluyendo la selección del
modelo y la configuración de los parámetros. Proporciona una interfaz统一 para interactuar
con diferentes LLMs.

### `context_cache.py` 📦

Gestiona el almacenamiento en caché del contexto del usuario para mejorar el rendimiento.
Almacena información relevante del usuario en caché para evitar tener que consultarla
constantemente a la base de datos.

### `tools.py` 🧰

Define las herramientas que puede utilizar el agente de IA. Cada herramienta representa
una acción específica que el agente puede realizar, como buscar información en la web,
crear una nota, etc.

## 3. Interacciones entre Archivos 🔗

Los archivos en el directorio `/core` interactúan entre sí para proporcionar la
funcionalidad principal de la aplicación. Algunas de las interacciones más importantes
son:

-   **`agent.py` utiliza `tools.py` y `llm_manager.py`:** El agente de IA (definido en
    `agent.py`) utiliza las herramientas definidas en `tools.py` para realizar acciones
específicas, como buscar información en la web o crear una nota. También utiliza
    `llm_manager.py` para interactuar con el modelo de lenguaje y generar respuestas
    inteligentes.
-   **`memory_manager.py` interactúa con `database.py`:** El gestor de memoria
    (definido en `memory_manager.py`) utiliza los modelos ORM definidos en `database.py`
    para acceder y modificar los datos en la base de datos. También utiliza la
    función `search_vector_db_optimized` para realizar búsquedas vectoriales en la base
    de datos.
-   **`notes_manager.py` y `reminders_manager.py` interactúan con `database.py`:** Estos
módulos utilizan los modelos ORM definidos en `database.py` para gestionar las notas
y los recordatorios del usuario.
-   **`websocket_manager.py` utiliza `config.py`:** El gestor de WebSockets utiliza la
    configuración definida en `config.py` para establecer la conexión con el servidor
    WebSocket.
-   **`agenda_manager.py` interactúa con `database.py`:** El gestor de agenda utiliza los modelos ORM definidos en `database.py` para gestionar los eventos de la agenda del usuario.
-   **`llm_manager.py` utiliza `config.py`:** El gestor de LLMs utiliza la configuración definida en `config.py` para seleccionar y configurar el modelo de lenguaje.
-   **`context_cache.py` interactúa con `database.py`:** El caché de contexto utiliza la base de datos para obtener la información inicial del usuario y luego la almacena en caché para mejorar el rendimiento.



(Descripción pendiente) Explicar cómo interactúan los archivos clave entre sí para
proporcionar la funcionalidad principal de la aplicación. Por ejemplo, cómo `agent.py`
utiliza `tools.py` y `llm_manager.py`, cómo `memory_manager.py` interactúa con
`database.py`, etc.
