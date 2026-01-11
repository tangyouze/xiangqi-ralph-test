"""
v004_defensive - 防守优先 AI

ID: v004
名称: Defensive AI
描述: 在 Greedy 基础上增强防守，避免送子

改进方向：防守优先
- 更强的被吃风险评估
- 保护高价值棋子
- 不轻易暴露将帅

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import Color, PieceType, GameResult, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove
    from jieqi.view import PlayerView


AI_ID = "v004"
AI_NAME = "defensive"


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


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def count_attackers(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少对方棋子可以攻击这个位置"""
    count = 0
    for enemy in board.get_all_pieces(color.opposite):
        if pos in board.get_potential_moves(enemy):
            count += 1
    return count


def count_defenders(board: SimulationBoard, pos: Position, color: Color) -> int:
    """计算有多少己方棋子可以保护这个位置"""
    count = 0
    for ally in board.get_all_pieces(color):
        if ally.position != pos and pos in board.get_potential_moves(ally):
            count += 1
    return count


@AIEngine.register(AI_NAME)
class DefensiveAI(AIStrategy):
    """防守优先 AI

    增强防守意识，避免送子
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "防守优先策略，避免送子 (v004)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        """选择得分最高的走法"""
        if not view.legal_moves:
            return None

        my_color = view.viewer
        best_moves: list[JieqiMove] = []
        best_score = float('-inf')

        # 创建模拟棋盘
        sim_board = SimulationBoard(view)

        for move in view.legal_moves:
            score = self._evaluate_move(sim_board, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move(self, board: SimulationBoard, move: JieqiMove, my_color: Color) -> float:
        """评估走法得分"""
        score = 0.0

        target = board.get_piece(move.to_pos)

        # 1. 吃子得分
        if target is not None and target.color != my_color:
            capture_value = get_piece_value(target)
            score += capture_value

            if target.actual_type == PieceType.KING:
                return 100000

        piece = board.get_piece(move.from_pos)
        if piece is None:
            return score

        was_hidden = piece.is_hidden
        captured = board.make_move(move)

        # 2. 检查获胜
        result = board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 3. 将军加分
        if board.is_in_check(my_color.opposite):
            score += 50

        # 4. 防守评估 - 核心改进
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers > 0:
                # 如果被攻击
                if defenders >= attackers:
                    # 有足够防守，损失较小
                    score -= my_piece_value * 0.2
                else:
                    # 防守不足，严重惩罚
                    score -= my_piece_value * 0.8

            # 特别保护高价值棋子（明子）
            if not moved_piece.is_hidden and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 200  # 额外惩罚暴露车

        # 5. 检查是否有棋子处于危险中
        for ally in board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            attackers = count_attackers(board, ally.position, my_color)
            if attackers > 0:
                defenders = count_defenders(board, ally.position, my_color)
                if defenders < attackers:
                    # 有棋子处于危险中，这步走法没有救它
                    score -= ally_value * 0.1

        # 6. 揭子加分（但更谨慎）
        if was_hidden:
            # 只有在安全位置才加分
            attackers = count_attackers(board, move.to_pos, my_color)
            if attackers == 0:
                score += 15
            else:
                score -= 10  # 揭子到危险位置反而减分

        board.undo_move(move, captured, was_hidden)

        return score
