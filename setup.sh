#!/usr/bin/env bash

# Kognito AI - Interactive Management & Setup Script
# Run directly: bash setup.sh
# Or via curl: curl -sSL https://raw.githubusercontent.com/gatovillano/KognitoAI/main/setup.sh | bash

INSTALL_DIR="${HOME}/.kognito"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/gatovillano/KognitoAI.git"
BASE_TARGET_DIR="${HOME}/KognitoAI"

# ── Resolve PROJECT_DIR ───────────────────────────────────────────────────────
# Priority:
#   1. Already running from inside a local checkout  → use it directly.
#   2. ~/KognitoAI exists                           → ask what to do.
#   3. ~/KognitoAI does NOT exist                   → fresh clone from GitHub.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/run_api.py" ]; then
    # Case 1: Running directly from an existing checkout
    PROJECT_DIR="${SCRIPT_DIR}"

elif [ -d "${BASE_TARGET_DIR}" ]; then
    # Case 2: ~/KognitoAI already exists — ask the user
    echo -e "${YELLOW}⚠️  El directorio ${BOLD}${BASE_TARGET_DIR}${NC}${YELLOW} ya existe.${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Usar la instalación existente (actualizar con git pull)"
    echo -e "  ${BLUE}2)${NC} Crear una nueva instancia paralela (se clonará en ${BASE_TARGET_DIR}_1, _2 …)"
    echo -e "  ${RED}3)${NC} Abortar"
    echo ""
    printf "  Selecciona una opción [1-3]: "
    read -r CLONE_CHOICE

    case "${CLONE_CHOICE}" in
        1)
             PROJECT_DIR="${BASE_TARGET_DIR}"
             echo -e "${YELLOW}🔄 Actualizando repositorio existente...${NC}"
             git -C "${PROJECT_DIR}" checkout -- package-lock.json 2>/dev/null || true
             git -C "${PROJECT_DIR}" pull
            ;;
        2)
            COUNT=1
            while [ -d "${BASE_TARGET_DIR}_${COUNT}" ]; do ((COUNT++)); done
            PROJECT_DIR="${BASE_TARGET_DIR}_${COUNT}"
            echo -e "${YELLOW}🌐 Clonando Kognito AI (rama: ${BOLD}main${NC}${YELLOW}) en ${PROJECT_DIR}...${NC}"
            git clone -b main "${REPO_URL}" "${PROJECT_DIR}"
            ;;
        *)
            echo "Abortando."
            exit 1
            ;;
    esac

else
    # Case 3: Fresh install — clone directly into ~/KognitoAI
    echo -e "${YELLOW}🌐 Clonando Kognito AI (rama: ${BOLD}main${NC}${YELLOW}) en ${BASE_TARGET_DIR}...${NC}"
    git clone -b main "${REPO_URL}" "${BASE_TARGET_DIR}"
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


run_setup() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}⚙️  Configurando entorno de usuario en ${INSTALL_DIR}...${NC}"

    mkdir -p "${INSTALL_DIR}/config" "${INSTALL_DIR}/skills" \
             "${INSTALL_DIR}/media/documents" "${INSTALL_DIR}/media/thumbnails" \
             "${INSTALL_DIR}/storage/onlyoffice/documents" "${INSTALL_DIR}/secrets"

    ENV_FILE="${INSTALL_DIR}/config/.env"
    if [ ! -f "${ENV_FILE}" ]; then
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}🔑 Configuración Inicial de Variables de Entorno${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}💡 Puedes dejar en blanco las opcionales y configurarlas luego en ~/.kognito/config/.env${NC}"
        echo ""

        printf "  Token del Bot de Telegram (TELEGRAM_BOT_TOKEN) [opcional]: "
        read -r TG_TOKEN

        printf "  URL de la Base de Datos [Enter para SQLite local]: "
        read -r DB_URL
        DB_URL="${DB_URL:-sqlite+aiosqlite:///${INSTALL_DIR}/kognito_db.sqlite}"

        cat <<EOF > "${ENV_FILE}"
# Kognito AI Environment Configuration
KOGNITO_HOME=${INSTALL_DIR}
KOGNITO_USER_SKILLS_DIR=${INSTALL_DIR}/skills
MEDIA_ROOT=${INSTALL_DIR}/media/documents
THUMBNAILS_ROOT=${INSTALL_DIR}/media/thumbnails
ONLYOFFICE_DOCS_ROOT=${INSTALL_DIR}/storage/onlyoffice/documents
KOGNITO_SECRETS_DIR=${INSTALL_DIR}/secrets
DATABASE_URL=${DB_URL}
TELEGRAM_BOT_TOKEN=${TG_TOKEN}
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

    # Node modules + Production Build
    echo -e "${YELLOW}📦 Instalando paquetes Node...${NC}"
    (cd "${PROJECT_DIR}" && npm install --silent)
    echo -e "${GREEN}✅ Dependencias Node instaladas.${NC}"

    echo -e "${YELLOW}🏗️  Construyendo Frontend (npm run build)...${NC}"
    (cd "${PROJECT_DIR}" && npm run build)
    echo -e "${GREEN}✅ Frontend construido exitosamente.${NC}"

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
    git checkout -- package-lock.json 2>/dev/null || true

    local OLD_HEAD
    OLD_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")

    if ! git pull; then
        echo -e "${RED}❌ El 'git pull' falló por cambios locales no resueltos.${NC}"
        echo -e "${YELLOW}   Guarda tus cambios (git stash) o descarta el archivo en conflicto y reintenta.${NC}"
        return 1
    fi

    local NEW_HEAD
    NEW_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")

    local CHANGED_FILES=""
    if [ -n "${OLD_HEAD}" ] && [ -n "${NEW_HEAD}" ] && [ "${OLD_HEAD}" != "${NEW_HEAD}" ]; then
        CHANGED_FILES=$(git diff --name-only "${OLD_HEAD}" "${NEW_HEAD}" 2>/dev/null || echo "")
    fi

    # Python dependencies
    if [ ! -d "${PROJECT_DIR}/venv_host" ] || echo "${CHANGED_FILES}" | grep -q "^requirements.txt$"; then
        echo -e "${BLUE}🐍 Actualizando dependencias de Python...${NC}"
        [ ! -d "${PROJECT_DIR}/venv_host" ] && python3 -m venv "${PROJECT_DIR}/venv_host"
        "${PROJECT_DIR}/venv_host/bin/pip" install -r requirements.txt --quiet 2>/dev/null || true
    else
        echo -e "${GREEN}⚡ Sin cambios en requirements.txt. Omitiendo pip install.${NC}"
    fi

    # Node dependencies
    if [ ! -d "${PROJECT_DIR}/node_modules" ] || echo "${CHANGED_FILES}" | grep -E -q "^(package\.json|package-lock\.json)$"; then
        echo -e "${BLUE}📦 Actualizando dependencias de Node...${NC}"
        npm install --silent
    else
        echo -e "${GREEN}⚡ Sin cambios en package.json/lock. Omitiendo npm install.${NC}"
    fi

    # Frontend build
    if [ ! -d "${PROJECT_DIR}/.next" ] || echo "${CHANGED_FILES}" | grep -E -q "^(src/|public/|package\.json|package-lock\.json|next\.config\.mjs|tsconfig\.json|tailwind\.config\.)"; then
        echo -e "${YELLOW}🏗️  Reconstruyendo Frontend (npm run build)...${NC}"
        npm run build
    else
        echo -e "${GREEN}⚡ Sin cambios en el frontend. Omitiendo npm run build (usando build existente).${NC}"
    fi

    # Re-install CLI in case it changed
    if [ -f "${HOME}/.local/bin/kognitoai" ]; then
        cp "${PROJECT_DIR}/kognitoai" "${HOME}/.local/bin/kognitoai" 2>/dev/null || true
        chmod +x "${HOME}/.local/bin/kognitoai" 2>/dev/null || true
    fi
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

run_install() {
    local BASE_DIR="${HOME}/KognitoAI"
    local INSTALL_TARGET

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🆕 Instalación de Kognito AI desde GitHub${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -d "${BASE_DIR}" ]; then
        echo -e "${YELLOW}⚠️  El directorio ${BOLD}${BASE_DIR}${NC}${YELLOW} ya existe.${NC}"
        echo ""
        echo -e "  ${GREEN}1)${NC} Actualizar instalación existente (git pull)"
        echo -e "  ${BLUE}2)${NC} Crear nueva instancia paralela (${BASE_DIR}_1, _2…)"
        echo -e "  ${RED}3)${NC} Cancelar"
        echo ""
        printf "  Selección [1-3]: "
        read -r INST_CHOICE

        case "${INST_CHOICE}" in
            1)
                INSTALL_TARGET="${BASE_DIR}"
                echo -e "${YELLOW}🔄 Actualizando repositorio existente...${NC}"
                git -C "${INSTALL_TARGET}" checkout -- package-lock.json 2>/dev/null || true
                git -C "${INSTALL_TARGET}" pull
                ;;
            2)
                local COUNT=1
                while [ -d "${BASE_DIR}_${COUNT}" ]; do ((COUNT++)); done
                INSTALL_TARGET="${BASE_DIR}_${COUNT}"
                echo -e "${YELLOW}🌐 Clonando rama ${BOLD}main${NC}${YELLOW} en ${INSTALL_TARGET}...${NC}"
                git clone -b main "${REPO_URL}" "${INSTALL_TARGET}"
                ;;
            *)
                echo "Instalación cancelada."
                return
                ;;
        esac
    else
        echo -e "${YELLOW}🌐 Clonando Kognito AI (rama: ${BOLD}main${NC}${YELLOW}) en ${BASE_DIR}...${NC}"
        git clone -b main "${REPO_URL}" "${BASE_DIR}"
        INSTALL_TARGET="${BASE_DIR}"
    fi

    # Switch PROJECT_DIR to the newly cloned/updated install
    PROJECT_DIR="${INSTALL_TARGET}"
    cd "${PROJECT_DIR}"

    run_setup
}

# ── Menu ──────────────────────────────────────────────────────────────────────

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
echo -e "  ${GREEN}1)${NC} 🆕 Instalar Kognito AI (primera instalación)"
echo -e "  ${GREEN}2)${NC} ▶️  Iniciar Kognito AI"
echo -e "  ${YELLOW}3)${NC} 🔄 Actualizar software (descarga últimos cambios)"
echo -e "  ${BLUE}4)${NC} ⚙️  Re-configurar entorno (~/.kognito)"
echo -e "  ${RED}5)${NC} ❌ Salir"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "  Selecciona una opción [1-5]: "
read -r OPTION

case "${OPTION}" in
    1)
        run_install
        check_and_start_docker
        exec ./start_local.sh
        ;;
    2)
        check_and_start_docker
        exec ./start_local.sh
        ;;
    3)
        run_update
        check_and_start_docker
        exec ./start_local.sh
        ;;
    4)
        run_setup
        check_and_start_docker
        exec ./start_local.sh
        ;;
    5)
        echo "Saliendo."
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Opción no reconocida. Iniciando por defecto...${NC}"
        check_and_start_docker
        exec ./start_local.sh
        ;;
esac
