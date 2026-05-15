"""
Orchestrator 三种执行模式: Sequential / Router / Parallel。
"""

import asyncio
from typing import Any

from src.jojo.agent.react_loop import Agent
from src.jojo.orchestrator.registry import AgentRegistry
from src.jojo.orchestrator.classifier import TaskClassifier
from src.jojo.orchestrator.router import Router
from src.jojo.logger import logger


class Orchestrator:
    """
    多 Agent 调度器。

    Usage:
        orch = Orchestrator(registry)
        orch.register(researcher)
        orch.register(coder)

        # Auto route
        result = await orch.auto("搜索 Python 最新版本")

        # Sequential
        result = await orch.sequential("调研并生成报告", ["researcher", "coder"])

        # Parallel
        result = await orch.parallel("对比三个语言", ["researcher", "researcher", "researcher"])
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.classifier = TaskClassifier()
        self.router = Router()

    def register(self, agent: Agent) -> None:
        self.registry.register(agent)

    # ========== 自动路由 (推荐) ==========

    async def auto(self, task: str, agent_name: str | None = None) -> str:
        """
        自动模式：分类 → 选模型 → (路由) → 执行。

        1. 分类器判断复杂度
        2. 按复杂度选 Flash/Pro 模型
        3. Router 选最合适的 Agent（如果未指定）
        4. Agent 执行
        """
        # 1. 分类
        complexity = await self.classifier.classify(task)
        model = self.classifier.get_model_for(complexity)
        logger.info(f"Auto: complexity={complexity}, model={model}")

        # 2. 路由（如果调用方没指定）
        if agent_name is None:
            agents = self.registry.list_all()
            agent_name = await self.router.route(task, agents)

        # 3. 执行
        agent = self.registry.get(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not found"

        # 如果 Agent 当前模型跟分类器选的不同，创建新 Agent 实例
        if agent.llm.model != model:
            agent = Agent(
                name=agent.name,
                description=agent.description,
                model=model,
                max_iterations=agent.max_iterations,
                verbose=agent.verbose,
            )

        return await agent.run(task)

    # ========== 顺序模式 ==========

    async def sequential(self, task: str, agent_names: list[str]) -> str:
        """
        流水线：Agent A → Agent B → Agent C。

        上一个 Agent 的输出是下一个的输入。
        """
        result = task
        for name in agent_names:
            agent = self.registry.get(name)
            if not agent:
                return f"Agent '{name}' not found. Available: {[a['name'] for a in self.registry.list_all()]}"
            logger.info(f"Sequential: {name} processing...")
            result = await agent.run(result)
        return result

    # ========== 并行模式 ==========

    async def parallel(
        self,
        task: str,
        agent_name: str,
        subtasks: list[str],
    ) -> str:
        """
        并行：同一个 Agent 的多个实例同时处理不同子任务。

        Args:
            task: 原始任务（用于汇总）
            agent_name: 使用的 Agent 名称
            subtasks: 分配给各实例的子任务列表

        并行收集结果后，用 LLM 汇总。
        """
        template = self.registry.get(agent_name)
        if not template:
            return f"Agent '{agent_name}' not found"

        # 为每个子任务创建独立 Agent 实例（避免消息历史交叉污染）
        async def work(sub: str) -> str:
            a = Agent(
                name=f"{agent_name}-worker",
                description=template.description,
                model=template.llm.model,
                max_iterations=template.max_iterations,
                verbose=False,
            )
            return await a.run(sub)

        logger.info(f"Parallel: running {len(subtasks)} workers")
        results = await asyncio.gather(*[work(s) for s in subtasks])

        # 汇总
        merger = Agent(
            name="merger",
            description="Merge multiple results into one summary",
            verbose=False,
        )
        merged = "\n---\n".join(
            f"Subtask {i+1}: {s}\nResult: {r}"
            for i, (s, r) in enumerate(zip(subtasks, results))
        )
        summary_prompt = (
            f"Original task: {task}\n\n"
            f"Results from parallel workers:\n{merged}\n\n"
            "Synthesize these into one comprehensive answer."
        )
        return await merger.run(summary_prompt)

    # ========== 智能选择 Agent 列表 ==========

    async def smart_plan(self, task: str) -> tuple[str, list[str]]:
        """
        根据任务复杂度自动规划：返回 (mode, agent_names)。

        simple  → ("auto", ["researcher"])
        medium  → ("sequential", ["researcher", "coder"])
        complex → ("sequential", ["researcher", "coder"])
        """
        complexity = await self.classifier.classify(task)

        agents = [a["name"] for a in self.registry.list_all()]

        if complexity == "simple":
            return ("auto", [agents[0]] if agents else ["researcher"])
        elif complexity == "medium":
            plan = [a for a in agents if a in ["researcher", "coder"]]
            return ("sequential", plan if plan else agents)
        else:
            plan = [a for a in agents if a in ["researcher", "coder"]]
            return ("sequential", plan if plan else agents)
