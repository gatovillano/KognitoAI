#!/bin/bash

# Definir colores para distinguir los logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # Sin color

# Crear directorio de logs y limpiar archivos de logs para esta sesión
mkdir -p logs
> logs/backend.log
> logs/frontend.log
> logs/telegram_gateway.log

echo -e "${BLUE}🐳 Verificando contenedores de base de datos...${NC}"
if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^kognito_db$"; then
    echo -e "${GREEN}✅ Contenedores de base de datos ya están en ejecución. Omitiendo inicio de Docker.${NC}"
else
    echo -e "${YELLOW}🔄 Contenedores no detectados en ejecución. Iniciando Docker Compose...${NC}"
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up -d
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        echo -e "${YELLOW}⚠️ Docker no encontrado o no activo. Asegúrate de iniciar la base de datos.${NC}"
    fi
fi

echo -e "${GREEN}Iniciando el servidor Backend (Kognito API)...${NC}"
echo -e "${GREEN}  → Logs: ./logs/backend.log${NC}"
export PYTHONPATH=.
./venv_host/bin/python run_api.py >> logs/backend.log 2>&1 &
BACKEND_PID=$!

echo -e "${BLUE}Iniciando el servidor Frontend (Next.js)...${NC}"
echo -e "${BLUE}  → Logs: ./logs/frontend.log${NC}"
echo -e "${YELLOW}Compilando el frontend con los últimos cambios...${NC}"
PORT=3002 npm run build >> logs/frontend.log 2>&1
PORT=3002 npm run start >> logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${YELLOW}Iniciando Telegram Gateway (ultraligero)...${NC}"
echo -e "${YELLOW}  → Logs: ./logs/telegram_gateway.log${NC}"
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

    if [ -n "$TAIL_PID" ]; then
        kill $TAIL_PID 2>/dev/null
    fi

    echo "Servicios detenidos exitosamente."
    exit 0
}

trap cleanup SIGINT

echo "=========================================================="
echo -e "${GREEN}🎉 Servicios en ejecución exitosamente:${NC}"
echo "- API Backend:        http://localhost:8889"
echo "- Web Frontend:       http://localhost:3002"
echo "- Telegram Gateway:   http://localhost:9091"
echo ""
echo -e "${YELLOW}Mostrando logs en tiempo real (Presiona Ctrl+C para salir)...${NC}"
echo "=========================================================="

# Mostrar logs en tiempo real en la consola
tail -f logs/backend.log logs/frontend.log logs/telegram_gateway.log &
TAIL_PID=$!

wait $TAIL_PID
