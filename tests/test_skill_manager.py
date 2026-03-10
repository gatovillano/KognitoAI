# tests/test_skill_manager.py
import pytest
import os
import shutil
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

DUMMY_MD_CODE = "This is a markdown injected description for the dummy skill."

@pytest.fixture
def temp_skills_dir(tmpdir):
    """Creates a temporary skills directory with a dummy skill and markdown."""
    skills_dir = os.path.join(tmpdir, "skills")
    os.makedirs(skills_dir)
    
    # Write Python file
    py_file = os.path.join(skills_dir, "dummy_skill.py")
    with open(py_file, "w") as f:
        f.write(DUMMY_TOOL_CODE)
        
    # Write Markdown file
    md_file = os.path.join(skills_dir, "dummy_skill.md")
    with open(md_file, "w") as f:
        f.write(DUMMY_MD_CODE)
        
    return skills_dir

@pytest.mark.asyncio
async def test_skill_manager_discovery_and_injection(temp_skills_dir):
    manager = SkillManager(skills_dir=temp_skills_dir)
    
    # Load tools
    tools = await manager.load_skills(account_id="test_account")
    
    assert len(tools) == 1
    tool = tools[0]
    
    assert tool.name == "dummy_skill"
    # Check that the Markdown description replaced the Python one
    assert tool.description == DUMMY_MD_CODE
    
    # Check execution
    result = tool._run(test_arg="hello")
    assert result == "Dummy ran with: hello"
