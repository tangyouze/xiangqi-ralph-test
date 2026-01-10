"""
贪婪 AI 策略

只考虑当前一步的最佳走法，不进行深度搜索
"""

import random
from typing import ClassVar

from xiangqi.ai.base import AIConfig, AIEngine, AIStrategy
from xiangqi.ai.evaluator import Evaluator
from xiangqi.game import Game
from xiangqi.types import Move


@AIEngine.register
class GreedyAI(AIStrategy):
    """贪婪 AI

    只评估当前局面和走一步后的局面，选择最好的走法
    适合作为简单的 AI 对手，比随机 AI 强但比 Minimax 弱
    """

    name: ClassVar[str] = "greedy"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.evaluator = Evaluator()

    def select_move(self, game: Game) -> Move | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        color = game.current_turn
        best_moves: list[tuple[Move, float]] = []

        for move in legal_moves:
            # 模拟走棋
            captured = game.board.make_move(move)
            game.current_turn = color.opposite

            # 评估走棋后的局面
            score = self.evaluator.evaluate(game.board, color)

            # 撤销走棋
            game.board.undo_move(move, captured)
            game.current_turn = color

            best_moves.append((move, score))

        # 选择最佳走法
        best_score = max(m[1] for m in best_moves)
        top_moves = [m[0] for m in best_moves if m[1] == best_score]

        # 从最佳走法中随机选择
        if len(top_moves) > 1:
            return random.choice(top_moves)

        return top_moves[0]
