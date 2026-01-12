"""
v010_fast - 快速评估 AI

ID: v010
名称: Fast AI
描述: 快速评估结合最佳策略

改进方向：性能优化
- 简化评估逻辑
- 结合 v007 reveal 策略的优点
- 快速子力计算

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import Color, GameResult, PieceType, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove
    from jieqi.view import PlayerView


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


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def count_hidden(board: SimulationBoard, color: Color) -> int:
    """统计某方隐藏棋子数量"""
    count = 0
    for piece in board.get_all_pieces(color):
        if piece.is_hidden:
            count += 1
    return count


def is_attacked_by(board: SimulationBoard, pos: Position, attacker_color: Color) -> bool:
    """检查某个位置是否被指定颜色的棋子攻击"""
    for piece in board.get_all_pieces(attacker_color):
        if pos in board.get_potential_moves(piece):
            return True
    return False


def has_defender(board: SimulationBoard, pos: Position, defender_color: Color) -> bool:
    """检查某个位置是否有保护"""
    for ally in board.get_all_pieces(defender_color):
        if ally.position != pos:
            if pos in board.get_potential_moves(ally):
                return True
    return False


def find_max_threat(board: SimulationBoard, enemy_color: Color) -> float:
    """快速找出对手最大威胁（简化版）"""
    max_threat = 0.0

    for enemy in board.get_all_pieces(enemy_color):
        for target_pos in board.get_potential_moves(enemy):
            target = board.get_piece(target_pos)
            if target and target.color != enemy_color:
                value = get_piece_value(target)
                if value > max_threat:
                    max_threat = value

    return max_threat


@AIEngine.register(AI_NAME)
class FastAI(AIStrategy):
    """快速评估 AI

    简化的评估逻辑，但保留核心策略
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "快速评估策略 (v010)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        """选择最佳走法"""
        if not view.legal_moves:
            return None

        my_color = view.viewer
        best_moves: list[JieqiMove] = []
        best_score = float("-inf")

        # 创建模拟棋盘
        sim_board = SimulationBoard(view)

        for move in view.legal_moves:
            score = self._evaluate_move_fast(sim_board, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move_fast(
        self,
        board: SimulationBoard,
        move: JieqiMove,
        my_color: Color,
    ) -> float:
        """快速评估走法"""
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

        # 逃离危险加分（快速版本）
        if is_attacked_by(board, move.from_pos, my_color.opposite):
            if not has_defender(board, move.from_pos, my_color):
                my_piece_value = get_piece_value(piece)
                score += my_piece_value * 0.35

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
            score += 60

        # 4. 安全性评估
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)

            # 检查是否被攻击
            if is_attacked_by(board, move.to_pos, my_color.opposite):
                if has_defender(board, move.to_pos, my_color):
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            # 保护车
            if not moved_piece.is_hidden and moved_piece.actual_type == PieceType.ROOK:
                if is_attacked_by(board, move.to_pos, my_color.opposite):
                    score -= 150

        # 5. 揭子策略（来自 v007）
        if was_hidden:
            # 计算隐藏棋子数量判断阶段
            my_hidden = count_hidden(board, my_color)
            enemy_hidden = count_hidden(board, my_color.opposite)
            total_hidden = my_hidden + enemy_hidden

            if total_hidden >= 20:
                phase_multiplier = 0.7
            elif total_hidden >= 10:
                phase_multiplier = 1.0
            else:
                phase_multiplier = 1.5

            # 安全性评估
            if not is_attacked_by(board, move.to_pos, my_color.opposite):
                base_reveal_bonus = 25
            else:
                if has_defender(board, move.to_pos, my_color):
                    base_reveal_bonus = 10
                else:
                    base_reveal_bonus = -40

            score += base_reveal_bonus * phase_multiplier

        # 6. 检查危险棋子
        for ally in board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            if is_attacked_by(board, ally.position, my_color.opposite):
                if not has_defender(board, ally.position, my_color):
                    score -= ally_value * 0.1

        # 7. 简单前瞻：考虑对手最大威胁
        max_threat = find_max_threat(board, my_color.opposite)
        score -= max_threat * 0.5

        # 8. 吃子额外加成
        if captured:
            score += get_piece_value(captured) * 0.2

        # 9. 位置评估：过河和中心控制
        if moved_piece and not moved_piece.is_hidden:
            if not move.to_pos.is_on_own_side(my_color):
                score += 12  # 过河加分
            if 3 <= move.to_pos.col <= 5:
                score += 6  # 中心控制
            elif 2 <= move.to_pos.col <= 6:
                score += 3  # 次中心

        board.undo_move(move, captured, was_hidden)

        return score
