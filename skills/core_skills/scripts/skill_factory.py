import os
import logging
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class SkillFactoryInput(BaseModel):
    skill_name: str = Field(description="Nombre interno de la skill (snake_case, ej: 'weather_fetcher').")
    python_code: str = Field(description="El contenido completo del archivo .py de la skill.")
    markdown_description: str = Field(description="El contenido completo del archivo .md con las instrucciones de la skill.")

class SkillFactoryTool(BaseTool):
    name: str = "skill_factory"
    description: str = "Crea una nueva habilidad (Skill) para KAI escribiendo los archivos necesarios en el sistema."
    args_schema: Type[BaseModel] = SkillFactoryInput
    workspace_name: Optional[str] = None  # Inyectado dinámicamente por el SkillManager
    account_id: Optional[str] = None      # Inyectado dinámicamente por el SkillManager

    def _run(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        try:
            # 1. Determinar el directorio base de skills (asumiendo que estamos en skills/core_skills/scripts/)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            skills_root = os.path.abspath(os.path.join(current_dir, "../.."))
            
            # 2. Determinar el scope (privado por defecto, o workspace si está inyectado)
            workspace_name = getattr(self, "workspace_name", None)
            account_id = getattr(self, "account_id", None)
            
            if workspace_name:
                scope = f"user_workspace_{workspace_name}"
            elif account_id:
                scope = f"user_account_{account_id}"
            else:
                scope = "user_global"
            
            # 3. Preparar rutas de forma robusta
            # Aseguramos que el nombre termine en _skill para mantener consistencia
            clean_name = skill_name.strip().lower().replace(" ", "_")
            if not clean_name.endswith("_skill"):
                skill_folder_name = f"{clean_name}_skill"
            else:
                skill_folder_name = clean_name
                
            # Construir ruta final: skills/[scope]/[skill_folder_name]/
            scope_dir = os.path.join(skills_root, scope)
            skill_dir = os.path.join(scope_dir, skill_folder_name)
            scripts_dir = os.path.join(skill_dir, "scripts")
            
            logger.info(f"📁 Creando estructura de directorios en: {skill_dir}")
            os.makedirs(scripts_dir, exist_ok=True)
            
            # 4. Crear __init__.py en cada nivel para asegurar que sea un paquete importable
            # Esto es vital para que importlib encuentre la skill
            # IMPORTANTE: También necesitamos un __init__.py en el scope_dir (ej: user_account_XYZ)
            for d in [scope_dir, skill_dir, scripts_dir]:
                init_file = os.path.join(d, "__init__.py")
                if not os.path.exists(init_file):
                    with open(init_file, "w") as f:
                        pass
                    logger.info(f"🆕 Archivo __init__.py creado en: {d}")
            
            # 5. Escribir archivos finales
            py_file = os.path.join(scripts_dir, f"{clean_name}.py")
            md_file = os.path.join(skill_dir, f"{skill_folder_name}.md")
            
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_description)

            logger.info(f"🚀 Skill '{skill_folder_name}' guardada correctamente en {scope_dir}")

            logger.info(f"🚀 Nueva skill de usuario '{skill_folder_name}' creada en {scope}.")
            
            return (
                f"✅ Skill de usuario '{skill_folder_name}' creada exitosamente en {scope}.\n"
                f"Ubicación:\n- Script: {py_file}\n- Instrucciones: {md_file}\n\n"
                "La habilidad estará disponible inmediatamente."
            )
        except Exception as e:
            logger.error(f"Error en skill_factory creando '{skill_name}': {e}", exc_info=True)
            return f"❌ Error al crear la skill: {str(e)}"

    async def _arun(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        return self._run(skill_name, python_code, markdown_description)
