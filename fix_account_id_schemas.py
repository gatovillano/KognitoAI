#!/usr/bin/env python3
"""
Script para arreglar herramientas que tienen account_id como parámetro requerido
en sus esquemas de entrada, cuando deberían obtenerlo del contexto.
"""

import os
import re
import glob
from typing import List, Tuple

def find_problematic_tools() -> List[Tuple[str, List[str]]]:
    """
    Encuentra herramientas que tienen account_id como parámetro requerido
    en sus esquemas de entrada.
    """
    problematic_tools = []
    
    # Buscar todos los archivos de herramientas
    tool_files = glob.glob("tools/*.py")
    
    for file_path in tool_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar clases Input que tengan account_id como parámetro requerido
            # Patrón: account_id: str = Field(..., description="...")
            required_account_id_pattern = r'account_id:\s*str\s*=\s*Field\(\s*\.\.\.\s*,'
            
            if re.search(required_account_id_pattern, content):
                # Encontrar todas las líneas problemáticas
                lines = content.split('\n')
                problematic_lines = []
                
                for i, line in enumerate(lines, 1):
                    if re.search(required_account_id_pattern, line):
                        problematic_lines.append(f"Línea {i}: {line.strip()}")
                
                if problematic_lines:
                    problematic_tools.append((file_path, problematic_lines))
        
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
    
    return problematic_tools

def fix_tool_schema(file_path: str) -> bool:
    """
    Arregla un archivo de herramienta removiendo account_id como parámetro requerido
    del esquema de entrada y agregando la lógica para obtenerlo del contexto.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Remover account_id como parámetro requerido del esquema Input
        # Patrón: account_id: str = Field(..., description="...")
        required_pattern = r'(\s*)account_id:\s*str\s*=\s*Field\(\s*\.\.\.\s*,\s*description="[^"]*"\s*\)'
        content = re.sub(required_pattern, '', content)
        
        # 2. Si la herramienta no tiene lógica de contexto, agregarla
        context_logic = '''        # Obtener account_id del contexto de configuración o instancia
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
        
        # Buscar el método _arun y agregar la lógica si no existe
        arun_pattern = r'(async def _arun\([^)]*\) -> str:\s*"""[^"]*"""\s*)'
        
        if re.search(arun_pattern, content):
            # Verificar si ya tiene lógica de contexto
            if "obtener account_id del contexto" not in content.lower():
                content = re.sub(arun_pattern, r'\1' + context_logic, content)
        
        # 3. Actualizar la descripción del esquema Input si es necesario
        input_class_pattern = r'(class \w+Input\(BaseModel\):\s*"""[^"]*)(Debe ser proporcionado por el LLM\.?)([^"]*""")'
        replacement = r'\1El account_id se obtiene automáticamente del contexto de la sesión.\3'
        content = re.sub(input_class_pattern, replacement, content)
        
        # Solo escribir si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error arreglando {file_path}: {e}")
        return False

def main():
    print("🔍 Buscando herramientas con account_id como parámetro requerido...")
    
    problematic_tools = find_problematic_tools()
    
    if not problematic_tools:
        print("✅ No se encontraron herramientas problemáticas.")
        return
    
    print(f"\n❌ Encontradas {len(problematic_tools)} herramientas problemáticas:")
    for file_path, lines in problematic_tools:
        print(f"\n📁 {file_path}:")
        for line in lines:
            print(f"  {line}")
    
    print(f"\n🔧 Arreglando herramientas...")
    
    fixed_count = 0
    for file_path, _ in problematic_tools:
        if fix_tool_schema(file_path):
            print(f"  ✅ Arreglado: {file_path}")
            fixed_count += 1
        else:
            print(f"  ⚠️  Sin cambios: {file_path}")
    
    print(f"\n📊 Resumen:")
    print(f"  - Herramientas problemáticas encontradas: {len(problematic_tools)}")
    print(f"  - Herramientas arregladas: {fixed_count}")
    
    if fixed_count > 0:
        print(f"\n🚀 Recuerda reconstruir la imagen Docker:")
        print(f"  docker compose build core")

if __name__ == "__main__":
    main()
