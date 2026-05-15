"""
MCP Server 配置模型。
"""

from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    """一个 MCP Server 的连接配置。"""
    name: str                              # 唯一名称
    transport: str = "stdio"               # "stdio" | "http"
    # stdio 模式
    command: str = ""                      # 可执行命令 (npx / python / uvx)
    args: list[str] = field(default_factory=list)  # 命令参数
    env: dict[str, str] = field(default_factory=dict)  # 环境变量
    cwd: str = ""                          # 工作目录 (子进程从哪个目录启动)
    # HTTP 模式
    url: str = ""                          # HTTP endpoint
    headers: dict[str, str] = field(default_factory=dict)
