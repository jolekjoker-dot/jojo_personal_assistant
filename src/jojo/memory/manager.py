"""
MemoryManager — 统一记忆管理接口。

协调三层记忆:
  L1 (Working):   当前对话消息历史
  L2 (ShortTerm): 会话摘要
  L3 (LongTerm):  持久化记忆 (SQLite + ChromaDB)

Agent 通过此接口操作记忆，不直接接触底层实现。
"""

from src.jojo.models import Message
from src.jojo.llm import LLMProvider
from src.jojo.memory.working import WorkingMemory
from src.jojo.memory.short_term import ShortTermMemory
from src.jojo.memory.long_term import LongTermMemory, MemoryRecord
from src.jojo.logger import logger


class MemoryManager:
    """
    记忆管理器。

    Usage:
        mem = MemoryManager()
        mem.add_user_message("帮我查一下")
        mem.add_assistant_message("好的...")

        # 检索相关长期记忆
        recalls = mem.recall("Python 调试")

        # 构建注入 Prompt 的记忆上下文
        context = mem.build_context("Python 调试")
    """

    def __init__(self):
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    # ========== L1: 工作记忆 ==========

    def add_user_message(self, content: str) -> None:
        self.working.add(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        self.working.add(Message(role="assistant", content=content))

    def add_tool_message(self, content: str, tool_call_id: str = "") -> None:
        self.working.add(Message(
            role="tool", content=content, tool_call_id=tool_call_id,
        ))

    def get_working_messages(self) -> list[Message]:
        return self.working.get_all()

    # ========== L2: 短期记忆压缩 ==========

    async def compress_if_needed(self) -> str | None:
        """
        如果工作记忆超过阈值，触发 LLM 摘要压缩。

        Returns:
            生成的摘要文本，或 None（未触发压缩）。
        """
        if not self.working.is_full():
            return None

        logger.info("Working memory full, compressing...")
        old_messages = self.working.clear()

        # 保留最近 5 条
        recent = old_messages[-5:]
        for msg in recent:
            self.working.add(msg)

        # LLM 摘要
        summary = await self._summarize(old_messages[:-5])
        self.short_term.add(summary)

        # 提取关键信息存入长期记忆
        key_points = await self._extract_key_points(old_messages)
        for point in key_points:
            imp = point.get("importance", "medium")
            self.long_term.add(
                content=point["content"],
                importance=imp,
            )

        return summary

    # ========== L3: 长期记忆 ==========

    def recall(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """从长期记忆检索。"""
        return self.long_term.retrieve(query, top_k=top_k)

    def remember(
        self,
        content: str,
        importance: str = "medium",
        tags: list[str] | None = None,
    ) -> str:
        """主动存入一条长期记忆。"""
        return self.long_term.add(content, importance=importance, tags=tags)

    # ========== 上下文构建 ==========

    def build_context(self, query: str = "") -> str:
        """
        构建可注入 System Prompt 的记忆上下文。

        合并: 短期摘要 + 长期记忆检索结果
        """
        parts = []

        # 短期摘要
        short_ctx = self.short_term.get_context_for_prompt()
        if short_ctx:
            parts.append(short_ctx)

        # 长期记忆
        if query:
            recalls = self.recall(query, top_k=3)
            if recalls:
                lines = ["\n## Long-Term Memories"]
                for i, rec in enumerate(recalls):
                    lines.append(
                        f"{i+1}. [{rec.importance.upper()}] {rec.content}"
                    )
                parts.append("\n".join(lines))

        return "\n".join(parts) if parts else ""

    # ========== LLM 辅助 ==========

    async def _summarize(self, messages: list[Message]) -> str:
        """用 LLM 生成对话摘要。"""
        llm = LLMProvider()
        dialog = "\n".join(
            f"[{m.role}] {m.content[:200]}" for m in messages
        )
        prompt = (
            "Summarize the following conversation in 2-3 sentences, "
            "capturing the user's intent, key decisions, and outcomes:\n\n"
            f"{dialog}\n\nSummary:"
        )
        try:
            return llm.chat([{"role": "user", "content": prompt}], max_tokens=200)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "(summary unavailable)"

    async def _extract_key_points(self, messages: list[Message]) -> list[dict]:
        """用 LLM 从对话中提取可长期保留的关键信息。"""
        llm = LLMProvider()
        dialog = "\n".join(
            f"[{m.role}] {m.content[:200]}" for m in messages
        )
        prompt = (
            "Extract key facts, user preferences, and decisions from this "
            "conversation. Output JSON array: "
            '[{"content": "...", "importance": "high|medium|low"}]\n\n'
            f"{dialog}\n\nJSON:"
        )
        try:
            result = llm.chat([{"role": "user", "content": prompt}], max_tokens=300)
            import json
            # 清理可能包裹的 markdown 代码块
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1]
                if result.endswith("```"):
                    result = result[:-3]
            return json.loads(result)
        except Exception as e:
            logger.error(f"Key point extraction failed: {e}")
            return []

    # ========== 维护 ==========

    def purge(self) -> int:
        """淘汰长期记忆中衰减过低的记录。"""
        return self.long_term.purge()
