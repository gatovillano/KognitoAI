#!/usr/bin/env python3
"""
Script para arreglar el error de Pydantic: "object has no field 'account_id'"

Este error ocurre cuando intentamos asignar self.account_id en __init__ 
sin haber definido account_id como un Field en la clase.
"""

import os
import re
from pathlib import Path

def fix_pydantic_field_error(file_path):
    """Arregla el error de campo Pydantic en una herramienta."""
    content = file_path.read_text()
    
    # Buscar si ya tiene el campo account_id definido
    if 'account_id: str = Field(' in content:
        return False, "Ya tiene el campo account_id definido"
    
    # Buscar si tiene __init__ con self.account_id = account_id
    if 'self.account_id = account_id' not in content:
        return False, "No tiene asignación de account_id en __init__"
    
    # Buscar el patrón: args_schema: Type[BaseModel] = SomeInput
    pattern = r'(\s+args_schema: Type\[BaseModel\] = \w+Input\s*\n)'
    match = re.search(pattern, content)
    
    if not match:
        return False, "No se encontró args_schema"
    
    # Insertar el campo account_id después de args_schema
    new_content = re.sub(
        pattern,
        r'\1    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")\n',
        content
    )
    
    if new_content != content:
        file_path.write_text(new_content)
        return True, "Campo account_id agregado"
    
    return False, "No se realizaron cambios"

def main():
    """Procesa todas las herramientas en el directorio tools/"""
    tools_dir = Path("tools")
    fixed_count = 0
    
    print("🔧 Arreglando errores de campo Pydantic...")
    
    for tool_file in tools_dir.glob("*.py"):
        if tool_file.name.startswith("__"):
            continue
            
        try:
            fixed, message = fix_pydantic_field_error(tool_file)
            if fixed:
                print(f"  ✅ {tool_file.name}: {message}")
                fixed_count += 1
            else:
                print(f"  ℹ️  {tool_file.name}: {message}")
        except Exception as e:
            print(f"  ❌ {tool_file.name}: Error - {e}")
    
    print(f"\n✅ Proceso completado. {fixed_count} herramientas arregladas.")

if __name__ == "__main__":
    main()
