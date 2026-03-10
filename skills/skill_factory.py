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

    def _run(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        try:
            # Determinar el directorio de skills
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Si estamos en /home/gato/KognitoAI/skills, current_dir es ese.
            skills_dir = current_dir
            
            # Sanitizar nombre
            skill_name = skill_name.strip().lower().replace(" ", "_")
            if not skill_name.endswith("_skill") and not skill_name == "skill_factory":
                # Opcional: forzar sufijo si se desea, pero no es estrictamente necesario
                pass

            py_file = os.path.join(skills_dir, f"{skill_name}.py")
            md_file = os.path.join(skills_dir, f"{skill_name}.md")

            # Escribir archivos
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(python_code)
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_description)

            logger.info(f"🚀 Nueva skill '{skill_name}' producida por skill_factory.")
            
            return (
                f"✅ Skill '{skill_name}' creada exitosamente.\n"
                f"Archivos generados:\n- {py_file}\n- {md_file}\n\n"
                "La habilidad estará disponible para su uso inmediatamente."
            )
        except Exception as e:
            logger.error(f"Error en skill_factory creando '{skill_name}': {e}", exc_info=True)
            return f"❌ Error al crear la skill: {str(e)}"

    async def _arun(self, skill_name: str, python_code: str, markdown_description: str) -> str:
        return self._run(skill_name, python_code, markdown_description)
