"""
ToolRegistry — 工具注册中心。

管理所有 Tool 的注册、发现和 Schema 导出。
"""

from src.jojo.tools.base import Tool
from src.jojo.logger import logger


class ToolRegistry:
    """
    工具注册中心。

    单例模式，全局统一管理所有可用工具。

    Usage:
        registry = ToolRegistry()
        registry.register(my_tool)
        schemas = registry.to_openai_schemas()
    """

    _instance: "ToolRegistry | None" = None

    def __new__(cls, *, _singleton: bool = True) -> "ToolRegistry":
        if not _singleton:
            instance = super().__new__(cls)
            instance._tools = {}
            return instance
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, Tool] = {}
        return cls._instance

    @property
    def tools(self) -> dict[str, Tool]:
        return self._tools

    def register(self, tool: Tool) -> None:
        """注册一个工具。"""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting.")
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered: {tool.name}")

    def register_from_decorated(self, func) -> None:
        """从 @tool 装饰过的函数注册。"""
        if hasattr(func, "tool"):
            self.register(func.tool)
        else:
            raise ValueError(f"Function '{func.__name__}' is not decorated with @tool")

    def get(self, name: str) -> Tool | None:
        """按名称获取工具。"""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """列出所有工具名称。"""
        return list(self._tools.keys())

    def to_openai_schemas(self) -> list[dict]:
        """导出所有工具为 OpenAI Function Calling 格式。"""
        return [t.to_openai_schema() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> str:
        """按名称执行工具。"""
        tool = self._tools.get(name)
        if not tool:
            available = ", ".join(self._tools.keys())
            raise ValueError(
                f"Tool '{name}' not found. Available: {available}"
            )
        logger.info(f"Executing tool: {name}({kwargs})")
        return await tool.execute(**kwargs)

    def unregister(self, name: str) -> None:
        """移除一个工具。"""
        self._tools.pop(name, None)

    def clear(self) -> None:
        """清空所有工具。"""
        self._tools.clear()


# 全局单例
registry = ToolRegistry()
