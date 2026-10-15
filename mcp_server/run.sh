#!/usr/bin/env bash
# Script de inicio para el servidor MCP de KognitoAI
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$DIR/venv_host/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

export PYTHONPATH="$DIR:$PYTHONPATH"
exec "$VENV_PYTHON" -m mcp_server
