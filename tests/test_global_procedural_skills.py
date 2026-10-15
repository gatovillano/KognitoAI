import pytest
import os
import shutil
from core.skill_manager import SkillManager
from core.prompt_manager import PromptManager
from core.agent import fetch_relevant_procedural_skills

GLOBAL_SKILL_MD = """---
name: Code Reviewer
description: Perform two-axis code reviews checking coding standards and functional specs.
---
# Code Reviewer Instructions
Step 1: Pin the fixed point SHA.
Step 2: Check repo coding standards.
Step 3: Verify functional requirements.
"""

DOCKER_AUDIT_SKILL_MD = """---
name: Docker Hardening Audit
description: Audit Docker containers, Dockerfile security, rootless setup, and vulnerability scanning.
---
# Docker Hardening Instructions
1. Inspect Dockerfile for USER directives.
2. Check container capabilities and exposed ports.
3. Audit base image tags and vulnerability reports.
"""

@pytest.fixture
def empty_skills_dir(tmpdir):
    d = os.path.join(tmpdir, "empty_skills")
    os.makedirs(d)
    return d


@pytest.fixture
def temp_global_skills_dir(tmpdir):
    global_dir = os.path.join(tmpdir, "global_skills")
    os.makedirs(global_dir)

    # 1. Create global-code-review skill
    cr_dir = os.path.join(global_dir, "global-code-review")
    os.makedirs(cr_dir)
    with open(os.path.join(cr_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(GLOBAL_SKILL_MD)

    # 2. Create docker-hardening-audit skill
    dh_dir = os.path.join(global_dir, "docker-hardening-audit")
    os.makedirs(dh_dir)
    with open(os.path.join(dh_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(DOCKER_AUDIT_SKILL_MD)

    return global_dir


@pytest.mark.asyncio
async def test_global_skills_discovery(empty_skills_dir, temp_global_skills_dir):
    manager = SkillManager(skills_dir=empty_skills_dir, global_skills_dirs=[temp_global_skills_dir])
    metadata = await manager.get_skills_metadata()

    skill_ids = [m["id"] for m in metadata]
    assert "global-code-review" in skill_ids
    assert "docker-hardening-audit" in skill_ids

    cr_meta = next(m for m in metadata if m["id"] == "global-code-review")
    assert cr_meta["type"] == "procedural"
    assert "Perform two-axis code reviews" in cr_meta["description"]


@pytest.mark.asyncio
async def test_semantic_skills_search_and_prompt_injection(empty_skills_dir, temp_global_skills_dir):
    manager = SkillManager(skills_dir=empty_skills_dir, global_skills_dirs=[temp_global_skills_dir])

    # Search for code review related query
    results = await manager.search_skills_semantic(
        query="necesito auditar la seguridad de mis contenedores Docker",
        top_k=2
    )

    assert len(results) > 0
    top_skill = results[0]
    assert top_skill["id"] == "docker-hardening-audit"

    # Inject into PromptManager build_system_prompt
    pm = PromptManager()
    prompt = pm.build_system_prompt(
        user_profile=None,
        relevant_memories="",
        summary_string="",
        custom_prompt_from_profile=None,
        workspace_prompt=None,
        tools=[],
        account_id="test_acc",
        telegram_id=None,
        user_message="necesito auditar la seguridad de mis contenedores Docker",
        relevant_skills=results
    )

    assert "MANUAL DE SKILLS Y PROCEDIMIENTOS RELEVANTES" in prompt
    assert "Docker Hardening Audit" in prompt
    assert "Inspect Dockerfile for USER directives" in prompt


@pytest.mark.asyncio
async def test_fetch_relevant_procedural_skills_tagged_and_semantic(empty_skills_dir, temp_global_skills_dir, monkeypatch):
    manager = SkillManager(skills_dir=empty_skills_dir, global_skills_dirs=[temp_global_skills_dir])
    monkeypatch.setattr("core.skill_manager.get_skill_manager", lambda: manager)

    # 1. Test explicit tag /global-code-review
    user_msg_tagged = "Revisa los últimos cambios /global-code-review por favor"
    skills = await fetch_relevant_procedural_skills(user_msg_tagged)

    assert len(skills) >= 1
    assert any(s["id"] == "global-code-review" for s in skills)


@pytest.mark.asyncio
async def test_skills_dynamic_force_refresh(empty_skills_dir, temp_global_skills_dir):
    manager = SkillManager(skills_dir=empty_skills_dir, global_skills_dirs=[temp_global_skills_dir])
    
    # Discovery before adding new skill
    meta_before = await manager.get_skills_metadata()
    assert not any(m["id"] == "newly-installed-skill" for m in meta_before)

    # Dynamically install a new skill into temp_global_skills_dir
    new_skill_dir = os.path.join(temp_global_skills_dir, "newly-installed-skill")
    os.makedirs(new_skill_dir)
    with open(os.path.join(new_skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: Newly Installed Skill\ndescription: Dynamic install test\n---\n# Instructions\nDo something.")

    # Re-fetch with force_refresh=True
    meta_after = await manager.get_skills_metadata(force_refresh=True)
    assert any(m["id"] == "newly-installed-skill" for m in meta_after)


@pytest.mark.asyncio
async def test_unrelated_query_filters_out_skills(empty_skills_dir, temp_global_skills_dir):
    manager = SkillManager(skills_dir=empty_skills_dir, global_skills_dirs=[temp_global_skills_dir])

    # Search with completely unrelated greeting message
    results = await manager.search_skills_semantic(
        query="Hola buenos días cómo estás",
        top_k=2
    )

    # Should be empty because no skill is relevant to simple greetings
    assert len(results) == 0
