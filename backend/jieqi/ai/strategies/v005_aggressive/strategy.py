"""
v005_aggressive - 进攻性 AI

ID: v005
名称: Aggressive AI
描述: 在防守基础上增加进攻性，主动威胁对方

改进方向：进攻性
- 威胁对方高价值棋子加分
- 靠近对方将帅加分
- 控制关键位置
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


AI_ID = "v005"
AI_NAME = "aggressive"


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


def distance_to_king(pos: Position, king_pos: Position | None) -> int:
    """计算到对方将的距离"""
    if king_pos is None:
        return 10
    return abs(pos.row - king_pos.row) + abs(pos.col - king_pos.col)


def count_threats(game: JieqiGame, pos: Position, color: Color) -> float:
    """计算这个位置能威胁多少对方棋子"""
    threats = 0.0
    moved_piece = game.board.get_piece(pos)
    if moved_piece is None:
        return 0

    potential_targets = moved_piece.get_potential_moves(game.board)
    for target_pos in potential_targets:
        target = game.board.get_piece(target_pos)
        if target and target.color != color:
            threats += get_piece_value(target) * 0.1
    return threats


@AIEngine.register(AI_NAME)
class AggressiveAI(AIStrategy):
    """进攻性 AI

    在防守基础上增加进攻性
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "进攻性策略，主动威胁对方 (v005)"

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

        # 3. 将军加分（进攻重点）
        if game.board.is_in_check(my_color.opposite):
            score += 100  # 提高将军奖励

        # 4. 防守评估
        moved_piece = game.board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(game, move.to_pos, my_color)
            defenders = count_defenders(game, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    score -= my_piece_value * 0.15
                else:
                    score -= my_piece_value * 0.7

        # 5. 进攻评估 - 核心改进
        if moved_piece:
            # 威胁对方棋子
            threats = count_threats(game, move.to_pos, my_color)
            score += threats

            # 靠近对方将
            enemy_king_pos = game.board.find_king(my_color.opposite)
            old_dist = distance_to_king(move.from_pos, enemy_king_pos)
            new_dist = distance_to_king(move.to_pos, enemy_king_pos)
            if new_dist < old_dist:
                score += (old_dist - new_dist) * 5  # 靠近对方将加分

        # 6. 揭子策略
        if was_hidden:
            attackers = count_attackers(game, move.to_pos, my_color)
            if attackers == 0:
                # 安全揭子
                threats = count_threats(game, move.to_pos, my_color)
                score += 10 + threats * 0.5  # 揭子到能威胁的位置更好

        game.board.undo_move(move, captured, was_hidden)

        return score
