"""
AgentRegistry — 管理所有可用 Agent，按能力匹配。
"""

from src.jojo.agent.react_loop import Agent


class AgentRegistry:
    """Agent 注册中心。"""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def list_all(self) -> list[dict]:
        """列出所有 Agent 的名称和描述。"""
        return [
            {"name": a.name, "description": a.description}
            for a in self._agents.values()
        ]

    def find_best_for(self, task: str) -> Agent:
        """返回默认 Agent（最简单场景）。复杂匹配由 Router 负责。"""
        if not self._agents:
            raise ValueError("No agents registered")
        # 默认返回第一个（后续由 Router 做 LLM 匹配）
        return list(self._agents.values())[0]

    def __len__(self) -> int:
        return len(self._agents)


# 全局单例
registry = AgentRegistry()
