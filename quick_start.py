#!/usr/bin/env python3
"""
QUICK START - Sistema de Skills agentskills.io
Verifica que todo está funcionando y prueba los comandos básicos.

Uso: python quick_start.py
"""

import sys
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*70}")
    print(f"🚀 {title}")
    print(f"{'='*70}\n")

def run_command(cmd, description):
    print(f"▶️  {description}")
    print(f"   $ {cmd}\n")
    
    try:
        import shlex
        cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
        result = subprocess.run(cmd_args, shell=False, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout[:500]}")  # Primeras 500 chars
        if result.returncode != 0 and result.stderr:
            print(f"   ❌ Error: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_file_exists(filepath, description):
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def main():
    print_header("Agent Skills - Quick Start Verification")
    
    print("Este script verifica que todo el sistema está correctamente configurado.\n")
    
    # 1. Verificar archivos core
    print("1️⃣  Verificando archivos core...")
    files_ok = all([
        check_file_exists("core/skill_installer.py", "Skill Installer"),
        check_file_exists("core/skill_sources.py", "Skill Sources"),
        check_file_exists("scripts/manage_skills.py", "CLI"),
        check_file_exists("scripts/validate_skills.py", "Validator"),
    ])
    print()
    
    # 2. Verificar documentación
    print("2️⃣  Verificando documentación...")
    docs_ok = all([
        check_file_exists("REFACTOR_SKILLS_GUIDE.md", "Refactor Guide"),
        check_file_exists("IMPLEMENTATION_PLAN.md", "Implementation Plan"),
        check_file_exists("SKILLS_CLI_GUIDE.md", "CLI Guide"),
        check_file_exists("SKILLS_SYSTEM_SUMMARY.md", "System Summary"),
    ])
    print()
    
    # 3. Verificar estructura de skills
    print("3️⃣  Verificando estructura de skills...")
    skills_ok = all([
        check_file_exists("skills/search_and_research_skill/SKILL.md", "Search & Research Skill"),
        check_file_exists("skills/rag_skill/SKILL.md", "RAG Skill"),
        check_file_exists("skills/knowledge_and_memory_skill/SKILL.md", "Knowledge Skill"),
        check_file_exists("skills/_templates/template-skill/SKILL.md", "Template Skill"),
    ])
    print()
    
    # 4. Probar CLI
    print("4️⃣  Probando CLI (si está disponible)...")
    cli_test = run_command(
        "python3 scripts/manage_skills.py --help",
        "CLI Help"
    )
    print()
    
    # 5. Probar validator
    print("5️⃣  Probando Validator...")
    validator_test = run_command(
        "python3 scripts/validate_skills.py --skills-dir skills",
        "Validar todos los skills"
    )
    print()
    
    # Resumen
    print_header("Resumen de Verificación")
    
    checks = [
        ("Core Files", files_ok),
        ("Documentation", docs_ok),
        ("Skills Structure", skills_ok),
        ("CLI Working", cli_test),
        ("Validator Working", validator_test),
    ]
    
    all_ok = all(check[1] for check in checks)
    
    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    print(f"\n{'='*70}")
    
    if all_ok:
        print("✅ Todo está configurado correctamente!\n")
        print("Próximos pasos:")
        print("1. Leer: cat SKILLS_CLI_GUIDE.md")
        print("2. Listar skills: python3 scripts/manage_skills.py list")
        print("3. Instalar skill: python3 scripts/manage_skills.py install owner/repo")
        print("4. Validar: python3 scripts/manage_skills.py validate")
    else:
        print("⚠️  Algunos componentes no están listos\n")
        print("Verifica los mensajes anteriores para los detalles.")
    
    print(f"{'='*70}\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
