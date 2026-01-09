"""
随机 AI 策略

最简单的 AI 实现，随机选择合法走法
"""

import random
from typing import ClassVar

from xiangqi.ai.base import AIConfig, AIEngine, AIStrategy
from xiangqi.game import Game
from xiangqi.types import Move


@AIEngine.register
class RandomAI(AIStrategy):
    """随机 AI

    随机选择一个合法走法，适合用于测试和调试
    """

    name: ClassVar[str] = "random"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random()

    def select_move(self, game: Game) -> Move | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None
        return self._rng.choice(legal_moves)
