"""
v009_coordination - 棋子协作 AI

ID: v009
名称: Coordination AI
描述: 在 v007 基础上增加棋子协作评估

改进方向：棋子协作
- 双车协作加分
- 炮马配合
- 保护链评估
- 相互支援能力
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


AI_ID = "v009"
AI_NAME = "coordination"


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


def evaluate_coordination(game: JieqiGame, my_color: Color) -> float:
    """评估棋子协作"""
    bonus = 0.0

    my_pieces = game.board.get_all_pieces(my_color)
    revealed_pieces = [p for p in my_pieces if p.is_revealed]

    # 找出高价值棋子
    rooks = [p for p in revealed_pieces if p.actual_type == PieceType.ROOK]
    cannons = [p for p in revealed_pieces if p.actual_type == PieceType.CANNON]
    horses = [p for p in revealed_pieces if p.actual_type == PieceType.HORSE]

    # 双车协作
    if len(rooks) >= 2:
        r1, r2 = rooks[0], rooks[1]
        # 同行或同列的双车更强
        if r1.position.row == r2.position.row or r1.position.col == r2.position.col:
            bonus += 30

    # 炮马配合
    for cannon in cannons:
        for horse in horses:
            dist = abs(cannon.position.row - horse.position.row) + abs(
                cannon.position.col - horse.position.col
            )
            if dist <= 3:
                bonus += 15

    # 保护链 - 高价值棋子被保护
    for piece in revealed_pieces:
        if piece.actual_type in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE):
            defenders = count_defenders(game, piece.position, my_color)
            if defenders >= 1:
                bonus += 10
            if defenders >= 2:
                bonus += 5

    return bonus


@AIEngine.register(AI_NAME)
class CoordinationAI(AIStrategy):
    """棋子协作 AI

    强调棋子之间的配合
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "棋子协作策略 (v009)"

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

            if moved_piece.is_revealed and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 5. 揭子策略（来自 v007）
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

        # 6. 棋子协作 - 核心改进
        old_coordination = evaluate_coordination(game, my_color)
        # 走完后重新评估协作
        new_coordination = evaluate_coordination(game, my_color)
        score += (new_coordination - old_coordination) * 0.3

        # 额外：走后的协作状态
        score += new_coordination * 0.1

        # 7. 检查危险棋子
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
