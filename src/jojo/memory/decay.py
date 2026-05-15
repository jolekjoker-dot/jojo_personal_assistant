"""
遗忘曲线 — 轻量三因子记忆衰减模型。

decay_score = time_decay(0.4) + access_boost(0.3) + importance(0.3)

规则:
  - time_decay:   半衰期 7 天，30 天未访问 → 分数归零
  - access_boost: 每次被检索命中 → +0.2（上限 1.0）
  - importance:   LLM 标记 high(1.0) / medium(0.6) / low(0.3)

检索: decay_score < 0.1 → 跳过
清理: decay_score < 0.05 → 永久删除
"""

import time
import math


# 半衰期（秒）
HALF_LIFE_SECONDS = 7 * 24 * 3600   # 7 天
# 淘汰阈值
RETRIEVAL_THRESHOLD = 0.1
PURGE_THRESHOLD = 0.05

# 重要性权重映射
IMPORTANCE_WEIGHTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.15,
}


def compute_time_decay(created_at: float, now: float | None = None) -> float:
    """
    指数衰减，半衰期 7 天。

    decay = 2^(-t / half_life)
    t=0   → 1.0  (刚刚创建)
    t=7d  → 0.5
    t=14d → 0.25
    t=30d → 0.05 (接近淘汰)
    """
    now = now or time.time()
    elapsed = now - created_at
    return math.pow(2, -elapsed / HALF_LIFE_SECONDS)


def compute_decay_score(
    created_at: float,
    access_count: int = 0,
    importance: str = "medium",
    last_accessed_at: float | None = None,
    now: float | None = None,
) -> float:
    """
    计算综合衰减分数。

    Args:
        created_at: 记忆创建时间戳
        access_count: 被检索命中的次数
        importance: "high" | "medium" | "low"
        last_accessed_at: 上次被命中的时间戳
        now: 当前时间戳

    Returns:
        0.0 ~ 1.0 的衰减分数，越高越"鲜活"
    """
    now = now or time.time()

    # 1. 时间衰减 (权重 0.4)
    time_decay = compute_time_decay(created_at, now)

    # 2. 访问强化 (权重 0.3)
    # 每次被检索命中 +0.25，上限 1.0，无保底分
    # 一直没人访问的记忆 → access_score = 0
    access_score = min(1.0, access_count * 0.25)
    if last_accessed_at and (now - last_accessed_at) < HALF_LIFE_SECONDS:
        access_score = min(1.0, access_score + 0.3)  # 近期访问加成

    # 3. 重要性 (权重 0.3)
    importance_score = IMPORTANCE_WEIGHTS.get(importance, 0.6)

    # 加权求和
    score = time_decay * 0.4 + access_score * 0.3 + importance_score * 0.3

    return round(score, 4)


def should_retrieve(score: float) -> bool:
    """是否应该在检索时返回。"""
    return score >= RETRIEVAL_THRESHOLD


def should_purge(score: float) -> bool:
    """是否应该永久删除。"""
    return score < PURGE_THRESHOLD
