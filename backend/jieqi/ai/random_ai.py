"""
随机 AI 策略

从所有合法走法中随机选择一个
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.types import JieqiMove


@AIEngine.register("random")
class RandomAI(AIStrategy):
    """随机 AI

    随机选择一个合法走法，无任何策略考量。
    适合作为基础测试对手。
    """

    description = "随机选择合法走法"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        # 使用独立的 Random 实例以避免全局状态问题
        self._rng = random.Random(self.config.seed)

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        """从合法走法中随机选择一个

        Args:
            game: 当前游戏状态

        Returns:
            随机选择的走法，如果没有合法走法则返回 None
        """
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None
        return self._rng.choice(legal_moves)
