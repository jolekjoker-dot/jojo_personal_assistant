"""
LLM 适配层单元测试。
"""

import pytest
from src.jojo.llm import LLMProvider, UsageTracker


class TestUsageTracker:
    """Token 用量跟踪器测试。"""

    def test_empty_tracker(self):
        tracker = UsageTracker()
        assert tracker.call_count == 0
        assert tracker.total_tokens == 0
        assert "No LLM calls" in tracker.summary()

    def test_record_single_call(self):
        tracker = UsageTracker()
        tracker.record("openai/gpt-4o-mini", prompt_tokens=100, completion_tokens=50)
        assert tracker.call_count == 1
        assert tracker.total_prompt_tokens == 100
        assert tracker.total_completion_tokens == 50
        assert tracker.total_tokens == 150

    def test_record_multiple_calls(self):
        tracker = UsageTracker()
        tracker.record("openai/gpt-4o-mini", 100, 50)
        tracker.record("openai/gpt-4o-mini", 200, 80)
        tracker.record("anthropic/claude-haiku-4-5", 150, 60)
        assert tracker.call_count == 3
        assert tracker.total_tokens == 640

    def test_summary_by_model(self):
        tracker = UsageTracker()
        tracker.record("openai/gpt-4o-mini", 100, 50)
        tracker.record("anthropic/claude-haiku-4-5", 200, 80)
        summary = tracker.summary()
        assert "openai/gpt-4o-mini" in summary
        assert "anthropic/claude-haiku-4-5" in summary

    def test_reset(self):
        tracker = UsageTracker()
        tracker.record("openai/gpt-4o-mini", 100, 50)
        tracker.reset()
        assert tracker.call_count == 0
        assert tracker.total_tokens == 0


class TestLLMProvider:
    """LLM Provider 集成测试（需要 API Key）。"""

    @pytest.mark.skip(reason="Requires API key — run manually")
    def test_chat_returns_string(self):
        provider = LLMProvider("openai/gpt-4o-mini")
        result = provider.chat([
            {"role": "user", "content": "Say exactly: hello world"}
        ])
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="Requires API key — run manually")
    def test_chat_tracks_usage(self):
        provider = LLMProvider("openai/gpt-4o-mini")
        provider.chat([
            {"role": "user", "content": "Hi"}
        ])
        assert provider.usage.call_count == 1
        assert provider.usage.total_tokens > 0

    @pytest.mark.skip(reason="Requires API key — run manually")
    def test_model_switch(self):
        """验证模型切换：换模型名不改代码。"""
        provider = LLMProvider("anthropic/claude-haiku-4-5")
        result = provider.chat([
            {"role": "user", "content": "Say: hello"}
        ])
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="Requires API key — run manually")
    async def test_stream_yields_chunks(self):
        provider = LLMProvider("openai/gpt-4o-mini")
        chunks = []
        async for chunk in provider.stream([
            {"role": "user", "content": "Count 1 to 3"}
        ]):
            chunks.append(chunk)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 0

    @pytest.mark.skip(reason="Requires API key — run manually")
    def test_chat_with_tools(self):
        provider = LLMProvider("openai/gpt-4o-mini")
        result = provider.chat_with_tools(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Calculate math expressions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        },
                        "required": ["expression"],
                    },
                },
            }],
        )
        assert "content" in result
        assert "tool_calls" in result
