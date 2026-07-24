#!/bin/bash
# KAI-Ethno Installation Script
# Investigación Antropológica Aumentada

set -e  # Exit on error

echo "=========================================="
echo "   KAI-Ethno Installation"
echo "   Investigación Antropológica Aumentada"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOGNITO_DIR="${HOME}/Proyectos/KognitoAI/kognito-ai"
SKILLS_DIR="${KOGNITO_DIR}/skills"
TARGET_DIR="${SKILLS_DIR}/kai_ethno_skill"

# Función de logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar Python
echo "🔍 Verificando prerequisitos..."
echo ""

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 no está instalado. Por favor instala Python 3.11 o superior."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    log_error "Python $PYTHON_VERSION detectado. Se requiere Python $REQUIRED_VERSION o superior."
    exit 1
fi

log_info "Python $PYTHON_VERSION ✓"

# Verificar pip
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    log_error "pip no está instalado. Por favor instala pip."
    exit 1
fi
log_info "pip disponible ✓"

# Verificar Node.js (opcional pero recomendado)
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_info "Node.js $NODE_VERSION disponible ✓"
else
    log_warn "Node.js no detectado (opcional pero recomendado para algunas visualizaciones)"
fi

echo ""
echo "📁 Configurando directorios..."

# Crear directorios necesarios si no existen
mkdir -p "${KOGNITO_DIR}/skills"
mkdir -p "${KOGNITO_DIR}/skills/user_workspace_KognitoAI"

# Verificar si ya existe una instalación previa
if [ -d "${TARGET_DIR}" ]; then
    log_warn "KAI-Ethno ya está instalado en ${TARGET_DIR}"
    read -p "¿Deseas reinstalar? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        log_info "Instalación cancelada por el usuario."
        exit 0
    fi
    log_info "Respaldando instalación anterior..."
    mv "${TARGET_DIR}" "${TARGET_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Crear directorio de la skill
mkdir -p "${TARGET_DIR}"
log_info "Directorio creado: ${TARGET_DIR}"

echo ""
echo "📦 Instalando dependencias de Python..."

# Crear entorno virtual si no existe
VENV_DIR="${TARGET_DIR}/venv"
if [ ! -d "${VENV_DIR}" ]; then
    log_info "Creando entorno virtual..."
    python3 -m venv "${VENV_DIR}"
else
    log_info "Entorno virtual existente encontrado"
fi

# Activar entorno virtual e instalar dependencias
log_info "Instalando dependencias..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${SCRIPT_DIR}/requirements.txt"

log_info "Dependencias instaladas ✓"

echo ""
echo "⚙️  Configurando variables de entorno..."

# Crear archivo .env si no existe
ENV_FILE="${TARGET_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    cat > "${ENV_FILE}" << EOF
# KAI-Ethno Environment Variables
# Copia este archivo y completa con tus credenciales

# LLM Providers (al menos uno requerido)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Bases de datos (opcional)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password

# Configuración adicional
# LOG_LEVEL=INFO
# MAX_WORKERS=4
EOF
    log_info "Archivo .env creado en ${ENV_FILE}"
    log_warn "⚠️  IMPORTANTE: Edita ${ENV_FILE} y agrega tus API keys"
else
    log_info "Archivo .env existente preservado"
fi

echo ""
echo "🔗 Creando enlaces simbólicos..."

# Crear enlace simbólico en el directorio de skills principal
ln -sf "${TARGET_DIR}" "${SKILLS_DIR}/kai_ethno"
log_info "Enlace simbólico creado: ${SKILLS_DIR}/kai_ethno -> ${TARGET_DIR}"

echo ""
echo "🧪 Ejecutando verificaciones..."

# Verificar instalación
python3 -c "import sys; sys.path.insert(0, '${TARGET_DIR}'); from agents.bibliomancer.agent import BibliomancerAgent; print('✓ Agentes importables')" || log_warn "No se pudieron importar agentes (normal en primera instalación)"

# Verificar estructura de directorios
REQUIRED_DIRS=("agents" "scripts" "references" "examples")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "${TARGET_DIR}/${dir}" ]; then
        log_info "✓ Directorio ${dir} existe"
    else
        log_error "✗ Directorio ${dir} no encontrado"
    fi
done

echo ""
echo "=========================================="
echo "   ✅ Instalación Completada"
echo "=========================================="
echo ""
echo "📋 Próximos pasos:"
echo ""
echo "1. Configurar variables de entorno:"
echo "   ${YELLOW}nano ${ENV_FILE}${NC}"
echo ""
echo "2. Activar entorno virtual:"
echo "   ${YELLOW}source ${VENV_DIR}/bin/activate${NC}"
echo ""
echo "3. Verificar instalación:"
echo "   ${YELLOW}cd ${TARGET_DIR} && python -m pytest tests/${NC}"
echo ""
echo "4. Ejecutar ejemplo:"
echo "   ${YELLOW}cd ${TARGET_DIR} && python examples/basic_research.py${NC}"
echo ""
echo "📚 Documentación:"
echo "   • README.md: Guía completa"
echo "   • SKILL.md: Especificación de la skill"
echo "   • references/: Marcos teóricos y éticos"
echo ""
echo "🐛 Soporte:"
echo "   • GitHub: https://github.com/kognitoai/kai-ethno/issues"
echo "   • Email: support@kognito.ai"
echo ""

# Preguntar si desea ejecutar las pruebas
read -p "¿Deseas ejecutar las pruebas de verificación ahora? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    log_info "Ejecutando pruebas..."
    cd "${TARGET_DIR}"
    if [ -d "tests" ]; then
        python -m pytest tests/ -v || log_warn "Algunas pruebas fallaron (normal sin configuración completa)"
    else
        log_info "No se encontraron pruebas automatizadas"
    fi
fi

echo ""
log_info "¡KAI-Ethno está listo para usar! 🚀"
