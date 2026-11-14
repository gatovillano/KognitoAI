#!/bin/bash

# Script adaptado para ejecución como servicio systemd
# No incluye logs en tiempo real ni manejo interactivo de señales

# Crear directorio de logs
mkdir -p logs

# Verificar contenedores de base de datos
if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^kognito_db$"; then
    echo "Contenedores de base de datos ya están en ejecución."
else
    echo "Iniciando contenedores de base de datos con Docker Compose..."
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up -d
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        echo "ADVERTENCIA: Docker no encontrado o no activo."
    fi
fi

# Inicializar variables de entorno
export PYTHONPATH=.

# Limpiar puertos previos
fuser -k 8889/tcp >/dev/null 2>&1 || true
fuser -k 3002/tcp >/dev/null 2>&1 || true
fuser -k 9091/tcp >/dev/null 2>&1 || true

# Iniciar Backend API
echo "Iniciando Kognito API..."
./venv_host/bin/python run_api.py >> logs/backend.log 2>&1 &
BACKEND_PID=$!

# Iniciar Frontend Next.js
echo "Iniciando Next.js frontend..."
PORT=3002 npm run start >> logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Iniciar Telegram Gateway
echo "Iniciando Telegram Gateway..."
./venv_host/bin/python run_telegram_gateway.py >> logs/telegram_gateway.log 2>&1 &
TELEGRAM_PID=$!

# Guardar PIDs para posible gestión
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid
echo $TELEGRAM_PID > logs/telegram_gateway.pid

# Mantener el script activo para que systemd pueda gestionarlo
wait