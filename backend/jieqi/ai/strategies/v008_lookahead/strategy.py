"""
v008_lookahead - 向前看一步 AI

ID: v008
名称: Lookahead AI
描述: 在 v007 基础上增加对手回应预测

改进方向：简单搜索
- 评估我方走法后对手的最佳回应
- 考虑对手吃子的威胁
- 避免被对手反吃
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


AI_ID = "v008"
AI_NAME = "lookahead"


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
    count = 0
    for piece in game.board.get_all_pieces(color):
        if piece.is_hidden:
            count += 1
    return count


def count_enemy_hidden(game: JieqiGame, color: Color) -> int:
    count = 0
    for piece in game.board.get_all_pieces(color.opposite):
        if piece.is_hidden:
            count += 1
    return count


def get_game_phase(game: JieqiGame, my_color: Color) -> str:
    my_hidden = count_my_hidden(game, my_color)
    enemy_hidden = count_enemy_hidden(game, my_color)
    total_hidden = my_hidden + enemy_hidden

    if total_hidden >= 20:
        return "early"
    elif total_hidden >= 10:
        return "mid"
    else:
        return "late"


def evaluate_board(game: JieqiGame, my_color: Color) -> float:
    """评估整个棋盘局势"""
    score = 0.0

    # 棋子价值
    for piece in game.board.get_all_pieces(my_color):
        score += get_piece_value(piece)

    for piece in game.board.get_all_pieces(my_color.opposite):
        score -= get_piece_value(piece)

    return score


@AIEngine.register(AI_NAME)
class LookaheadAI(AIStrategy):
    """向前看一步 AI

    考虑对手的最佳回应
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "向前看一步策略 (v008)"

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
            score = self._evaluate_move_with_response(game, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move_with_response(
        self, game: JieqiGame, move: JieqiMove, my_color: Color
    ) -> float:
        """评估走法，考虑对手最佳回应"""
        target = game.board.get_piece(move.to_pos)

        # 直接吃将
        if target is not None and target.color != my_color:
            if target.actual_type == PieceType.KING:
                return 100000

        piece = game.board.get_piece(move.from_pos)
        if piece is None:
            return 0

        was_hidden = piece.is_hidden
        captured = game.board.make_move(move)

        # 检查获胜
        result = game.board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            game.board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            game.board.undo_move(move, captured, was_hidden)
            return 100000

        # 基础分数
        base_score = self._evaluate_move_base(game, move, my_color, was_hidden)

        # 预测对手最佳回应
        enemy_best_capture = self._find_best_enemy_capture(game, my_color.opposite)

        game.board.undo_move(move, captured, was_hidden)

        # 如果对手能吃掉高价值棋子，扣分
        final_score = base_score - enemy_best_capture * 0.8

        return final_score

    def _find_best_enemy_capture(self, game: JieqiGame, enemy_color: Color) -> float:
        """找出对手能吃掉的最高价值棋子"""
        best_capture = 0.0

        # 只检查吃子走法，不模拟执行
        for enemy in game.board.get_all_pieces(enemy_color):
            potential_moves = enemy.get_potential_moves(game.board)
            for target_pos in potential_moves:
                target = game.board.get_piece(target_pos)
                if target and target.color != enemy_color:
                    value = get_piece_value(target)
                    if value > best_capture:
                        best_capture = value

        return best_capture

    def _evaluate_move_base(
        self, game: JieqiGame, move: JieqiMove, my_color: Color, was_hidden: bool
    ) -> float:
        """基础走法评估（来自 v007）"""
        score = 0.0

        # 吃子得分
        target = game.board.get_piece(move.to_pos)
        if target is None:
            # 检查是否刚吃掉
            pass
        else:
            if target.color != my_color:
                score += get_piece_value(target)

        # 将军加分
        if game.board.is_in_check(my_color.opposite):
            score += 60

        # 防守评估
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

            if moved_piece.is_revealed and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 揭子策略
        if was_hidden:
            game_phase = get_game_phase(game, my_color)
            attackers = count_attackers(game, move.to_pos, my_color)
            defenders = count_defenders(game, move.to_pos, my_color)

            if attackers == 0:
                base_reveal_bonus = 25
            elif defenders >= attackers:
                base_reveal_bonus = 10
            else:
                base_reveal_bonus = -40

            if game_phase == "early":
                phase_multiplier = 0.7
            elif game_phase == "mid":
                phase_multiplier = 1.0
            else:
                phase_multiplier = 1.5

            score += base_reveal_bonus * phase_multiplier

        return score
