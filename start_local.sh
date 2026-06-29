#!/bin/bash

# Definir colores para distinguir los logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # Sin color

# Crear directorio de logs si no existe
mkdir -p logs

echo -e "${GREEN}Iniciando el servidor Backend (Kognito API)...${NC}"
echo -e "${GREEN}  → Logs: ./logs/backend.log${NC}"
export PYTHONPATH=.
# Arranca el backend en segundo plano, guardando logs en archivo
./venv_host/bin/python run_api.py >> logs/backend.log 2>&1 &
BACKEND_PID=$!

echo -e "${BLUE}Iniciando el servidor Frontend (Next.js)...${NC}"
echo -e "${BLUE}  → Logs: ./logs/frontend.log${NC}"
# Arranca el frontend en segundo plano, guardando logs en archivo
# Usar puerto 3002 para evitar conflicto con otros servicios
PORT=3002 npm run start >> logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo -e "${YELLOW}Iniciando Telegram Gateway (ultraligero, sin Docker)...${NC}"
echo -e "${YELLOW}  → Logs: ./logs/telegram_gateway.log${NC}"
# Arranca el telegram_gateway en segundo plano
./venv_host/bin/python run_telegram_gateway.py >> logs/telegram_gateway.log 2>&1 &
TELEGRAM_PID=$!

# Función para detener todos los servicios al presionar Ctrl+C
cleanup() {
    echo ""
    echo -e "${GREEN}Deteniendo el backend (PID: $BACKEND_PID)...${NC}"
    kill $BACKEND_PID 2>/dev/null

    echo -e "${BLUE}Deteniendo el frontend (PID: $FRONTEND_PID)...${NC}"
    kill $FRONTEND_PID 2>/dev/null

    echo -e "${YELLOW}Deteniendo Telegram Gateway (PID: $TELEGRAM_PID)...${NC}"
    kill $TELEGRAM_PID 2>/dev/null

    echo "Servicios detenidos exitosamente."
    exit 0
}

# Capturar la señal SIGINT (cuando pulsas Ctrl+C) y ejecutar la función cleanup
trap cleanup SIGINT

echo "=========================================================="
echo "Servicios en ejecución:"
echo "- API Backend:        http://localhost:8889"
echo "- Web Frontend:       http://localhost:3002"
echo "- Telegram Gateway:   http://localhost:9091"
echo ""
echo "Para ver logs en tiempo real:"
echo "  tail -f logs/backend.log           # Backend Python"
echo "  tail -f logs/frontend.log          # Frontend Next.js"
echo "  tail -f logs/telegram_gateway.log  # Telegram Gateway"
echo "  tail -f logs/backend.log logs/telegram_gateway.log  # Backend + Telegram"
echo "Presiona Ctrl+C para detener todos los servicios."
echo "=========================================================="

# Esperar a que los procesos terminen (esto mantiene el script vivo)
wait $BACKEND_PID $FRONTEND_PID $TELEGRAM_PID
