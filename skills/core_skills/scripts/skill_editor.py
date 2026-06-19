import os
import logging
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class SkillEditorInput(BaseModel):
    skill_name: str = Field(description="Nombre de la carpeta de la skill a modificar (ej: 'host_terminal_skill').")
    scope: str = Field(description="Scope de la skill: 'user_global', 'user_account_{id}' o 'user_workspace_{id}'.")
    new_python_code: Optional[str] = Field(None, description="El nuevo contenido completo para el archivo .py (opcional si solo cambias el .md).")
    new_markdown_description: Optional[str] = Field(None, description="El nuevo contenido completo para el archivo .md (opcional).")

class SkillEditorTool(BaseTool):
    name: str = "skill_editor"
    description: str = "Modifica o actualiza el código y la descripción de una habilidad (Skill) existente."
    args_schema: Type[BaseModel] = SkillEditorInput

    def _run(self, skill_name: str, scope: str, new_python_code: Optional[str] = None, new_markdown_description: Optional[str] = None) -> str:
        try:
            # 1. Determinar rutas
            current_dir = os.path.dirname(os.path.abspath(__file__))
            skills_root = os.path.abspath(os.path.join(current_dir, "../.."))
            skill_dir = os.path.join(skills_root, scope, skill_name)
            
            if not os.path.exists(skill_dir):
                return f"❌ La skill '{skill_name}' no existe en el scope '{scope}'."

            scripts_dir = os.path.join(skill_dir, "scripts")
            results = []

            # 2. Actualizar Python Code
            if new_python_code:
                # El archivo .py suele llamarse como el nombre base de la carpeta o el nombre de la herramienta
                # Buscamos el primer .py en scripts/ que no sea __init__.py
                py_files = [f for f in os.listdir(scripts_dir) if f.endswith(".py") and f != "__init__.py"]
                if py_files:
                    target_py = os.path.join(scripts_dir, py_files[0])
                    with open(target_py, "w", encoding="utf-8") as f:
                        f.write(new_python_code)
                    results.append(f"✅ Script actualizado: {py_files[0]}")
                else:
                    return f"❌ No se encontró archivo .py principal en {scripts_dir}"

            # 3. Actualizar Markdown
            if new_markdown_description:
                md_files = [f for f in os.listdir(skill_dir) if f.endswith(".md")]
                if md_files:
                    target_md = os.path.join(skill_dir, md_files[0])
                    with open(target_md, "w", encoding="utf-8") as f:
                        f.write(new_markdown_description)
                    results.append(f"✅ Documentación actualizada: {md_files[0]}")

            return "Información de actualización:\n" + "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error en skill_editor: {e}", exc_info=True)
            return f"❌ Error al modificar la skill: {str(e)}"

    async def _arun(self, skill_name: str, scope: str, new_python_code: Optional[str] = None, new_markdown_description: Optional[str] = None) -> str:
        return self._run(skill_name, scope, new_python_code, new_markdown_description)
