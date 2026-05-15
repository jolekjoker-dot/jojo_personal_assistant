"""
任务复杂度分类器 — Flash 模型快速判断，按复杂度选模型。
"""

from src.jojo.llm import LLMProvider
from src.jojo.config import config
from src.jojo.logger import logger


class TaskClassifier:
    """
    用 Flash 模型快速判断任务复杂度，返回对应模型。

    simple  → Flash (便宜)    — 问候、闲聊、简单问答
    medium  → Flash (省 Token) — 需要 1-2 个工具或简单搜索
    complex → Pro  (保证质量)  — 多步骤、需代码执行或文件写入
    """

    def __init__(self):
        self.llm = LLMProvider(config.orchestrator.classifier_model)

    async def classify(self, task: str) -> str:
        """判断任务复杂度，返回 simple/medium/complex。"""
        # 极短输入直接判为 simple，不调 LLM
        if len(task.strip()) < 10 and "?" not in task and "帮" not in task:
            return "simple"

        prompt = (
            "Analyze the following user request and output exactly ONE word "
            "(simple, medium, or complex):\n\n"
            "- simple: greeting, small talk, single simple question, trivial math\n"
            "- medium: needs search, file read, or 1-2 tool calls\n"
            "- complex: needs code execution, file write, or 3+ tool calls\n\n"
            f"Request: {task[:300]}\nClassification:"
        )

        try:
            result = self.llm.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            result = result.strip().lower()
            if "complex" in result:
                return "complex"
            if "simple" in result:
                return "simple"
            return "medium"
        except Exception as e:
            logger.warning(f"Classifier failed, defaulting to medium: {e}")
            return "medium"

    def get_model_for(self, complexity: str) -> str:
        """根据复杂度返回应使用的模型。"""
        if complexity == "complex":
            return config.orchestrator.pro_model
        return config.orchestrator.flash_model
