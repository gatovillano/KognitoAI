#!/usr/bin/env bash

# Kognito AI - Full Commercial Installation & Launcher Script
# Clones/Prepares dependencies, initializes ~/.kognito, starts database containers, and launches full application stack.

set -e

INSTALL_DIR="${HOME}/.kognito"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=====================================================${NC}"
echo -e "${GREEN}       🚀 Kognito AI - Full Software Installer       ${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo -e "Target User Home: ${INSTALL_DIR}"
echo -e "Project Base Dir: ${PROJECT_DIR}"
echo -e "${BLUE}-----------------------------------------------------${NC}"

# 1. Create directory structure for isolated execution
echo -e "${BLUE}📁 1. Initializing isolated user workspace at ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}/config"
mkdir -p "${INSTALL_DIR}/skills"
mkdir -p "${INSTALL_DIR}/media/documents"
mkdir -p "${INSTALL_DIR}/media/thumbnails"
mkdir -p "${INSTALL_DIR}/storage/onlyoffice/documents"
mkdir -p "${INSTALL_DIR}/secrets"

# 2. Generate clean configuration file
ENV_FILE="${INSTALL_DIR}/config/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${BLUE}⚙️  2. Generating user configuration at ${ENV_FILE}...${NC}"
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
    echo -e "${GREEN}✅ Configuration created.${NC}"
else
    echo -e "${YELLOW}ℹ️  Configuration already exists at ${ENV_FILE}. Preserving.${NC}"
fi

# 3. Check and Start Docker Containers (Postgres, Neo4j, Redis, Kokoro TTS)
echo -e "${BLUE}🐳 3. Starting database & AI backend containers (Docker)...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose up -d db neo4j redis kokoro-tts
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose up -d db neo4j redis kokoro-tts
else
    echo -e "${RED}⚠️  Docker or Docker Compose not found. Please ensure Docker is running.${NC}"
fi

# 4. Check/Install Python Dependencies in Virtual environment
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

# 5. Check/Install Frontend Node Modules
echo -e "${BLUE}📦 5. Checking Frontend dependencies...${NC}"
if [ ! -d "${PROJECT_DIR}/node_modules" ]; then
    echo -e "${YELLOW}Installing Node packages (npm install)...${NC}"
    (cd "${PROJECT_DIR}" && npm install)
fi

echo -e "${BLUE}-----------------------------------------------------${NC}"
echo -e "${GREEN}✅ Full Installation & Environment Setup Complete!${NC}"
echo -e "${YELLOW}🚀 Starting Kognito AI Services (Backend, Frontend & Telegram Gateway)...${NC}"
echo -e "${BLUE}-----------------------------------------------------${NC}"

# 6. Launch full stack services using start_local.sh
cd "${PROJECT_DIR}"
exec ./start_local.sh
