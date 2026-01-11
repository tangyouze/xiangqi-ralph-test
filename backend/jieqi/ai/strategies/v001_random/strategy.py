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
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.types import JieqiMove


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

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        """从合法走法中随机选择一个"""
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None
        return self._rng.choice(legal_moves)
