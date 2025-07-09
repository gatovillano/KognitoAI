#!/usr/bin/env python3
"""
Script para arreglar automáticamente las herramientas que requieren account_id explícitamente.
"""

import os
import re
from pathlib import Path

# Herramientas prioritarias que necesitan ser arregladas
PRIORITY_TOOLS = [
    "memory_add_tool.py",
    "add_note_tool.py", 
    "get_notes_tool.py",
    "update_note_tool.py",
    "delete_note_tool.py",
    "schedule_event_tool.py",
    "cancel_event_tool.py",
    "set_reminder_tool.py",
    "image_generation_tool.py",
    "natural_query_interpreter_tool.py",
    "vector_db_search_tool.py",
    "memory_search_optimized_tool.py"
]

def remove_account_id_from_schema(file_path):
    """Elimina account_id del esquema de entrada de una herramienta."""
    content = file_path.read_text()
    
    # Patrón para encontrar y eliminar account_id del esquema
    patterns = [
        # Patrón 1: account_id con Field(...) - requerido
        r'\s*account_id:\s*str\s*=\s*Field\(\s*\.\.\.,.*?\n(?:\s*.*?\n)*?\s*\)',
        # Patrón 2: account_id con Field(default=...) - opcional
        r'\s*account_id:\s*str\s*=\s*Field\(\s*default=.*?\n(?:\s*.*?\n)*?\s*\)',
        # Patrón 3: account_id simple
        r'\s*account_id:\s*str\s*=\s*Field\(.*?\)',
    ]
    
    modified = False
    for pattern in patterns:
        new_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            content = new_content
            modified = True
    
    # Limpiar líneas vacías múltiples
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    if modified:
        file_path.write_text(content)
        return True
    return False

def add_account_id_context_logic(file_path):
    """Agrega lógica para obtener account_id del contexto en _arun."""
    content = file_path.read_text()
    
    # Buscar la función _arun y agregar lógica de contexto si no existe
    arun_pattern = r'(async def _arun\(.*?\) -> str:.*?""".*?""")'
    
    context_logic = '''
        # Obtener account_id del contexto de configuración o instancia
        account_id = None
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
        if not account_id:
            account_id = getattr(self, 'account_id', "")

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."
'''
    
    def replace_arun(match):
        arun_def = match.group(1)
        return arun_def + context_logic
    
    new_content = re.sub(arun_pattern, replace_arun, content, flags=re.MULTILINE | re.DOTALL)
    
    if new_content != content:
        file_path.write_text(new_content)
        return True
    return False

def fix_tool(tool_name):
    """Arregla una herramienta específica."""
    tool_path = Path("tools") / tool_name
    
    if not tool_path.exists():
        print(f"  ❌ {tool_name} - No existe")
        return False
    
    print(f"  🔧 Arreglando {tool_name}...")
    
    # Paso 1: Eliminar account_id del esquema
    schema_fixed = remove_account_id_from_schema(tool_path)
    
    # Paso 2: Agregar lógica de contexto (si es necesario)
    # context_fixed = add_account_id_context_logic(tool_path)
    
    if schema_fixed:
        print(f"    ✅ Esquema actualizado")
    else:
        print(f"    ℹ️  Sin cambios necesarios")
    
    return True

def main():
    print("🔧 Arreglando herramientas prioritarias...")
    
    fixed_count = 0
    for tool in PRIORITY_TOOLS:
        if fix_tool(tool):
            fixed_count += 1
    
    print(f"\n✅ Proceso completado. {fixed_count}/{len(PRIORITY_TOOLS)} herramientas procesadas.")
    print("\n💡 Nota: Algunas herramientas pueden necesitar ajustes manuales adicionales.")

if __name__ == "__main__":
    main()
