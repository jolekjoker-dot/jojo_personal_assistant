"""
Token 用量跟踪 — 记录每次 LLM 调用的 Token 消耗。
"""

from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class UsageRecord:
    """单次调用的用量记录。"""
    model: str
    prompt_tokens: int
    completion_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class UsageTracker:
    """
    Token 用量跟踪器。

    跟踪每次 LLM 调用的输入/输出 Token 数，
    提供总和统计，方便观测成本。
    """

    def __init__(self):
        self.records: list[UsageRecord] = []

    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """记录一次调用。"""
        self.records.append(UsageRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ))

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self.records)

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def call_count(self) -> int:
        return len(self.records)

    def summary(self) -> str:
        """生成用量摘要。"""
        if not self.records:
            return "No LLM calls recorded."

        by_model: dict[str, dict[str, int]] = {}
        for r in self.records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "prompt": 0, "completion": 0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["prompt"] += r.prompt_tokens
            by_model[r.model]["completion"] += r.completion_tokens

        lines = [
            f"Total Calls: {self.call_count}",
            f"Total Tokens: {self.total_tokens} "
            f"(prompt: {self.total_prompt_tokens}, completion: {self.total_completion_tokens})",
            "",
            "By Model:",
        ]
        for model, stats in by_model.items():
            lines.append(
                f"  {model}: {stats['calls']} calls, "
                f"{stats['prompt'] + stats['completion']} tokens"
            )

        return "\n".join(lines)

    def reset(self) -> None:
        """重置所有统计。"""
        self.records.clear()
