"""
MCP Client — 通过 JSON-RPC 与 MCP Server 通信。

支持两种传输:
  - stdio: 启动子进程，stdin/stdout 通信
  - http:  HTTP POST 远程通信
"""

import asyncio
import json
import os

import httpx

from src.jojo.mcp.config import MCPServerConfig
from src.jojo.logger import logger


class MCPClient:
    """
    MCP 协议客户端。

    管理多个 MCP Server 连接，提供工具发现和调用能力。

    Usage:
        client = MCPClient()
        client.register(MCPServerConfig(name="my-server", command="python", args=["server.py"]))
        await client.connect("my-server")
        tools = await client.list_tools("my-server")
        result = await client.call_tool("my-server", "search", {"q": "hello"})
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._connections: dict[str, asyncio.subprocess.Process | httpx.AsyncClient] = {}
        self._tools_cache: dict[str, list[dict]] = {}
        self._next_id = 1

    # ========== 注册 & 配置 ==========

    def register(self, config: MCPServerConfig) -> None:
        self._servers[config.name] = config
        logger.debug(f"MCP server registered: {config.name} ({config.transport})")

    # ========== 连接管理 ==========

    async def connect(self, name: str) -> None:
        if name not in self._servers:
            raise ValueError(f"MCP server '{name}' not registered. Available: {list(self._servers)}")

        cfg = self._servers[name]
        if cfg.transport == "stdio":
            await self._connect_stdio(name, cfg)
        elif cfg.transport == "http":
            await self._connect_http(name, cfg)
        else:
            raise ValueError(f"Unknown transport: {cfg.transport}")

        logger.info(f"MCP connected: {name}")

    async def _connect_stdio(self, name: str, cfg: MCPServerConfig) -> None:
        env = os.environ.copy()
        env.update(cfg.env)

        kwargs = {
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "env": env,
        }
        if cfg.cwd:
            kwargs["cwd"] = cfg.cwd

        process = await asyncio.create_subprocess_exec(
            cfg.command, *cfg.args, **kwargs,
        )

        # 发送 initialize
        response = await self._stdio_request(process, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jojo-agent", "version": "1.0.0"},
        })

        if "error" in response:
            process.terminate()
            raise RuntimeError(f"MCP init failed: {response['error']}")

        self._connections[name] = process

    async def _connect_http(self, name: str, cfg: MCPServerConfig) -> None:
        client = httpx.AsyncClient(
            base_url=cfg.url,
            headers=cfg.headers,
            timeout=30.0,
        )
        # 发送 initialize
        response = await self._http_request(client, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jojo-agent", "version": "1.0.0"},
        })

        if "error" in response:
            await client.aclose()
            raise RuntimeError(f"MCP init failed: {response['error']}")

        self._connections[name] = client

    # ========== JSON-RPC 通信 ==========

    async def _stdio_request(
        self, process: asyncio.subprocess.Process,
        method: str, params: dict,
    ) -> dict:
        """通过 stdio 发送 JSON-RPC 请求。"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }
        self._next_id += 1

        raw = json.dumps(request, ensure_ascii=False) + "\n"
        process.stdin.write(raw.encode())
        await process.stdin.drain()

        # 跳过非 JSON 行 (部分 MCP Server 会在 stdout 输出 banner/调试信息)
        for _ in range(20):  # 最多跳过 20 行，防止死循环
            line = await asyncio.wait_for(process.stdout.readline(), timeout=30)
            decoded = line.decode().strip()
            if not decoded:
                continue
            if decoded.startswith("{"):
                return json.loads(decoded)
            logger.debug(f"MCP stdio skipped non-JSON: {decoded[:80]}")

        raise RuntimeError("MCP server sent no valid JSON-RPC response")

    async def _http_request(
        self, client: httpx.AsyncClient,
        method: str, params: dict,
    ) -> dict:
        """通过 HTTP 发送 JSON-RPC 请求。"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }
        self._next_id += 1

        resp = await client.post("/mcp", json=request)
        resp.raise_for_status()
        return resp.json()

    # ========== 工具发现 ==========

    async def list_tools(self, server_name: str) -> list[dict]:
        """列出 MCP Server 提供的所有工具。"""
        if server_name in self._tools_cache:
            return self._tools_cache[server_name]

        conn = self._get_conn(server_name)
        response = await self._request(server_name, conn, "tools/list", {})
        tools = response.get("result", {}).get("tools", [])
        self._tools_cache[server_name] = tools
        logger.info(f"MCP tools from '{server_name}': {[t['name'] for t in tools]}")
        return tools

    async def list_all_tools(self) -> dict[str, list[dict]]:
        """列出所有已连接 MCP Server 的工具。"""
        result = {}
        for name in self._connections:
            try:
                result[name] = await self.list_tools(name)
            except Exception as e:
                logger.warning(f"Failed to list tools from '{name}': {e}")
                result[name] = []
        return result

    # ========== 工具调用 ==========

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict,
    ) -> str:
        """调用 MCP Server 的工具并返回格式化文本。"""
        conn = self._get_conn(server_name)
        response = await self._request(server_name, conn, "tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")

        content = response.get("result", {}).get("content", [])
        return self._format_content(content)

    # ========== 资源访问 ==========

    async def list_resources(self, server_name: str) -> list[dict]:
        conn = self._get_conn(server_name)
        resp = await self._request(server_name, conn, "resources/list", {})
        return resp.get("result", {}).get("resources", [])

    async def read_resource(self, server_name: str, uri: str) -> str:
        conn = self._get_conn(server_name)
        resp = await self._request(server_name, conn, "resources/read", {"uri": uri})
        return self._format_content(resp.get("result", {}).get("contents", []))

    # ========== 内部 ==========

    def _get_conn(self, name: str):
        if name not in self._connections:
            raise RuntimeError(f"MCP server '{name}' not connected. Call connect() first.")
        return self._connections[name]

    async def _request(self, name: str, conn, method: str, params: dict) -> dict:
        if isinstance(conn, httpx.AsyncClient):
            return await self._http_request(conn, method, params)
        else:
            return await self._stdio_request(conn, method, params)

    @staticmethod
    def _format_content(content: list) -> str:
        """将 MCP content 数组格式化为 LLM 可读文本。"""
        if not content:
            return "(no output)"

        parts = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("type", "text")
                if t == "text":
                    parts.append(item.get("text", ""))
                elif t == "image":
                    parts.append(f"[Image: data or {item.get('uri', 'unknown')}]")
                elif t == "resource":
                    parts.append(f"[Resource: {item.get('uri', '')}]")
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    # ========== 清理 ==========

    async def disconnect(self, name: str) -> None:
        conn = self._connections.pop(name, None)
        if conn is None:
            return
        if isinstance(conn, httpx.AsyncClient):
            await conn.aclose()
        else:
            conn.terminate()
        self._tools_cache.pop(name, None)

    async def disconnect_all(self) -> None:
        for name in list(self._connections):
            await self.disconnect(name)

    @property
    def connected_servers(self) -> list[str]:
        return list(self._connections.keys())
