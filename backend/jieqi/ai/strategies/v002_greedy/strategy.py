"""
v002_greedy - 贪心 AI 策略

ID: v002
名称: Greedy AI
描述: 只考虑当前一步的收益，选择得分最高的走法

特点:
- 只看一步，不考虑后续
- 优先吃子，考虑棋子价值
- 避免送子（评估被吃风险）
- 将军时小幅加分

评估因素:
1. 吃子价值（对方棋子价值）
2. 走后是否将军
3. 走后是否直接获胜
4. 走后自己棋子被吃的风险
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.types import Color, PieceType, GameResult

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.types import JieqiMove
    from jieqi.piece import JieqiPiece


AI_ID = "v002"
AI_NAME = "greedy"


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

# 暗子期望价值（因为不知道真实身份，用平均值估算）
# 15个非将棋子：2车(900*2) + 2马(400*2) + 2炮(450*2) + 2象(200*2) + 2士(200*2) + 5兵(100*5)
# 总价值 = 1800 + 800 + 900 + 400 + 400 + 500 = 4800
# 平均每个暗子价值 = 4800 / 15 = 320
HIDDEN_PIECE_VALUE = 320


def get_piece_value(piece: JieqiPiece) -> int:
    """获取棋子价值

    暗子使用期望价值，明子使用真实价值
    """
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


@AIEngine.register(AI_NAME)
class GreedyAI(AIStrategy):
    """贪心 AI

    只考虑当前一步的收益：
    - 吃子得分（对方棋子价值）
    - 被吃风险（自己棋子可能被吃）
    - 将军加分
    - 胜利直接选择
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "贪心策略，只考虑下一步收益 (v002)"

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

        # 从得分相同的最佳走法中随机选择
        return self._rng.choice(best_moves)

    def _evaluate_move(self, game: JieqiGame, move: JieqiMove, my_color: Color) -> float:
        """评估走法得分"""
        score = 0.0

        # 获取目标位置的棋子（可能被吃）
        target = game.board.get_piece(move.to_pos)

        # 1. 吃子得分
        if target is not None and target.color != my_color:
            capture_value = get_piece_value(target)
            score += capture_value

            # 吃将直接获胜，给最高分
            if target.actual_type == PieceType.KING:
                return 100000

        # 模拟走棋
        piece = game.board.get_piece(move.from_pos)
        if piece is None:
            return score

        was_hidden = piece.is_hidden
        captured = game.board.make_move(move)

        # 2. 检查是否直接获胜
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

        # 4. 评估被吃风险
        moved_piece = game.board.get_piece(move.to_pos)
        if moved_piece:
            for enemy_piece in game.board.get_all_pieces(my_color.opposite):
                if move.to_pos in enemy_piece.get_potential_moves(game.board):
                    # 可能被吃，减分
                    my_piece_value = get_piece_value(moved_piece)
                    score -= my_piece_value * 0.3
                    break

        # 5. 揭子有小幅加分（了解更多信息）
        if was_hidden:
            score += 10

        # 撤销走棋
        game.board.undo_move(move, captured, was_hidden)

        return score
