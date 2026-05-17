#!/bin/bash
# 🚀 Quick Start Guide para Skills Manager
# Este script muestra los comandos correctos para usar el CLI

set -e

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════╗"
echo "║      🧰 Agent Skills Manager - Setup Guide            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if venv_host exists
if [ ! -d "venv_host" ]; then
    echo "❌ Error: venv_host directory not found"
    echo "Please create the virtual environment first"
    exit 1
fi

PYTHON="./venv_host/bin/python"

echo "✅ Using Python: $PYTHON"
echo ""

# Show available commands
echo "📖 Available Commands:"
echo "─────────────────────────────────────────────────────────"
echo ""
echo "List all skills:"
echo "  $ $PYTHON manage_skills.py list"
echo ""
echo "Search for skills:"
echo "  $ $PYTHON manage_skills.py search -q 'react'"
echo ""
echo "Get skill details:"
echo "  $ $PYTHON manage_skills.py show knowledge-memory-management"
echo ""
echo "Validate all skills:"
echo "  $ $PYTHON manage_skills.py validate"
echo ""
echo "Install a local skill:"
echo "  $ $PYTHON manage_skills.py install ./path/to/skill"
echo ""
echo "Install from GitHub:"
echo "  $ $PYTHON manage_skills.py install owner/repo"
echo ""
echo "See all commands:"
echo "  $ $PYTHON manage_skills.py --help"
echo ""
echo "─────────────────────────────────────────────────────────"
echo ""

# Run a test command
echo "🧪 Running test command: list"
echo ""
$PYTHON manage_skills.py list
echo ""
echo "✅ Setup complete! You can now use the skills manager."
echo ""
echo "💡 Quick Tips:"
echo "   - Use './venv_host/bin/python manage_skills.py [command]' for full path"
echo "   - Or activate: source venv_host/bin/activate.fish"
echo "   - Then: python manage_skills.py [command]"
echo ""
