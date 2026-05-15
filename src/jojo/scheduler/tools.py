"""
定时任务工具 — 注册为 Agent Tool，对话中管理定时任务。
"""

from src.jojo.tools.base import tool
from src.jojo.scheduler.engine import engine


@tool(
    "add_cron_job",
    "添加一个定时任务。name=任务名, cron=Cron表达式(如'0 9 * * *'), task=任务描述",
    risk="write",
)
async def add_cron_job(name: str, cron: str, task: str) -> str:
    """Agent 可调用的添加定时任务工具。"""
    try:
        job = engine.add_job(name=name, cron=cron, task=task)
        return (
            f"定时任务已添加:\n"
            f"  名称: {job.name}\n"
            f"  时间: {job.cron}\n"
            f"  任务: {job.task}\n"
            f"  ID: {job.id}"
        )
    except Exception as e:
        return f"添加失败: {e}"


@tool(
    "remove_cron_job",
    "按名称移除一个定时任务。name=任务名",
    risk="write",
)
async def remove_cron_job(name: str) -> str:
    """Agent 可调用的移除定时任务工具。"""
    if engine.remove_by_name(name):
        return f"定时任务 '{name}' 已移除"
    return f"未找到任务 '{name}'"


@tool(
    "list_cron_jobs",
    "列出所有已设置的定时任务",
    risk="read",
)
async def list_cron_jobs() -> str:
    """Agent 可调用的列出定时任务工具。"""
    jobs = engine.list_jobs()
    if not jobs:
        return "当前没有定时任务"

    lines = ["当前定时任务:"]
    for j in jobs:
        status = "启用" if j.enabled else "停用"
        lines.append(
            f"  [{j.name}] {j.cron} → {j.agent}: {j.task} ({status})"
        )
    return "\n".join(lines)
