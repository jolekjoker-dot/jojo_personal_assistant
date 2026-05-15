"""
MCP 适配器 — 将 MCP Server 的工具转换为 Agent Tool 格式。
"""

from src.jojo.tools.base import Tool
from src.jojo.tools.registry import registry as tool_registry
from src.jojo.mcp.client import MCPClient
from src.jojo.logger import logger


class MCPAdapter:
    """
    发现 MCP Server 的工具，自动注册到 ToolRegistry。

    工具命名: mcp__<server_name>__<tool_name>
    来源标记: source="mcp"
    风险等级: 默认 "dangerous"（外部工具需审批）
    """

    def __init__(self, mcp_client: MCPClient):
        self._client = mcp_client

    async def discover_and_register(self, server_name: str) -> list[str]:
        """
        发现一个 MCP Server 的所有工具并注册。

        已注册的工具会先移除再重新注册（支持热更新）。
        """
        # 先移除旧注册
        self._unregister_server(server_name)

        tools = await self._client.list_tools(server_name)
        registered = []

        for mcp_tool in tools:
            tool = self._convert(server_name, mcp_tool)
            tool_registry.register(tool)
            registered.append(tool.name)

        logger.info(
            f"Registered {len(registered)} MCP tools from '{server_name}': {registered}"
        )
        return registered

    async def discover_all(self) -> dict[str, list[str]]:
        """发现所有已连接 MCP Server 的工具并注册。"""
        result = {}
        for name in self._client.connected_servers:
            result[name] = await self.discover_and_register(name)
        return result

    def _convert(self, server_name: str, mcp_tool: dict) -> Tool:
        """将一个 MCP tool 定义转为 Agent Tool。"""
        tool_name = f"mcp__{server_name}__{mcp_tool['name']}"

        async def execute(**kwargs):
            return await self._client.call_tool(
                server_name, mcp_tool["name"], kwargs,
            )

        return Tool(
            name=tool_name,
            description=f"[MCP:{server_name}] {mcp_tool.get('description', 'No description')}",
            parameters=mcp_tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": [],
            }),
            function=execute,
            risk="dangerous",  # 外部 MCP 工具默认需要审批
            source="mcp",
        )

    def _unregister_server(self, server_name: str) -> None:
        """移除某个 MCP Server 之前注册的所有工具。"""
        prefix = f"mcp__{server_name}__"
        for name in list(tool_registry.tools):
            if name.startswith(prefix):
                tool_registry.unregister(name)
