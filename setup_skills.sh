#!/bin/bash
# 🚀 Quick Setup - Sistema de Skills Estándar

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║    Agent Skills - Sistema Estándar de Instalación              ║"
echo "║    Compatible con: agentskills.io, skills.sh, Claude Code      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Verificando archivos...${NC}"
echo ""

# Archivosdel sistema
FILES=(
    "core/skill_installer.py"
    "core/skill_sources.py"
    "scripts/manage_skills.py"
    "scripts/validate_skills.py"
    "SKILLS_SYSTEM_SUMMARY.md"
    "SKILLS_CLI_GUIDE.md"
)

all_ok=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${YELLOW}⚠️ ${NC} $file (MISSING)"
        all_ok=false
    fi
done

echo ""
echo -e "${BLUE}🧰 Probando CLI...${NC}"
echo ""

if python3 scripts/manage_skills.py --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} CLI funcionando"
else
    echo -e "${YELLOW}⚠️ ${NC} CLI no disponible"
    all_ok=false
fi

echo ""
echo -e "${BLUE}✔️  Validando skills...${NC}"
echo ""

if python3 scripts/validate_skills.py --skills-dir skills > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} Validador funcionando"
else
    echo -e "${YELLOW}⚠️ ${NC} Algunos skills necesitan actualización"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     PRÓXIMOS PASOS                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo -e "${BLUE}📖 Documentación:${NC}"
echo "  1. Lee el resumen:     cat SKILLS_SYSTEM_SUMMARY.md"
echo "  2. Lee la guía CLI:    cat SKILLS_CLI_GUIDE.md"
echo "  3. Lee refactoring:    cat REFACTOR_SKILLS_GUIDE.md"
echo ""

echo -e "${BLUE}🧰 Usando el CLI:${NC}"
echo "  • Listar skills:"
echo "    python3 scripts/manage_skills.py list"
echo ""
echo "  • Instalar desde GitHub:"
echo "    python3 scripts/manage_skills.py install owner/repo"
echo ""
echo "  • Instalar desde skills.sh:"
echo "    python3 scripts/manage_skills.py install microsoft/azure-skills/azure-compute"
echo ""
echo "  • Buscar skills:"
echo "    python3 scripts/manage_skills.py search -q 'react'"
echo ""
echo "  • Validar estructura:"
echo "    python3 scripts/manage_skills.py validate"
echo ""

echo -e "${BLUE}🔧 Desarrollo:${NC}"
echo "  • Crear skill local:   cp -r skills/_templates/template-skill skills/my-skill"
echo "  • Verificar setup:     python3 quick_start.py"
echo ""

echo -e "${GREEN}✅ Sistema listo para usar!${NC}"
echo ""
