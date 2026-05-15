"""
WorkingMemory — 工作记忆，当前对话窗口内的消息历史。
"""

from src.jojo.models import Message
from src.jojo.config import config


class WorkingMemory:
    """
    工作记忆 — 进程内存中的消息列表。

    生命周期: 单次 Agent.run() 调用。
    容量限制: config.memory.working_max_messages（默认 20），超出时触发压缩。
    """

    def __init__(self):
        self.messages: list[Message] = []
        self._max_messages = config.memory.working_max_messages

    def add(self, message: Message) -> None:
        """添加一条消息。"""
        self.messages.append(message)

    def get_all(self) -> list[Message]:
        """返回所有消息。"""
        return self.messages

    def get_recent(self, n: int = 10) -> list[Message]:
        """返回最近 n 条消息。"""
        return self.messages[-n:]

    def is_full(self) -> bool:
        """是否超过容量阈值，需要压缩。"""
        return len(self.messages) > self._max_messages

    def clear(self) -> list[Message]:
        """清空并返回所有消息（留给压缩器处理）。"""
        old = self.messages
        self.messages = []
        return old

    def to_openai_format(self) -> list[dict]:
        """转换为 OpenAI 消息格式。"""
        result = []
        for msg in self.messages:
            item = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            result.append(item)
        return result

    def __len__(self) -> int:
        return len(self.messages)
