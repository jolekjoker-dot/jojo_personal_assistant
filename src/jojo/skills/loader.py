"""
SkillLoader — 从 Markdown 文件解析 Skill。
"""

import re
from pathlib import Path

import yaml

from src.jojo.skills.models import Skill
from src.jojo.logger import logger


class SkillLoader:
    """
    解析 skills/ 目录下的 .md 文件。

    格式:
      ---
      name: code-review
      description: 审查代码变更
      version: 1.0.0
      tags: [code, review]
      triggers: ["review", "审查"]
      requires:
        tools: [read_file]
        mcp_servers: []
      ---

      # Code Review Skill

      ## 执行流程
      ...
    """

    @staticmethod
    def parse_file(filepath: Path) -> Skill | None:
        """解析单个 Skill Markdown 文件。"""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read skill file {filepath}: {e}")
            return None

        # 解析 YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not match:
            logger.warning(f"Skill file {filepath} has no valid frontmatter")
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            logger.warning(f"YAML parse error in {filepath}: {e}")
            return None

        if not isinstance(frontmatter, dict) or "name" not in frontmatter:
            logger.warning(f"Skill file {filepath} missing 'name' field")
            return None

        body = match.group(2).strip()

        requires = frontmatter.get("requires", {})

        return Skill(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", "unknown"),
            tags=frontmatter.get("tags", []),
            triggers=frontmatter.get("triggers", []),
            tools_required=requires.get("tools", []),
            mcp_servers_required=requires.get("mcp_servers", []),
            body=body,
        )

    @staticmethod
    def load_directory(skills_dir: str) -> list[Skill]:
        """加载目录下所有 Skill 文件。"""
        path = Path(skills_dir)
        if not path.exists():
            logger.warning(f"Skills directory not found: {skills_dir}")
            return []

        skills = []
        for filepath in path.glob("**/*.md"):
            skill = SkillLoader.parse_file(filepath)
            if skill:
                skills.append(skill)
                logger.debug(f"Loaded skill: {skill.name} from {filepath}")

        return skills
