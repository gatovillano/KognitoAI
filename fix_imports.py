#!/usr/bin/env python3
"""
Script para corregir imports incorrectos de modelos SQLAlchemy
de core.dependencies a core.database
"""
import os
import re
from pathlib import Path

# Modelos que deben estar en core.database
MODELS = [
    'Album', 'Account', 'Photo', 'SharedAlbumLink', 'ContactProfile',
    'ChatThread', 'SharedConversationLink', 'Form', 'FormResponse',
    'Nota', 'AgendaEvent', 'Task', 'UserDocumentTopic'
]

def fix_imports_in_file(filepath):
    """Corrige imports en un archivo específico"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrón para encontrar imports problemáticos
    # Ejemplo: from core.dependencies import get_db_session, Album, Account
    pattern = r'from core\.dependencies import (get_db_session(?:,\s*\w+)*)'
    
    def replace_import(match):
        imports = match.group(1)
        parts = [p.strip() for p in imports.split(',')]
        
        # Separar get_db_session de los modelos
        db_session_imports = ['get_db_session']
        model_imports = []
        
        for part in parts:
            if part == 'get_db_session':
                continue
            elif part in MODELS:
                model_imports.append(part)
        
        # Construir las líneas de import
        lines = []
        if 'get_db_session' in parts:
            lines.append('from core.dependencies import get_db_session')
        
        if model_imports:
            models_str = ', '.join(model_imports)
            lines.append(f'from core.database import {models_str}')
        
        return '\n'.join(lines)
    
    # Aplicar el reemplazo
    new_content = re.sub(pattern, replace_import, content)
    
    if new_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ Corregido: {filepath}")
        return True
    return False

def main():
    # Buscar todos los archivos Python en api/ y extensions/
    directories = ['api', 'extensions', 'utils']
    
    fixed_count = 0
    
    for directory in directories:
        dir_path = Path('/home/gato/Proyectos/KognitoAI/kognito-ai') / directory
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob('*.py'):
            if fix_imports_in_file(py_file):
                fixed_count += 1
    
    print(f"\n✅ Total de archivos corregidos: {fixed_count}")

if __name__ == '__main__':
    main()