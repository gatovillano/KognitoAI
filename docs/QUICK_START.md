# 🚀 Guía de Inicio Rápido - Kognito AI

## ⚡ Configuración en 5 Minutos

### **1. Prerrequisitos**
```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar recursos
# Mínimo: 8GB RAM, 20GB espacio libre
# Recomendado: 16GB RAM, 50GB espacio libre
```

### **2. Configuración Inicial**
```bash
# Clonar repositorio
git clone [repo-url]
cd kognito-ai

# Copiar configuración
cp .env.example .env
```

### **3. Configurar Variables Esenciales**
Edita el archivo `.env` con tus credenciales:

```bash
# IA y LLM (OBLIGATORIO)
GOOGLE_API_KEY=tu_google_api_key_aqui

# Bases de Datos (OBLIGATORIO)
POSTGRES_PASSWORD=password_seguro_aqui
NEO4J_PASSWORD=neo4j_password_aqui

# Telegram (OPCIONAL)
TELEGRAM_BOT_TOKEN=tu_bot_token
BOT_USERNAME=tu_bot_username
```

### **4. Iniciar Servicios**
```bash
# Iniciar todos los servicios
docker compose up -d

# Verificar que todo esté corriendo
docker compose ps
```

### **5. Verificar Instalación**
```bash
# API Core
curl http://localhost:8889/health

# Frontend Web
open http://localhost:8880

# Neo4j Browser
open http://localhost:7474
```

## 🧠 Primeros Pasos con Grafos de Conocimiento

### **Opción A: Datos de Demostración**
```bash
# Generar datos de ejemplo
docker exec -it kognito_core python scripts/test_cognee.py

# Ver en Neo4j Browser
# URL: http://localhost:7474
# Usuario: neo4j / Password: tu_neo4j_password
# Consulta: MATCH (n) RETURN n LIMIT 25
```

### **Opción B: Migrar Datos Existentes**
```bash
# 1. Analizar datos actuales
docker exec -it kognito_core python scripts/analyze_pgvector_data.py

# 2. Migración selectiva (recomendado para empezar)
docker exec -it kognito_core python scripts/selective_migration.py

# 3. Migración completa (cuando estés listo)
docker exec -it kognito_core python scripts/migrate_pgvector_to_neo4j.py
```

## 🎯 Casos de Uso Inmediatos

### **1. Chat con IA**
```bash
# Telegram: Habla con @tu_bot_username
# Web: http://localhost:8880/chat
# API: POST http://localhost:8889/chat
```

### **2. Subir Documentos**
```bash
# Web: http://localhost:8880/documents
# Se procesan automáticamente en ambas bases de datos
```

### **3. Crear Grafos de Conocimiento**
```bash
# Desde el chat:
"Crea un grafo de conocimiento con mis documentos"
"¿Cómo se relacionan mis proyectos de IA?"
"Muéstrame insights de mi base de conocimientos"
```

### **4. Visualizar Grafos**
```bash
# Neo4j Browser: http://localhost:7474
# Consultas útiles:
MATCH (n) RETURN n LIMIT 25
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10
MATCH (n) WHERE n.content CONTAINS "IA" RETURN n
```

## 🔧 Solución de Problemas Comunes

### **Error: "Cannot connect to Neo4j"**
```bash
# Verificar que Neo4j esté corriendo
docker logs kognito_neo4j

# Reiniciar Neo4j
docker-compose restart neo4j
```

### **Error: "Google API Key not found"**
```bash
# Verificar variable de entorno
docker exec -it kognito_core env | grep GOOGLE_API_KEY

# Reiniciar servicios después de cambiar .env
docker-compose restart core
```

### **Error: "Out of memory during build"**
```bash
# Aumentar memoria de Docker
# Docker Desktop: Settings > Resources > Memory > 8GB+

# Build por partes
docker-compose build --no-cache core
```

### **Servicios lentos**
```bash
# Verificar recursos
docker stats

# Optimizar para desarrollo
# En docker-compose.yml, comentar servicios no esenciales temporalmente
```

## 📚 Próximos Pasos

### **Explorar Funcionalidades**
1. 📄 **Documentos**: Sube PDFs, DOCX, TXT
2. 📝 **Notas**: Crea notas personales y de equipo
3. 📅 **Agenda**: Programa eventos y recordatorios
4. 🧠 **Grafos**: Explora relaciones en tu conocimiento
5. 🔍 **Búsqueda**: Prueba búsqueda semántica e híbrida

### **Personalización**
1. 🎨 **Temas**: Personaliza la interfaz web
2. 🔧 **Herramientas**: Configura herramientas del agente
3. 👥 **Equipos**: Crea espacios colaborativos
4. 🔒 **Permisos**: Configura acceso granular

### **Integración**
1. 🤖 **Telegram**: Configura tu bot personal
2. 🌐 **API**: Integra con tus aplicaciones
3. 📊 **Webhooks**: Automatiza flujos de trabajo
4. 🔗 **Servicios**: Conecta GitHub, Google Drive, etc.

## 📞 Obtener Ayuda

- 📖 **Documentación**: [docs/COGNEE_USAGE_GUIDE.md](docs/COGNEE_USAGE_GUIDE.md)
- 🐛 **Issues**: GitHub Issues para problemas
- 💬 **Telegram**: @KognitoAIBot para pruebas
- 📧 **Email**: contacto@kognitoai.cloud

---

¡Listo para potenciar tu inteligencia con Kognito AI! 🧠✨
