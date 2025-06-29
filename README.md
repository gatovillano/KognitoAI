# Kognito AI System

Kognito AI es un sistema modular de asistente inteligente diseñado para integrar diversas funcionalidades de IA y gestión de información personal a través de múltiples plataformas, comenzando con Telegram y una aplicación web. Su arquitectura desacoplada asegura que la lógica de negocio principal sea independiente de la interfaz de usuario, permitiendo una experiencia unificada y extensible.

El sistema centraliza la gestión de datos del usuario (notas, agenda, documentos, memoria) y expone estas funcionalidades a través de una API robusta, utilizada tanto por el bot de Telegram como por la webapp.

DEMO http://kognito.gatoslibres.art

## Características principales

*   **Identidad Universal:** Cada usuario tiene un `account_id` único (UUID), independiente de la plataforma (Telegram, web, etc.), permitiendo una gestión de datos coherente.
*   **Bot de Telegram:** Interfaz conversacional completa con soporte para comandos, gestión de documentos (subida, consulta, eliminación), notas, agenda y recordatorios.
*   **API Centralizada (FastAPI):** Backend que expone endpoints para chat, autenticación JWT, gestión de documentos, notas, agenda y más. Sirve como el cerebro del sistema.
*   **WebApp / Panel de Usuario:** Interfaz web (`public_chat_ui/`) para interactuar con el asistente, gestionar documentos, ver notas, etc., autenticada vía JWT o login con Telegram.
*   **Memoria a Largo Plazo y RAG:** Utiliza PostgreSQL con la extensión `pgvector` para almacenar memorias vectoriales y perfiles estructurados, permitiendo al agente de IA recordar conversaciones y documentos relevantes.
*   **Herramientas LangChain:** Un conjunto de herramientas personalizadas para el agente de IA, incluyendo CRUD de notas, gestión de agenda, scraping web, generación de imágenes, gestión de documentos (subir, listar, ver contenido, eliminar), y más. Estas herramientas operan con el `account_id` universal.
*   **Autenticación Universal:** Soporte para login vía Telegram (para el bot) y autenticación JWT para la webapp y la API.
*   **Arquitectura Modular:** Separación clara de responsabilidades en directorios clave: `core/` (lógica de negocio), `telegram_client/` (lógica específica de Telegram), `tools/` (herramientas LangChain), `utils/` (utilidades generales), y `public_chat_ui/` (frontend web).

## Estructura del Proyecto

```
KognitoAI/
├── core/                # Lógica de negocio desacoplada (notas, agenda, memoria, config, DB)
├── telegram_client/     # Bot de Telegram, handlers y lógica específica
├── tools/               # Herramientas LangChain para el agente de IA (notas, agenda, scraping, documentos, etc.)
├── utils/               # Utilidades generales (embeddings, helpers, paginador, generación de imágenes)
├── public_chat_ui/      # Webapp de panel de control (HTML, CSS, JS)
├── run_api.py           # Punto de entrada para el servidor FastAPI (API central y webapp)
├── run_telegram_bot.py  # Punto de entrada para el bot de Telegram
├── requirements.txt     # Dependencias principales (backend y bot)
├── requirements.telegram.txt # Dependencias mínimas para el cliente de Telegram ligero
├── Dockerfile*          # Archivos Docker para backend/webapp y cliente Telegram
├── .env.example         # Ejemplo de archivo de configuración de entorno
└── ...                  # Otros archivos de configuración y scripts
```

## Instalación y despliegue rápido

Sigue estos pasos para poner en marcha el sistema Kognito AI.

1.  **Clona el repositorio**

```bash
git clone <repo-url>
cd KognitoAI
```

2.  **Configura el entorno**

Copia el archivo `.env.example` a `.env` y completa las variables necesarias. Esto incluye tokens de API (Telegram, Google), URL de la base de datos, claves secretas, etc.

```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales y configuraciones
```

3.  **Instala las dependencias**

Puedes instalar las dependencias completas para el backend y el bot, o solo las mínimas para el cliente Telegram si lo ejecutas por separado.

*   Para el backend (API y webapp) y el bot completo:

```bash
pip install -r requirements.txt
```

*   Para el cliente Telegram ligero (si el backend se ejecuta aparte):

```bash
pip install -r requirements.telegram.txt
```

4.  **Inicializa la base de datos**

Asegúrate de tener una instancia de PostgreSQL accesible con la extensión `pgvector` habilitada. El sistema creará las tablas automáticamente al iniciar el backend por primera vez.

5.  **Ejecuta el backend (API y webapp)**

Inicia el servidor FastAPI que maneja la API central y sirve la webapp.

```bash
python run_api.py
```

6.  **Ejecuta el bot de Telegram**

Inicia el script del bot de Telegram.

```bash
python run_telegram_bot.py
```

7.  **(Opcional) Despliegue con Docker**

Puedes usar Docker Compose para construir y ejecutar los servicios (backend/webapp y bot) en contenedores.

```bash
docker-compose up --build
```

## Principales variables de entorno (`.env`)

Asegúrate de configurar estas variables en tu archivo `.env`:

*   `TELEGRAM_BOT_TOKEN`: Token proporcionado por BotFather.
*   `GOOGLE_API_KEY`: API Key para acceder a modelos de Google (Gemini, etc.).
*   `GOOGLE_PROJECT_ID` y `GOOGLE_PROJECT_LOCATION`: Identificador y región de tu proyecto en Google Cloud (si usas Vertex AI).
*   `DATABASE_URL`: URL de conexión a tu base de datos PostgreSQL (ej: `postgresql://user:password@host:port/dbname`).
*   `JWT_SECRET_KEY`: Clave secreta para firmar los tokens JWT.
*   `TELEGRAM_WEBAPP_URL`: URL pública donde está accesible la webapp/panel de usuario.
*   `ADMIN_TELEGRAM_ID`: Opcional, ID de Telegram de un administrador para funcionalidades específicas.
*   ...y otras variables para configuración de herramientas, logging, etc.

## Arquitectura y módulos clave

*   **`core/`**: Contiene la lógica de negocio principal. Módulos como `notes_manager`, `agenda_manager`, `memory_manager`, `config_manager`, y la capa de acceso a datos (`db`). Es la parte del sistema que sabe *qué* hacer con los datos del usuario, independientemente de *cómo* se le pida.
*   **`telegram_client/`**: Implementa la interfaz específica para Telegram. Contiene los handlers de mensajes, comandos, callbacks, gestión de archivos, etc. Traduce las interacciones de Telegram a llamadas a la lógica de `core/` o a las herramientas.
*   **`tools/`**: Define las herramientas que el agente de IA (basado en LangChain) puede utilizar. Cada archivo aquí (`get_notes_tool.py`, `update_note_tool.py`, `delete_document_tool.py`, `get_agenda_tool.py`, `get_document_content_tool.py`, etc.) representa una capacidad específica (buscar notas, actualizar agenda, eliminar documentos, etc.) y se conecta a la lógica en `core/`. Son agnósticas a la plataforma, recibiendo siempre el `account_id`.
*   **`utils/`**: Módulo para funciones de utilidad general que no pertenecen a la lógica de negocio ni a una interfaz específica. Incluye helpers para embeddings, paginación, manejo de fechas, generación de imágenes, etc.
*   **`public_chat_ui/`**: Contiene los archivos estáticos (HTML, CSS, JavaScript) para la webapp del panel de usuario. Esta webapp interactúa con el backend a través de la API expuesta por `run_api.py`.

## Docker y despliegue

El proyecto incluye soporte para Docker para facilitar el despliegue:

*   `Dockerfile.core`: Para construir la imagen del backend (API y webapp).
*   `Dockerfile.telegram`: Para construir una imagen ligera solo con el cliente de Telegram y sus dependencias mínimas.
*   `docker-compose.yml`: Define los servicios para ejecutar el backend y el bot (y potencialmente la base de datos) en contenedores.

## Contribución

¡Las contribuciones son bienvenidas! Si deseas contribuir:

1.  Haz un fork del repositorio.
2.  Crea una rama para tu feature o corrección (`git checkout -b feature/nombre-de-la-feature`).
3.  Sigue la arquitectura modular existente y los patrones de importación.
4.  Asegúrate de que tu código cumpla con los estándares de linting y, si es posible, añade tests.
5.  Haz commit de tus cambios (`git commit -m 'feat: Añade nueva funcionalidad'`).
6.  Haz push a tu rama (`git push origin feature/nombre-de-la-feature`).
7.  Abre un Pull Request explicando tus cambios.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---

**Kognito AI System** — Un asistente inteligente modular, seguro y extensible.
