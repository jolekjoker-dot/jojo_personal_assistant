"""
ReAct 循环引擎 — Agent 的心跳。

流程:
  User Input
    → 检索记忆
    → LLM 思考 (Thought)
    → 决策: 调工具? 还是最终回复?
    → 如果要调工具:
        → 检查风险等级
        → read → 自动执行
        → write/dangerous → 弹出审批
        → 用户批准 → 执行 → 观察结果 → 回到 LLM 思考
        → 用户拒绝 → 注入拒绝信息 → 回到 LLM 思考
    → 如果是最终回复:
        → 保存记忆 → 返回答案
"""

import json
import re
from typing import Callable

from src.jojo.llm import LLMProvider
from src.jojo.tools.registry import registry
from src.jojo.agent.guard import LoopGuard
from src.jojo.agent.approval import (
    ApprovalHandler, ApprovalDecision, ApprovalRequest,
)
from src.jojo.agent.prompt import build_system_prompt
from src.jojo.memory import MemoryManager
from src.jojo.logger import logger


class Agent:
    """
    ReAct Agent — 思考→行动→观察 循环。

    Usage:
        agent = Agent(name="JoJo", description="personal assistant")
        agent.approval.allow_all()  # 可选: 跳过审批
        reply = await agent.run("帮我搜索 Python")
    """

    def __init__(
        self,
        name: str = "JoJo",
        description: str = "A helpful personal assistant",
        model: str | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        verbose: bool = False,
        approval_callback: Callable | None = None,
    ):
        self.name = name
        self.description = description
        self.llm = LLMProvider(model=model) if model else LLMProvider()
        self.max_iterations = max_iterations
        self.verbose = verbose

        # Base system prompt (without memory context, added per-run)
        self._base_system_prompt = system_prompt or build_system_prompt(
            agent_name=name,
            agent_description=description,
        )

        # 审批
        self.approval = ApprovalHandler()

        # 外部审批回调 (CLI 注入，替代默认的 input())
        self._approval_callback = approval_callback

        # 记忆系统
        self.memory = MemoryManager()

        # 对话历史 (L1 工作记忆的快捷引用)
        self.messages: list[dict] = []

    # ========== 主循环 ==========

    async def run(self, user_input: str) -> str:
        """
        执行 ReAct 循环，返回最终回复。

        Args:
            user_input: 用户输入文本

        Returns:
            Agent 的最终回复
        """
        # 初始化
        guard = LoopGuard(max_iterations=self.max_iterations)
        guard.start()

        # 检索长期记忆
        memory_context = self.memory.build_context(user_input)
        self.system_prompt = self._base_system_prompt
        if memory_context:
            self.system_prompt += f"\n\n## Relevant Memories\n{memory_context}"
            if self.verbose:
                print(f"\n  [Memory] Recalled context for: {user_input[:50]}")

        # 匹配 Skill
        from src.jojo.skills import registry as skill_registry
        skill_prompts = skill_registry.get_skill_prompts(user_input)
        if skill_prompts:
            self.system_prompt += "\n\n" + skill_prompts
            if self.verbose:
                matched = skill_registry.match(user_input)
                names = [s.name for s in matched]
                print(f"\n  [Skill] Matched: {names}")

        # 添加到工作记忆
        self.memory.add_user_message(user_input)
        self.messages.append({"role": "user", "content": user_input})

        while True:
            # 检查终止条件
            stop_reason = guard.check("")
            if stop_reason:
                logger.warning(f"Agent stopped: {stop_reason}")
                return stop_reason

            # 准备给 LLM 的消息
            llm_messages = self._build_llm_messages()

            if self.verbose:
                self._print_messages(llm_messages)

            # 调用 LLM (带工具 Schema)
            response = self.llm.chat_with_tools(
                messages=llm_messages,
                tools=registry.to_openai_schemas(),
            )

            content = response["content"]
            tool_calls = response["tool_calls"]
            reasoning = response.get("reasoning_content")  # DeepSeek V4 Pro

            if self.verbose and content:
                print(f"\n  [Thought] {content}")

            # 情况 1: 有工具调用 → 执行工具
            if tool_calls:
                for tc in tool_calls:
                    result = await self._handle_tool_call(tc)
                    tc_normalized = {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc.get("arguments", "{}"),
                        },
                    }
                    # 保留 reasoning_content（DeepSeek Pro 要求）
                    assistant_msg = {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": [tc_normalized],
                    }
                    if reasoning:
                        assistant_msg["reasoning_content"] = reasoning
                    self.messages.append(assistant_msg)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                continue

            # 情况 2: 最终回复
            assistant_msg = {"role": "assistant", "content": content}
            if reasoning:
                assistant_msg["reasoning_content"] = reasoning
            self.messages.append(assistant_msg)
            self.memory.add_assistant_message(content)

            # 压缩工作记忆（如果超过阈值）
            await self.memory.compress_if_needed()

            return content or "No response generated."

    # ========== 内部方法 ==========

    def _build_llm_messages(self) -> list[dict]:
        """构建发给 LLM 的完整消息列表（含记忆上下文）。"""
        return [{"role": "system", "content": self.system_prompt}] + self.messages

    def recall(self, query: str) -> str:
        """手动查询长期记忆，返回格式化的记忆文本。"""
        records = self.memory.recall(query)
        if not records:
            return "No relevant memories found."
        lines = []
        for i, r in enumerate(records):
            lines.append(f"{i+1}. [{r.importance.upper()}] {r.content} (score={r.decay_score:.2f})")
        return "\n".join(lines)

    async def _handle_tool_call(self, tc: dict) -> str:
        """处理单个工具调用：审批 → 执行 → 返回结果。"""
        tool_name = tc["name"]
        tool = registry.get(tool_name)

        if not tool:
            return f"Tool '{tool_name}' not found. Available: {registry.list_tools()}"

        # 解析参数
        args = self._parse_args(tc.get("arguments", "{}"))

        # 风险审批
        if self.approval.needs_approval(tool.risk):
            if self.verbose:
                print(f"\n  [APPROVAL] {tool_name}({args}) risk={tool.risk}")

            decision = await self._request_approval(tool_name, tool.risk, args)

            if decision == ApprovalDecision.DENY:
                return (
                    f"User denied the execution of tool '{tool_name}'. "
                    f"Please try a different approach or ask the user for permission."
                )
            elif decision == ApprovalDecision.ALLOW_ALL:
                self.approval.allow_all()
                logger.info("User allowed all remaining tool calls")

        # 执行
        if self.verbose:
            print(f"\n  [Action] {tool_name}({args})")
        try:
            result = await tool.execute(**args)
            if self.verbose:
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"  [Observation] {preview}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Tool execution error: {e}"

    async def _request_approval(
        self, tool_name: str, risk: str, args: dict
    ) -> ApprovalDecision:
        """请求人工审批。"""
        req = ApprovalRequest(
            tool_name=tool_name,
            tool_description=registry.get(tool_name).description if registry.get(tool_name) else "",
            risk=risk,
            arguments=args,
        )

        # 如果有外部回调 (CLI 注入)
        if self._approval_callback:
            response = await self._approval_callback(req)
            return self.approval.parse_response(response, risk)

        # 默认: 命令行交互
        print(self.approval.build_prompt(req))
        response = input("  > ").strip() or "y"
        return self.approval.parse_response(response, risk)

    @staticmethod
    def _parse_args(args_raw: str | dict) -> dict:
        """解析工具参数 (LLM 可能返回 JSON 字符串或 dict)。"""
        if isinstance(args_raw, dict):
            return args_raw
        try:
            return json.loads(args_raw)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tool args: {args_raw}")
            return {}

    @staticmethod
    def _print_messages(messages: list[dict]) -> None:
        """打印发送给 LLM 的消息概要 (verbose 模式)。"""
        print("\n  " + "-" * 40)
        for msg in messages:
            role = msg["role"]
            content = str(msg.get("content", ""))
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    content += f" [call: {tc['name']}]"
            preview = content[:120] + "..." if len(content) > 120 else content
            print(f"  [{role}] {preview}")
        print("  " + "-" * 40)
