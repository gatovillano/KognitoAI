# skills/marketing_installer.py
"""
Instalador de Marketing Skills desde GitHub.
"""

import os
import shutil
import git
from pathlib import Path

def install_marketing_skills(repo_url="https://github.com/kostja94/marketing-skills.git", target_dir="./skills"):
    """
    Instala las marketing skills desde GitHub.
    
    Args:
        repo_url: URL del repositorio de marketing skills
        target_dir: Directorio donde instalar las skills
    
    Returns:
        Dict con el resultado de la instalación
    """
    try:
        # Crear directorio de destino si no existe
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Clonar repositorio temporal
        temp_dir = "/tmp/marketing_skills_temp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        print(f"Clonando repositorio desde {repo_url}...")
        git.Repo.clone_from(repo_url, temp_dir)
        
        # Mover archivos al directorio de destino
        skills_installed = []
        for item in Path(temp_dir).iterdir():
            if item.is_dir() and item.name not in ['.git', '__pycache__']:
                dest = target_path / item.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                skills_installed.append(item.name)
        
        # Limpiar directorio temporal
        shutil.rmtree(temp_dir)
        
        return {
            "status": "success",
            "message": f"Instaladas {len(skills_installed)} skills exitosamente",
            "skills": skills_installed,
            "location": str(target_path.absolute())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error durante la instalación: {str(e)}"
        }

if __name__ == "__main__":
    result = install_marketing_skills()
    print(result)