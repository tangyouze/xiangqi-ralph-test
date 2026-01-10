"""
防守型 AI 策略

在贪婪策略基础上增加防守意识，会考虑自己棋子被吃的风险
"""

import random
from typing import ClassVar

from xiangqi.ai.base import AIConfig, AIEngine, AIStrategy
from xiangqi.ai.evaluator import Evaluator
from xiangqi.game import Game
from xiangqi.types import Move


@AIEngine.register
class DefensiveAI(AIStrategy):
    """防守型 AI

    考虑攻击和防守两方面：
    1. 评估走棋后己方的得分
    2. 评估对手可能的反击

    比单纯贪婪 AI 更强，因为会避免送子
    """

    name: ClassVar[str] = "defensive"

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

            # 评估走棋后的局面（己方视角）
            my_score = self.evaluator.evaluate(game.board, color)

            # 评估对手最好的反击
            opponent_moves = game.board.get_legal_moves(color.opposite)
            worst_opponent_score = 0.0

            for opp_move in opponent_moves:
                # 模拟对手走棋
                opp_captured = game.board.make_move(opp_move)
                game.current_turn = color

                # 评估对手走棋后的局面（还是己方视角）
                after_score = self.evaluator.evaluate(game.board, color)
                # 记录对我方最不利的情况
                damage = my_score - after_score
                worst_opponent_score = max(worst_opponent_score, damage)

                # 撤销对手走棋
                game.board.undo_move(opp_move, opp_captured)
                game.current_turn = color.opposite

            # 撤销己方走棋
            game.board.undo_move(move, captured)
            game.current_turn = color

            # 综合评分：当前收益 - 对手可能造成的损失
            final_score = my_score - worst_opponent_score * 0.8

            best_moves.append((move, final_score))

        # 选择最佳走法
        best_score = max(m[1] for m in best_moves)
        top_moves = [m[0] for m in best_moves if m[1] == best_score]

        # 从最佳走法中随机选择
        if len(top_moves) > 1:
            return random.choice(top_moves)

        return top_moves[0]
