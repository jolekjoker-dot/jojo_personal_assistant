"""
Tool 基类 — 统一的工具接口定义。
"""

from typing import Any, Callable, Literal
from dataclasses import dataclass, field

# 工具风险等级
#   read      — 只读操作，自动放行
#   write     — 写入文件，需要人工审批
#   dangerous — 执行代码等高危操作，需要人工审批
RiskLevel = Literal["read", "write", "dangerous"]


@dataclass
class Tool:
    """
    一个工具实例。

    既可以通过 @tool 装饰器创建，也可以手动构造。
    """
    name: str
    description: str
    parameters: dict[str, Any]     # JSON Schema
    function: Callable             # 实际执行的异步函数
    risk: RiskLevel = "read"       # 风险等级
    source: str = "builtin"        # "builtin" | "mcp" | "custom"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI Function Calling 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs) -> str:
        """执行工具，返回字符串结果。"""
        import inspect
        import asyncio

        result = self.function(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return str(result) if result is not None else "(no output)"


def tool(
    name: str,
    description: str,
    risk: RiskLevel = "read",
    source: str = "builtin",
    metadata: dict[str, Any] | None = None,
) -> Callable:
    """
    工具装饰器 — 将普通函数注册为 Tool。

    Args:
        name: 工具名称
        description: 工具描述 (给 LLM 看)
        risk: 风险等级 — "read"(自动放行) / "write"(需审批) / "dangerous"(需审批)
        source: 来源 — "builtin" / "mcp" / "custom"

    Usage:
        @tool("web_search", "搜索互联网", risk="read")
        async def web_search(query: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        from src.jojo.tools.schema import function_to_schema

        func.tool = Tool(
            name=name,
            description=description,
            parameters=function_to_schema(func),
            function=func,
            risk=risk,
            source=source,
            metadata=metadata or {},
        )
        return func
    return decorator
