#!/bin/bash
# setup_storage_almacenamiento.sh
# Script para configurar almacenamiento en /media/gato/Almacenamiento

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
STORAGE_BASE="/media/gato/Almacenamiento"
KOGNITO_DATA="$STORAGE_BASE/kognito-ai"
PROJECT_DIR="/home/gato/KognitoAI/kognito-ai"

echo -e "${BLUE}🚀 Configurando almacenamiento para KognitoAI + UMACO${NC}"
echo -e "${BLUE}📍 Ubicación: $KOGNITO_DATA${NC}"
echo ""

# Verificar que el disco esté montado
if [ ! -d "$STORAGE_BASE" ]; then
    echo -e "${RED}❌ Error: $STORAGE_BASE no está montado${NC}"
    echo "Por favor, monta la partición primero"
    exit 1
fi

# Verificar espacio disponible
AVAILABLE_SPACE=$(df -BG "$STORAGE_BASE" | awk 'NR==2 {print $4}' | sed 's/G//')
echo -e "${BLUE}💾 Espacio disponible: ${AVAILABLE_SPACE}GB${NC}"

if [ "$AVAILABLE_SPACE" -lt 50 ]; then
    echo -e "${YELLOW}⚠️  Advertencia: Menos de 50GB disponibles. Se recomienda al menos 100GB${NC}"
    read -p "¿Continuar de todos modos? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Crear estructura de directorios
echo -e "${YELLOW}📁 Creando estructura de directorios...${NC}"

# Directorios principales
mkdir -p "$KOGNITO_DATA"/{neo4j/{data,logs,backups},umaco/{models,agent_data,workflows,cache},cognee/{embeddings,graphs,processed},postgres/{data,backups},shared/{logs,temp,exports}}

# Directorios específicos para UMACO
mkdir -p "$KOGNITO_DATA"/umaco/{agents/{research,analysis,synthesis,knowledge_graph},orchestrator/{configs,workflows,templates},shared/{models,cache,logs}}

# Configurar permisos
echo -e "${YELLOW}🔐 Configurando permisos...${NC}"
sudo chown -R $USER:$USER "$KOGNITO_DATA"
chmod -R 755 "$KOGNITO_DATA"

# Crear enlaces simbólicos para fácil acceso
echo -e "${YELLOW}🔗 Creando enlaces simbólicos...${NC}"
ln -sf "$KOGNITO_DATA" ~/kognito-storage
ln -sf "$KOGNITO_DATA" "$PROJECT_DIR/external-storage"

# Crear archivo de configuración .env para las rutas
echo -e "${YELLOW}⚙️ Creando configuración de rutas...${NC}"
cat > "$PROJECT_DIR/.env.storage" << EOF
# Configuración de almacenamiento externo
# Generado automáticamente por setup_storage_almacenamiento.sh

# Ruta base del almacenamiento externo
EXTERNAL_STORAGE_ROOT=$KOGNITO_DATA

# Neo4j
NEO4J_DATA_PATH=\${EXTERNAL_STORAGE_ROOT}/neo4j/data
NEO4J_LOGS_PATH=\${EXTERNAL_STORAGE_ROOT}/neo4j/logs
NEO4J_BACKUPS_PATH=\${EXTERNAL_STORAGE_ROOT}/neo4j/backups

# UMACO
UMACO_ROOT_PATH=\${EXTERNAL_STORAGE_ROOT}/umaco
UMACO_MODELS_PATH=\${UMACO_ROOT_PATH}/models
UMACO_AGENT_DATA_PATH=\${UMACO_ROOT_PATH}/agent_data
UMACO_WORKFLOWS_PATH=\${UMACO_ROOT_PATH}/workflows
UMACO_CACHE_PATH=\${UMACO_ROOT_PATH}/cache
UMACO_ORCHESTRATOR_PATH=\${UMACO_ROOT_PATH}/orchestrator

# Cognee
COGNEE_ROOT_PATH=\${EXTERNAL_STORAGE_ROOT}/cognee
COGNEE_EMBEDDINGS_PATH=\${COGNEE_ROOT_PATH}/embeddings
COGNEE_GRAPHS_PATH=\${COGNEE_ROOT_PATH}/graphs
COGNEE_PROCESSED_PATH=\${COGNEE_ROOT_PATH}/processed

# PostgreSQL
POSTGRES_EXTERNAL_DATA_PATH=\${EXTERNAL_STORAGE_ROOT}/postgres/data
POSTGRES_BACKUPS_PATH=\${EXTERNAL_STORAGE_ROOT}/postgres/backups

# Shared
SHARED_LOGS_PATH=\${EXTERNAL_STORAGE_ROOT}/shared/logs
SHARED_TEMP_PATH=\${EXTERNAL_STORAGE_ROOT}/shared/temp
SHARED_EXPORTS_PATH=\${EXTERNAL_STORAGE_ROOT}/shared/exports

# Configuración de recursos (ajustable según necesidades)
NEO4J_MEMORY_LIMIT=4G
UMACO_MEMORY_LIMIT=6G
COGNEE_MEMORY_LIMIT=3G
POSTGRES_MEMORY_LIMIT=2G

# Configuración de backup automático
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"  # Diario a las 2 AM
EOF

# Añadir configuración al .env principal
echo -e "${YELLOW}📝 Actualizando .env principal...${NC}"
if [ -f "$PROJECT_DIR/.env" ]; then
    # Crear backup del .env actual
    cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Añadir referencia al archivo de storage
    if ! grep -q "source.*\.env\.storage" "$PROJECT_DIR/.env"; then
        echo "" >> "$PROJECT_DIR/.env"
        echo "# Configuración de almacenamiento externo" >> "$PROJECT_DIR/.env"
        echo "# Las rutas están definidas en .env.storage" >> "$PROJECT_DIR/.env"
        echo "include .env.storage" >> "$PROJECT_DIR/.env"
    fi
else
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado. Creando uno básico...${NC}"
    cp "$PROJECT_DIR/.env.storage" "$PROJECT_DIR/.env"
fi

# Crear script de monitoreo de espacio
echo -e "${YELLOW}📊 Creando script de monitoreo...${NC}"
cat > "$KOGNITO_DATA/monitor_storage.sh" << 'EOF'
#!/bin/bash
# Script de monitoreo de almacenamiento

STORAGE_PATH="/media/gato/Almacenamiento/kognito-ai"

echo "📊 Estado del almacenamiento KognitoAI"
echo "======================================="
echo ""

# Espacio total del disco
echo "💾 Espacio en disco:"
df -h /media/gato/Almacenamiento | tail -1

echo ""
echo "📁 Uso por componente:"

# Función para mostrar tamaño de directorio
show_size() {
    if [ -d "$1" ]; then
        SIZE=$(du -sh "$1" 2>/dev/null | cut -f1)
        echo "  $2: $SIZE"
    else
        echo "  $2: No existe"
    fi
}

show_size "$STORAGE_PATH/neo4j" "Neo4j"
show_size "$STORAGE_PATH/umaco" "UMACO"
show_size "$STORAGE_PATH/cognee" "Cognee"
show_size "$STORAGE_PATH/postgres" "PostgreSQL"
show_size "$STORAGE_PATH/shared" "Compartido"

echo ""
echo "🔍 Top 10 archivos más grandes:"
find "$STORAGE_PATH" -type f -exec du -h {} + 2>/dev/null | sort -rh | head -10

echo ""
echo "⚠️  Alertas:"
USAGE=$(df /media/gato/Almacenamiento | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -gt 90 ]; then
    echo "  🔴 CRÍTICO: Uso del disco > 90%"
elif [ "$USAGE" -gt 80 ]; then
    echo "  🟡 ADVERTENCIA: Uso del disco > 80%"
else
    echo "  🟢 OK: Uso del disco normal ($USAGE%)"
fi
EOF

chmod +x "$KOGNITO_DATA/monitor_storage.sh"

# Crear script de limpieza
echo -e "${YELLOW}🧹 Creando script de limpieza...${NC}"
cat > "$KOGNITO_DATA/cleanup_storage.sh" << 'EOF'
#!/bin/bash
# Script de limpieza de almacenamiento

STORAGE_PATH="/media/gato/Almacenamiento/kognito-ai"

echo "🧹 Limpieza de almacenamiento KognitoAI"
echo "======================================"

# Limpiar logs antiguos (más de 30 días)
echo "📝 Limpiando logs antiguos..."
find "$STORAGE_PATH" -name "*.log" -type f -mtime +30 -delete 2>/dev/null
find "$STORAGE_PATH/shared/logs" -type f -mtime +30 -delete 2>/dev/null

# Limpiar cache temporal
echo "🗑️  Limpiando cache temporal..."
find "$STORAGE_PATH/shared/temp" -type f -mtime +7 -delete 2>/dev/null
find "$STORAGE_PATH/umaco/cache" -type f -mtime +7 -delete 2>/dev/null

# Limpiar backups antiguos (más de 30 días)
echo "💾 Limpiando backups antiguos..."
find "$STORAGE_PATH/neo4j/backups" -type f -mtime +30 -delete 2>/dev/null
find "$STORAGE_PATH/postgres/backups" -type f -mtime +30 -delete 2>/dev/null

echo "✅ Limpieza completada"
EOF

chmod +x "$KOGNITO_DATA/cleanup_storage.sh"

# Mostrar resumen
echo ""
echo -e "${GREEN}✅ Configuración completada exitosamente!${NC}"
echo ""
echo -e "${BLUE}📍 Ubicaciones importantes:${NC}"
echo "  • Almacenamiento principal: $KOGNITO_DATA"
echo "  • Enlace rápido: ~/kognito-storage"
echo "  • Enlace en proyecto: $PROJECT_DIR/external-storage"
echo "  • Configuración: $PROJECT_DIR/.env.storage"
echo ""
echo -e "${BLUE}🛠️  Scripts útiles:${NC}"
echo "  • Monitoreo: $KOGNITO_DATA/monitor_storage.sh"
echo "  • Limpieza: $KOGNITO_DATA/cleanup_storage.sh"
echo ""
echo -e "${BLUE}📊 Espacio asignado por componente:${NC}"
echo "  • Neo4j: ~30GB (datos + logs + backups)"
echo "  • UMACO: ~35GB (modelos + datos + cache)"
echo "  • Cognee: ~15GB (embeddings + grafos)"
echo "  • PostgreSQL: ~8GB (datos + backups)"
echo "  • Compartido: ~10GB (logs + temp + exports)"
echo "  • Total estimado: ~100GB"
echo ""
echo -e "${YELLOW}🔄 Próximos pasos:${NC}"
echo "1. Revisar y ajustar docker-compose.yml para usar las nuevas rutas"
echo "2. Ejecutar: docker compose down && docker compose up -d"
echo "3. Verificar que los servicios funcionen correctamente"
echo "4. Ejecutar: $KOGNITO_DATA/monitor_storage.sh"
echo ""
echo -e "${GREEN}🎉 ¡Listo para usar UMACO con almacenamiento optimizado!${NC}"
EOF
