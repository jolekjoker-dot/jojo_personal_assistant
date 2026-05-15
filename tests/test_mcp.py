"""
MCP system unit tests.
"""

import tempfile
from pathlib import Path

import yaml
import pytest

from src.jojo.mcp.config import MCPServerConfig
from src.jojo.mcp.loader import load_mcp_config, _expand_env_vars
from src.jojo.mcp.client import MCPClient
from src.jojo.mcp.adapter import MCPAdapter


class TestMCPServerConfig:
    """MCP config model tests."""

    def test_stdio_config(self):
        cfg = MCPServerConfig(
            name="test-server",
            transport="stdio",
            command="python",
            args=["server.py"],
        )
        assert cfg.name == "test-server"
        assert cfg.transport == "stdio"
        assert cfg.command == "python"

    def test_http_config(self):
        cfg = MCPServerConfig(
            name="remote",
            transport="http",
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert cfg.transport == "http"
        assert cfg.url == "https://api.example.com/mcp"

    def test_default_transport(self):
        cfg = MCPServerConfig(name="default")
        assert cfg.transport == "stdio"


class TestMCPLoader:
    """YAML loader tests."""

    def test_expand_env_vars(self):
        import os
        os.environ["TEST_VAR"] = "resolved_value"
        result = _expand_env_vars("hello ${TEST_VAR} world")
        assert result == "hello resolved_value world"

    def test_expand_env_vars_dict(self):
        import os
        os.environ["TEST_KEY"] = "secret123"
        d = {"headers": {"Authorization": "Bearer ${TEST_KEY}"}}
        result = _expand_env_vars(d)
        assert result["headers"]["Authorization"] == "Bearer secret123"

    def test_load_from_yaml(self):
        d = Path(tempfile.mkdtemp())
        yaml_path = d / "mcp.yaml"
        yaml_path.write_text("""
mcp_servers:
  test-server:
    transport: stdio
    command: python
    args: ["-m", "test"]
  remote:
    transport: http
    url: https://example.com/mcp
""", encoding="utf-8")
        try:
            configs = load_mcp_config(str(yaml_path))
            assert len(configs) == 2
            assert configs[0].name == "test-server"
            assert configs[0].transport == "stdio"
            assert configs[1].transport == "http"
        finally:
            yaml_path.unlink()
            d.rmdir()

    def test_load_empty_config(self):
        configs = load_mcp_config("nonexistent.yaml")
        assert configs == []


class TestMCPClient:
    """MCP client tests (registration, no real server)."""

    @pytest.mark.asyncio
    async def test_register(self):
        client = MCPClient()
        cfg = MCPServerConfig(name="test", command="echo", args=["hello"])
        client.register(cfg)
        assert "test" in client._servers

    @pytest.mark.asyncio
    async def test_connect_missing_server(self):
        client = MCPClient()
        with pytest.raises(ValueError, match="not registered"):
            await client.connect("nonexistent")

    @pytest.mark.asyncio
    async def test_connected_servers(self):
        client = MCPClient()
        assert client.connected_servers == []


class TestMCPAdapter:
    """MCP adapter tests."""

    def test_mcp_tool_name_format(self):
        adapter = MCPAdapter(MCPClient())
        mcp_tool = {
            "name": "search",
            "description": "Search the web",
            "inputSchema": {"type": "object", "properties": {}},
        }
        tool = adapter._convert("my-server", mcp_tool)
        assert tool.name == "mcp__my-server__search"
        assert tool.risk == "dangerous"
        assert tool.source == "mcp"
        assert "[MCP:my-server]" in tool.description
