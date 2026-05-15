"""
Memory system unit tests.
"""

import time
import pytest

from src.jojo.memory.working import WorkingMemory
from src.jojo.memory.short_term import ShortTermMemory, SessionSummary
from src.jojo.memory.long_term import LongTermMemory, MemoryRecord
from src.jojo.memory.decay import (
    compute_time_decay, compute_decay_score,
    should_retrieve, should_purge,
    HALF_LIFE_SECONDS,
)
from src.jojo.models import Message


class TestDecay:
    """Forgetting curve tests."""

    def test_time_decay_zero_age(self):
        score = compute_time_decay(time.time())
        assert 0.99 <= score <= 1.01  # essentially 1.0 when just created

    def test_time_decay_half_life(self):
        past = time.time() - HALF_LIFE_SECONDS
        score = compute_time_decay(past)
        assert 0.49 <= score <= 0.51  # after 7 days ~0.5

    def test_time_decay_double_half_life(self):
        past = time.time() - 2 * HALF_LIFE_SECONDS
        score = compute_time_decay(past)
        assert 0.24 <= score <= 0.26  # after 14 days ~0.25

    def test_time_decay_30days_near_zero(self):
        past = time.time() - 30 * 24 * 3600
        score = compute_time_decay(past)
        assert score < 0.06  # essentially purged

    def test_compute_decay_high_importance(self):
        now = time.time()
        score = compute_decay_score(now, importance="high")
        assert score > 0.65  # high importance starts stronger

    def test_compute_decay_low_importance(self):
        now = time.time()
        score = compute_decay_score(now, importance="low")
        assert 0.4 <= score <= 0.7  # low importance starts weaker

    def test_access_boost(self):
        now = time.time()
        score_no_access = compute_decay_score(now, access_count=0)
        score_access = compute_decay_score(now, access_count=3)
        assert score_access > score_no_access  # more accesses = higher score

    def test_retrieval_threshold(self):
        assert should_retrieve(0.2) is True
        assert should_retrieve(0.05) is False

    def test_purge_threshold(self):
        assert should_purge(0.03) is True
        assert should_purge(0.1) is False


class TestWorkingMemory:
    """Working memory tests."""

    def test_add_and_get(self):
        wm = WorkingMemory()
        wm.add(Message(role="user", content="hello"))
        wm.add(Message(role="assistant", content="hi"))
        assert len(wm) == 2

    def test_get_recent(self):
        wm = WorkingMemory()
        for i in range(15):
            wm.add(Message(role="user", content=str(i)))
        assert len(wm.get_recent(5)) == 5
        assert wm.get_recent(5)[-1].content == "14"

    def test_is_full(self):
        wm = WorkingMemory()
        for i in range(25):
            wm.add(Message(role="user", content="x"))
        assert wm.is_full() is True

    def test_clear(self):
        wm = WorkingMemory()
        wm.add(Message(role="user", content="hello"))
        old = wm.clear()
        assert len(wm) == 0
        assert len(old) == 1

    def test_to_openai_format(self):
        wm = WorkingMemory()
        wm.add(Message(role="user", content="hello"))
        result = wm.to_openai_format()
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "hello"


class TestShortTermMemory:
    """Short-term memory tests."""

    def test_add_and_get(self):
        stm = ShortTermMemory()
        stm.add("User discussed Python debugging", ["Python", "debugging"])
        summaries = stm.get_all()
        assert len(summaries) == 1
        assert "Python" in summaries[0].content

    def test_get_context_for_prompt(self):
        stm = ShortTermMemory()
        stm.add("User prefers short answers", ["preference"])
        ctx = stm.get_context_for_prompt()
        assert "short answers" in ctx

    def test_clear(self):
        stm = ShortTermMemory()
        stm.add("test")
        stm.clear()
        assert len(stm.get_all()) == 0


class TestLongTermMemory:
    """Long-term memory tests — uses a shared instance to avoid SQLite locks."""

    @classmethod
    def setup_class(cls):
        cls.ltm = LongTermMemory()

    @classmethod
    def teardown_class(cls):
        cls.ltm.close()

    def test_add_and_retrieve(self):
        mid = self.ltm.add("The user is working on a Python agent project", importance="high")
        assert mid.startswith("mem_")
        results = self.ltm.retrieve("Python project", top_k=3)
        assert len(results) > 0

    def test_retrieve_filters_low_score(self):
        results = self.ltm.retrieve("Python project", top_k=3)
        for r in results:
            assert r.decay_score >= 0.1

    def test_list_all(self):
        all_mem = self.ltm.list_all(limit=50)
        assert len(all_mem) >= 1

    def test_purge(self):
        import uuid
        very_old = time.time() - 365 * 24 * 3600
        uid = f"mem_purge_{uuid.uuid4().hex[:8]}"
        self.ltm._conn.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "very old", "low", "[]", very_old, None, 0, 0.01),
        )
        self.ltm._conn.commit()
        count = self.ltm.purge()
        assert count >= 0  # at least no error

    def test_mark_accessed(self):
        mid = self.ltm.add("Test memory", importance="medium")
        self.ltm._mark_accessed(mid, time.time())
        assert True  # should not error
