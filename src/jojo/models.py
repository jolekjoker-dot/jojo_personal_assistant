"""
核心数据模型 — 整个框架共享的基础类型。
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    一条消息 — Agent 与用户/工具之间的最小通信单元。

    符合 OpenAI Chat Completion 格式。
    """
    role: Literal["user", "assistant", "system", "tool"] = "user"
    content: str
    name: str | None = None          # 可选发送者名称
    tool_call_id: str | None = None  # tool 角色时关联的 tool_call id
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolDefinition(BaseModel):
    """
    工具定义 — 暴露给 LLM 的工具 Schema。

    parameters 遵循 JSON Schema 规范。
    """
    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []}
    )

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


class ToolResult(BaseModel):
    """工具执行结果。"""
    success: bool = True
    data: Any = None
    error: str | None = None
    tool_name: str = ""
    duration_ms: float = 0.0

    def to_message(self, tool_call_id: str = "") -> str:
        """转换为注入 LLM 对话的消息文本。"""
        if self.success:
            return str(self.data) if self.data is not None else "(no output)"
        return f"Error: {self.error}"


class AgentConfig(BaseModel):
    """
    Agent 配置 — 定义一个 Agent 的身份和能力。
    """
    name: str = "assistant"
    description: str = "A helpful AI assistant"
    model: str = "openai/gpt-4o-mini"
    system_prompt: str = "You are a helpful AI assistant."
    tools: list[str] = Field(default_factory=list)
    max_iterations: int = 10
    temperature: float = 0.7


class Session(BaseModel):
    """
    会话 — 一次对话的元数据。
    """
    id: str
    title: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
