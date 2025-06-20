# Kognito AI System

Kognito AI es un sistema modular de asistente inteligente que integra un bot de Telegram, una API centralizada basada en FastAPI, una webapp de panel de control y un motor de IA con memoria a largo plazo y herramientas personalizadas. El proyecto está diseñado para ser extensible, seguro y fácil de desplegar en entornos modernos.

## Características principales

- **Bot de Telegram**: Interfaz conversacional con soporte para comandos, documentos, notas, agenda y recordatorios.
- **API y WebApp**: Servidor centralizado con endpoints para chat, autenticación, gestión de documentos y panel de usuario.
- **Memoria y RAG**: Almacenamiento de memorias vectoriales y perfil estructurado del usuario usando PostgreSQL y pgvector.
- **Herramientas LangChain**: Integración de herramientas personalizadas para notas, agenda, documentos, scraping web, generación de imágenes y más.
- **Autenticación Universal**: Sistema de cuentas desacoplado de la plataforma, con login vía Telegram y JWT para la webapp.
- **Arquitectura Modular**: Separación clara entre lógica de negocio, utilidades, herramientas y controladores de plataforma.

## Estructura del Proyecto

```
KognitoAI/
├── core/                # Lógica de negocio (notas, agenda, memoria, config, DB)
├── telegram_client/     # Bot de Telegram y handlers
├── tools/               # Herramientas LangChain (notas, agenda, scraping, etc.)
├── utils/               # Utilidades generales (embeddings, helpers, paginador)
├── public_chat_ui/      # Webapp de panel de control (HTML, CSS, JS)
├── run_api.py           # Servidor FastAPI (API central y webapp)
├── run_telegram_bot.py  # Punto de entrada del bot de Telegram
├── requirements.txt     # Dependencias principales
├── Dockerfile*          # Dockerización para backend y webapp
└── ...
```

## Instalación y despliegue rápido

1. **Clona el repositorio**

```bash
git clone <repo-url>
cd KognitoAI
```

2. **Configura el entorno**

Copia el archivo `.env.example` a `.env` y completa las variables necesarias (tokens, claves de Google, URL de la base de datos, etc).

3. **Instala las dependencias**

```bash
pip install -r requirements.txt
```

4. **Inicializa la base de datos**

Asegúrate de tener PostgreSQL y la extensión `pgvector` habilitada. El sistema creará las tablas automáticamente al iniciar el backend.

5. **Ejecuta el backend (API y webapp)**

```bash
python run_api.py
```

6. **Ejecuta el bot de Telegram**

```bash
python run_telegram_bot.py
```

7. **(Opcional) Despliegue con Docker**

```bash
docker-compose up --build
```

## Principales variables de entorno (`.env`)

- `TELEGRAM_BOT_TOKEN` — Token del bot de Telegram
- `GOOGLE_API_KEY` — API Key de Google para LLMs y Vertex AI
- `GOOGLE_PROJECT_ID` y `GOOGLE_PROJECT_LOCATION` — Proyecto y región de Google Cloud
- `DATABASE_URL` — URL de conexión a PostgreSQL
- `JWT_SECRET_KEY` — Clave secreta para autenticación JWT
- `TELEGRAM_WEBAPP_URL` — URL pública de la webapp/panel
- ...y otras para configuración avanzada

## Arquitectura y módulos clave

- **core/**: Lógica de negocio desacoplada de la plataforma (notas, agenda, memoria, recordatorios, config, DB).
- **telegram_client/**: Handlers y lógica específica del bot de Telegram.
- **tools/**: Herramientas LangChain para IA (CRUD de notas, agenda, scraping, documentos, imágenes, etc).
- **utils/**: Utilidades generales (embeddings, helpers, paginador, generación de imágenes).
- **public_chat_ui/**: Webapp de panel de usuario (autenticación, chat, gestión de documentos).

## Contribución

1. Haz un fork y crea una rama para tu feature o fix.
2. Sigue la arquitectura modular y los patrones de importación del proyecto.
3. Asegúrate de que tu código pase los tests y linting antes de hacer un PR.

## Licencia

MIT. Consulta el archivo LICENSE para más detalles.

---

**Kognito AI System** — Asistente modular, seguro y extensible para equipos modernos.
