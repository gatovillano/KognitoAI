#!/usr/bin/env bash

# Kognito AI - Interactive Management & Setup Script
# Run directly: bash setup.sh
# Or via curl: curl -sSL https://raw.githubusercontent.com/gatovillano/KognitoAI/main/setup.sh | bash

INSTALL_DIR="${HOME}/.kognito"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/gatovillano/KognitoAI.git"
TARGET_REPO_DIR="${HOME}/KognitoAI"

# Determine PROJECT_DIR (local repo or auto-clone)
if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/run_api.py" ]; then
    PROJECT_DIR="${SCRIPT_DIR}"
elif [ -f "./run_api.py" ]; then
    PROJECT_DIR="$(pwd)"
else
    if [ ! -d "${TARGET_REPO_DIR}" ]; then
        echo -e "${YELLOW}🌐 Clonando Kognito AI desde GitHub en ${TARGET_REPO_DIR}...${NC}"
        git clone "${REPO_URL}" "${TARGET_REPO_DIR}"
    else
        echo -e "${YELLOW}ℹ️ Repositorio encontrado en ${TARGET_REPO_DIR}.${NC}"
    fi
    PROJECT_DIR="${TARGET_REPO_DIR}"
fi

cd "${PROJECT_DIR}"

# ── Helpers ──────────────────────────────────────────────────────────────────

run_setup() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}⚙️  Configurando entorno de usuario en ${INSTALL_DIR}...${NC}"

    mkdir -p "${INSTALL_DIR}/config" "${INSTALL_DIR}/skills" \
             "${INSTALL_DIR}/media/documents" "${INSTALL_DIR}/media/thumbnails" \
             "${INSTALL_DIR}/storage/onlyoffice/documents" "${INSTALL_DIR}/secrets"

    ENV_FILE="${INSTALL_DIR}/config/.env"
    if [ ! -f "${ENV_FILE}" ]; then
        cat <<EOF > "${ENV_FILE}"
# Kognito AI Environment Configuration
KOGNITO_HOME=${INSTALL_DIR}
KOGNITO_USER_SKILLS_DIR=${INSTALL_DIR}/skills
MEDIA_ROOT=${INSTALL_DIR}/media/documents
THUMBNAILS_ROOT=${INSTALL_DIR}/media/thumbnails
ONLYOFFICE_DOCS_ROOT=${INSTALL_DIR}/storage/onlyoffice/documents
KOGNITO_SECRETS_DIR=${INSTALL_DIR}/secrets
DATABASE_URL=sqlite+aiosqlite:///${INSTALL_DIR}/kognito_db.sqlite
EOF
        echo -e "${GREEN}✅ Configuración generada en ${ENV_FILE}.${NC}"
    else
        echo -e "${YELLOW}ℹ️  Configuración existente conservada.${NC}"
    fi

    # Migrate user data from repo if present
    if [ -d "${PROJECT_DIR}/skills" ]; then
        find "${PROJECT_DIR}/skills" -maxdepth 1 -type d -name "user_*" | while read -r d; do
            echo -e "   -> Migrando skill: $(basename "$d")"
            cp -rn "$d" "${INSTALL_DIR}/skills/" 2>/dev/null || true
        done
    fi
    for src in "media/documents" "media/thumbnails" "storage/onlyoffice/documents"; do
        if [ -d "${PROJECT_DIR}/${src}" ] && [ "$(ls -A "${PROJECT_DIR}/${src}" 2>/dev/null)" ]; then
            cp -rn "${PROJECT_DIR}/${src}/"* "${INSTALL_DIR}/${src}/" 2>/dev/null || true
        fi
    done

    # Python venv
    if [ ! -d "${PROJECT_DIR}/venv_host" ]; then
        echo -e "${YELLOW}🐍 Creando entorno virtual Python...${NC}"
        python3 -m venv "${PROJECT_DIR}/venv_host"
        "${PROJECT_DIR}/venv_host/bin/pip" install --upgrade pip --quiet
        [ -f "${PROJECT_DIR}/requirements.txt" ] && \
            "${PROJECT_DIR}/venv_host/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" --quiet
        echo -e "${GREEN}✅ Dependencias Python instaladas.${NC}"
    fi

    # Node modules
    if [ ! -d "${PROJECT_DIR}/node_modules" ]; then
        echo -e "${YELLOW}📦 Instalando paquetes Node...${NC}"
        (cd "${PROJECT_DIR}" && npm install --silent)
        echo -e "${GREEN}✅ Dependencias Node instaladas.${NC}"
    fi

    # Install global kognitoai CLI
    CLI_TARGET="${HOME}/.local/bin/kognitoai"
    mkdir -p "${HOME}/.local/bin"
    cp "${PROJECT_DIR}/kognitoai" "${CLI_TARGET}"
    chmod +x "${CLI_TARGET}"
    echo -e "${GREEN}✅ Comando 'kognitoai' instalado en ${CLI_TARGET}${NC}"
    if ! echo "$PATH" | grep -q "${HOME}/.local/bin"; then
        echo -e "${YELLOW}💡 Añade ~/.local/bin a tu PATH:${NC}"
        echo -e "   ${BOLD}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${NC}"
    fi
}

run_update() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🔄 Actualizando Kognito AI desde GitHub...${NC}"
    git pull origin main
    "${PROJECT_DIR}/venv_host/bin/pip" install -r requirements.txt --quiet 2>/dev/null || true
    npm install --silent
    # Re-install CLI in case it changed
    cp "${PROJECT_DIR}/kognitoai" "${HOME}/.local/bin/kognitoai"
    chmod +x "${HOME}/.local/bin/kognitoai"
    echo -e "${GREEN}✅ Actualización completada.${NC}"
}

check_and_start_docker() {
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^kognito_db$"; then
        echo -e "${GREEN}✅ Contenedores ya en ejecución. Omitiendo Docker.${NC}"
    elif command -v docker &>/dev/null && docker compose version &>/dev/null; then
        echo -e "${YELLOW}🐳 Iniciando contenedores Docker...${NC}"
        docker compose up -d
    elif command -v docker-compose &>/dev/null; then
        docker-compose up -d
    else
        echo -e "${RED}⚠️  Docker no encontrado.${NC}"
    fi
}

# ── Menu ─────────────────────────────────────────────────────────────────────

# Allow non-interactive direct command: bash setup.sh setup|update|start
NONINTERACTIVE_CMD="${1:-}"

if [ -n "${NONINTERACTIVE_CMD}" ]; then
    case "${NONINTERACTIVE_CMD}" in
        setup)   run_setup; check_and_start_docker; exec ./start_local.sh ;;
        update)  run_update; check_and_start_docker; exec ./start_local.sh ;;
        start)   check_and_start_docker; exec ./start_local.sh ;;
        *)       echo "Uso: bash setup.sh [setup|update|start]"; exit 1 ;;
    esac
fi

# Interactive mode
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  🚀 Kognito AI — Gestión del Sistema${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}1)${NC} Iniciar Kognito AI"
echo -e "  ${YELLOW}2)${NC} 🔄 Actualizar software (descarga últimos cambios)"
echo -e "  ${BLUE}3)${NC} ⚙️  Re-configurar entorno (~/.kognito)"
echo -e "  ${RED}4)${NC} ❌ Salir"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "  Selecciona una opción [1-4]: "
read -r OPTION

case "${OPTION}" in
    1)
        check_and_start_docker
        exec ./start_local.sh
        ;;
    2)
        run_update
        check_and_start_docker
        exec ./start_local.sh
        ;;
    3)
        run_setup
        check_and_start_docker
        exec ./start_local.sh
        ;;
    4)
        echo "Saliendo."
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Opción no reconocida. Iniciando por defecto...${NC}"
        check_and_start_docker
        exec ./start_local.sh
        ;;
esac
