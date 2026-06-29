#!/usr/bin/env bash

# Kognito AI - Interactive Management & Setup Script
# Auto-clones repo if executed remotely, handles updates (git pull), environment setup (~/.kognito), and service execution.

set -e

INSTALL_DIR="${HOME}/.kognito"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 0. Check if running inside cloned repo, otherwise clone automatically
REPO_URL="https://github.com/gatovillano/KognitoAI.git"
TARGET_REPO_DIR="${HOME}/KognitoAI"

if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/run_api.py" ]; then
    PROJECT_DIR="${SCRIPT_DIR}"
elif [ -f "./run_api.py" ]; then
    PROJECT_DIR="$(pwd)"
else
    echo -e "${YELLOW}🌐 Repository not detected locally. Cloning from GitHub...${NC}"
    if [ ! -d "${TARGET_REPO_DIR}" ]; then
        git clone "${REPO_URL}" "${TARGET_REPO_DIR}"
    else
        echo -e "${YELLOW}ℹ️ Directory ${TARGET_REPO_DIR} already exists.${NC}"
    fi
    PROJECT_DIR="${TARGET_REPO_DIR}"
fi

cd "${PROJECT_DIR}"

# Function to run full setup and migration
run_setup() {
    echo -e "${BLUE}📁 1. Creating isolated directory structure in ${INSTALL_DIR}...${NC}"
    mkdir -p "${INSTALL_DIR}/config"
    mkdir -p "${INSTALL_DIR}/skills"
    mkdir -p "${INSTALL_DIR}/media/documents"
    mkdir -p "${INSTALL_DIR}/media/thumbnails"
    mkdir -p "${INSTALL_DIR}/storage/onlyoffice/documents"
    mkdir -p "${INSTALL_DIR}/secrets"

    ENV_FILE="${INSTALL_DIR}/config/.env"
    if [ ! -f "${ENV_FILE}" ]; then
        echo -e "${BLUE}⚙️  2. Generating environment configuration at ${ENV_FILE}...${NC}"
        cat <<EOF > "${ENV_FILE}"
# Kognito AI Environment Configuration
KOGNITO_HOME=${INSTALL_DIR}
KOGNITO_USER_SKILLS_DIR=${INSTALL_DIR}/skills
MEDIA_ROOT=${INSTALL_DIR}/media/documents
THUMBNAILS_ROOT=${INSTALL_DIR}/media/thumbnails
ONLYOFFICE_DOCS_ROOT=${INSTALL_DIR}/storage/onlyoffice/documents
KOGNITO_SECRETS_DIR=${INSTALL_DIR}/secrets

# Database configuration
DATABASE_URL=sqlite+aiosqlite:///${INSTALL_DIR}/kognito_db.sqlite
EOF
        echo -e "${GREEN}✅ Configuration file created.${NC}"
    else
        echo -e "${YELLOW}ℹ️  Existing configuration file found at ${ENV_FILE}. Preserving.${NC}"
    fi

    echo -e "${BLUE}🚚 3. Checking for existing user data in repository to migrate...${NC}"
    if [ -d "${PROJECT_DIR}/skills" ]; then
        find "${PROJECT_DIR}/skills" -maxdepth 1 -type d -name "user_*" | while read -r user_skill_dir; do
            folder_name=$(basename "${user_skill_dir}")
            echo -e "   -> Migrating user skill: ${folder_name}"
            cp -rn "${user_skill_dir}" "${INSTALL_DIR}/skills/"
        done
    fi

    if [ -d "${PROJECT_DIR}/media/documents" ] && [ "$(ls -A "${PROJECT_DIR}/media/documents" 2>/dev/null)" ]; then
        echo -e "   -> Migrating documents from media/documents..."
        cp -rn "${PROJECT_DIR}/media/documents/"* "${INSTALL_DIR}/media/documents/" 2>/dev/null || true
    fi

    if [ -d "${PROJECT_DIR}/media/thumbnails" ] && [ "$(ls -A "${PROJECT_DIR}/media/thumbnails" 2>/dev/null)" ]; then
        echo -e "   -> Migrating thumbnails from media/thumbnails..."
        cp -rn "${PROJECT_DIR}/media/thumbnails/"* "${INSTALL_DIR}/media/thumbnails/" 2>/dev/null || true
    fi

    if [ -d "${PROJECT_DIR}/storage/onlyoffice/documents" ] && [ "$(ls -A "${PROJECT_DIR}/storage/onlyoffice/documents" 2>/dev/null)" ]; then
        echo -e "   -> Migrating OnlyOffice documents..."
        cp -rn "${PROJECT_DIR}/storage/onlyoffice/documents/"* "${INSTALL_DIR}/storage/onlyoffice/documents/" 2>/dev/null || true
    fi

    echo -e "${BLUE}🐍 4. Checking Python virtual environment...${NC}"
    if [ ! -d "${PROJECT_DIR}/venv_host" ]; then
        echo -e "${YELLOW}Creating Python virtual environment in venv_host...${NC}"
        python3 -m venv "${PROJECT_DIR}/venv_host"
        "${PROJECT_DIR}/venv_host/bin/pip" install --upgrade pip
        if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
            echo -e "${YELLOW}Installing Python dependencies...${NC}"
            "${PROJECT_DIR}/venv_host/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
        fi
    fi

    echo -e "${BLUE}📦 5. Checking Frontend dependencies...${NC}"
    if [ ! -d "${PROJECT_DIR}/node_modules" ]; then
        echo -e "${YELLOW}Installing Node packages (npm install)...${NC}"
        (cd "${PROJECT_DIR}" && npm install)
    fi
}

# Function to update repository and dependencies
run_update() {
    echo -e "${BLUE}🔄 Actualizando Kognito AI desde GitHub...${NC}"
    git pull origin main
    
    echo -e "${BLUE}🐍 Actualizando dependencias de Python...${NC}"
    if [ -d "${PROJECT_DIR}/venv_host" ]; then
        "${PROJECT_DIR}/venv_host/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
    fi

    echo -e "${BLUE}📦 Actualizando dependencias de Node...${NC}"
    npm install
    
    echo -e "${GREEN}✅ Actualización completada con éxito.${NC}"
}

# Interactive Menu Selection
show_menu() {
    echo ""
    echo -e "${BLUE}=====================================================${NC}"
    echo -e "${GREEN}       🚀 Kognito AI - Menú de Gestión             ${NC}"
    echo -e "${BLUE}=====================================================${NC}"
    echo -e " 1) 🚀 Iniciar Kognito AI (Ejecución normal)"
    echo -e " 2) 🔄 Actualizar Software (Descargar últimos cambios de GitHub)"
    echo -e " 3) ⚙️  Re-configurar / Migrar Entorno (~/.kognito)"
    echo -e " 4) ❌ Salir"
    echo -e "${BLUE}-----------------------------------------------------${NC}"
}

# Determine if running interactively
if [ -t 0 ] || [ -c /dev/tty ]; then
    show_menu
    read -p "Selecciona una opción [1-4]: " OPTION </dev/tty
    case "$OPTION" in
        1)
            echo -e "${GREEN}Iniciando Kognito AI...${NC}"
            exec ./start_local.sh
            ;;
        2)
            run_update
            echo -e "${GREEN}Iniciando Kognito AI tras actualización...${NC}"
            exec ./start_local.sh
            ;;
        3)
            run_setup
            exec ./start_local.sh
            ;;
        4)
            echo "Saliendo."
            exit 0
            ;;
        *)
            echo "Opción no válida. Iniciando por defecto..."
            exec ./start_local.sh
            ;;
    esac
else
    # Non-interactive fallback (e.g. piped execution)
    run_setup
    exec ./start_local.sh
fi
