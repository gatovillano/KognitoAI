# Estructura de `run_api.py`

Este documento detalla la estructura del archivo `run_api.py`, que es el núcleo de la API central del sistema Kognito AI. A continuación, se presenta un árbol jerárquico que representa las secciones y subsecciones del código, junto con breves descripciones de cada parte.

```plaintext
run_api.py
├── Importaciones
│   ├── Módulos estándar de Python (logging, asyncio, os, json, etc.)
│   ├── Bibliotecas de terceros (FastAPI, pydantic, httpx, etc.)
│   ├── Módulos internos del proyecto (core.config, core.database, etc.)
│
├── Configuración de Logging
│   └── Configuración básica de logging con formato personalizado
│
├── Inicialización de la Aplicación FastAPI
│   └── Definición de la app con título, descripción y versión
│
├── Evento de Inicio (startup_event)
│   └── Inicialización de recursos críticos (tablas de BD, LLMs)
│
├── Configuración de CORS
│   └── Lista de orígenes permitidos y configuración de middleware
│
├── Dependencias
│   ├── get_db (Gestión de sesiones de base de datos)
│   ├── get_internal_api_key (Validación de clave API interna)
│   ├── get_validated_user_id (Validación de usuario de Telegram)
│
├── Modelos Pydantic
│   ├── RegisterRequest (Estructura para registro de usuario)
│   ├── LoginRequest (Estructura para inicio de sesión)
│   ├── TokenResponse (Estructura para respuesta de token)
│   ├── TelegramLoginRequest (Estructura para login de Telegram)
│   ├── AuthRequestCode (Estructura para solicitar código de verificación)
│   ├── AuthVerifyCode (Estructura para verificar código)
│   ├── UserProfileResponse (Estructura para perfil de usuario)
│   ├── ChatRequest (Estructura para solicitud de chat)
│   ├── ChatResponse (Estructura para respuesta de chat)
│   ├── ListNotesRequest (Estructura para listar notas)
│   ├── NoteRequest (Estructura para añadir nota)
│   ├── NoteUpdateRequest (Estructura para actualizar nota)
│   ├── NoteDeleteRequest (Estructura para eliminar nota)
│   ├── EventRequest (Estructura para añadir evento)
│   ├── EventCancelRequest (Estructura para cancelar evento)
│   ├── UpdateMetadataRequest (Estructura para actualizar metadatos de documento)
│   ├── DocumentContentRequest (Estructura para obtener contenido de documento)
│   ├── AnalyzeDocumentRequest (Estructura para analizar documento)
│   ├── AnalyzeCollectionRequest (Estructura para analizar colección)
│   ├── ThreadResponse (Estructura para respuesta de hilo de chat)
│   ├── MessageResponse (Estructura para mensaje de chat)
│   └── TTSRequest (Estructura para solicitud de texto a voz)
│
├── Endpoints de Autenticación
│   ├── Registro de Usuario (/api/auth/register)
│   ├── Inicio de Sesión (/api/auth/login)
│   ├── Login de Telegram (/api/auth/telegram/callback)
│   ├── Solicitud de Código de Verificación (/api/auth/request-code)
│   ├── Verificación de Código (/api/auth/verify-code)
│
├── Endpoints de Perfil de Usuario
│   └── Obtener Perfil (/api/users/me)
│
├── Endpoints de Chat
│   └── Procesar Mensaje de Chat (/api/chat)
│
├── Endpoints para Panel de Telegram
│   ├── Servir Panel de Control (/)
│   ├── Obtener Prompt de Sistema (/api/get-system-prompt)
│   ├── Guardar Prompt de Sistema (/api/save-system-prompt)
│
├── Endpoints de Gestión de Documentos (RAG)
│   ├── Subir Documento (/api/upload-document)
│   ├── Listar Documentos (/api/list-documents)
│   ├── Eliminar Documento (/api/delete-document)
│   ├── Actualizar Metadatos de Documento (/api/update-document-metadata)
│   ├── Obtener Contenido de Documento (/api/get-document-content)
│   ├── Listar Colecciones (/api/list-collections)
│   ├── Iniciar Análisis de Documento (/api/start-document-analysis)
│   ├── Obtener Resultado de Análisis (/api/get-analysis-result/{task_id})
│   ├── Analizar Documento (/api/analyze-document)
│   ├── Iniciar Análisis de Colección (/api/start-collection-analysis)
│
├── Endpoints de Notas
│   ├── Listar Notas (/api/list-notes)
│   ├── Añadir Nota (/api/add-note)
│   ├── Actualizar Nota (/api/update-note)
│   ├── Eliminar Nota (/api/delete-note)
│
├── Endpoints de Agenda
│   ├── Listar Eventos (/api/list-events)
│   ├── Añadir Evento (/api/add-event)
│   ├── Cancelar Evento (/api/cancel-event)
│
├── Endpoints de Hilos de Chat
│   ├── Listar Hilos (/api/threads)
│   ├── Crear Hilo (/api/threads)
│   ├── Obtener Mensajes de Hilo (/api/threads/{thread_id}/messages)
│   ├── Eliminar Hilo (/api/threads/{thread_id})
│   ├── Obtener Hilo por ID (/api/threads/{thread_id})
│
├── Endpoints Internos
│   └── Crear Hilo por Bot (/internal/bot-create-thread)
│
├── Endpoints de Audio
│   ├── Transcribir Audio (/api/transcribe-audio)
│   ├── Texto a Voz (/api/text-to-speech)
│
└── Bloque de Ejecución para Desarrollo Local
    └── Ejecución con Uvicorn (if __name__ == "__main__")
```

## Descripción General

`run_api.py` es un archivo extenso que define la API central del sistema Kognito AI utilizando FastAPI. Está organizado en secciones lógicas que cubren desde la configuración inicial y autenticación hasta la gestión de documentos, notas, agenda, chat y funcionalidades de audio. Cada sección contiene endpoints específicos con sus respectivas funciones y modelos de datos definidos mediante Pydantic.

Este archivo actúa como el punto de entrada principal para todas las interacciones con el backend del sistema, proporcionando una interfaz robusta para la autenticación, procesamiento de datos y comunicación con otros servicios internos y externos.
