# tests/test_skill_manager.py
import pytest
import os
import shutil
import yaml
from pydantic import BaseModel
from langchain_core.tools import BaseTool

from core.skill_manager import SkillManager

# A dummy tool class that we'll write to a temp file
DUMMY_TOOL_CODE = """
from pydantic import BaseModel
from langchain_core.tools import BaseTool

class DummyInput(BaseModel):
    test_arg: str

class DummySkill(BaseTool):
    name: str = "dummy_skill"
    description: str = "Original python description"
    args_schema: type[BaseModel] = DummyInput

    def _run(self, test_arg: str) -> str:
        return f"Dummy ran with: {test_arg}"
"""

DUMMY_MD_FRONTMATTER = """---
name: Dummy Custom Skill
description: Custom markdown description from YAML frontmatter.
instructions: |
  Step 1: Parse YAML frontmatter.
  Step 2: Read procedural instructions.
  Step 3: Execute tool.
---
# Dummy Custom Skill
Here are some extra natural language guides.
"""

@pytest.fixture
def temp_skills_dir(tmpdir):
    """Creates a temporary skills directory structure mimicking KognitoAI's hybrid scopes."""
    skills_dir = os.path.join(tmpdir, "skills")
    os.makedirs(skills_dir)
    
    # 1. Create a native skill category
    native_cat_dir = os.path.join(skills_dir, "native-cat")
    os.makedirs(os.path.join(native_cat_dir, "scripts"))
    
    with open(os.path.join(native_cat_dir, "scripts", "dummy_skill.py"), "w") as f:
        f.write(DUMMY_TOOL_CODE)
        
    with open(os.path.join(native_cat_dir, "SKILL.md"), "w") as f:
        f.write(DUMMY_MD_FRONTMATTER)
        
    # 2. Create a user global skill category
    global_scope_dir = os.path.join(skills_dir, "user_global")
    user_skill_dir = os.path.join(global_scope_dir, "user-global-skill")
    os.makedirs(os.path.join(user_skill_dir, "scripts"))
    
    with open(os.path.join(user_skill_dir, "scripts", "user_skill.py"), "w") as f:
        f.write(DUMMY_TOOL_CODE.replace("dummy_skill", "user_global_skill"))
        
    with open(os.path.join(user_skill_dir, "SKILL.md"), "w") as f:
        f.write(DUMMY_MD_FRONTMATTER.replace("Dummy Custom Skill", "Global User Skill"))

    # 3. Create a procedural-only skill in workspace scope
    workspace_scope_dir = os.path.join(skills_dir, "user_workspace_my_workspace")
    procedural_skill_dir = os.path.join(workspace_scope_dir, "procedural-guide")
    os.makedirs(procedural_skill_dir) # No scripts folder
    
    procedural_md = """---
name: Procedural Guide Skill
description: How to design premium interfaces.
instructions: |
  Follow glassmorphism rules.
  Use harmonized color palettes.
---
# Procedural Guide
Step-by-step styling rules.
"""
    with open(os.path.join(procedural_skill_dir, "SKILL.md"), "w") as f:
        f.write(procedural_md)

    return skills_dir

@pytest.mark.asyncio
async def test_skill_manager_discovery_and_injection(temp_skills_dir):
    manager = SkillManager(skills_dir=temp_skills_dir)
    
    # Load tools for test_account and my_workspace
    tools = await manager.load_skills(
        account_id="test_account",
        workspace_name="my_workspace"
    )
    
    # We should have loaded:
    # 1. native-cat/scripts/dummy_skill.py
    # 2. user_global/user-global-skill/scripts/user_skill.py
    # Note: procedural-guide is procedural-only (no scripts/py files), so it doesn't return an executable tool.
    assert len(tools) == 2
    
    # Validate names and descriptions from YAML frontmatter
    tool_names = [t.name for t in tools]
    assert "dummy_skill" in tool_names
    assert "user_global_skill" in tool_names
    
    # Check that descriptions were loaded and set
    dummy_tool = next(t for t in tools if t.name == "dummy_skill")
    assert "Custom markdown description" in dummy_tool.description

@pytest.mark.asyncio
async def test_skill_manager_markdown_frontmatter_parsing(temp_skills_dir):
    manager = SkillManager(skills_dir=temp_skills_dir)
    
    # Direct YAML frontmatter parsing test
    guide_md = os.path.join(temp_skills_dir, "user_workspace_my_workspace", "procedural-guide", "SKILL.md")
    with open(guide_md, "r") as f:
        content = f.read()
    skill_data = manager.parse_skill_markdown(content)
    
    assert skill_data is not None
    assert skill_data["name"] == "Procedural Guide Skill"
    assert skill_data["description"] == "How to design premium interfaces."
    assert "glassmorphism" in skill_data["instructions"]

@pytest.mark.asyncio
async def test_skill_manager_semantic_search_scoping(temp_skills_dir):
    # Mocking embedding manager/model is not strictly necessary if we test discovery/scoping logic.
    # Since search_skills_semantic uses the EmbeddingManager, let's verify that discovery gathers all three.
    manager = SkillManager(skills_dir=temp_skills_dir)
    
    # Discover all skills (including procedural-only) for account_id="test_account", workspace_name="my_workspace"
    skills = await manager.get_skills_metadata(account_id="test_account", workspace_name="my_workspace")
    
    # We should discover:
    # 1. native-cat (native)
    # 2. user-global-skill (user_global)
    # 3. procedural-guide (user_workspace_my_workspace)
    assert len(skills) == 3
    
    ids = [s["id"] for s in skills]
    assert "native-cat" in ids
    assert "user-global-skill" in ids
    assert "procedural-guide" in ids
