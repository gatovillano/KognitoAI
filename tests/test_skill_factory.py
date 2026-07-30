# tests/test_skill_factory.py
import os
import shutil
import pytest
import yaml
from pathlib import Path
from skills.core_skills.scripts.skill_factory import SkillFactoryTool
from scripts.validate_skills import SkillValidator

DUMMY_PYTHON_CODE = """
from pydantic import BaseModel
from langchain_core.tools import BaseTool

class EchoInput(BaseModel):
    message: str

class EchoTool(BaseTool):
    name: str = "echo_tool"
    description: str = "Echoes input message."
    args_schema: type[BaseModel] = EchoInput

    def _run(self, message: str) -> str:
        return f"Echo: {message}"
"""

DUMMY_MD_WITH_FRONTMATTER = """---
name: test-skill-factory
description: Skill de prueba para verificar creación mediante SkillFactory.
---

# Test Skill Factory
Esta es una skill de prueba.
"""

DUMMY_MD_WITHOUT_FRONTMATTER = """# Test Skill Plain
Esta es una descripción sin frontmatter explícito pero con contenido procedimental.
"""

@pytest.fixture
def temp_skills_environment(tmpdir, monkeypatch):
    """Configura un entorno de skills temporal para aislamiento de pruebas."""
    temp_dir = Path(tmpdir) / "skills"
    temp_dir.mkdir()
    
    # Crear carpeta user_global
    user_global = temp_dir / "user_global"
    user_global.mkdir()
    
    return temp_dir

@pytest.mark.asyncio
async def test_skill_factory_creates_valid_skill_md_with_frontmatter(temp_skills_environment, monkeypatch):
    tool = SkillFactoryTool()
    
    # Mockear _prepare_structure para apuntar a nuestro directorio temporal
    target_skill_dir = temp_skills_environment / "user_global" / "test_factory_skill"
    scripts_dir = target_skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    py_file = scripts_dir / "test_factory.py"
    md_file = target_skill_dir / "SKILL.md"
    
    monkeypatch.setattr(
        tool, 
        "_prepare_structure", 
        lambda skill_name: (
            str(py_file), 
            str(md_file), 
            "user_global", 
            "test_factory_skill", 
            str(temp_skills_environment / "user_global")
        )
    )
    
    res = await tool._arun(
        skill_name="test_factory",
        python_code=DUMMY_PYTHON_CODE,
        markdown_description=DUMMY_MD_WITH_FRONTMATTER
    )
    
    assert "creada exitosamente" in res
    assert md_file.exists()
    assert py_file.exists()
    
    content = md_file.read_text(encoding="utf-8")
    assert content.startswith("---")
    
    parts = content.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["name"] == "test-skill-factory"
    assert "description" in frontmatter

    # Validar con SkillValidator
    validator = SkillValidator(skills_root=str(temp_skills_environment / "user_global"))
    valid = validator.validate_skill(target_skill_dir)
    assert valid is True

@pytest.mark.asyncio
async def test_skill_factory_auto_injects_frontmatter_if_missing(temp_skills_environment, monkeypatch):
    tool = SkillFactoryTool()
    
    target_skill_dir = temp_skills_environment / "user_global" / "test_plain_skill"
    scripts_dir = target_skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    py_file = scripts_dir / "test_plain.py"
    md_file = target_skill_dir / "SKILL.md"
    
    monkeypatch.setattr(
        tool, 
        "_prepare_structure", 
        lambda skill_name: (
            str(py_file), 
            str(md_file), 
            "user_global", 
            "test_plain_skill", 
            str(temp_skills_environment / "user_global")
        )
    )
    
    res = await tool._arun(
        skill_name="test_plain",
        python_code=DUMMY_PYTHON_CODE,
        markdown_description=DUMMY_MD_WITHOUT_FRONTMATTER
    )
    
    assert "creada exitosamente" in res
    assert md_file.exists()
    
    content = md_file.read_text(encoding="utf-8")
    assert content.startswith("---")
    
    parts = content.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["name"] == "test-plain"
    assert "description" in frontmatter

    # Validar con SkillValidator
    validator = SkillValidator(skills_root=str(temp_skills_environment / "user_global"))
    valid = validator.validate_skill(target_skill_dir)
    assert valid is True
