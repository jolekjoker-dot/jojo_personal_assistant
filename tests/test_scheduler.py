"""
Scheduler unit tests.
"""

import pytest
from src.jojo.scheduler.models import CronJob
from src.jojo.scheduler.store import JobStore
from src.jojo.scheduler.engine import SchedulerEngine


class TestCronJob:
    """CronJob model tests."""

    def test_create_job(self):
        job = CronJob(
            id="test-1", name="weather", cron="0 9 * * *",
            task="播报天气", agent="researcher",
        )
        assert job.name == "weather"
        assert job.cron == "0 9 * * *"
        assert job.enabled is True

    def test_job_defaults(self):
        job = CronJob(id="test-2", name="test", cron="* * * * *", task="test")
        assert job.agent == "researcher"
        assert job.enabled is True
        assert job.run_count == 0


class TestJobStore:
    """Job persistence tests."""

    def setup_method(self):
        self.store = JobStore()

    def test_save_and_get(self):
        job = CronJob(id="j1", name="weather", cron="30 9 * * *",
                      task="昆明呈贡区天气", agent="researcher")
        self.store.save(job)
        loaded = self.store.get("j1")
        assert loaded is not None
        assert loaded.name == "weather"
        assert loaded.cron == "30 9 * * *"

    def test_list_all(self):
        self.store.save(CronJob(id="j2", name="a", cron="0 8 * * *", task="x"))
        self.store.save(CronJob(id="j3", name="b", cron="0 9 * * *", task="y"))
        jobs = self.store.list_all()
        assert len(jobs) >= 2

    def test_delete(self):
        self.store.save(CronJob(id="j4", name="tmp", cron="* * * * *", task="x"))
        assert self.store.delete("j4") is True
        assert self.store.get("j4") is None

    def test_delete_nonexistent(self):
        assert self.store.delete("nonexistent") is False

    def test_mark_run(self):
        self.store.save(CronJob(id="j5", name="run-test", cron="* * * * *", task="x"))
        self.store.mark_run("j5")
        job = self.store.get("j5")
        assert job.run_count == 1
        assert job.last_run_at is not None


class TestSchedulerEngine:
    """Scheduler engine tests."""

    @pytest.mark.asyncio
    async def test_add_and_remove_job(self):
        engine = SchedulerEngine()
        engine.start()  # need running event loop
        job = engine.add_job("weather", "30 9 * * *",
                             "播报昆明呈贡区天气", "researcher")
        assert job.name == "weather"

        jobs = engine.list_jobs()
        assert any(j.name == "weather" for j in jobs)

        assert engine.remove_by_name("weather") is True
        # also remove persisted
        engine._store.delete(job.id)
        engine.stop()

    @pytest.mark.asyncio
    async def test_list_empty(self):
        engine = SchedulerEngine()
        engine.start()
        jobs = engine.list_jobs()
        assert isinstance(jobs, list)
        engine.stop()
