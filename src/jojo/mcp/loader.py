"""
MCP Loader — 从 YAML 加载 MCP Server 配置。
"""

import os
import re
from pathlib import Path

import yaml

from src.jojo.mcp.config import MCPServerConfig
from src.jojo.logger import logger


def load_mcp_config(config_path: str | None = None) -> list[MCPServerConfig]:
    """
    从 YAML 文件加载 MCP Server 配置。

    格式兼容 Claude Code 的 mcp_servers 配置:

    ```yaml
    mcp_servers:
      filesystem:
        transport: stdio
        command: npx
        args:
          - "@anthropic/mcp-server-filesystem"
          - "/path/to/allowed/dir"

      remote-api:
        transport: http
        url: https://api.example.com/mcp
        headers:
          Authorization: "Bearer ${API_TOKEN}"
    ```

    ${VAR} 会替换为环境变量。
    """
    path = Path(config_path) if config_path else Path("configs/mcp_servers.yaml")

    if not path.exists():
        logger.warning(f"MCP config not found: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    servers_data = data.get("mcp_servers", {})
    if not servers_data:
        return []

    configs = []
    for name, cfg in servers_data.items():
        if not isinstance(cfg, dict):
            continue

        # 展开环境变量 ${VAR}
        cfg = _expand_env_vars(cfg)

        configs.append(MCPServerConfig(
            name=name,
            transport=cfg.get("transport", "stdio"),
            command=cfg.get("command", ""),
            args=cfg.get("args", []),
            env=cfg.get("env", {}),
            cwd=cfg.get("cwd", ""),
            url=cfg.get("url", ""),
            headers=cfg.get("headers", {}),
        ))

    logger.info(f"Loaded {len(configs)} MCP server configs from {path}")
    return configs


def _expand_env_vars(obj):
    """递归展开 ${VAR} 环境变量。"""
    if isinstance(obj, str):
        def replacer(match):
            return os.environ.get(match.group(1), match.group(0))
        return re.sub(r"\$\{(\w+)\}", replacer, obj)
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(i) for i in obj]
    return obj
