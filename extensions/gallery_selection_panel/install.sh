#!/usr/bin/env bash

# KogniPhotos Gallery Selection Panel - Remote Installer
# Installs the extension into an existing KognitoAI installation.
# Can be run directly from GitHub:
#   curl -sSL https://raw.githubusercontent.com/gatovillano/KognitoAI/main/extensions/gallery_selection_panel/install.sh | bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/gatovillano/KognitoAI.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  📸 KogniPhotos — Instalador de Extensión${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Resolve PROJECT_DIR: running inside repo, or find installation at ~/KognitoAI
if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/../../run_api.py" ]; then
    PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
elif [ -f "${HOME}/KognitoAI/run_api.py" ]; then
    PROJECT_DIR="${HOME}/KognitoAI"
elif [ -f "./run_api.py" ]; then
    PROJECT_DIR="$(pwd)"
else
    echo -e "${YELLOW}⚠️  No se detectó instalación local. Clonando desde GitHub...${NC}"
    TARGET="${HOME}/KognitoAI"
    if [ ! -d "${TARGET}" ]; then
        git clone "${REPO_URL}" "${TARGET}"
    else
        echo -e "${YELLOW}ℹ️  Actualizando repositorio existente...${NC}"
        git -C "${TARGET}" pull origin main || true
    fi
    PROJECT_DIR="${TARGET}"
fi

echo -e "  Instalación detectada en: ${GREEN}${PROJECT_DIR}${NC}"

# Find the Python interpreter from the venv
PYTHON="${PROJECT_DIR}/venv_host/bin/python"
if [ ! -f "${PYTHON}" ]; then
    echo -e "${RED}❌ No se encontró el entorno virtual en ${PROJECT_DIR}/venv_host.${NC}"
    echo -e "   Asegúrate de haber ejecutado el instalador principal primero."
    exit 1
fi

# Interactive action menu
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}1)${NC} 📸 Instalar KogniPhotos Gallery"
echo -e "  ${RED}2)${NC} 🗑️  Desinstalar (restaurar galería original)"
echo -e "  ${YELLOW}3)${NC} ❌ Salir"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "  Selecciona una opción [1-3]: "
read -r OPTION

case "${OPTION}" in
    1)
        echo -e "\n${GREEN}🚀 Instalando extensión KogniPhotos...${NC}"
        (cd "${PROJECT_DIR}" && PYTHONPATH=. "${PYTHON}" extensions/gallery_selection_panel/install.py)
        ;;
    2)
        echo -e "\n${YELLOW}🔄 Desinstalando extensión KogniPhotos...${NC}"
        (cd "${PROJECT_DIR}" && PYTHONPATH=. "${PYTHON}" extensions/gallery_selection_panel/install.py --uninstall)
        ;;
    3)
        echo "Saliendo."
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Opción no reconocida. Ejecutando instalación por defecto...${NC}"
        (cd "${PROJECT_DIR}" && PYTHONPATH=. "${PYTHON}" extensions/gallery_selection_panel/install.py)
        ;;
esac
