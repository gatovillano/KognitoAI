#!/usr/bin/env bash

# Kognito AI - External Setup & Migration Script
# Sets up user directory structure in ~/.kognito isolating user data from source repository.

set -e

INSTALL_DIR="${HOME}/.kognito"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "====================================================="
echo "       🚀 Kognito AI - Commercial Setup             "
echo "====================================================="
echo "Target Installation Directory: ${INSTALL_DIR}"
echo "Repository Directory:           ${PROJECT_DIR}"
echo "-----------------------------------------------------"

# 1. Create directory structure
echo "📁 Creating directory structure in ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}/config"
mkdir -p "${INSTALL_DIR}/skills"
mkdir -p "${INSTALL_DIR}/media/documents"
mkdir -p "${INSTALL_DIR}/media/thumbnails"
mkdir -p "${INSTALL_DIR}/storage/onlyoffice/documents"
mkdir -p "${INSTALL_DIR}/secrets"

# 2. Create default .env in ~/.kognito/config/.env if not present
ENV_FILE="${INSTALL_DIR}/config/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo "⚙️  Generating default environment configuration at ${ENV_FILE}..."
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
    echo "✅ Configuration file created."
else
    echo "ℹ️  Existing configuration file found at ${ENV_FILE}. Preserving."
fi

# 3. Migrate existing user content from repo if present
echo "🚚 Checking for existing user data in repository to migrate..."

# Migrate user skills
if [ -d "${PROJECT_DIR}/skills" ]; then
    find "${PROJECT_DIR}/skills" -maxdepth 1 -type d -name "user_*" | while read -r user_skill_dir; do
        folder_name=$(basename "${user_skill_dir}")
        echo "   -> Migrating user skill: ${folder_name}"
        cp -rn "${user_skill_dir}" "${INSTALL_DIR}/skills/"
    done
fi

# Migrate media files
if [ -d "${PROJECT_DIR}/media/documents" ] && [ "$(ls -A "${PROJECT_DIR}/media/documents" 2>/dev/null)" ]; then
    echo "   -> Migrating documents from media/documents..."
    cp -rn "${PROJECT_DIR}/media/documents/"* "${INSTALL_DIR}/media/documents/" 2>/dev/null || true
fi

if [ -d "${PROJECT_DIR}/media/thumbnails" ] && [ "$(ls -A "${PROJECT_DIR}/media/thumbnails" 2>/dev/null)" ]; then
    echo "   -> Migrating thumbnails from media/thumbnails..."
    cp -rn "${PROJECT_DIR}/media/thumbnails/"* "${INSTALL_DIR}/media/thumbnails/" 2>/dev/null || true
fi

# Migrate onlyoffice docs
if [ -d "${PROJECT_DIR}/storage/onlyoffice/documents" ] && [ "$(ls -A "${PROJECT_DIR}/storage/onlyoffice/documents" 2>/dev/null)" ]; then
    echo "   -> Migrating OnlyOffice documents..."
    cp -rn "${PROJECT_DIR}/storage/onlyoffice/documents/"* "${INSTALL_DIR}/storage/onlyoffice/documents/" 2>/dev/null || true
fi

echo "-----------------------------------------------------"
echo "✅ Setup and migration completed successfully!"
echo "User data and customized skills are now safely isolated in:"
echo "   ${INSTALL_DIR}"
echo "====================================================="
