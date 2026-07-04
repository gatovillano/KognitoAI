#!/usr/bin/env bash

# Kognito AI - Full Commercial Installation Script (For New Users)
# Auto-clones repo, generates secure secrets, builds frontend, starts containers, and launches stack.

set -e

INSTALL_DIR="${HOME}/.kognito"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# 0. Resolve PROJECT_DIR (clone from GitHub or use local checkout)
REPO_URL="https://github.com/gatovillano/KognitoAI.git"
BASE_TARGET_DIR="${HOME}/KognitoAI"

_clone_fresh() {
    local dest="$1"
    echo -e "${YELLOW}🌐 Clonando Kognito AI (rama: ${BOLD}main${NC}${YELLOW}) en ${dest}...${NC}"
    git clone -b main "${REPO_URL}" "${dest}"
}

if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/run_api.py" ]; then
    # Running from inside an existing checkout — use it directly
    PROJECT_DIR="${SCRIPT_DIR}"
elif [ -d "${BASE_TARGET_DIR}" ]; then
    # ~/KognitoAI already exists — ask the user
    echo -e "${YELLOW}⚠️  El directorio ${BOLD}${BASE_TARGET_DIR}${NC}${YELLOW} ya existe.${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Actualizar instalación existente (git pull)"
    echo -e "  ${BLUE}2)${NC} Crear nueva instancia paralela (${BASE_TARGET_DIR}_1, _2…)"
    echo -e "  ${RED}3)${NC} Abortar"
    echo ""
    printf "  Selecciona una opción [1-3]: "
    read -r CLONE_CHOICE

    case "${CLONE_CHOICE}" in
        1)
            PROJECT_DIR="${BASE_TARGET_DIR}"
            echo -e "${YELLOW}🔄 Actualizando repositorio existente...${NC}"
            git -C "${PROJECT_DIR}" pull
            ;;
        2)
            COUNT=1
            while [ -d "${BASE_TARGET_DIR}_${COUNT}" ]; do ((COUNT++)); done
            PROJECT_DIR="${BASE_TARGET_DIR}_${COUNT}"
            _clone_fresh "${PROJECT_DIR}"
            ;;
        *)
            echo "Instalación abortada."
            exit 1
            ;;
    esac
else
    # Fresh install — clone into ~/KognitoAI
    _clone_fresh "${BASE_TARGET_DIR}"
    PROJECT_DIR="${BASE_TARGET_DIR}"
fi

cd "${PROJECT_DIR}"

# Persist the resolved repo path so the kognitoai CLI can find it on any machine
mkdir -p "${HOME}/.kognito/config"
_KOGNITO_ENV="${HOME}/.kognito/config/.env"
if [ -f "${_KOGNITO_ENV}" ] && grep -q '^KOGNITO_REPO_DIR=' "${_KOGNITO_ENV}"; then
    sed -i "s|^KOGNITO_REPO_DIR=.*|KOGNITO_REPO_DIR=${PROJECT_DIR}|" "${_KOGNITO_ENV}"
else
    echo "KOGNITO_REPO_DIR=${PROJECT_DIR}" >> "${_KOGNITO_ENV}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  🚀 Kognito AI — Instalación Completa (Nuevo Usuario)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Directorio de datos: ${INSTALL_DIR}"
echo -e "  Repositorio:         ${PROJECT_DIR}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 1. Create directory structure
echo -e "${BLUE}📁 1. Creando estructura de directorios en ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}/config" "${INSTALL_DIR}/skills" \
         "${INSTALL_DIR}/media/documents" "${INSTALL_DIR}/media/thumbnails" \
         "${INSTALL_DIR}/storage/onlyoffice/documents" "${INSTALL_DIR}/secrets"
chmod 700 "${INSTALL_DIR}/secrets"

# 2. Generate .env with secure auto-generated secrets (only if not already exists)
ENV_FILE="${INSTALL_DIR}/config/.env"
if [ -f "${ENV_FILE}" ]; then
    echo -e "${YELLOW}ℹ️  Configuración existente encontrada. Preservando.${NC}"
else
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🔑 2. Configuración inicial${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}💡 Los secrets de seguridad se generan automáticamente.${NC}"
    echo -e "${YELLOW}   Solo necesitas ingresar tu token de Telegram (opcional).${NC}"
    echo ""
    printf "  🤖 Token del Bot de Telegram [dejar vacío para configurar luego]: "
    read -r TG_TOKEN

    # Auto-generate all secure secrets
    echo -e "\n${BLUE}🔐 Generando secrets seguros automáticamente...${NC}"
    JWT_SECRET=$(openssl rand -hex 32)
    DB_ENC_KEY=$(openssl rand -hex 32)
    INTERNAL_API_KEY=$(openssl rand -hex 24)
    ADMIN_SECRET=$(openssl rand -hex 16)

    # Auto-generate PostgreSQL credentials
    PG_USER="kognito"
    PG_PASSWORD=$(openssl rand -hex 20)
    PG_DB="kognito_db"

    cat <<EOF > "${ENV_FILE}"
# Kognito AI Environment Configuration
# Generated automatically on $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Paths ───────────────────────────────────────────────────
KOGNITO_HOME=${INSTALL_DIR}
KOGNITO_USER_SKILLS_DIR=${INSTALL_DIR}/skills
MEDIA_ROOT=${INSTALL_DIR}/media/documents
THUMBNAILS_ROOT=${INSTALL_DIR}/media/thumbnails
ONLYOFFICE_DOCS_ROOT=${INSTALL_DIR}/storage/onlyoffice/documents
KOGNITO_SECRETS_DIR=${INSTALL_DIR}/secrets

# ── Database (PostgreSQL) ────────────────────────────
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASSWORD}
POSTGRES_DB=${PG_DB}
DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASSWORD}@localhost:5432/${PG_DB}

# ── Security (auto-generated) ────────────────────────
JWT_SECRET_KEY=${JWT_SECRET}
DB_ENCRYPTION_KEY=${DB_ENC_KEY}
INTERNAL_API_KEY_FOR_BOT=${INTERNAL_API_KEY}
ADMIN_SECRET=${ADMIN_SECRET}

# ── Telegram ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=${TG_TOKEN}
EOF
    chmod 600 "${ENV_FILE}"

    # Write project-level .env for docker-compose
    DOCKER_ENV_FILE="${PROJECT_DIR}/.env"
    cat <<EOF > "${DOCKER_ENV_FILE}"
# Auto-generated by Kognito AI installer - $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Used by docker-compose to configure PostgreSQL container
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASSWORD}
POSTGRES_DB=${PG_DB}
EOF
    chmod 600 "${DOCKER_ENV_FILE}"

    echo -e "${GREEN}✅ Configuración generada de forma segura en ${ENV_FILE}${NC}"
    echo -e "   ${YELLOW}JWT, DB encryption key, PG credentials, internal keys → generados automáticamente.${NC}"
fi

# 3. Docker containers
echo -e "\n${BLUE}🐳 3. Verificando contenedores Docker...${NC}"
if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^kognito_db$"; then
    echo -e "${GREEN}✅ Contenedores ya en ejecución.${NC}"
elif command -v docker &>/dev/null && docker compose version &>/dev/null; then
    docker compose up -d
elif command -v docker-compose &>/dev/null; then
    docker-compose up -d
else
    echo -e "${RED}⚠️  Docker no encontrado.${NC}"
fi

# 4. Python virtual environment
echo -e "\n${BLUE}🐍 4. Entorno virtual Python...${NC}"
if [ ! -d "${PROJECT_DIR}/venv_host" ]; then
    python3 -m venv "${PROJECT_DIR}/venv_host"
    "${PROJECT_DIR}/venv_host/bin/pip" install --upgrade pip --quiet
    [ -f "${PROJECT_DIR}/requirements.txt" ] && \
        "${PROJECT_DIR}/venv_host/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" --quiet
    echo -e "${GREEN}✅ Dependencias Python instaladas.${NC}"
else
    echo -e "${GREEN}✅ Entorno virtual Python ya existe.${NC}"
fi

# 5. Node modules + Production Frontend Build
echo -e "\n${BLUE}📦 5. Instalando dependencias Node...${NC}"
(cd "${PROJECT_DIR}" && npm install --silent)
echo -e "${YELLOW}🏗️  Construyendo Frontend para producción (npm run build)...${NC}"
(cd "${PROJECT_DIR}" && npm run build)
echo -e "${GREEN}✅ Frontend construido exitosamente.${NC}"

# 6. Install global kognitoai CLI
CLI_TARGET="${HOME}/.local/bin/kognitoai"
mkdir -p "${HOME}/.local/bin"
cp "${PROJECT_DIR}/kognitoai" "${CLI_TARGET}"
chmod +x "${CLI_TARGET}"
echo -e "${GREEN}✅ Comando 'kognitoai' disponible en ${CLI_TARGET}${NC}"
if ! echo "$PATH" | grep -q "${HOME}/.local/bin"; then
    echo -e "${YELLOW}💡 Añade ~/.local/bin a tu PATH para usar 'kognitoai' globalmente:${NC}"
    echo -e "   ${BOLD}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✅ Instalación completa!${NC}"
echo -e "${YELLOW}🚀 Iniciando Kognito AI...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e " Al iniciar, abre en tu navegador:"
echo -e "   ${GREEN}${BOLD}http://localhost:3002${NC}  → Interfaz Web"
echo -e " El asistente de configuración inicial se abrirá automáticamente."
echo ""

# 7. Launch full stack
exec ./start_local.sh
