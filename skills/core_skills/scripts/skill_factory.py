import os
import yaml
import logging
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class SkillFactoryInput(BaseModel):
    skill_name: str = Field(description="Nombre interno de la skill en snake_case (ej: 'weather_fetcher').")
    python_code: str = Field(description="El contenido completo del archivo .py de la habilidad.")
    markdown_description: str = Field(
        description=(
            "El contenido completo del archivo SKILL.md de la habilidad. DEBE comenzar con YAML frontmatter delimitado por '---\\n':\n"
            "---\n"
            "name: <nombre-de-la-skill-con-guiones>\n"
            "description: <descripción detallada de cuándo y para qué usar la habilidad>\n"
            "---\n\n"
            "# Habilidad\n"
            "## Objetivo\n...\n"
            "## Procedimiento\n...\n"
            "## Ejemplos\n..."
        )
    )

class SkillFactoryTool(BaseTool):
    name: str = "skill_factory"
    description: str = (
        "Crea una nueva habilidad (Skill) para KAI escribiendo los archivos necesarios en el sistema. "
        "Requiere generar un SKILL.md con YAML frontmatter delimitado por '---' que contenga los campos "
        "'name' y 'description', seguido de instrucciones procedimentales detalladas en formato Markdown."
    )
    args_schema: Type[BaseModel] = SkillFactoryInput
    workspace_name: Optional[str] = None  # Inyectado dinámicamente por el SkillManager
    account_id: Optional[str] = None      # Inyectado dinámicamente por el SkillManager

    def _ensure_valid_skill_md(self, skill_name: str, markdown_content: str) -> str:
        """
        Valida y normaliza el contenido del SKILL.md.
        Garantiza que comience con el YAML frontmatter adecuado ('---', name, description).
        """
        content = (markdown_content or "").strip()
        
        # Verificar si ya tiene frontmatter YAML
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict) and "name" in frontmatter and "description" in frontmatter:
                        # Frontmatter es válido
                        return content
                except Exception as e:
                    logger.warning(f"Error parseando frontmatter en skill_factory: {e}")
        
        # Si no tiene frontmatter o no es válido, generar frontmatter por defecto
        clean_name = skill_name.strip().lower().replace(" ", "-").replace("_", "-")
        body = content if not content.startswith("---") else content.split("---")[-1].strip()
        first_line = body.split("\n")[0].replace("#", "").strip() if body else f"Habilidad {clean_name}"
        desc = first_line if len(first_line) >= 10 else f"Habilidad '{clean_name}' creada dinámicamente para KAI."
        if len(desc) > 500:
            desc = desc[:497] + "..."
            
        frontmatter_str = f"---\nname: {clean_name}\ndescription: |\n  {desc}\n---\n\n"
        return frontmatter_str + body

    def _prepare_structure(self, skill_name: str) -> tuple:
        """Prepara la estructura de directorios y devuelve las rutas necesarias."""
        # 1. Determinar el directorio base de skills
        current_dir = os.path.dirname(os.path.abspath(__file__))
        skills_root = os.path.abspath(os.path.join(current_dir, "../.."))
        
        # 2. Determinar el scope
        workspace_name = getattr(self, "workspace_name", None)
        account_id = getattr(self, "account_id", None)
        
        if workspace_name:
            scope = f"user_workspace_{workspace_name}"
        elif account_id:
            scope = f"user_account_{account_id}"
        else:
            scope = "user_global"
        
        # 3. Preparar nombres
        clean_name = skill_name.strip().lower().replace(" ", "_")
        if not clean_name.endswith("_skill"):
            skill_folder_name = f"{clean_name}_skill"
        else:
            skill_folder_name = clean_name
            
        scope_dir = os.path.join(skills_root, scope)
        skill_dir = os.path.join(scope_dir, skill_folder_name)
        scripts_dir = os.path.join(skill_dir, "scripts")
        
        os.makedirs(scripts_dir, exist_ok=True)
        
        # 4. Crear __init__.py
        for d in [scope_dir, skill_dir, scripts_dir]:
            init_file = os.path.join(d, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    pass
        
        py_file = os.path.join(scripts_dir, f"{clean_name}.py")
        md_file = os.path.join(skill_dir, "SKILL.md")
        
        return py_file, md_file, scope, skill_folder_name, scope_dir

    def _run(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        """Ejecución sincrónica (solo escribe archivos, no recarga en caliente si requiere await)."""
        try:
            py_file, md_file, scope, skill_folder_name, scope_dir = self._prepare_structure(skill_name)
            valid_md_content = self._ensure_valid_skill_md(skill_name, markdown_description)
            
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(valid_md_content)

            logger.info(f"🚀 Skill '{skill_folder_name}' guardada correctamente en {scope_dir}")
            
            return (
                f"✅ Skill de usuario '{skill_folder_name}' creada exitosamente en {scope}.\n"
                f"Ubicación:\n- Script: {py_file}\n- Instrucciones: {md_file}\n\n"
                "⚠️ Nota: El sistema sincrónico no admite recarga en caliente automática. Reinicia si es necesario."
            )
        except Exception as e:
            logger.error(f"Error en skill_factory (sync) creando '{skill_name}': {e}")
            return f"❌ Error: {str(e)}"

    async def _arun(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        """Ejecución asíncrona (escribe archivos y recarga en caliente)."""
        try:
            py_file, md_file, scope, skill_folder_name, scope_dir = self._prepare_structure(skill_name)
            valid_md_content = self._ensure_valid_skill_md(skill_name, markdown_description)
            
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(valid_md_content)

            logger.info(f"🚀 Skill '{skill_folder_name}' guardada correctamente en {scope_dir}")

            # ✅ RECARGAR SKILLS EN CALIENTE INMEDIATAMENTE
            from core.skill_manager import get_skill_manager
            try:
                skill_manager = get_skill_manager()
                account_id = getattr(self, "account_id", None)
                workspace_name = getattr(self, "workspace_name", None)
                if account_id:
                    await skill_manager.reload_user_skills(account_id, workspace_name)
                    logger.info(f"✅ Skills recargadas correctamente para usuario {account_id}")
            except Exception as reload_error:
                logger.warning(f"No se pudo recargar skills en caliente: {reload_error}")

            return (
                f"✅ Skill de usuario '{skill_folder_name}' creada exitosamente en {scope}.\n"
                f"Ubicación:\n- Script: {py_file}\n- Instrucciones: {md_file}\n\n"
                "✅ La habilidad ya está disponible inmediatamente en esta conversación y todas las futuras."
            )
        except Exception as e:
            logger.error(f"Error en skill_factory (async) creando '{skill_name}': {e}", exc_info=True)
            return f"❌ Error al crear la skill: {str(e)}"

