"""
LLM Provider — 统一的 LLM 调用接口，基于 litellm。
"""

from typing import AsyncIterator

import litellm

from src.jojo.logger import logger
from src.jojo.llm.usage import UsageTracker


class LLMProvider:
    """
    统一的 LLM 调用接口。

    使用 litellm 作为适配层，一行代码切换模型:
      provider = LLMProvider("openai/gpt-4o-mini")
      provider = LLMProvider("anthropic/claude-haiku-4-5")

    支持:
      - 同步调用 chat()
      - 流式调用 stream()
      - 自动 Token 统计
    """

    def __init__(self, model: str | None = None):
        from src.jojo.config import config
        self.model = model or config.llm.default_model
        self.usage = UsageTracker()

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        同步调用 LLM，返回完整回复文本。

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}, ...]
            tools: OpenAI Function Calling 格式的工具定义
            temperature: 采样温度
            max_tokens: 最大输出 token 数

        Returns:
            LLM 回复的文本内容
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools

        try:
            response = litellm.completion(**kwargs)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

        # 统计 Token 用量
        if hasattr(response, "usage") and response.usage:
            self.usage.record(
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
            )

        choice = response.choices[0]
        message = choice.message

        # 返回 content (可能为 None 当只有 tool_calls 时)
        return message.content or ""

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict:
        """
        调用 LLM，返回完整 message 对象（含可能的 tool_calls）。

        Returns:
            {"content": str, "tool_calls": list | None}
        """
        response = litellm.completion(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )

        if hasattr(response, "usage") and response.usage:
            self.usage.record(
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
            )

        msg = response.choices[0].message

        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in msg.tool_calls
            ]

        # DeepSeek V4 Pro 需要 reasoning_content 回传
        reasoning = getattr(msg, "reasoning_content", None)

        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
            "reasoning_content": reasoning,
        }

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        流式调用 LLM，逐块返回文本。

        Usage:
            async for chunk in provider.stream(messages):
                print(chunk, end="")
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            raise

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

            # 流式 Token 统计（最后一个 chunk 可能带 usage）
            if hasattr(chunk, "usage") and chunk.usage:
                self.usage.record(
                    model=self.model,
                    prompt_tokens=chunk.usage.prompt_tokens or 0,
                    completion_tokens=chunk.usage.completion_tokens or 0,
                )
