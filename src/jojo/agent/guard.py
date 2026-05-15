"""
终止条件检测 — 防止 Agent 死循环。
"""

import time


class LoopGuard:
    """
    ReAct 循环守卫。

    三重保护:
    1. 最大迭代次数 (默认 10 次)
    2. 最大执行时间 (默认 120 秒)
    3. 重复检测 (连续 3 次相同输出 → 终止)
    """

    def __init__(
        self,
        max_iterations: int = 10,
        max_duration_seconds: int = 120,
        repeat_threshold: int = 3,
    ):
        self.max_iterations = max_iterations
        self.max_duration_seconds = max_duration_seconds
        self.repeat_threshold = repeat_threshold

        self.iteration_count = 0
        self.start_time: float | None = None
        self.last_responses: list[str] = []

    def start(self) -> None:
        """开始计时。"""
        self.iteration_count = 0
        self.start_time = time.monotonic()
        self.last_responses = []

    def check(self, latest_content: str) -> str | None:
        """
        检查是否应该终止。

        Returns:
            None → 继续循环
            str → 终止原因 (用于日志)
        """
        self.iteration_count += 1

        # 1. 迭代次数检查
        if self.iteration_count > self.max_iterations:
            return (
                f"达到最大迭代次数 ({self.max_iterations})，强制终止。"
            )

        # 2. 时间检查
        if self.start_time:
            elapsed = time.monotonic() - self.start_time
            if elapsed > self.max_duration_seconds:
                return f"执行超时 ({elapsed:.0f}s > {self.max_duration_seconds}s)，强制终止。"

        # 3. 重复检测
        if latest_content:
            self.last_responses.append(latest_content.strip())
            if len(self.last_responses) > self.repeat_threshold:
                self.last_responses.pop(0)

            if len(self.last_responses) >= self.repeat_threshold:
                if len(set(self.last_responses)) == 1:
                    return "检测到连续重复输出，终止循环。"

        return None
