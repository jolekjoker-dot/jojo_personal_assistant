"""
ShortTermMemory — 短期记忆，会话级别的摘要和关键信息。
"""

import time
from dataclasses import dataclass, field

from src.jojo.config import config


@dataclass
class SessionSummary:
    """一个会话摘要。"""
    content: str                              # 摘要文本
    key_points: list[str] = field(default_factory=list)  # 关键决策/事实
    created_at: float = field(default_factory=time.time)


class ShortTermMemory:
    """
    短期记忆 — 内存缓存中的会话摘要。

    生命周期: 单次会话（进程存活期间）。
    当 WorkingMemory 超过阈值时触发压缩 → LLM 生成摘要存入这里。
    提供 TTL 过期清理（默认 1 小时）。
    """

    def __init__(self):
        self._summaries: list[SessionSummary] = []
        self._ttl_seconds = config.memory.short_term_ttl_seconds

    def add(self, summary: str, key_points: list[str] | None = None) -> None:
        """存入一份摘要。"""
        self._summaries.append(SessionSummary(
            content=summary,
            key_points=key_points or [],
        ))

    def get_recent(self, n: int = 3) -> list[SessionSummary]:
        """返回最近 n 份摘要。"""
        self._expire()
        return self._summaries[-n:]

    def get_all(self) -> list[SessionSummary]:
        """返回所有未过期的摘要。"""
        self._expire()
        return self._summaries

    def get_context_for_prompt(self, max_chars: int = 500) -> str:
        """生成可注入 System Prompt 的上下文片段。"""
        summaries = self.get_recent(2)
        if not summaries:
            return ""

        parts = ["## Recent Context"]
        total = 0
        for s in summaries:
            text = f"- {s.content}"
            if total + len(text) > max_chars:
                parts.append(text[:max_chars - total] + "...")
                break
            parts.append(text)
            total += len(text)

        return "\n".join(parts)

    def _expire(self) -> None:
        """清理过期的摘要。"""
        now = time.time()
        cutoff = now - self._ttl_seconds
        self._summaries = [s for s in self._summaries if s.created_at > cutoff]

    def clear(self) -> None:
        """清空所有。"""
        self._summaries.clear()
