"""
v006_balanced - 综合平衡 AI

ID: v006
名称: Balanced AI
描述: 综合 Defensive + Positional，平衡攻防

改进方向：综合平衡
- 防守为主 (来自 v004)
- 位置评估 (来自 v003)
- 适度进攻
- 棋子协调
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.types import Color, PieceType, GameResult, Position

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.types import JieqiMove
    from jieqi.piece import JieqiPiece


AI_ID = "v006"
AI_NAME = "balanced"


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


def count_attackers(game: JieqiGame, pos, color: Color) -> int:
    count = 0
    for enemy in game.board.get_all_pieces(color.opposite):
        if pos in enemy.get_potential_moves(game.board):
            count += 1
    return count


def count_defenders(game: JieqiGame, pos, color: Color) -> int:
    count = 0
    for ally in game.board.get_all_pieces(color):
        if ally.position != pos and pos in ally.get_potential_moves(game.board):
            count += 1
    return count


def get_position_bonus(piece: JieqiPiece, pos: Position) -> float:
    """位置加成（来自 v003）"""
    bonus = 0.0
    color = piece.color

    # 中心控制
    if 3 <= pos.col <= 5:
        bonus += 8
    elif 2 <= pos.col <= 6:
        bonus += 4

    # 过河加分
    crossed_river = False
    if color == Color.RED and pos.row >= 5:
        crossed_river = True
    elif color == Color.BLACK and pos.row <= 4:
        crossed_river = True

    if crossed_river:
        bonus += 15

    # 前进加分
    if color == Color.RED:
        bonus += pos.row * 1.5
    else:
        bonus += (9 - pos.row) * 1.5

    return bonus


@AIEngine.register(AI_NAME)
class BalancedAI(AIStrategy):
    """综合平衡 AI

    结合防守、位置和适度进攻
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "综合平衡策略 (v006)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        my_color = game.current_turn
        best_moves: list[JieqiMove] = []
        best_score = float('-inf')

        for move in legal_moves:
            score = self._evaluate_move(game, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move(self, game: JieqiGame, move: JieqiMove, my_color: Color) -> float:
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

        # 3. 将军加分
        if game.board.is_in_check(my_color.opposite):
            score += 60

        # 4. 防守评估（核心，来自 v004）
        moved_piece = game.board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(game, move.to_pos, my_color)
            defenders = count_defenders(game, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            # 保护车
            if moved_piece.is_revealed and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 5. 位置评估（来自 v003）
        if moved_piece:
            old_pos_bonus = get_position_bonus(piece, move.from_pos)
            new_pos_bonus = get_position_bonus(moved_piece, move.to_pos)
            score += (new_pos_bonus - old_pos_bonus) * 0.5  # 降低权重

        # 6. 检查危险棋子
        for ally in game.board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            attackers = count_attackers(game, ally.position, my_color)
            if attackers > 0:
                defenders = count_defenders(game, ally.position, my_color)
                if defenders < attackers:
                    score -= ally_value * 0.1

        # 7. 揭子策略
        if was_hidden:
            attackers = count_attackers(game, move.to_pos, my_color)
            if attackers == 0:
                score += 12
            else:
                score -= 15

        game.board.undo_move(move, captured, was_hidden)

        return score
