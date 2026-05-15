"""
SkillRegistry — 加载、发现、匹配 Skill。
"""

from src.jojo.skills.models import Skill
from src.jojo.skills.loader import SkillLoader
from src.jojo.config import config
from src.jojo.logger import logger


class SkillRegistry:
    """Skill 注册中心。"""

    def __init__(self, skills_dir: str | None = None):
        self._skills: dict[str, Skill] = {}
        self._skills_dir = skills_dir or config.skills_dir
        self.reload()

    def reload(self) -> None:
        """重新加载 skills/ 目录下所有 Skill。"""
        self._skills.clear()
        loaded = SkillLoader.load_directory(self._skills_dir)
        for skill in loaded:
            self._skills[skill.name] = skill
        logger.info(f"Loaded {len(self._skills)} skills: {list(self._skills.keys())}")

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def match(self, user_input: str) -> list[Skill]:
        """
        根据用户输入匹配最相关的 Skill。

        匹配策略（加权计分）:
        - 关键词触发 (triggers): +10 分
        - 标签匹配 (tags): +3 分
        - 名称匹配: +5 分
        - 描述匹配: +1 分/词
        """
        scored: list[tuple[int, Skill]] = []
        input_lower = user_input.lower()

        for skill in self._skills.values():
            score = 0

            for trigger in skill.triggers:
                if trigger.lower() in input_lower:
                    score += 10
                    break  # 一组 trigger 只计一次

            for tag in skill.tags:
                if tag.lower() in input_lower:
                    score += 3

            if skill.name.lower() in input_lower:
                score += 5

            desc_words = skill.description.lower().split()
            matched_words = sum(
                1 for w in desc_words if len(w) > 3 and w in input_lower
            )
            score += matched_words

            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)

        if scored:
            logger.info(
                f"Skill match: '{user_input[:50]}' → "
                f"{[s.name for _, s in scored[:3]]}"
            )

        return [s for _, s in scored[:3]]  # 最多返回 3 个

    def get_skill_prompts(self, user_input: str) -> str:
        """
        匹配 Skill 并生成可注入 Prompt 的片段。
        """
        matched = self.match(user_input)
        if not matched:
            return ""

        prompts = []
        for skill in matched:
            prompts.append(skill.to_system_prompt())

        header = "\n## Active Skills\n"
        header += "The following skills are available for this task. "
        header += "Follow the skill's defined workflow when applicable.\n\n"
        return header + "\n".join(prompts)

    def __len__(self) -> int:
        return len(self._skills)


# 全局单例
registry = SkillRegistry()
