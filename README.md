# 🧠 Kognito AI System



![Screenshot from 2025-07-04 09-19-16](https://github.com/user-attachments/assets/0eb98075-8f09-41a0-a8ab-103ab38bd19e)
![image](https://github.com/user-attachments/assets/c315e215-c133-4b48-9748-b9f6e97c1921)
![Screenshot from 2025-07-04 17-45-17](https://github.com/user-attachments/assets/46b13225-486c-4ffc-b149-a6a2bcda5398)
![Screenshot from 2025-07-04 18-05-08](https://github.com/user-attachments/assets/4ca15d85-2999-41e5-8565-cf97658c59d8)


¡Bienvenido a Kognito AI System! Un exocerebro digital personalizable y colaborativo diseñado para aumentar tu inteligencia y la de tu equipo. Kognito AI integra capacidades avanzadas de Inteligencia Artificial, gestión de conocimiento (RAG), y una interfaz multi-plataforma para ayudarte a organizar tu vida digital, automatizar tareas y potenciar la colaboración.

Este repositorio contiene el código fuente de Kognito AI y está destinado exclusivamente a colaboradores cercanos para revisión y desarrollo.

## ✨ Características Principales

Kognito AI está diseñado para ser tu asistente inteligente definitivo, ofreciendo:

*   **Identidad Universal de Usuario:** Unifica tu perfil y datos a través de diferentes plataformas.
*   **Agente de IA Conversacional (KAI):** Un asistente inteligente capaz de entender tus necesidades, responder preguntas y ejecutar acciones.
*   **Memoria a Largo Plazo (RAG):**
    *   **Gestión Documental Inteligente:** Sube y organiza tus documentos (PDFs, DOCX, TXT, MD). Kognito AI los procesa, genera embeddings y los almacena en una base de datos vectorial (PGVector) para una recuperación de información contextual.
    *   **Notas Colaborativas:** Crea y gestiona notas personales o compártelas con tus equipos.
    *   **Insights Proactivos:** El sistema analiza continuamente tu base de conocimiento para encontrar conexiones, sinergias, duplicidades y brechas de información, presentándote descubrimientos relevantes.
        *   **Feedback del Usuario sobre Insights:** Los usuarios pueden ahora proporcionar feedback (útil/no útil, categorías, comentarios) sobre los insights generados. Esta información se utilizará en el futuro para mejorar la relevancia y precisión de los descubrimientos proactivos.
*   **Gestión de la Agenda:** Programa eventos y recordatorios, tanto personales como para equipos.
*   **Entrada Multimodal:** Interactúa con Kognito AI a través de texto, audio (transcripción) e imágenes (generación y procesamiento).
*   **Herramientas Extensibles:** El agente de IA puede utilizar una variedad de herramientas para interactuar con el sistema y el mundo exterior (búsqueda web, gestión de GitHub, análisis de texto, generación de mapas mentales, etc.).
*   **Interfaces Multi-Plataforma:**
    *   **Bot de Telegram:** Tu asistente personal accesible directamente desde Telegram, con chat conversacional y funcionalidades integradas.
    *   **Panel de Control Web (Telegram Web App):** Una interfaz web rica y visual integrada en Telegram para una gestión avanzada de documentos, agenda, notas y configuración.
    *   **Frontend Web (Next.js):** Un dashboard completo y moderno para una experiencia de usuario más profunda y rica en funcionalidades.
*   **Colaboración en Equipo:** Crea equipos, comparte documentos, notas y eventos, y potencia el conocimiento colectivo.

## 🚀 Arquitectura del Proyecto

Kognito AI está construido como un sistema de microservicios, diseñado para ser modular, escalable y mantenible.

**Representación en Árbol Simple:**

```
Kognito AI System
├── 1. Backend (API Central - FastAPI)
│   ├── core/ (Lógica de Negocio y Cerebro)
│   │   ├── config.py (Configuración global)
│   │   ├── database.py (Conexión y modelos DB)
│   │   ├── llm_manager.py (Gestión de LLMs)
│   │   ├── memory_manager.py (RAG y DB Vectorial)
│   │   ├── agent.py (Agente de IA y Orquestación)
│   │   ├── agenda_manager.py (Lógica de Agenda)
│   │   ├── notes_manager.py (Lógica de Notas)
│   │   └── reminders_manager.py (Lógica de Recordatorios)
│   ├── api/ (Endpoints de la API)
│   │   ├── auth/
│   │   ├── users/
│   │   ├── chat/
│   │   ├── documents/
│   │   ├── notes/
│   │   ├── agenda/
│   │   ├── teams/
│   │   ├── workspaces/
│   │   └── analysis/
│   ├── tools/ (Herramientas para el Agente de IA)
│   │   ├── add_note_tool.py
│   │   ├── analyze_text_for_insights_tool.py
│   │   ├── comprehensive_web_analysis_tool.py
│   │   ├── document_rag_tool.py
│   │   ├── image_generation_tool.py
│   │   ├── proactive_knowledge_linker_tool.py
│   │   └── ... (otras herramientas)
│   └── utils/ (Utilidades Compartidas)
│       ├── advanced_text_analyzer.py
│       ├── db_session.py
│       ├── document_parser.py
│       ├── embeddings.py
│       ├── generate_mind_map.py
│       ├── proactive_knowledge_linker.py
│       └── security.py
│
├── 2. Frontend Web (Next.js Dashboard)
│   ├── src/app/(dashboard)/ (Páginas del Dashboard)
│   │   ├── chat/
│   │   ├── agenda/
│   │   ├── notes/
│   │   ├── rag/
│   │   ├── teams/
│   │   └── workspaces/
│   ├── src/components/ (Componentes UI Reutilizables)
│   │   ├── ui/ (Componentes Shadcn/ui)
│   │   └── ... (componentes personalizados)
│   ├── src/contexts/ (Contextos de React)
│   └── src/hooks/ (Hooks Personalizados, ej. useToast)
│
├── 3. Telegram Client (Bot)
│   ├── telegram_client/bot_manager.py (Gestión del Bot)
│   ├── telegram_client/notification_scheduler.py (Programación de Notificaciones)
│   └── telegram_client/handlers/ (Lógica de Respuestas del Bot)
│
├── 4. Telegram Panel (Web App)
│   ├── telegram_panel/index.html (Interfaz de Usuario)
│   ├── telegram_panel/script.js (Lógica Frontend)
│   ├── telegram_panel/style.css (Estilos)
│   └── run_telegram_panel.py (Servidor FastAPI para el Panel)
│
├── 5. Base de Datos
│   └── PostgreSQL + PGVector
│
├── 6. PGAdmin (Interfaz de Administración DB)
│
├── 7. Infraestructura de Despliegue
│   ├── Dockerfile.core
│   ├── Dockerfile.frontend
│   ├── Dockerfile.telegram
│   ├── Dockerfile.webapp
│   ├── docker-compose.yml (Orquestación de Servicios)
│   └── nginx.conf (Proxy Inverso)
│
├── 8. (Próximamente) Redis (Broker de Mensajes / Pub/Sub)
│
└── 9. (Próximamente) Celery Workers (Procesamiento de Tareas en Segundo Plano)
```

## 🛠️ Stack Tecnológico

*   **Backend:** Python 3.11, FastAPI, SQLAlchemy (Async), LangChain, LangGraph, Ollama, Google Generative AI (Gemini), spaCy, KeyBERT, `python-telegram-bot`.
*   **Frontend:** Next.js 14, React, TypeScript, Shadcn/ui, Tailwind CSS, Framer Motion.
*   **Base de Datos:** PostgreSQL, PGVector.
*   **Contenerización:** Docker, Docker Compose.
*   **Proxy Inverso:** Nginx.
*   **Colas de Tareas:** Celery, Redis (próximamente).
*   **Comunicación en Tiempo Real:** WebSockets (próximamente).

## 🚧 Próximas Mejoras (En Desarrollo)

Estamos trabajando activamente en:

*   **Integración de Celery:** Para una gestión robusta de tareas en segundo plano (procesamiento de documentos, análisis de LLMs, generación de insights) que no bloquee la API principal y garantice la persistencia y escalabilidad.
*   **WebSockets con Redis Pub/Sub:** Para notificaciones en tiempo real al frontend, eliminando el polling y proporcionando una experiencia de usuario instantánea y fluida.
*   **Refinamiento de Insights Proactivos Basado en Feedback:** Mejorar el algoritmo de generación de insights para que aprenda de las preferencias y correcciones del usuario, utilizando el feedback recolectado para ofrecer descubrimientos aún más personalizados y acertados.
