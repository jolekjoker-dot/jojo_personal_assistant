"""
定时任务引擎 — 基于 APScheduler，支持 Cron 表达式。
"""

import uuid
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.jojo.scheduler.models import CronJob
from src.jojo.scheduler.store import JobStore
from src.jojo.agent.react_loop import Agent
from src.jojo.orchestrator.registry import registry as agent_registry
from src.jojo.agents import create_researcher, create_coder
from src.jojo.memory.manager import MemoryManager
from src.jojo.logger import logger


class SchedulerEngine:
    """
    定时任务引擎。

    Usage:
        engine = SchedulerEngine()
        engine.start()

        # 添加任务
        engine.add_job("weather", "0 9 * * *", "播报北京天气", "researcher")

        # 移除
        engine.remove_job("my-job")
    """

    def __init__(self):
        self._aps = AsyncIOScheduler()
        self._store = JobStore()
        self._memory = MemoryManager()
        self._notifications: list[str] = []  # 通知队列

    # ========== 生命周期 ==========

    def start(self) -> None:
        """启动调度器，恢复所有持久化任务。"""
        jobs = self._store.list_all()
        for job in jobs:
            if job.enabled:
                self._schedule(job)
        self._aps.start()
        logger.info(f"Scheduler started with {len(jobs)} jobs")

    def stop(self) -> None:
        self._aps.shutdown(wait=False)
        logger.info("Scheduler stopped")

    # ========== 任务管理 ==========

    def add_job(
        self, name: str, cron: str, task: str, agent: str = "researcher"
    ) -> CronJob:
        """添加一个定时任务。"""
        job = CronJob(
            id=f"job_{uuid.uuid4().hex[:12]}",
            name=name, cron=cron, task=task, agent=agent,
        )
        self._store.save(job)
        self._schedule(job)
        logger.info(f"Job added: {name} ({cron}) → {agent}")
        return job

    def remove_job(self, job_id: str) -> bool:
        """根据 ID 移除任务。"""
        try:
            self._aps.remove_job(job_id)
        except Exception:
            pass
        deleted = self._store.delete(job_id)
        if deleted:
            logger.info(f"Job removed: {job_id}")
        return deleted

    def remove_by_name(self, name: str) -> bool:
        """根据名称移除任务。"""
        jobs = self._store.list_all()
        for job in jobs:
            if job.name == name:
                return self.remove_job(job.id)
        return False

    def list_jobs(self) -> list[CronJob]:
        return self._store.list_all()

    def pop_notifications(self) -> list[str]:
        """取出并清空当前通知队列。"""
        msgs = self._notifications[:]
        self._notifications.clear()
        return msgs

    # ========== 内部 ==========

    def _schedule(self, job: CronJob) -> None:
        """将 CronJob 注册到 APScheduler。"""
        self._aps.add_job(
            self._execute,
            trigger=CronTrigger.from_crontab(job.cron),
            id=job.id,
            name=job.name,
            kwargs={"job_id": job.id},
            replace_existing=True,
        )

    async def _execute(self, job_id: str) -> None:
        """执行定时任务。"""
        job = self._store.get(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return

        logger.info(f"Executing job: {job.name} — {job.task}")

        # Ensure agents are registered
        if len(agent_registry) == 0:
            agent_registry.register(create_researcher())
            agent_registry.register(create_coder())

        # Create agent and execute
        agent = Agent(
            name=job.agent,
            description="Scheduled task executor",
        )

        try:
            result = await agent.run(job.task)
            # Save result to long-term memory
            # 推送到聊天通知队列
            preview = result[:200] + "..." if len(result) > 200 else result
            self._notifications.append(
                f"[定时任务: {job.name}] {preview}"
            )
            # 保留最近 20 条
            if len(self._notifications) > 20:
                self._notifications = self._notifications[-20:]

            self._memory.remember(
                f"[定时任务: {job.name}] {result[:500]}",
                importance="medium",
            )
            logger.info(f"Job '{job.name}' completed: {result[:100]}...")
        except Exception as e:
            logger.error(f"Job '{job.name}' failed: {e}")

        self._store.mark_run(job_id)


# 全局单例
engine = SchedulerEngine()
