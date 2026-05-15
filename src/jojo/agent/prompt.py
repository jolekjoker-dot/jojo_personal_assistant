"""
System Prompt 构建器 — 组装 Agent 的身份和能力描述。
"""

from src.jojo.tools import registry


def build_system_prompt(
    agent_name: str = "JoJo",
    agent_description: str = "A helpful personal AI assistant",
    custom_instructions: str = "",
) -> str:
    """
    构建 Agent 的 System Prompt。

    包含: 身份 → 能力 → 可用工具 → ReAct 格式 → 行为规则
    """
    tools_desc = _build_tools_description()

    prompt = f"""You are {agent_name}, {agent_description}.

## Available Tools
{tools_desc}

## Response Format (ReAct)
For each step, use this format:

Thought: <your reasoning about the situation and what to do next>
Action: <tool_name>(<parameters in JSON>)

When you have the final answer:
Final Answer: <your complete response to the user>

## Rules
1. **Always think first** — write a Thought before calling any tool.
2. **One action at a time** — call only one tool per response, then wait for the result.
3. **Use tools when needed** — if a tool can help answer the question, use it.
4. **Read results carefully** — after a tool returns, analyze the result before answering.
5. **Be concise** — give direct answers, not lengthy explanations unless asked.
6. **Stop when done** — output Final Answer as soon as you have enough information.
"""

    if custom_instructions:
        prompt += f"\n## Custom Instructions\n{custom_instructions}\n"

    return prompt


def _build_tools_description() -> str:
    """构建可用工具列表描述。"""
    tools = registry.list_tools()
    if not tools:
        return "(No tools available)"

    lines = []
    for name in tools:
        tool = registry.get(name)
        if tool:
            risk_emoji = {"read": "[R]", "write": "[W]", "dangerous": "[!]"}
            emoji = risk_emoji.get(tool.risk, "")
            lines.append(
                f"- **{name}** {emoji}: {tool.description}\n"
                f"  Parameters: {tool.parameters.get('properties', {})}"
            )

    return "\n".join(lines)
