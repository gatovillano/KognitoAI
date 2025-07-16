# 🧠 Kognito AI System

![Screenshot from 2025-07-04 09-19-16](https://github.com/user-attachments/assets/0eb98075-8f09-41a0-a8ab-103ab38bd19e)
![image](https://github.com/user-attachments/assets/c315e215-c133-4b48-9748-b9f6e97c1921)
![Screenshot from 2025-07-04 17-45-17](https://github.com/user-attachments/assets/46b13225-486c-4ffc-b149-a6a2bcda5398)
![Screenshot from 2025-07-04 18-05-08](https://github.com/user-attachments/assets/4ca15d85-2999-41e5-8565-cf97658c59d8)

¡Bienvenido a **Kognito AI System**! Un exocerebro digital personalizable y colaborativo diseñado para aumentar tu inteligencia y la de tu equipo. Kognito AI integra capacidades avanzadas de Inteligencia Artificial, **grafos de conocimiento**, gestión de memoria vectorial (RAG), y una interfaz multi-plataforma para ayudarte a organizar tu vida digital, automatizar tareas y potenciar la colaboración.

## 🌟 **Novedades Principales**

- 🧠 **Grafos de Conocimiento con Cognee**: Crea automáticamente mapas conceptuales de tus documentos
- 🔗 **Arquitectura Híbrida**: Combina PGVector (búsqueda semántica) + Neo4j (relaciones conceptuales)
- 🎨 **Visualización Interactiva**: Explora tus conocimientos de forma visual e intuitiva
- 🔄 **Migración Automática**: Scripts para convertir tu base de conocimientos existente en grafos
- 🔍 **Búsqueda Híbrida**: Lo mejor de la búsqueda semántica y navegación relacional

Este repositorio contiene el código fuente de Kognito AI y está destinado exclusivamente a colaboradores cercanos para revisión y desarrollo.

## ✨ Características Principales

Kognito AI está diseñado para ser tu asistente inteligente definitivo, ofreciendo:

### 🧠 **Sistema de Conocimiento Híbrido**
*   **Grafos de Conocimiento (Cognee + Neo4j):** Crea automáticamente mapas conceptuales que muestran cómo se relacionan tus ideas, documentos y conceptos.
*   **Búsqueda Vectorial (PGVector):** Encuentra información por similitud semántica con precisión ultra-rápida.
*   **Búsqueda Híbrida Inteligente:** Combina lo mejor de ambos mundos - contenido relevante + relaciones conceptuales.
*   **Visualización Interactiva:** Explora tu conocimiento de forma visual con grafos navegables.

### 🤖 **Inteligencia Artificial Avanzada**
*   **Identidad Universal de Usuario:** Unifica tu perfil y datos a través de diferentes plataformas.
*   **Agente de IA Conversacional (KAI):** Un asistente inteligente capaz de entender tus necesidades, responder preguntas y ejecutar acciones.
*   **Herramientas Extensibles:** El agente puede usar 30+ herramientas especializadas (búsqueda web, GitHub, análisis de texto, generación de mapas mentales, grafos de conocimiento, etc.).

### 📚 **Gestión de Conocimiento**
*   **Gestión Documental Inteligente:** Sube y organiza documentos (PDFs, DOCX, TXT, MD). Se procesan automáticamente en ambas bases de datos.
*   **Notas Colaborativas:** Crea y gestiona notas personales o compártelas con equipos.
*   **Insights Proactivos:** Análisis continuo para encontrar conexiones, sinergias, duplicidades y brechas de información.
*   **Migración Automática:** Scripts para convertir tu base de conocimientos existente en grafos.

### 🎯 **Productividad y Organización**
*   **Gestión de Agenda:** Programa eventos y recordatorios, tanto personales como para equipos.
*   **Entrada Multimodal:** Interactúa a través de texto, audio (transcripción) e imágenes (generación y procesamiento).
*   **Colaboración en Equipo:** Crea equipos, comparte documentos, notas y eventos.

### 🌐 **Interfaces Multi-Plataforma**
*   **Bot de Telegram:** Asistente personal accesible directamente desde Telegram.
*   **Panel Web (Telegram Web App):** Interfaz rica integrada en Telegram para gestión avanzada.
*   **Frontend Web (Next.js):** Dashboard completo con visualización de grafos de conocimiento.
*   **Neo4j Browser:** Exploración avanzada de grafos para power users.

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
├── 5. Bases de Datos (Arquitectura Híbrida)
│   ├── PostgreSQL + PGVector (Búsqueda Semántica)
│   └── Neo4j (Grafos de Conocimiento)
│
├── 6. Grafos de Conocimiento
│   ├── knowledge_graph/
│   │   ├── cognee_integration.py (Integración con Cognee)
│   │   ├── graph_database.py (Conexión Neo4j)
│   │   └── hybrid_cognee_adapter.py (Adaptador Híbrido)
│   ├── tools/cognee_knowledge_graph_tool.py (Herramienta del Agente)
│   └── scripts/ (Scripts de Migración)
│       ├── migrate_pgvector_to_neo4j.py
│       ├── analyze_pgvector_data.py
│       └── selective_migration.py
│
├── 8. PGAdmin (Interfaz de Administración DB)
│
├── 9. Infraestructura de Despliegue
│   ├── Dockerfile.core
│   ├── Dockerfile.frontend
│   ├── Dockerfile.telegram
│   ├── Dockerfile.webapp
│   ├── docker-compose.yml (Orquestación de Servicios)
│   └── nginx.conf (Proxy Inverso)
│
├── 10. (Próximamente) Redis (Broker de Mensajes / Pub/Sub)
│
└── 11. (Próximamente) Celery Workers (Procesamiento de Tareas en Segundo Plano)
```

## 🛠️ Stack Tecnológico

### **Backend & IA**
*   **Core:** Python 3.11, FastAPI, SQLAlchemy (Async)
*   **IA & LLM:** LangChain, LangGraph, Google Generative AI (Gemini 2.0 Flash), spaCy, KeyBERT
*   **Grafos de Conocimiento:** Cognee, Neo4j, NetworkX, Cytoscape.js
*   **Comunicación:** `python-telegram-bot`, WebSockets

### **Frontend & UI**
*   **Web Dashboard:** Next.js 14, React, TypeScript, Shadcn/ui, Tailwind CSS, Framer Motion
*   **Visualización:** Cytoscape.js (grafos interactivos), D3.js, Plotly
*   **Telegram:** Bot nativo + Web App integrada

### **Bases de Datos**
*   **Búsqueda Semántica:** PostgreSQL + PGVector (embeddings vectoriales)
*   **Grafos de Conocimiento:** Neo4j 5 (relaciones conceptuales)
*   **Administración:** PGAdmin (PostgreSQL), Neo4j Browser (grafos)

### **Infraestructura**
*   **Contenerización:** Docker, Docker Compose
*   **Proxy Inverso:** Nginx
*   **Colas de Tareas:** Celery, Redis (próximamente)
*   **Monitoreo:** Logs estructurados, métricas de rendimiento

## 🧠 Grafos de Conocimiento con Cognee

### **¿Qué son los Grafos de Conocimiento?**

Los grafos de conocimiento representan información como una red de entidades conectadas, permitiendo:

- 🔗 **Navegación Conceptual**: Explora cómo se relacionan tus ideas
- 🎯 **Descubrimiento de Patrones**: Encuentra conexiones ocultas en tu información
- 🧠 **Comprensión Contextual**: Ve el panorama completo de tu conocimiento
- 🔍 **Búsqueda Inteligente**: Encuentra información por relaciones, no solo por palabras

### **Arquitectura Híbrida: Lo Mejor de Ambos Mundos**

```
📊 PGVector (Búsqueda Semántica)     🕸️ Neo4j (Relaciones Conceptuales)
├─ Embeddings vectoriales            ├─ Nodos (entidades, conceptos)
├─ Similitud coseno                  ├─ Aristas (relaciones)
├─ Búsqueda ultra-rápida            ├─ Consultas Cypher
└─ Contenido detallado              └─ Visualización interactiva
                    ↓
            🔄 Búsqueda Híbrida
         (Combina ambas fuentes)
```

### **Casos de Uso Prácticos**

#### **Para Investigadores:**
- 📚 Mapea automáticamente literatura científica
- 🔗 Encuentra conexiones entre papers
- 💡 Descubre gaps de investigación

#### **Para Empresas:**
- 📋 Organiza conocimiento corporativo
- 🎯 Identifica sinergias entre proyectos
- 📊 Visualiza flujos de información

#### **Para Estudiantes:**
- 📖 Conecta conceptos de diferentes materias
- 🧠 Crea mapas mentales automáticos
- 🔍 Encuentra relaciones entre temas

### **Herramientas Disponibles**

#### **1. Herramienta del Agente IA**
```python
# El agente puede usar automáticamente:
"Crea un grafo de conocimiento con mis documentos sobre IA"
"¿Cómo se relaciona machine learning con mis proyectos?"
"Muéstrame insights de mi base de conocimientos"
```

#### **2. Scripts de Migración**
```bash
# Analizar datos existentes
python scripts/analyze_pgvector_data.py

# Migración completa automática
python scripts/migrate_pgvector_to_neo4j.py

# Migración selectiva con filtros
python scripts/selective_migration.py
```

#### **3. Visualización**
- **Neo4j Browser**: http://localhost:7474 (análisis avanzado)
- **Frontend Web**: Grafos interactivos con Cytoscape.js
- **Telegram**: Imágenes estáticas + enlaces a vista web

## 🚀 Configuración Rápida

### **Prerrequisitos**
- Docker y Docker Compose
- 8GB RAM mínimo (recomendado 16GB)
- Google API Key (para LLM y embeddings)

### **Variables de Entorno Esenciales**

Crea un archivo `.env` basado en `.env.example`:

```bash
# IA y LLM
GOOGLE_API_KEY=tu_google_api_key_aqui
GOOGLE_PROJECT_ID=tu_proyecto_google_cloud
GOOGLE_PROJECT_LOCATION=us-central1

# Bases de Datos
POSTGRES_PASSWORD=tu_password_seguro
NEO4J_PASSWORD=tu_neo4j_password

# Neo4j (para Grafos de Conocimiento)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=tu_bot_token
BOT_USERNAME=tu_bot_username
```

### **Inicio Rápido**

```bash
# 1. Clonar repositorio
git clone [repo-url]
cd kognito-ai

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Iniciar servicios
docker-compose up -d

# 4. Verificar servicios
docker-compose ps

# 5. Acceder a interfaces
# - API: http://localhost:8889
# - Frontend: http://localhost:8880
# - Neo4j Browser: http://localhost:7474
# - PGAdmin: http://localhost:5050
```

### **Primeros Pasos con Grafos**

```bash
# 1. Analizar datos existentes (si los tienes)
docker exec -it kognito_core python scripts/analyze_pgvector_data.py

# 2. Generar datos de demostración
docker exec -it kognito_core python scripts/test_cognee.py

# 3. Migrar datos existentes (opcional)
docker exec -it kognito_core python scripts/migrate_pgvector_to_neo4j.py

# 4. Explorar en Neo4j Browser
# URL: http://localhost:7474
# Usuario: neo4j
# Password: tu_neo4j_password
# Consulta: MATCH (n) RETURN n LIMIT 25
```

## 🚧 Próximas Mejoras (En Desarrollo)

### **Grafos de Conocimiento**
*   **Visualización Avanzada:** Componentes React para grafos interactivos en el frontend
*   **IA Generativa para Grafos:** Generación automática de insights y resúmenes conceptuales
*   **Colaboración en Grafos:** Grafos compartidos entre equipos con permisos granulares
*   **Exportación:** Formatos Gephi, Cytoscape, GraphML para análisis externos

### **Infraestructura**
*   **Integración de Celery:** Procesamiento de grafos en segundo plano para datasets grandes
*   **WebSockets con Redis Pub/Sub:** Notificaciones en tiempo real de cambios en grafos
*   **Caché Inteligente:** Optimización de consultas híbridas frecuentes
*   **Métricas Avanzadas:** Dashboard de rendimiento para ambas bases de datos

## 📚 Documentación Adicional

### **Guías Específicas**
- 📖 [Guía de Uso de Cognee](docs/COGNEE_USAGE_GUIDE.md) - Tutorial completo de grafos de conocimiento
- 🔧 [Configuración Avanzada](docs/ADVANCED_CONFIGURATION.md) - Optimización y personalización
- 🛠️ [API Reference](http://localhost:8889/docs) - Documentación interactiva de la API
- 🎨 [Guía de Visualización](docs/VISUALIZATION_GUIDE.md) - Personalizar grafos y dashboards

### **Scripts y Herramientas**
- 🔄 [Scripts de Migración](scripts/) - Herramientas para migrar datos existentes
- 📊 [Ejemplos de Uso](examples/) - Casos de uso prácticos con código
- 🧪 [Tests](tests/) - Suite de pruebas automatizadas
- 📝 [Logs](docs/LOGGING_IMPLEMENTATION_SUMMARY.md) - Sistema de logging avanzado

### **Arquitectura Técnica**
- 🏗️ [Diseño del Sistema](docs/SYSTEM_ARCHITECTURE.md) - Arquitectura detallada
- 🔌 [Integración de APIs](docs/API_INTEGRATION.md) - Conectar servicios externos
- 🛡️ [Seguridad](docs/SECURITY.md) - Mejores prácticas de seguridad
- 📈 [Escalabilidad](docs/SCALABILITY.md) - Optimización para grandes volúmenes

## 🤝 Contribución y Desarrollo

### **Para Desarrolladores**

```bash
# Desarrollo local
git clone [repo-url]
cd kognito-ai

# Configurar entorno de desarrollo
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
pip install -r requirements-build.txt

# Ejecutar tests
pytest tests/

# Linting y formato
black .
flake8 .
```

### **Estructura de Contribución**
- 🐛 **Issues**: Reporta bugs o solicita features
- 🔧 **Pull Requests**: Contribuye con código siguiendo las guías
- 📖 **Documentación**: Mejora guías y ejemplos
- 🧪 **Testing**: Agrega tests para nuevas funcionalidades

### **Roadmap de Desarrollo**

#### **Q1 2025**
- ✅ Integración completa de Cognee
- ✅ Arquitectura híbrida PGVector + Neo4j
- 🔄 Visualización avanzada de grafos
- 🔄 Scripts de migración automática

#### **Q2 2025**
- 📱 App móvil nativa
- 🤖 IA generativa para grafos
- 🔗 Integración con más fuentes de datos
- 📊 Analytics avanzados

#### **Q3 2025**
- 🌐 Modo multi-tenant
- 🔒 Seguridad enterprise
- 📈 Optimizaciones de rendimiento
- 🎨 Temas y personalización avanzada

## 📞 Soporte y Comunidad

### **Canales de Comunicación**
- 💬 **Telegram**: [@KognitoAIBot](https://t.me/KognitoAIBot) - Bot oficial para pruebas
- 📧 **Email**: [contacto@kognito.ai](mailto:contacto@kognito.ai)
- 🐛 **Issues**: GitHub Issues para bugs y features
- 📖 **Wiki**: Documentación colaborativa

### **Recursos Útiles**
- 🎥 **Demos**: Videos de funcionalidades principales
- 📚 **Tutoriales**: Guías paso a paso
- 🔧 **Troubleshooting**: Solución de problemas comunes
- 💡 **Best Practices**: Recomendaciones de uso

---

## 📄 Licencia

Este proyecto está bajo licencia privada y es exclusivo para colaboradores autorizados.

**© 2024-2025 Kognito AI System. Todos los derechos reservados.**

---

*Construido con ❤️ para potenciar la inteligencia humana a través de la tecnología.*
