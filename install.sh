#!/usr/bin/env bash

# Kognito AI - Commercial Clean Installation Script (For New Users)
# Prepares an isolated environment in ~/.kognito without importing repository data.

set -e

INSTALL_DIR="${HOME}/.kognito"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "====================================================="
echo "       🚀 Kognito AI - Fresh Installation            "
echo "====================================================="
echo "Target Installation Directory: ${INSTALL_DIR}"
echo "-----------------------------------------------------"

# 1. Create directory structure for isolated execution
echo "📁 Initializing isolated directory structure in ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}/config"
mkdir -p "${INSTALL_DIR}/skills"
mkdir -p "${INSTALL_DIR}/media/documents"
mkdir -p "${INSTALL_DIR}/media/thumbnails"
mkdir -p "${INSTALL_DIR}/storage/onlyoffice/documents"
mkdir -p "${INSTALL_DIR}/secrets"

# 2. Generate clean configuration file
ENV_FILE="${INSTALL_DIR}/config/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo "⚙️  Generating clean environment configuration at ${ENV_FILE}..."
    cat <<EOF > "${ENV_FILE}"
# Kognito AI Environment Configuration
KOGNITO_HOME=${INSTALL_DIR}
KOGNITO_USER_SKILLS_DIR=${INSTALL_DIR}/skills
MEDIA_ROOT=${INSTALL_DIR}/media/documents
THUMBNAILS_ROOT=${INSTALL_DIR}/media/thumbnails
ONLYOFFICE_DOCS_ROOT=${INSTALL_DIR}/storage/onlyoffice/documents
KOGNITO_SECRETS_DIR=${INSTALL_DIR}/secrets

# Database configuration (Defaults to local PostgreSQL or SQLite)
DATABASE_URL=sqlite+aiosqlite:///${INSTALL_DIR}/kognito_db.sqlite
EOF
    echo "✅ Configuration created successfully."
else
    echo "ℹ️  Configuration file already exists at ${ENV_FILE}. Preserving."
fi

echo "-----------------------------------------------------"
echo "✅ Installation completed successfully!"
echo "Your isolated user space is configured at:"
echo "   ${INSTALL_DIR}"
echo ""
echo "To start Kognito AI using this configuration:"
echo "   export KOGNITO_HOME=${INSTALL_DIR}"
echo "   python run_api.py"
echo "====================================================="
