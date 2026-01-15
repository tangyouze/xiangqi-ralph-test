"""
v001_random - 随机 AI 策略

ID: v001
名称: Random AI
描述: 从所有合法走法中随机选择一个，无任何策略考量

特点:
- 完全随机，无策略
- 适合作为基础对照
- 用于测试游戏逻辑正确性
"""

from __future__ import annotations

import random

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import get_legal_moves_from_fen

AI_ID = "v001"
AI_NAME = "random"


@AIEngine.register(AI_NAME)
class RandomAI(AIStrategy):
    """随机 AI

    随机选择一个合法走法，无任何策略考量。
    适合作为基础测试对手。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "随机选择合法走法 (v001)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """从合法走法中随机选择 n 个"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        # 随机选择最多 n 个走法
        selected = self._rng.sample(legal_moves, min(n, len(legal_moves)))
        # 所有走法评分相同（随机策略）
        return [(move, 0.0) for move in selected]
