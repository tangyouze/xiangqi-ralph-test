"""
v006_balanced - 综合平衡 AI

ID: v006
名称: Balanced AI
描述: 综合 Defensive + Positional，平衡攻防

改进方向：综合平衡
- 防守为主 (来自 v004)
- 位置评估 (来自 v003)
- 适度进攻
- 棋子协调

注意：AI 使用 FEN 接口，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimPiece, SimulationBoard
from jieqi.types import Color, GameResult, PieceType, Position

if TYPE_CHECKING:
    from jieqi.types import JieqiMove


AI_ID = "v006"
AI_NAME = "balanced"


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
        potential_moves = board.get_potential_moves(enemy)
        for target_pos in potential_moves:
            target = board.get_piece(target_pos)
            if target and target.color != enemy_color:
                value = get_piece_value(target)
                if value > best_capture:
                    best_capture = value

    return best_capture


def get_position_bonus(piece: SimPiece, pos: Position) -> float:
    """位置加成（来自 v003）"""
    bonus = 0.0
    color = piece.color

    # 中心控制
    if 3 <= pos.col <= 5:
        bonus += 8
    elif 2 <= pos.col <= 6:
        bonus += 4

    # 过河加分
    crossed_river = False
    if color == Color.RED and pos.row >= 5:
        crossed_river = True
    elif color == Color.BLACK and pos.row <= 4:
        crossed_river = True

    if crossed_river:
        bonus += 15

    # 前进加分
    if color == Color.RED:
        bonus += pos.row * 1.5
    else:
        bonus += (9 - pos.row) * 1.5

    return bonus


@AIEngine.register(AI_NAME)
class BalancedAI(AIStrategy):
    """综合平衡 AI

    结合防守、位置和适度进攻
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "综合平衡策略 (v006)"

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

        # 逃离危险加分：如果原位置被攻击，移动到安全位置
        old_attackers = count_attackers(board, move.from_pos, my_color)
        if old_attackers > 0:
            old_defenders = count_defenders(board, move.from_pos, my_color)
            if old_defenders < old_attackers:
                # 棋子处于危险中，检查新位置是否更安全
                my_piece_value = get_piece_value(piece)
                score += my_piece_value * 0.3  # 逃跑奖励

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

        # 4. 防守评估（核心，来自 v004）
        moved_piece = board.get_piece(move.to_pos)
        if moved_piece:
            my_piece_value = get_piece_value(moved_piece)
            attackers = count_attackers(board, move.to_pos, my_color)
            defenders = count_defenders(board, move.to_pos, my_color)

            if attackers > 0:
                if defenders >= attackers:
                    score -= my_piece_value * 0.2
                else:
                    score -= my_piece_value * 0.75

            # 保护车
            if not moved_piece.is_hidden and moved_piece.actual_type == PieceType.ROOK:
                if attackers > 0:
                    score -= 150

        # 5. 位置评估（来自 v003）
        if moved_piece:
            old_pos_bonus = get_position_bonus(piece, move.from_pos)
            new_pos_bonus = get_position_bonus(moved_piece, move.to_pos)
            score += (new_pos_bonus - old_pos_bonus) * 0.5  # 降低权重

        # 6. 检查危险棋子
        for ally in board.get_all_pieces(my_color):
            if ally.position == move.to_pos:
                continue
            ally_value = get_piece_value(ally)
            attackers = count_attackers(board, ally.position, my_color)
            if attackers > 0:
                defenders = count_defenders(board, ally.position, my_color)
                if defenders < attackers:
                    score -= ally_value * 0.1

        # 7. 揭子策略
        if was_hidden:
            attackers = count_attackers(board, move.to_pos, my_color)
            if attackers == 0:
                score += 12
            else:
                score -= 15

        # 8. 1层前瞻：考虑对手的最佳吃子
        enemy_threat = find_best_enemy_capture(board, my_color.opposite)
        score -= enemy_threat * 0.6

        # 9. 吃子加成（额外奖励）
        if captured:
            score += get_piece_value(captured) * 0.3

        # 10. 机动性评估：己方可走步数 vs 敌方可走步数
        my_mobility = len(board.get_legal_moves(my_color))
        enemy_mobility = len(board.get_legal_moves(my_color.opposite))
        score += (my_mobility - enemy_mobility) * 0.5

        board.undo_move(move, captured, was_hidden)

        return score
