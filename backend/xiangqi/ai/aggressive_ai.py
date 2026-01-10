"""
进攻型 AI 策略

侧重进攻，优先考虑吃子和将军
"""

import random
from typing import ClassVar

from xiangqi.ai.base import AIConfig, AIEngine, AIStrategy
from xiangqi.ai.evaluator import Evaluator
from xiangqi.game import Game
from xiangqi.types import Move


@AIEngine.register
class AggressiveAI(AIStrategy):
    """进攻型 AI

    优先考虑：
    1. 将军对方
    2. 吃子（优先吃高价值棋子）
    3. 推进棋子到更有利位置
    """

    name: ClassVar[str] = "aggressive"

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
            # 计算走法的进攻价值
            score = 0.0

            # 检查是否吃子
            target = game.board.get_piece(move.to_pos)
            if target:
                # 吃子得分（按棋子价值）
                score += self.evaluator.PIECE_VALUES[target.piece_type] * 2

            # 模拟走棋
            captured = game.board.make_move(move)
            game.current_turn = color.opposite

            # 检查是否将军
            if game.board.is_in_check(color.opposite):
                score += 300  # 将军加分

            # 检查是否将死
            opponent_moves = game.board.get_legal_moves(color.opposite)
            if not opponent_moves:
                score += 50000  # 将死巨额加分

            # 基础局面评估
            score += self.evaluator.evaluate(game.board, color) * 0.5

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
