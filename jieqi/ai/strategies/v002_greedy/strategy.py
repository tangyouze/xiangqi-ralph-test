"""
v002_greedy - 贪心 AI 策略

ID: v002
名称: Greedy AI
描述: 贪心策略，优先吃子，简单但有效

特点:
- 优先吃高价值棋子
- 避免送子（检查被吃风险）
- 将军加分
- 位置控制加分

迭代记录:
- v1: 初始版本，效果一般
- v2: 尝试1层搜索，效果不佳
- v3: 回归简单策略，增强位置评估和安全检查

注意：AI 使用 FEN 接口，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import Color, GameResult, PieceType, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove


AI_ID = "v002"
AI_NAME = "greedy"


# 棋子基础价值
PIECE_VALUES = {
    PieceType.KING: 100000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

# 暗子期望价值
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


def find_best_enemy_capture(board: SimulationBoard, enemy_color: Color) -> float:
    """找出对手能吃掉的最高价值棋子"""
    best_capture = 0.0
    for enemy in board.get_all_pieces(enemy_color):
        for target_pos in board.get_potential_moves(enemy):
            target = board.get_piece(target_pos)
            if target and target.color != enemy_color:
                value = get_piece_value(target)
                if value > best_capture:
                    best_capture = value
    return best_capture


@AIEngine.register(AI_NAME)
class GreedyAI(AIStrategy):
    """贪心 AI

    优先吃子，避免送子，考虑位置
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "贪心策略，优先吃子 (v002)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self._rng = random.Random(self.config.seed)

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        state = parse_fen(fen)
        my_color = state.turn
        sim_board = create_board_from_fen(fen)

        # 计算每个走法的评分
        scored_moves: list[tuple[str, float]] = []
        for move_str in legal_moves:
            move, _ = parse_move(move_str)
            score = self._evaluate_move(sim_board, move, my_color)
            scored_moves.append((move_str, score))

        # 按分数降序排序
        scored_moves.sort(key=lambda x: x[1], reverse=True)

        # 处理同分情况：同分的走法随机打乱
        result: list[tuple[str, float]] = []
        i = 0
        while i < len(scored_moves) and len(result) < n:
            current_score = scored_moves[i][1]
            # 收集所有同分的走法
            same_score_moves = []
            while i < len(scored_moves) and scored_moves[i][1] == current_score:
                same_score_moves.append(scored_moves[i])
                i += 1
            # 随机打乱同分走法
            self._rng.shuffle(same_score_moves)
            # 添加到结果
            for move in same_score_moves:
                if len(result) < n:
                    result.append(move)

        return result

    def _evaluate_move(self, board: SimulationBoard, move: "JieqiMove", my_color: Color) -> float:
        """评估走法得分"""
        score = 0.0

        target = board.get_piece(move.to_pos)

        # 1. 吃子得分 - MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
        if target is not None and target.color != my_color:
            victim_value = get_piece_value(target)
            attacker = board.get_piece(move.from_pos)
            attacker_value = get_piece_value(attacker) if attacker else 0
            # MVV-LVA: 用低价值棋子吃高价值棋子更好
            mvv_lva_bonus = victim_value * 1.5 - attacker_value * 0.1
            score += mvv_lva_bonus

            if target.actual_type == PieceType.KING:
                return 100000

        piece = board.get_piece(move.from_pos)
        if piece is None:
            return score

        was_hidden = piece.is_hidden
        captured = board.make_move(move)

        # 2. 检查是否直接获胜
        result = board.get_game_result(my_color.opposite)
        if result == GameResult.RED_WIN and my_color == Color.RED:
            board.undo_move(move, captured, was_hidden)
            return 100000
        elif result == GameResult.BLACK_WIN and my_color == Color.BLACK:
            board.undo_move(move, captured, was_hidden)
            return 100000

        # 3. 将军加分
        if board.is_in_check(my_color.opposite):
            score += 80

        # 4. 安全性评估 - 避免送子
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    # 有保护，小幅惩罚
                    score -= my_piece_value * 0.2
                else:
                    # 无保护，大幅惩罚
                    score -= my_piece_value * 0.8

            # 逃离威胁加分
            old_attackers = count_attackers(board, move.from_pos, my_color)
            if old_attackers > 0 and attackers == 0:
                score += my_piece_value * 0.4

        # 5. 位置加分
        if moved_piece and not moved_piece.is_hidden:
            # 过河加分
            if not move.to_pos.is_on_own_side(my_color):
                score += 15

            # 控制中心加分
            if 3 <= move.to_pos.col <= 5:
                score += 10

        # 6. 揭子加分
        if was_hidden:
            attackers = count_attackers(board, move.to_pos, my_color)
            if attackers == 0:
                score += 20
            else:
                score -= 10

        # 7. 1层前瞻：考虑对手的最佳吃子
        enemy_threat = find_best_enemy_capture(board, my_color.opposite)
        score -= enemy_threat * 0.5

        board.undo_move(move, captured, was_hidden)

        return score
