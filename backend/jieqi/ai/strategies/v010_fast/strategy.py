"""
v010_fast - 快速评估 AI

ID: v010
名称: Fast AI
描述: 使用 BitBoard 快速评估，结合最佳策略

改进方向：性能优化
- 使用 BitBoard 快速评估
- 结合 v007 reveal 策略的优点
- 快速子力计算
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.bitboard import FastMoveGenerator
from jieqi.types import Color, PieceType, GameResult, Position

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.types import JieqiMove
    from jieqi.piece import JieqiPiece


AI_ID = "v010"
AI_NAME = "fast"


# 棋子价值表
PIECE_VALUES = {
    PieceType.KING: 10000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

HIDDEN_PIECE_VALUE = 320


def get_piece_value(piece: JieqiPiece) -> int:
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


@AIEngine.register(AI_NAME)
class FastAI(AIStrategy):
    """快速评估 AI

    使用 BitBoard 加速评估
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "快速评估策略 (v010)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        my_color = game.current_turn
        best_moves: list[JieqiMove] = []
        best_score = float("-inf")

        # 创建快速走法生成器
        fast_gen = FastMoveGenerator(game.board)

        for move in legal_moves:
            score = self._evaluate_move_fast(game, move, my_color, fast_gen)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move_fast(
        self,
        game: JieqiGame,
        move: JieqiMove,
        my_color: Color,
        fast_gen: FastMoveGenerator,
    ) -> float:
        score = 0.0

        target = game.board.get_piece(move.to_pos)

        # 1. 吃子得分
        if target is not None and target.color != my_color:
            capture_value = get_piece_value(target)
            score += capture_value

            if target.actual_type == PieceType.KING:
                return 100000

        piece = game.board.get_piece(move.from_pos)
        if piece is None:
            return score

        was_hidden = piece.is_hidden
        captured = game.board.make_move(move)

        # 2. 检查获胜
        result = game.board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            game.board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            game.board.undo_move(move, captured, was_hidden)
            return 100000

        # 3. 将军加分（使用快速检测）
        fast_gen.invalidate_cache()  # 重置缓存
        if fast_gen.is_in_check_fast(my_color.opposite):
            score += 60

        # 4. 安全性评估（快速版）
        moved_piece = game.board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)

            # 检查是否被攻击
            if fast_gen.is_attacked_by(move.to_pos, my_color.opposite):
                # 检查是否有保护
                has_defender = False
                for ally in game.board.get_all_pieces(my_color):
                    if ally.position != move.to_pos:
                        potential = ally.get_potential_moves(game.board)
                        if move.to_pos in potential:
                            has_defender = True
                            break

                if has_defender:
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            # 保护车
            if moved_piece.is_revealed and moved_piece.actual_type == PieceType.ROOK:
                if fast_gen.is_attacked_by(move.to_pos, my_color.opposite):
                    score -= 150

        # 5. 揭子策略（来自 v007）
        if was_hidden:
            # 计算隐藏棋子数量判断阶段
            my_hidden = len(game.board.get_hidden_pieces(my_color))
            enemy_hidden = len(game.board.get_hidden_pieces(my_color.opposite))
            total_hidden = my_hidden + enemy_hidden

            if total_hidden >= 20:
                phase_multiplier = 0.7
            elif total_hidden >= 10:
                phase_multiplier = 1.0
            else:
                phase_multiplier = 1.5

            # 安全性评估
            if not fast_gen.is_attacked_by(move.to_pos, my_color.opposite):
                base_reveal_bonus = 25
            else:
                # 检查保护
                has_defender = False
                for ally in game.board.get_all_pieces(my_color):
                    if ally.position != move.to_pos:
                        potential = ally.get_potential_moves(game.board)
                        if move.to_pos in potential:
                            has_defender = True
                            break

                if has_defender:
                    base_reveal_bonus = 10
                else:
                    base_reveal_bonus = -40

            score += base_reveal_bonus * phase_multiplier

        # 6. 检查危险棋子
        for ally in game.board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            if fast_gen.is_attacked_by(ally.position, my_color.opposite):
                # 检查是否有保护
                has_defender = False
                for other_ally in game.board.get_all_pieces(my_color):
                    if other_ally.position != ally.position:
                        potential = other_ally.get_potential_moves(game.board)
                        if ally.position in potential:
                            has_defender = True
                            break
                if not has_defender:
                    score -= ally_value * 0.1

        game.board.undo_move(move, captured, was_hidden)

        return score
