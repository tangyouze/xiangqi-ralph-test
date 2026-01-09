"""
Minimax AI 策略

带 Alpha-Beta 剪枝的 Minimax 搜索 AI
"""

import random
from typing import ClassVar

from xiangqi.ai.base import AIConfig, AIEngine, AIStrategy
from xiangqi.ai.evaluator import Evaluator
from xiangqi.game import Game
from xiangqi.types import Color, GameResult, Move


@AIEngine.register
class MinimaxAI(AIStrategy):
    """Minimax AI

    使用 Minimax 算法和 Alpha-Beta 剪枝进行搜索
    """

    name: ClassVar[str] = "minimax"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.evaluator = Evaluator()
        self._nodes_searched = 0

    def select_move(self, game: Game) -> Move | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        self._nodes_searched = 0
        color = game.current_turn
        depth = self.config.depth

        # 使用 Alpha-Beta 剪枝搜索最佳走法
        best_moves: list[tuple[Move, float]] = []
        alpha = float("-inf")
        beta = float("inf")

        # 走法排序优化：优先搜索吃子走法
        sorted_moves = self._sort_moves(game, legal_moves)

        for move in sorted_moves:
            # 模拟走棋
            captured = game.board.make_move(move)
            game.current_turn = color.opposite

            # 递归搜索
            score = -self._minimax(game, depth - 1, -beta, -alpha, color.opposite)

            # 撤销走棋
            game.board.undo_move(move, captured)
            game.current_turn = color

            best_moves.append((move, score))

            if score > alpha:
                alpha = score

        # 选择最佳走法（可能有多个相同分数）
        best_score = max(m[1] for m in best_moves)
        top_moves = [m[0] for m in best_moves if m[1] == best_score]

        # 如果配置了随机性，从最佳走法中随机选择
        if self.config.randomness > 0 and len(top_moves) > 1:
            return random.choice(top_moves)

        return top_moves[0]

    def _minimax(
        self, game: Game, depth: int, alpha: float, beta: float, maximizing_color: Color
    ) -> float:
        """Minimax 搜索，带 Alpha-Beta 剪枝

        使用 Negamax 变体简化实现
        """
        self._nodes_searched += 1

        # 检查游戏结束
        result = game.board.get_game_result(game.current_turn)
        if result != GameResult.ONGOING:
            if result == GameResult.DRAW:
                return 0
            # 被将死
            winner_color = Color.RED if result == GameResult.RED_WIN else Color.BLACK
            if winner_color == maximizing_color:
                return 10000 + depth  # 越快获胜越好
            else:
                return -10000 - depth  # 越慢被将死越好

        # 达到搜索深度，返回评估值
        if depth <= 0:
            return self.evaluator.evaluate(game.board, game.current_turn)

        legal_moves = game.board.get_legal_moves(game.current_turn)
        if not legal_moves:
            # 无合法走法但游戏未结束（应该不会发生）
            return self.evaluator.evaluate(game.board, game.current_turn)

        # 走法排序
        sorted_moves = self._sort_moves(game, legal_moves)

        best_score = float("-inf")

        for move in sorted_moves:
            # 模拟走棋
            captured = game.board.make_move(move)
            game.current_turn = game.current_turn.opposite

            # 递归搜索（Negamax）
            score = -self._minimax(game, depth - 1, -beta, -alpha, maximizing_color)

            # 撤销走棋
            game.board.undo_move(move, captured)
            game.current_turn = game.current_turn.opposite

            best_score = max(best_score, score)
            alpha = max(alpha, score)

            # Alpha-Beta 剪枝
            if alpha >= beta:
                break

        return best_score

    def _sort_moves(self, game: Game, moves: list[Move]) -> list[Move]:
        """走法排序，优化搜索效率

        优先搜索：吃子走法 > 将军走法 > 其他走法
        """

        def move_score(move: Move) -> float:
            score = 0.0
            target = game.board.get_piece(move.to_pos)
            if target is not None:
                # 吃子走法，按目标价值排序
                score += self.evaluator.PIECE_VALUES[target.piece_type]
            return score

        return sorted(moves, key=move_score, reverse=True)

    @property
    def nodes_searched(self) -> int:
        """返回上次搜索的节点数"""
        return self._nodes_searched
