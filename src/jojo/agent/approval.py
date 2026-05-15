"""
人工审批 Hook — Agent 执行高风险工具前暂停，等待用户确认。
"""

from enum import Enum
from dataclasses import dataclass, field

from src.jojo.tools.base import RiskLevel


class ApprovalDecision(Enum):
    ALLOW = "allow"              # 单次放行
    DENY = "deny"                # 单次拒绝
    ALLOW_ALL = "allow_all"      # 本次会话全部放行


@dataclass
class ApprovalRequest:
    """一次审批请求。"""
    tool_name: str
    tool_description: str
    risk: RiskLevel
    arguments: dict
    session_allow_all: bool = False  # 用户是否已选了"全部放行"


class ApprovalHandler:
    """
    审批处理器。

    判断某个工具调用是否需要人工审批，并执行审批流程。

    规则:
    - risk="read" → 自动放行 (不需要审批)
    - risk="write" → 需要审批 (除非 session 已 allow_all)
    - risk="dangerous" → 需要审批 (总是需要)
    """

    def __init__(self):
        self._session_allow_all = False

    def needs_approval(self, risk: RiskLevel) -> bool:
        """判断给定风险等级是否需要审批。"""
        if risk == "read":
            return False  # 只读，永远不需要
        if risk == "write":
            return not self._session_allow_all  # allow_all 后跳过
        if risk == "dangerous":
            return True  # 高危操作，始终审批
        return True

    def allow_all(self) -> None:
        """设置本次会话全部放行（仅影响 risk="write"）。"""
        self._session_allow_all = True

    def build_prompt(self, req: ApprovalRequest) -> str:
        """构建审批提示文本。"""
        args_str = ", ".join(
            f"{k}={repr(v)[:60]}" for k, v in req.arguments.items()
        )

        risk_label = {"read": "[Read]", "write": "[Write]", "dangerous": "[DANGER]"}

        return (
            f"\n  {risk_label.get(req.risk, req.risk)} "
            f"Agent wants to: {req.tool_name}({args_str})\n"
            f"  [Y] Allow  [n] Deny  [a] Allow all in this session"
        )

    def parse_response(self, response: str, risk: RiskLevel) -> ApprovalDecision:
        """解析用户的审批输入。"""
        r = response.strip().lower()

        if r == "a" and risk != "dangerous":
            return ApprovalDecision.ALLOW_ALL
        if r in ("n", "no"):
            return ApprovalDecision.DENY

        return ApprovalDecision.ALLOW  # 默认允许（Y / 回车）
