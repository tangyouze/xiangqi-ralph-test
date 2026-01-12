"""
v005_aggressive - 进攻性 AI

ID: v005
名称: Aggressive AI
描述: 在防守基础上增加进攻性，主动威胁对方

改进方向：进攻性 + 1层前瞻搜索
- 威胁对方高价值棋子加分
- 靠近对方将帅加分
- 控制关键位置
- 1层前瞻搜索避免送子

迭代记录：
- v1: 初始版本，过于激进，无搜索
- v2: 增加防守权重 - 效果不好
- v3: 添加1层前瞻搜索，更好地评估局面

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import ActionType, Color, PieceType, GameResult, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove
    from jieqi.view import PlayerView


AI_ID = "v005"
AI_NAME = "aggressive"


# 棋子价值
PIECE_VALUES = {
    PieceType.KING: 100000,
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


def evaluate_position(board: SimulationBoard, color: Color) -> float:
    """评估当前局面对某方的分数"""
    score = 0.0

    my_pieces = board.get_all_pieces(color)
    enemy_pieces = board.get_all_pieces(color.opposite)

    # 1. 子力价值
    for piece in my_pieces:
        score += get_piece_value(piece)
    for piece in enemy_pieces:
        score -= get_piece_value(piece)

    # 2. 将军加分
    if board.is_in_check(color.opposite):
        score += 100
    if board.is_in_check(color):
        score -= 100

    # 3. 进攻性加分 - 威胁对方棋子
    for piece in my_pieces:
        if not piece.is_hidden:
            for target_pos in board.get_potential_moves(piece):
                target = board.get_piece(target_pos)
                if target and target.color != color:
                    # 威胁高价值棋子更好
                    score += get_piece_value(target) * 0.1

    # 4. 位置控制 - 中心位置
    for piece in my_pieces:
        if not piece.is_hidden:
            # 过河加分
            if not piece.position.is_on_own_side(color):
                score += 20

    return score


@AIEngine.register(AI_NAME)
class AggressiveAI(AIStrategy):
    """进攻性 AI - 带1层前瞻搜索"""

    name = AI_NAME
    ai_id = AI_ID
    description = "进攻性策略，带1层前瞻搜索 (v005)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        """选择得分最高的走法"""
        if not view.legal_moves:
            return None

        my_color = view.viewer
        best_moves: list[JieqiMove] = []
        best_score = float("-inf")

        # 创建模拟棋盘
        sim_board = SimulationBoard(view)

        for move in view.legal_moves:
            score = self._evaluate_move_with_lookahead(sim_board, move, my_color)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

    def _evaluate_move_with_lookahead(
        self, board: SimulationBoard, move: JieqiMove, my_color: Color
    ) -> float:
        """评估走法，考虑对方最佳回应"""
        piece = board.get_piece(move.from_pos)
        if piece is None:
            return float("-inf")

        # 逃离危险加分
        escape_bonus = 0.0
        old_attackers = count_attackers(board, move.from_pos, my_color)
        if old_attackers > 0:
            my_piece_value = get_piece_value(piece)
            escape_bonus = my_piece_value * 0.3

        was_hidden = piece.is_hidden
        captured = board.make_move(move)

        # 检查是否吃到将
        if captured and captured.actual_type == PieceType.KING:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 检查是否获胜
        if board.find_king(my_color.opposite) is None:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 1层前瞻：考虑对方最佳回应
        enemy_moves = board.get_legal_moves(my_color.opposite)

        if not enemy_moves:
            # 对方无路可走
            if board.is_in_check(my_color.opposite):
                board.undo_move(move, captured, was_hidden)
                return 100000  # 将杀
            else:
                board.undo_move(move, captured, was_hidden)
                return 0  # 和棋

        # 找对方最佳回应后的局面分数
        worst_score = float("inf")
        for enemy_move in enemy_moves:
            enemy_piece = board.get_piece(enemy_move.from_pos)
            if enemy_piece is None:
                continue

            enemy_was_hidden = enemy_piece.is_hidden
            enemy_captured = board.make_move(enemy_move)

            # 如果对方吃掉我的将，这是最坏结果
            if enemy_captured and enemy_captured.actual_type == PieceType.KING:
                board.undo_move(enemy_move, enemy_captured, enemy_was_hidden)
                worst_score = -100000
                break

            # 评估对方回应后的局面
            score = evaluate_position(board, my_color)

            board.undo_move(enemy_move, enemy_captured, enemy_was_hidden)

            if score < worst_score:
                worst_score = score

        board.undo_move(move, captured, was_hidden)

        # 加入进攻性奖励
        attack_bonus = 0.0

        # 吃子奖励
        if captured:
            attack_bonus += get_piece_value(captured) * 0.5

        # 将军奖励
        if board.is_in_check(my_color.opposite):
            attack_bonus += 50

        # 威胁评估和位置评估需要在 undo 前的 board 状态中评估
        # 使用原始 piece 信息
        if piece and not was_hidden:
            # 位置评估：过河和中心控制
            if not move.to_pos.is_on_own_side(my_color):
                attack_bonus += 15  # 过河加分
            if 3 <= move.to_pos.col <= 5:
                attack_bonus += 8  # 中心控制

        return worst_score + attack_bonus + escape_bonus
