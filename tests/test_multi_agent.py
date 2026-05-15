"""
Multi-agent orchestration tests.
"""

import pytest

from src.jojo.orchestrator.registry import AgentRegistry
from src.jojo.orchestrator.classifier import TaskClassifier
from src.jojo.orchestrator.router import Router
from src.jojo.agents import create_researcher, create_coder


class TestAgentRegistry:
    """Agent registry tests."""

    def test_register_and_list(self):
        reg = AgentRegistry()
        r = create_researcher()
        c = create_coder()
        reg.register(r)
        reg.register(c)
        assert len(reg) == 2
        names = [a["name"] for a in reg.list_all()]
        assert "researcher" in names
        assert "coder" in names

    def test_get(self):
        reg = AgentRegistry()
        reg.register(create_researcher())
        agent = reg.get("researcher")
        assert agent is not None
        assert agent.name == "researcher"

    def test_get_missing(self):
        reg = AgentRegistry()
        assert reg.get("nonexistent") is None

    def test_find_best_for_default(self):
        reg = AgentRegistry()
        reg.register(create_researcher())
        agent = reg.find_best_for("any task")
        assert agent.name == "researcher"


class TestTaskClassifier:
    """Task complexity classifier tests."""

    @pytest.mark.asyncio
    async def test_trivial_input_is_simple(self):
        c = TaskClassifier()
        result = await c.classify("hi")
        assert result == "simple"

    @pytest.mark.asyncio
    async def test_very_short_is_simple(self):
        c = TaskClassifier()
        result = await c.classify("hello")
        assert result == "simple"

    @pytest.mark.asyncio
    async def test_get_model_for_simple(self):
        c = TaskClassifier()
        model = c.get_model_for("simple")
        assert "deepseek" in model

    @pytest.mark.asyncio
    async def test_get_model_for_complex(self):
        c = TaskClassifier()
        model = c.get_model_for("complex")
        assert "deepseek" in model


class TestRouter:
    """LLM-based router tests."""

    @pytest.mark.skip(reason="Requires API key")
    @pytest.mark.asyncio
    async def test_route_to_researcher(self):
        router = Router()
        agents = [
            {"name": "researcher", "description": "Searches the web"},
            {"name": "coder", "description": "Writes code and files"},
        ]
        name = await router.route("search for latest AI news", agents)
        assert name == "researcher"

    @pytest.mark.skip(reason="Requires API key")
    @pytest.mark.asyncio
    async def test_route_to_coder(self):
        router = Router()
        agents = [
            {"name": "researcher", "description": "Searches the web"},
            {"name": "coder", "description": "Writes code and files"},
        ]
        name = await router.route("write a sorting function", agents)
        assert name == "coder"


class TestPresetAgents:
    """Preset agent creation tests."""

    def test_create_researcher(self):
        agent = create_researcher()
        assert agent.name == "researcher"
        assert "search" in agent.description.lower() or "research" in agent.description.lower()

    def test_create_coder(self):
        agent = create_coder()
        assert agent.name == "coder"
        assert "code" in agent.description.lower()
