#!/bin/bash

# ============================================================================
# Script de Visualización de Logs del Core - KognitoAI
# ============================================================================
# Muestra logs en tiempo real del backend, frontend y LLM con colores
# diferenciados y opciones de filtrado.
#
# Uso:
#   ./view_core_logs.sh              # Todos los logs en tiempo real
#   ./view_core_logs.sh --backend    # Solo logs del backend
#   ./view_core_logs.sh --frontend   # Solo logs del frontend
#   ./view_core_logs.sh --llm        # Solo logs del LLM
#   ./view_core_logs.sh --history    # Ver historial de logs LLM
#   ./view_core_logs.sh --tail N     # Últimas N líneas de cada fuente
# ============================================================================

# Definir colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # Sin color
BOLD='\033[1m'

# Configuración por defecto
TAIL_LINES=50
SHOW_BACKEND=true
SHOW_FRONTEND=true
SHOW_LLM=true
SHOW_HISTORY=false
FOLLOW=true

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend)
            SHOW_BACKEND=true
            SHOW_FRONTEND=false
            SHOW_LLM=false
            shift
            ;;
        --frontend)
            SHOW_BACKEND=false
            SHOW_FRONTEND=true
            SHOW_LLM=false
            shift
            ;;
        --llm)
            SHOW_BACKEND=false
            SHOW_FRONTEND=false
            SHOW_LLM=true
            shift
            ;;
        --history)
            SHOW_HISTORY=true
            shift
            ;;
        --tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        --no-follow)
            FOLLOW=false
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --backend     Mostrar solo logs del backend"
            echo "  --frontend    Mostrar solo logs del frontend"
            echo "  --llm         Mostrar solo logs del LLM"
            echo "  --history     Ver historial de logs LLM (no en tiempo real)"
            echo "  --tail N      Mostrar últimas N líneas (default: 50)"
            echo "  --no-follow   No seguir archivos en tiempo real"
            echo "  -h, --help    Mostrar esta ayuda"
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1"
            echo "Usa -h para ver la ayuda"
            exit 1
            ;;
    esac
done

# Directorio del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

# Función para mostrar el encabezado
show_header() {
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║${NC}  ${CYAN}📊 KognitoAI - Visualizador de Logs del Core${NC}                  ${BOLD}║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Función para mostrar logs del backend
show_backend_logs() {
    echo -e "${GREEN}${BOLD}▶ BACKEND (Python/Uvicorn)${NC}"
    echo -e "${GREEN}──────────────────────────────────────────────────────────────${NC}"
    
    if [ "$FOLLOW" = true ]; then
        # Buscar el PID del backend y obtener sus logs
        BACKEND_PID=$(pgrep -f "run_api.py" | head -1)
        if [ -n "$BACKEND_PID" ]; then
            # Si el proceso está corriendo, mostrar sus logs en tiempo real
            echo -e "${GREEN}✓ Backend detectado en ejecución (PID: $BACKEND_PID)${NC}"
            echo -e "${GREEN}  Mostrando últimas $TAIL_LINES líneas y siguiendo...${NC}"
            echo ""
            # Mostrar últimas líneas y seguir
            journalctl -u kognito-backend 2>/dev/null | tail -n "$TAIL_LINES" | while read line; do
                echo -e "${GREEN}[BACKEND]${NC} $line"
            done
            echo ""
            echo -e "${GREEN}  (Para ver logs en tiempo real del proceso, usa: strace -p $BACKEND_PID)${NC}"
        else
            echo -e "${YELLOW}⚠ Backend no detectado en ejecución${NC}"
            echo -e "${YELLOW}  Inicia el backend con: ./start_local.sh${NC}"
        fi
    else
        echo -e "${GREEN}Mostrando últimas $TAIL_LINES líneas de logs del backend...${NC}"
        # Buscar en archivos de log del backend si existen
        if [ -d "logs" ]; then
            find logs -name "*.log" -type f 2>/dev/null | head -5 | while read logfile; do
                echo -e "${GREEN}--- $logfile ---${NC}"
                tail -n "$TAIL_LINES" "$logfile" | while read line; do
                    echo -e "${GREEN}[BACKEND]${NC} $line"
                done
                echo ""
            done
        fi
    fi
    echo ""
}

# Función para mostrar logs del frontend
show_frontend_logs() {
    echo -e "${BLUE}${BOLD}▶ FRONTEND (Next.js)${NC}"
    echo -e "${BLUE}──────────────────────────────────────────────────────────────${NC}"
    
    if [ "$FOLLOW" = true ]; then
        # Buscar el PID del frontend y mostrar sus logs
        FRONTEND_PID=$(pgrep -f "next dev" | head -1)
        if [ -n "$FRONTEND_PID" ]; then
            echo -e "${BLUE}✓ Frontend detectado en ejecución (PID: $FRONTEND_PID)${NC}"
            echo -e "${BLUE}  Mostrando últimas $TAIL_LINES líneas y siguiendo...${NC}"
            echo ""
            # Los logs de Next.js van a stdout del proceso
            echo -e "${BLUE}  (Para ver logs en tiempo real del proceso, usa: strace -p $FRONTEND_PID)${NC}"
        else
            echo -e "${YELLOW}⚠ Frontend no detectado en ejecución${NC}"
            echo -e "${YELLOW}  Inicia el frontend con: ./start_local.sh${NC}"
        fi
    else
        echo -e "${BLUE}Mostrando últimas $TAIL_LINES líneas de logs del frontend...${NC}"
        # Buscar archivos de log de Next.js
        if [ -d ".next" ]; then
            find .next -name "*.log" -type f 2>/dev/null | head -3 | while read logfile; do
                echo -e "${BLUE}--- $logfile ---${NC}"
                tail -n "$TAIL_LINES" "$logfile" | while read line; do
                    echo -e "${BLUE}[FRONTEND]${NC} $line"
                done
                echo ""
            done
        fi
    fi
    echo ""
}

# Función para mostrar logs del LLM
show_llm_logs() {
    echo -e "${YELLOW}${BOLD}▶ LLM LOGS (Comunicación con LLM)${NC}"
    echo -e "${YELLOW}──────────────────────────────────────────────────────────────${NC}"
    
    # Buscar el archivo de log más reciente del LLM
    LATEST_LOG=$(ls -t logs/llm_detailed_*.log 2>/dev/null | head -1)
    
    if [ -n "$LATEST_LOG" ]; then
        echo -e "${YELLOW}✓ Archivo de log más reciente: $(basename "$LATEST_LOG")${NC}"
        echo -e "${YELLOW}  Mostrando últimas $TAIL_LINES líneas...${NC}"
        echo ""
        
        # Mostrar el log con formato mejorado
        tail -n "$TAIL_LINES" "$LATEST_LOG" | while IFS= read -r line; do
            # Formatear según el tipo de log
            if [[ "$line" == *"[LLM START]"* ]] || [[ "$line" == *"[CHAT MODEL START]"* ]]; then
                echo -e "${YELLOW}🚀 $line${NC}"
            elif [[ "$line" == *"[LLM END]"* ]] || [[ "$line" == *"[RESPONSE"* ]]; then
                echo -e "${YELLOW}✅ $line${NC}"
            elif [[ "$line" == *"[TOOL START]"* ]]; then
                echo -e "${MAGENTA}🔧 $line${NC}"
            elif [[ "$line" == *"[TOOL END]"* ]]; then
                echo -e "${MAGENTA}✅ $line${NC}"
            elif [[ "$line" == *"[LLM ERROR]"* ]] || [[ "$line" == *"[TOOL ERROR]"* ]]; then
                echo -e "${RED}❌ $line${NC}"
            elif [[ "$line" == *"[PROMPT"* ]] || [[ "$line" == *"[MESSAGE"* ]]; then
                echo -e "${CYAN}📨 $line${NC}"
            elif [[ "$line" == *"[CONTENT]"* ]]; then
                echo -e "${CYAN}📄 $line${NC}"
            elif [[ "$line" == *"[AGENT INPUT]"* ]]; then
                echo -e "${CYAN}🎯 $line${NC}"
            elif [[ "$line" == *"DEBUG"* ]] && [[ "$line" == *"langchain"* ]]; then
                echo -e "${YELLOW}🔍 $line${NC}"
            else
                echo -e "${YELLOW}$line${NC}"
            fi
        done
        
        if [ "$FOLLOW" = true ]; then
            echo ""
            echo -e "${YELLOW}  Siguiendo $(basename "$LATEST_LOG") en tiempo real...${NC}"
            echo -e "${YELLOW}  (Presiona Ctrl+C para salir)${NC}"
            echo ""
            # Seguir el archivo en tiempo real
            tail -f "$LATEST_LOG" | while IFS= read -r line; do
                if [[ "$line" == *"[LLM START]"* ]] || [[ "$line" == *"[CHAT MODEL START]"* ]]; then
                    echo -e "${YELLOW}🚀 $line${NC}"
                elif [[ "$line" == *"[LLM END]"* ]] || [[ "$line" == *"[RESPONSE"* ]]; then
                    echo -e "${YELLOW}✅ $line${NC}"
                elif [[ "$line" == *"[TOOL START]"* ]]; then
                    echo -e "${MAGENTA}🔧 $line${NC}"
                elif [[ "$line" == *"[TOOL END]"* ]]; then
                    echo -e "${MAGENTA}✅ $line${NC}"
                elif [[ "$line" == *"[LLM ERROR]"* ]] || [[ "$line" == *"[TOOL ERROR]"* ]]; then
                    echo -e "${RED}❌ $line${NC}"
                elif [[ "$line" == *"[PROMPT"* ]] || [[ "$line" == *"[MESSAGE"* ]]; then
                    echo -e "${CYAN}📨 $line${NC}"
                elif [[ "$line" == *"[CONTENT]"* ]]; then
                    echo -e "${CYAN}📄 $line${NC}"
                elif [[ "$line" == *"[AGENT INPUT]"* ]]; then
                    echo -e "${CYAN}🎯 $line${NC}"
                elif [[ "$line" == *"DEBUG"* ]] && [[ "$line" == *"langchain"* ]]; then
                    echo -e "${YELLOW}🔍 $line${NC}"
                else
                    echo -e "${YELLOW}$line${NC}"
                fi
            done
        fi
    else
        echo -e "${YELLOW}⚠ No se encontraron archivos de log del LLM${NC}"
        echo -e "${YELLOW}  Los logs se guardan en: logs/llm_detailed_*.log${NC}"
    fi
    echo ""
}

# Función para mostrar historial de logs LLM
show_llm_history() {
    echo -e "${YELLOW}${BOLD}▶ HISTORIAL DE LOGS LLM${NC}"
    echo -e "${YELLOW}──────────────────────────────────────────────────────────────${NC}"
    
    if [ -d "logs" ]; then
        LOG_COUNT=$(ls -1 logs/llm_detailed_*.log 2>/dev/null | wc -l)
        if [ "$LOG_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}Se encontraron $LOG_COUNT archivos de log del LLM:${NC}"
            echo ""
            ls -lhS logs/llm_detailed_*.log 2>/dev/null | while read -r line; do
                echo -e "  ${YELLOW}$line${NC}"
            done
            echo ""
            echo -e "${YELLOW}Para ver un log específico:${NC}"
            echo -e "  ${YELLOW}tail -f logs/NOMBRE_DEL_ARCHIVO.log${NC}"
            echo ""
            echo -e "${YELLOW}O usa el monitor interactivo:${NC}"
            echo -e "  ${YELLOW}python3 scripts/monitor_llm_logs.py${NC}"
        else
            echo -e "${YELLOW}⚠ No hay archivos de log del LLM${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Directorio logs/ no encontrado${NC}"
    fi
    echo ""
}

# Función para mostrar estadísticas
show_stats() {
    echo -e "${BOLD}📈 ESTADÍSTICAS${NC}"
    echo -e "──────────────────────────────────────────────────────────────"
    
    # Contar archivos de log
    if [ -d "logs" ]; then
        LLM_LOGS=$(ls -1 logs/llm_detailed_*.log 2>/dev/null | wc -l)
        echo -e "  ${CYAN}Logs LLM totales:${NC}    $LLM_LOGS archivos"
    fi
    
    # Verificar servicios
    BACKEND_PID=$(pgrep -f "run_api.py" | head -1)
    FRONTEND_PID=$(pgrep -f "next dev" | head -1)
    
    if [ -n "$BACKEND_PID" ]; then
        echo -e "  ${GREEN}Backend:${NC}           ✓ Corriendo (PID: $BACKEND_PID)"
    else
        echo -e "  ${RED}Backend:${NC}           ✗ No detectado"
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        echo -e "  ${BLUE}Frontend:${NC}          ✓ Corriendo (PID: $FRONTEND_PID)"
    else
        echo -e "  ${RED}Frontend:${NC}          ✗ No detectado"
    fi
    
    echo ""
}

# Función principal
main() {
    # Limpiar pantalla
    clear
    
    # Mostrar encabezado
    show_header
    
    # Mostrar estadísticas
    show_stats
    
    # Si es modo historial, solo mostrar eso
    if [ "$SHOW_HISTORY" = true ]; then
        show_llm_history
        exit 0
    fi
    
    # Mostrar logs según configuración
    if [ "$SHOW_BACKEND" = true ]; then
        show_backend_logs
    fi
    
    if [ "$SHOW_FRONTEND" = true ]; then
        show_frontend_logs
    fi
    
    if [ "$SHOW_LLM" = true ]; then
        show_llm_logs
    fi
    
    # Si no es modo follow, salir
    if [ "$FOLLOW" = false ]; then
        exit 0
    fi
    
    # Mensaje de espera
    echo -e "${BOLD}Presiona Ctrl+C para salir${NC}"
    echo ""
    
    # Mantener el script corriendo
    wait
}

# Manejar Ctrl+C
trap 'echo -e "\n${GREEN}👋 Visualizador de logs detenido${NC}"; exit 0' INT

# Ejecutar función principal
main
