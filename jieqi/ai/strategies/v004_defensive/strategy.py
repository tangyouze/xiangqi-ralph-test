"""
v004_defensive - 防守优先 AI

ID: v004
名称: Defensive AI
描述: 在 Greedy 基础上增强防守，避免送子

改进方向：防守优先
- 更强的被吃风险评估
- 保护高价值棋子
- 不轻易暴露将帅

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

        # 处理同分情况
        result: list[tuple[str, float]] = []
        i = 0
        while i < len(scored_moves) and len(result) < n:
            current_score = scored_moves[i][1]
            same_score_moves = []
            while i < len(scored_moves) and scored_moves[i][1] == current_score:
                same_score_moves.append(scored_moves[i])
                i += 1
            self._rng.shuffle(same_score_moves)
            for move in same_score_moves:
                if len(result) < n:
                    result.append(move)

        return result

    def _evaluate_move(self, board: SimulationBoard, move: "JieqiMove", my_color: Color) -> float:
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

        # 逃离危险加分
        old_attackers = count_attackers(board, move.from_pos, my_color)
        if old_attackers > 0:
            old_defenders = count_defenders(board, move.from_pos, my_color)
            if old_defenders < old_attackers:
                my_piece_value = get_piece_value(piece)
                score += my_piece_value * 0.4  # 防守策略更重视逃跑

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

            # 位置评估 - 过河和中心控制
            if not moved_piece.is_hidden:
                if not move.to_pos.is_on_own_side(my_color):
                    score += 12  # 过河加分
                if 3 <= move.to_pos.col <= 5:
                    score += 6  # 中心控制

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

        # 7. 1层前瞻：考虑对手的最佳吃子
        enemy_threat = find_best_enemy_capture(board, my_color.opposite)
        score -= enemy_threat * 0.7  # 防守策略更重视威胁

        # 8. 吃子额外加成
        if captured:
            score += get_piece_value(captured) * 0.2

        board.undo_move(move, captured, was_hidden)

        return score
