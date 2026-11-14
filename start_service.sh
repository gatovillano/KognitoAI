#!/bin/bash

cd /home/gato/Proyectos/KognitoAI

# Crear directorio de logs
mkdir -p logs

# Iniciar Docker si es necesario
if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^kognito_db$"; then
    echo "Base de datos ya en ejecución."
else
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up -d
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d
    fi
fi

export PYTHONPATH=.

# Limpiar puertos
fuser -k 8889/tcp >/dev/null 2>&1 || true
fuser -k 3002/tcp >/dev/null 2>&1 || true
fuser -k 9091/tcp >/dev/null 2>&1 || true

# Iniciar servicios redirigiendo salida a logs
./venv_host/bin/python run_api.py >> logs/backend.log 2>&1 &
BACKEND_PID=$!

PORT=3002 npm run start >> logs/frontend.log 2>&1 &
FRONTEND_PID=$!

./venv_host/bin/python run_telegram_gateway.py >> logs/telegram_gateway.log 2>&1 &
TELEGRAM_PID=$!

# Manejar cierre limpiamente
cleanup() {
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $TELEGRAM_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT

# Esperar a los procesos
wait
