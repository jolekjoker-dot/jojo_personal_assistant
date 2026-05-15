"""
Skill system unit tests.
"""

import tempfile
from pathlib import Path

from src.jojo.skills.models import Skill
from src.jojo.skills.loader import SkillLoader
from src.jojo.skills.registry import SkillRegistry


SAMPLE_SKILL = """---
name: test-skill
description: A test skill for unit testing
version: 1.0.0
tags: [test, demo]
triggers: ["test", "testing"]
requires:
  tools: [read_file]
  mcp_servers: []
---

# Test Skill

## Workflow
1. Read the file
2. Report findings
"""


class TestSkillModel:
    """Skill data model tests."""

    def test_create_skill(self):
        s = Skill(
            name="test",
            description="A test skill",
            tags=["test"],
            triggers=["test"],
            body="# Test\nDo something.",
        )
        assert s.name == "test"

    def test_to_system_prompt(self):
        s = Skill(
            name="code-review",
            description="Review code",
            body="## Workflow\n1. Read\n2. Report",
        )
        prompt = s.to_system_prompt()
        assert "code-review" in prompt
        assert "Review code" in prompt
        assert "## Workflow" in prompt


class TestSkillLoader:
    """Skill markdown loader tests."""

    def test_parse_valid_skill(self):
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text(SAMPLE_SKILL, encoding="utf-8")
        try:
            skill = SkillLoader.parse_file(tmp)
            assert skill is not None
            assert skill.name == "test-skill"
            assert skill.description == "A test skill for unit testing"
            assert "test" in skill.tags
            assert "testing" in skill.triggers
            assert "read_file" in skill.tools_required
            assert "Test Skill" in skill.body
        finally:
            tmp.unlink()

    def test_parse_no_frontmatter(self):
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text("# Just a heading\nNo frontmatter here.", encoding="utf-8")
        try:
            skill = SkillLoader.parse_file(tmp)
            assert skill is None
        finally:
            tmp.unlink()

    def test_parse_missing_name(self):
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text("---\ndescription: no name\n---\nBody", encoding="utf-8")
        try:
            skill = SkillLoader.parse_file(tmp)
            assert skill is None
        finally:
            tmp.unlink()

    def test_load_directory(self):
        d = Path(tempfile.mkdtemp())
        f1 = d / "skill1.md"
        f2 = d / "skill2.md"
        f1.write_text(SAMPLE_SKILL, encoding="utf-8")
        f2.write_text(
            SAMPLE_SKILL.replace("test-skill", "second-skill"), encoding="utf-8"
        )
        try:
            skills = SkillLoader.load_directory(str(d))
            assert len(skills) == 2
        finally:
            f1.unlink()
            f2.unlink()
            d.rmdir()


class TestSkillRegistry:
    """SkillRegistry matching tests."""

    def setup_method(self):
        d = Path(tempfile.mkdtemp())
        f1 = d / "code-review.md"
        f2 = d / "daily-summary.md"
        f1.write_text(SAMPLE_SKILL, encoding="utf-8")
        f2.write_text("""---
name: daily-summary
description: Generate daily work summary
tags: [productivity, daily]
triggers: ["summary", "daily", "日报"]
requires:
  tools: [read_file]
  mcp_servers: []
---

# Daily Summary
""", encoding="utf-8")
        self._tmpdir = d
        self.registry = SkillRegistry(skills_dir=str(d))

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir)

    def test_loads_skills(self):
        assert len(self.registry) == 2

    def test_list_all(self):
        all_skills = self.registry.list_all()
        names = {s.name for s in all_skills}
        assert "test-skill" in names
        assert "daily-summary" in names

    def test_match_by_trigger(self):
        matched = self.registry.match("please test this code")
        assert len(matched) > 0
        assert matched[0].name == "test-skill"

    def test_match_daily(self):
        matched = self.registry.match("generate my daily 日报")
        assert len(matched) > 0
        # daily-summary should score high due to trigger "daily" + "日报"
        assert any(s.name == "daily-summary" for s in matched)

    def test_no_match(self):
        matched = self.registry.match("hello world")
        assert len(matched) == 0

    def test_get_skill_prompts_empty(self):
        prompts = self.registry.get_skill_prompts("random unrelated text")
        assert prompts == ""

    def test_get_skill_prompts_has_match(self):
        prompts = self.registry.get_skill_prompts("test this code")
        assert "test-skill" in prompts
        assert "Active Skills" in prompts

    def test_get_by_name(self):
        s = self.registry.get("test-skill")
        assert s is not None
        assert s.name == "test-skill"

    def test_get_missing(self):
        assert self.registry.get("nonexistent") is None

    def test_global_registry_loads_default(self):
        from src.jojo.skills import registry as global_registry
        # Loads from config.skills_dir ("skills/")
        assert len(global_registry) >= 2
