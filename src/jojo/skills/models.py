"""
Skill 数据模型 — 可复用的 Agent 能力包。
"""

from dataclasses import dataclass, field


@dataclass
class Skill:
    """一个 Skill = Prompt模板 + 工具依赖 + 触发规则。"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "jojo"
    tags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)       # 触发关键词
    tools_required: list[str] = field(default_factory=list)  # 依赖的工具
    mcp_servers_required: list[str] = field(default_factory=list)  # 依赖的 MCP
    body: str = ""           # Markdown 正文（执行流程 / Prompt）

    def to_system_prompt(self) -> str:
        """转换为可注入 System Prompt 的片段。"""
        return (
            f"<skill name=\"{self.name}\" description=\"{self.description}\">\n"
            f"{self.body}\n"
            f"</skill>"
        )
