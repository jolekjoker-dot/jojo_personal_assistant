"""
路由模式 — LLM 自动选择最合适的 Agent。
"""

from src.jojo.llm import LLMProvider
from src.jojo.config import config
from src.jojo.logger import logger


class Router:
    """
    根据任务描述，让 LLM 从所有 Agent 中选出最合适的。

    不是硬编码 if-else，是 LLM 读能力描述后自己判断。
    """

    def __init__(self):
        self.llm = LLMProvider(config.orchestrator.classifier_model)

    async def route(self, task: str, agent_list: list[dict]) -> str:
        """
        返回最合适的 Agent 名称。

        Args:
            task: 用户任务
            agent_list: [{"name": "researcher", "description": "..."}, ...]

        Returns:
            Agent name
        """
        if len(agent_list) == 1:
            return agent_list[0]["name"]

        capabilities = "\n".join(
            f"- {a['name']}: {a['description']}" for a in agent_list
        )

        prompt = (
            "You are a task router. Given a user request and available agents, "
            "output ONLY the name of the most suitable agent (one word).\n\n"
            f"Available agents:\n{capabilities}\n\n"
            f"User request: {task[:200]}\n\n"
            "Best agent:"
        )

        try:
            result = self.llm.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            choice = result.strip().lower()
            for a in agent_list:
                if a["name"] in choice:
                    logger.info(f"Router: '{task[:40]}...' → {a['name']}")
                    return a["name"]
            return agent_list[0]["name"]
        except Exception as e:
            logger.warning(f"Router failed: {e}")
            return agent_list[0]["name"]
