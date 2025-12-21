#!/usr/bin/env python3
"""
Script para comparar las salidas de `git ls-files` y `find`.
Identifica archivos excluidos por Git pero no por `find`.
"""

import subprocess
import os

def get_git_tracked_files():
    """Obtiene la lista de archivos rastreados por Git."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True
    )
    return set(result.stdout.strip().split('\n'))

def get_find_files():
    """Obtiene la lista de archivos usando `find`, excluyendo patrones de .gitignore."""
    # Leer .gitignore para obtener patrones de exclusión
    gitignore_patterns = []
    gitignore_path = ".gitignore"
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as file:
            gitignore_patterns = [line.strip() for line in file if line.strip() and not line.startswith("#")]
    
    # Construir el comando `find` con exclusiones
    find_command = ["find", ".", "-type", "f"]
    
    # Añadir exclusiones basadas en .gitignore
    for pattern in gitignore_patterns:
        if pattern.endswith("/"):
            # Excluir directorios
            find_command.extend(["-not", "-path", f"*/{pattern}/*"])
        elif "/" in pattern:
            # Excluir archivos con rutas específicas
            find_command.extend(["-not", "-wholename", pattern])
        else:
            # Excluir archivos por nombre
            find_command.extend(["-not", "-name", pattern])
    
    result = subprocess.run(
        find_command,
        capture_output=True,
        text=True,
        check=True
    )
    return set(result.stdout.strip().split('\n'))

def compare_files():
    """Compara las salidas de `git ls-files` y `find`."""
    git_files = get_git_tracked_files()
    find_files = get_find_files()
    
    # Archivos en `find` pero no en `git ls-files`
    files_in_find_not_in_git = find_files - git_files
    
    # Archivos en `git ls-files` pero no en `find`
    files_in_git_not_in_find = git_files - find_files
    
    print(f"Total de archivos rastreados por Git: {len(git_files)}")
    print(f"Total de archivos encontrados por `find`: {len(find_files)}")
    print(f"\nArchivos en `find` pero no en Git: {len(files_in_find_not_in_git)}")
    print(f"Archivos en Git pero no en `find`: {len(files_in_git_not_in_find)}")
    
    # Mostrar ejemplos de diferencias
    if files_in_find_not_in_git:
        print("\nEjemplos de archivos en `find` pero no en Git:")
        for file in list(files_in_find_not_in_git)[:10]:
            print(f"  - {file}")
    
    if files_in_git_not_in_find:
        print("\nEjemplos de archivos en Git pero no en `find`:")
        for file in list(files_in_git_not_in_find)[:10]:
            print(f"  - {file}")

if __name__ == "__main__":
    compare_files()