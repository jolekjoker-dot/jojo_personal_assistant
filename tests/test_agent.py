"""
Agent core loop unit tests.
"""

import asyncio
import pytest

from src.jojo.agent.guard import LoopGuard
from src.jojo.agent.approval import (
    ApprovalHandler, ApprovalDecision, ApprovalRequest,
)
from src.jojo.agent import Agent
from src.jojo.tools import registry


class TestLoopGuard:
    """LoopGuard termination tests."""

    def test_allows_within_limits(self):
        guard = LoopGuard(max_iterations=5)
        guard.start()
        for i in range(3):
            assert guard.check(f"unique {i}") is None  # different content, no repeat

    def test_max_iterations(self):
        guard = LoopGuard(max_iterations=2)
        guard.start()
        guard.check("a")
        guard.check("b")
        result = guard.check("c")  # iteration 3 > 2
        assert result is not None

    def test_repeat_detection(self):
        guard = LoopGuard(max_iterations=10, repeat_threshold=3)
        guard.start()
        guard.check("hello")
        guard.check("hello")
        result = guard.check("hello")  # 3rd repeat triggers
        assert result is not None


class TestApprovalHandler:
    """Approval handler tests."""

    def test_read_never_needs_approval(self):
        handler = ApprovalHandler()
        assert handler.needs_approval("read") is False

    def test_write_needs_approval_by_default(self):
        handler = ApprovalHandler()
        assert handler.needs_approval("write") is True

    def test_write_skips_after_allow_all(self):
        handler = ApprovalHandler()
        handler.allow_all()
        assert handler.needs_approval("write") is False

    def test_dangerous_always_needs_approval(self):
        handler = ApprovalHandler()
        assert handler.needs_approval("dangerous") is True
        handler.allow_all()
        assert handler.needs_approval("dangerous") is True

    def test_parse_allow(self):
        handler = ApprovalHandler()
        assert handler.parse_response("y", "write") == ApprovalDecision.ALLOW
        assert handler.parse_response("", "write") == ApprovalDecision.ALLOW

    def test_parse_deny(self):
        handler = ApprovalHandler()
        assert handler.parse_response("n", "write") == ApprovalDecision.DENY

    def test_parse_allow_all(self):
        handler = ApprovalHandler()
        assert handler.parse_response("a", "write") == ApprovalDecision.ALLOW_ALL

    def test_allow_all_not_available_for_dangerous(self):
        handler = ApprovalHandler()
        assert handler.parse_response("a", "dangerous") == ApprovalDecision.ALLOW

    def test_build_prompt(self):
        handler = ApprovalHandler()
        req = ApprovalRequest(
            tool_name="write_file",
            tool_description="Write to file",
            risk="write",
            arguments={"path": "test.txt", "content": "hello"},
        )
        prompt = handler.build_prompt(req)
        assert "write_file" in prompt
        assert "test.txt" in prompt
        assert "[Y]" in prompt


class TestToolRiskLevels:
    """Verify builtin tool risk levels."""

    def test_search_is_read(self):
        assert registry.get("web_search").risk == "read"

    def test_read_file_is_read(self):
        assert registry.get("read_file").risk == "read"

    def test_write_file_is_write(self):
        assert registry.get("write_file").risk == "write"

    def test_list_files_is_read(self):
        assert registry.get("list_files").risk == "read"

    def test_python_is_dangerous(self):
        assert registry.get("execute_python").risk == "dangerous"


class TestAgentIntegration:
    """Agent integration tests (require API Key)."""

    @pytest.mark.skip(reason="Requires API key")
    async def test_simple_question(self):
        agent = Agent(verbose=False)
        agent.approval.allow_all()
        reply = await agent.run("Say exactly: hello")
        assert isinstance(reply, str)
        assert len(reply) > 0

    @pytest.mark.skip(reason="Requires API key")
    async def test_uses_tool(self):
        agent = Agent(verbose=False)
        agent.approval.allow_all()
        reply = await agent.run("What is 2+2? Use the execute_python tool.")
        assert isinstance(reply, str)
        assert len(reply) > 0

    @pytest.mark.skip(reason="Requires API key")
    async def test_approval_deny(self):
        async def deny_callback(req):
            return "n"

        agent = Agent(verbose=False, approval_callback=deny_callback)
        reply = await agent.run("Create a file named test.txt")
        assert isinstance(reply, str)
