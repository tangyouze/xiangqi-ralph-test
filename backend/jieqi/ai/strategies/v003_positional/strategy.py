"""
v003_positional - 位置评估 AI 策略

ID: v003
名称: Positional AI
描述: 在 Greedy 基础上增加位置评估，棋子在不同位置有不同价值

改进方向：位置评估
- 中心位置更有价值
- 过河棋子加分
- 靠近对方将的位置加分
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


AI_ID = "v003"
AI_NAME = "positional"


# 棋子基础价值
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
    """获取棋子基础价值"""
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def get_position_bonus(piece: JieqiPiece, pos: Position) -> float:
    """获取位置加成

    评估因素：
    1. 中心控制 - 中间列更有价值
    2. 过河加分 - 过河后战力增强
    3. 前进加分 - 靠近对方更有威胁
    """
    bonus = 0.0
    color = piece.color

    # 1. 中心控制（第3-5列更有价值）
    center_bonus = 0
    if 3 <= pos.col <= 5:
        center_bonus = 10
    elif 2 <= pos.col <= 6:
        center_bonus = 5

    # 2. 过河加分
    crossed_river = False
    if color == Color.RED and pos.row >= 5:
        crossed_river = True
    elif color == Color.BLACK and pos.row <= 4:
        crossed_river = True

    cross_bonus = 20 if crossed_river else 0

    # 3. 前进加分（靠近对方更有威胁）
    if color == Color.RED:
        advance_bonus = pos.row * 2  # 越靠近黑方越好
    else:
        advance_bonus = (9 - pos.row) * 2  # 越靠近红方越好

    # 特殊棋子的位置修正
    if piece.is_revealed:
        if piece.actual_type == PieceType.PAWN:
            # 兵过河后更有价值
            cross_bonus = 30 if crossed_river else 0
        elif piece.actual_type == PieceType.ROOK:
            # 车在中间列更强
            center_bonus *= 2
        elif piece.actual_type == PieceType.CANNON:
            # 炮在后方更强（远程攻击）
            if color == Color.RED:
                advance_bonus = (9 - pos.row) * 1.5
            else:
                advance_bonus = pos.row * 1.5

    bonus = center_bonus + cross_bonus + advance_bonus
    return bonus


@AIEngine.register(AI_NAME)
class PositionalAI(AIStrategy):
    """位置评估 AI

    在 Greedy 基础上增加位置评估
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "位置评估策略，考虑棋子位置价值 (v003)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        """选择得分最高的走法"""
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
        """评估走法得分"""
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
            score += 50

        # 4. 位置评估变化
        moved_piece = game.board.get_piece(move.to_pos)
        if moved_piece:
            old_pos_bonus = get_position_bonus(piece, move.from_pos)
            new_pos_bonus = get_position_bonus(moved_piece, move.to_pos)
            score += (new_pos_bonus - old_pos_bonus)

        # 5. 被吃风险
        if moved_piece:
            for enemy_piece in game.board.get_all_pieces(my_color.opposite):
                if move.to_pos in enemy_piece.get_potential_moves(game.board):
                    my_piece_value = get_piece_value(moved_piece)
                    score -= my_piece_value * 0.3
                    break

        # 6. 揭子加分
        if was_hidden:
            score += 10

        game.board.undo_move(move, captured, was_hidden)

        return score
