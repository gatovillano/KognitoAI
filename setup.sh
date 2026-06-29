#!/usr/bin/env bash

# Kognito AI - External Setup & Migration Script (For Existing Users)
# Auto-clones repo if executed remotely, migrates user data to ~/.kognito, starts containers, and launches stack.

set -e

INSTALL_DIR="${HOME}/.kognito"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=====================================================${NC}"
echo -e "${GREEN}       🚀 Kognito AI - Auto-Clone & Setup            ${NC}"
echo -e "${BLUE}=====================================================${NC}"

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
        echo -e "${YELLOW}ℹ️ Directory ${TARGET_REPO_DIR} already exists. Updating via git pull...${NC}"
        (cd "${TARGET_REPO_DIR}" && git pull origin main || true)
    fi
    PROJECT_DIR="${TARGET_REPO_DIR}"
fi

cd "${PROJECT_DIR}"

echo -e "Target User Home: ${INSTALL_DIR}"
echo -e "Repository Dir:   ${PROJECT_DIR}"
echo -e "${BLUE}-----------------------------------------------------${NC}"

# 1. Create directory structure
echo -e "${BLUE}📁 1. Creating isolated directory structure in ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}/config"
mkdir -p "${INSTALL_DIR}/skills"
mkdir -p "${INSTALL_DIR}/media/documents"
mkdir -p "${INSTALL_DIR}/media/thumbnails"
mkdir -p "${INSTALL_DIR}/storage/onlyoffice/documents"
mkdir -p "${INSTALL_DIR}/secrets"

# 2. Create default .env in ~/.kognito/config/.env if not present
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

# 3. Migrate existing user content from repo if present
echo -e "${BLUE}🚚 3. Checking for existing user data in repository to migrate...${NC}"

# Migrate user skills
if [ -d "${PROJECT_DIR}/skills" ]; then
    find "${PROJECT_DIR}/skills" -maxdepth 1 -type d -name "user_*" | while read -r user_skill_dir; do
        folder_name=$(basename "${user_skill_dir}")
        echo -e "   -> Migrating user skill: ${folder_name}"
        cp -rn "${user_skill_dir}" "${INSTALL_DIR}/skills/"
    done
fi

# Migrate media files
if [ -d "${PROJECT_DIR}/media/documents" ] && [ "$(ls -A "${PROJECT_DIR}/media/documents" 2>/dev/null)" ]; then
    echo -e "   -> Migrating documents from media/documents..."
    cp -rn "${PROJECT_DIR}/media/documents/"* "${INSTALL_DIR}/media/documents/" 2>/dev/null || true
fi

if [ -d "${PROJECT_DIR}/media/thumbnails" ] && [ "$(ls -A "${PROJECT_DIR}/media/thumbnails" 2>/dev/null)" ]; then
    echo -e "   -> Migrating thumbnails from media/thumbnails..."
    cp -rn "${PROJECT_DIR}/media/thumbnails/"* "${INSTALL_DIR}/media/thumbnails/" 2>/dev/null || true
fi

# Migrate onlyoffice docs
if [ -d "${PROJECT_DIR}/storage/onlyoffice/documents" ] && [ "$(ls -A "${PROJECT_DIR}/storage/onlyoffice/documents" 2>/dev/null)" ]; then
    echo -e "   -> Migrating OnlyOffice documents..."
    cp -rn "${PROJECT_DIR}/storage/onlyoffice/documents/"* "${INSTALL_DIR}/storage/onlyoffice/documents/" 2>/dev/null || true
fi

# 4. Check and Start Docker Containers (Postgres, Neo4j, Redis, Kokoro TTS)
echo -e "${BLUE}🐳 4. Starting database & AI backend containers (Docker)...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose up -d db neo4j redis kokoro-tts
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose up -d db neo4j redis kokoro-tts
else
    echo -e "${RED}⚠️  Docker or Docker Compose not found. Please ensure Docker is running.${NC}"
fi

# 5. Check/Install Python Dependencies in Virtual environment
echo -e "${BLUE}🐍 5. Checking Python virtual environment...${NC}"
if [ ! -d "${PROJECT_DIR}/venv_host" ]; then
    echo -e "${YELLOW}Creating Python virtual environment in venv_host...${NC}"
    python3 -m venv "${PROJECT_DIR}/venv_host"
    "${PROJECT_DIR}/venv_host/bin/pip" install --upgrade pip
    if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        "${PROJECT_DIR}/venv_host/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
    fi
fi

# 6. Check/Install Frontend Node Modules
echo -e "${BLUE}📦 6. Checking Frontend dependencies...${NC}"
if [ ! -d "${PROJECT_DIR}/node_modules" ]; then
    echo -e "${YELLOW}Installing Node packages (npm install)...${NC}"
    (cd "${PROJECT_DIR}" && npm install)
fi

echo -e "${BLUE}-----------------------------------------------------${NC}"
echo -e "${GREEN}✅ Migration & Environment Setup Complete!${NC}"
echo -e "${YELLOW}🚀 Starting Kognito AI Services (Backend, Frontend & Telegram Gateway)...${NC}"
echo -e "${BLUE}-----------------------------------------------------${NC}"

# 7. Launch full stack services using start_local.sh
exec ./start_local.sh
