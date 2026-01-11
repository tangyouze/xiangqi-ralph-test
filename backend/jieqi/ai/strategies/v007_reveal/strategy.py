"""
v007_reveal - 揭子策略优化 AI

ID: v007
名称: Reveal AI
描述: 专注优化揭子策略，智能选择何时、如何揭子

改进方向：揭子策略
- 智能揭子时机选择
- 评估揭子位置安全性
- 考虑揭子后的威胁能力
- 优先在有保护的位置揭子
- 后期更激进揭子
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


AI_ID = "v007"
AI_NAME = "reveal"


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


def count_my_hidden(game: JieqiGame, color: Color) -> int:
    """统计我方隐藏棋子数量"""
    count = 0
    for piece in game.board.get_all_pieces(color):
        if piece.is_hidden:
            count += 1
    return count


def count_enemy_hidden(game: JieqiGame, color: Color) -> int:
    """统计对方隐藏棋子数量"""
    count = 0
    for piece in game.board.get_all_pieces(color.opposite):
        if piece.is_hidden:
            count += 1
    return count


def get_revealed_piece_value(game: JieqiGame, pos: Position, color: Color) -> float:
    """评估揭子后棋子的威胁能力"""
    piece = game.board.get_piece(pos)
    if piece is None or not piece.is_revealed:
        return 0

    threat_value = 0.0
    potential_targets = piece.get_potential_moves(game.board)
    for target_pos in potential_targets:
        target = game.board.get_piece(target_pos)
        if target and target.color != color:
            threat_value += get_piece_value(target) * 0.15
    return threat_value


def is_protected_position(game: JieqiGame, pos: Position, color: Color) -> bool:
    """检查位置是否有保护"""
    defenders = count_defenders(game, pos, color)
    return defenders > 0


def get_game_phase(game: JieqiGame, my_color: Color) -> str:
    """判断游戏阶段"""
    my_hidden = count_my_hidden(game, my_color)
    enemy_hidden = count_enemy_hidden(game, my_color)
    total_hidden = my_hidden + enemy_hidden

    # 基于隐藏棋子数量判断阶段
    if total_hidden >= 20:
        return "early"
    elif total_hidden >= 10:
        return "mid"
    else:
        return "late"


@AIEngine.register(AI_NAME)
class RevealAI(AIStrategy):
    """揭子策略优化 AI

    专注于优化揭子时机和方式
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "揭子策略优化 (v007)"

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

        # 4. 防守评估（来自 v004）
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

        # 5. 揭子策略 - 核心改进
        if was_hidden:
            game_phase = get_game_phase(game, my_color)
            attackers = count_attackers(game, move.to_pos, my_color)
            defenders = count_defenders(game, move.to_pos, my_color)

            # 基础安全性评估
            if attackers == 0:
                # 完全安全的揭子
                base_reveal_bonus = 25
            elif defenders >= attackers:
                # 有保护的揭子
                base_reveal_bonus = 10
            else:
                # 危险的揭子 - 大幅惩罚
                base_reveal_bonus = -40

            # 阶段调整
            if game_phase == "early":
                # 早期谨慎揭子
                phase_multiplier = 0.7
            elif game_phase == "mid":
                # 中期正常揭子
                phase_multiplier = 1.0
            else:
                # 后期激进揭子
                phase_multiplier = 1.5

            score += base_reveal_bonus * phase_multiplier

            # 揭子后威胁能力加分
            if moved_piece and moved_piece.is_revealed:
                threat_value = get_revealed_piece_value(game, move.to_pos, my_color)
                score += threat_value * phase_multiplier

            # 在宫殿附近揭子更安全
            if my_color == Color.RED:
                if move.to_pos.row <= 2 and 3 <= move.to_pos.col <= 5:
                    score += 8
            else:
                if move.to_pos.row >= 7 and 3 <= move.to_pos.col <= 5:
                    score += 8

            # 揭出高价值棋子的额外奖励
            if moved_piece and moved_piece.is_revealed:
                actual_value = PIECE_VALUES.get(moved_piece.actual_type, 0)
                if actual_value >= 400:  # 车/炮/马
                    if attackers == 0:
                        score += 15

        # 6. 检查危险棋子
        for ally in game.board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            ally_attackers = count_attackers(game, ally.position, my_color)
            if ally_attackers > 0:
                ally_defenders = count_defenders(game, ally.position, my_color)
                if ally_defenders < ally_attackers:
                    score -= ally_value * 0.1

        game.board.undo_move(move, captured, was_hidden)

        return score
