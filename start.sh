#!/bin/bash

# start.sh - Script para iniciar KognitoAI con información clara

echo "🚀 Iniciando KognitoAI..."
echo ""

# Colores para mejor visualización
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Construyendo contenedores...${NC}"
docker-compose build

echo ""
echo -e "${BLUE}🔄 Iniciando servicios...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}✅ KognitoAI iniciado correctamente!${NC}"
echo ""

echo -e "${YELLOW}🌐 URLs de Acceso:${NC}"
echo -e "  📍 ${GREEN}Frontend Web:${NC}     http://localhost:8880"
echo -e "  🔧 ${GREEN}API Backend:${NC}      http://localhost:8889"
echo -e "  📚 ${GREEN}API Docs:${NC}         http://localhost:8889/docs"
echo -e "  📱 ${GREEN}Panel Telegram:${NC}   http://localhost:8010"
echo -e "  🗄️  ${GREEN}PGAdmin:${NC}          http://localhost:5056"
echo ""

echo -e "${YELLOW}🌍 URLs Públicas:${NC}"
echo -e "  🌐 ${GREEN}Frontend:${NC}         https://kognito.gatoslibres.art"
echo -e "  🔧 ${GREEN}API:${NC}              https://apibase.gatoslibres.art"
echo -e "  📱 ${GREEN}Telegram Panel:${NC}   https://webapp3.gatoslibres.art"
echo ""

echo -e "${RED}⚠️  IMPORTANTE:${NC}"
echo -e "   ${YELLOW}NO uses localhost:3000 aunque aparezca en los logs${NC}"
echo -e "   ${YELLOW}El puerto 3000 es interno del contenedor${NC}"
echo -e "   ${GREEN}Usa localhost:8880 para el frontend${NC}"
echo ""

echo -e "${BLUE}📊 Verificar estado:${NC}"
echo -e "  docker ps"
echo -e "  docker logs kognito_frontend"
echo -e "  docker logs kognito_core"
echo ""

echo -e "${BLUE}🔄 Para reconstruir después de cambios:${NC}"
echo -e "  docker-compose build && docker-compose up -d"
echo ""

# Esperar un momento para que los servicios se inicien
echo -e "${BLUE}⏳ Esperando que los servicios se inicien...${NC}"
sleep 5

# Verificar que los servicios estén corriendo
echo -e "${BLUE}🔍 Verificando servicios...${NC}"
if curl -s http://localhost:8889/health > /dev/null 2>&1; then
    echo -e "  ✅ ${GREEN}API Backend: OK${NC}"
else
    echo -e "  ❌ ${RED}API Backend: No responde${NC}"
fi

if curl -s http://localhost:8880 > /dev/null 2>&1; then
    echo -e "  ✅ ${GREEN}Frontend: OK${NC}"
else
    echo -e "  ❌ ${RED}Frontend: No responde (puede tardar unos segundos más)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 ¡Listo! Abre http://localhost:8880 en tu navegador${NC}"
