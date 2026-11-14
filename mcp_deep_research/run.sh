#!/usr/bin/env bash
# Script de inicio para el servidor MCP de Deep Research de KognitoAI
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Priorizar venv_host o venv
if [ -f "$DIR/venv_host/bin/python3" ]; then
    VENV_PYTHON="$DIR/venv_host/bin/python3"
elif [ -f "$DIR/venv/bin/python3" ]; then
    VENV_PYTHON="$DIR/venv/bin/python3"
else
    VENV_PYTHON="python3"
fi

export PYTHONPATH="$DIR:$PYTHONPATH"
exec "$VENV_PYTHON" -m mcp_deep_research "$@"
