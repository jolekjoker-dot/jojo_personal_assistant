"""
CronJob 数据模型。
"""

from dataclasses import dataclass, field
import time


@dataclass
class CronJob:
    """一个定时任务。"""
    id: str                              # 唯一 ID
    name: str                            # 任务名称
    cron: str                            # Cron 表达式 "0 9 * * *"
    task: str                            # 任务描述
    agent: str = "researcher"            # 执行 Agent
    enabled: bool = True                 # 是否启用
    created_at: float = field(default_factory=time.time)
    last_run_at: float | None = None
    run_count: int = 0
