"""
v013_iterative - Iterative Deepening Alpha-Beta AI

ID: v013
名称: Iterative AI
描述: 在 v012 基础上添加迭代加深和更精细的评估函数

改进方向：
- 迭代加深搜索（更好的时间控制）
- PV (Principal Variation) 节点优化
- 更精细的评估函数（位置、机动性、安全性）
- 静态搜索 (Quiescence Search)

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    pass


AI_ID = "v013"
AI_NAME = "iterative"


# 棋子基础价值（单位：厘兵）
PIECE_VALUES = {
    PieceType.KING: 100000,
    PieceType.ROOK: 9000,
    PieceType.CANNON: 4500,
    PieceType.HORSE: 4000,
    PieceType.ELEPHANT: 2000,
    PieceType.ADVISOR: 2000,
    PieceType.PAWN: 1000,
}

HIDDEN_PIECE_VALUE = 3500  # 隐藏棋子估计价值

# 位置权重表 (10行 x 9列 = 90)
# 马的位置权重
HORSE_POSITION = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    10,
    20,
    20,
    20,
    20,
    20,
    10,
    0,
    0,
    20,
    30,
    30,
    30,
    30,
    30,
    20,
    0,
    10,
    30,
    40,
    50,
    50,
    50,
    40,
    30,
    10,
    20,
    40,
    50,
    60,
    60,
    60,
    50,
    40,
    20,
    20,
    40,
    50,
    60,
    60,
    60,
    50,
    40,
    20,
    10,
    30,
    40,
    50,
    50,
    50,
    40,
    30,
    10,
    0,
    20,
    30,
    30,
    30,
    30,
    30,
    20,
    0,
    0,
    10,
    20,
    20,
    20,
    20,
    20,
    10,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

# 车的位置权重
ROOK_POSITION = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    10,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    10,
    20,
    20,
    30,
    40,
    50,
    40,
    30,
    20,
    20,
    20,
    20,
    30,
    40,
    50,
    40,
    30,
    20,
    20,
    10,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    10,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
]

# 炮的位置权重
CANNON_POSITION = [
    0,
    10,
    20,
    20,
    30,
    20,
    20,
    10,
    0,
    0,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    0,
    0,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    0,
    10,
    20,
    30,
    40,
    50,
    40,
    30,
    20,
    10,
    20,
    30,
    40,
    50,
    60,
    50,
    40,
    30,
    20,
    20,
    30,
    40,
    50,
    60,
    50,
    40,
    30,
    20,
    10,
    20,
    30,
    40,
    50,
    40,
    30,
    20,
    10,
    0,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    0,
    0,
    10,
    20,
    30,
    40,
    30,
    20,
    10,
    0,
    0,
    10,
    20,
    20,
    30,
    20,
    20,
    10,
    0,
]

POSITION_TABLES = {
    PieceType.HORSE: HORSE_POSITION,
    PieceType.ROOK: ROOK_POSITION,
    PieceType.CANNON: CANNON_POSITION,
}


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


def get_position_value(piece: SimPiece) -> int:
    """获取位置价值"""
    if piece.is_hidden or piece.actual_type is None:
        return 0
    table = POSITION_TABLES.get(piece.actual_type)
    if table is None:
        return 0
    pos_index = piece.position.row * 9 + piece.position.col
    if 0 <= pos_index < 90:
        return table[pos_index]
    return 0


class TTFlag(IntEnum):
    EXACT = 0
    LOWERBOUND = 1
    UPPERBOUND = 2


@dataclass
class TTEntry:
    hash_key: int
    depth: int
    score: float
    flag: TTFlag
    best_move: JieqiMove | None


class TranspositionTable:
    def __init__(self, max_size: int = 200000):
        self.max_size = max_size
        self.table: dict[int, TTEntry] = {}

    def get(self, hash_key: int) -> TTEntry | None:
        return self.table.get(hash_key)

    def store(
        self,
        hash_key: int,
        depth: int,
        score: float,
        flag: TTFlag,
        best_move: JieqiMove | None,
    ) -> None:
        if len(self.table) >= self.max_size:
            old_entry = self.table.get(hash_key)
            if old_entry is not None and old_entry.depth > depth:
                return
        self.table[hash_key] = TTEntry(hash_key, depth, score, flag, best_move)

    def clear(self) -> None:
        self.table.clear()


@AIEngine.register(AI_NAME)
class IterativeAI(AIStrategy):
    """Iterative Deepening Alpha-Beta AI

    使用迭代加深来逐步增加搜索深度，
    确保在时间限制内返回最佳走法。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "迭代加深搜索 (v013)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        # 最大搜索深度
        self.max_depth = self.config.depth if self.config.depth > 0 else 4
        # 时间限制（秒）
        self.time_limit = self.config.time_limit or 2.0

        self._rng = random.Random(self.config.seed)
        self._tt = TranspositionTable()
        self._nodes_evaluated = 0
        self._history: dict[tuple[Position, Position], int] = {}
        self._killers: list[list[JieqiMove]] = [[] for _ in range(20)]
        self._start_time = 0.0

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        if len(legal_moves) == 1:
            return [(legal_moves[0], 0.0)]

        state = parse_fen(fen)
        my_color = state.turn

        # 创建模拟棋盘
        sim_board = create_board_from_fen(fen)
        self._nodes_evaluated = 0
        self._start_time = time.time()

        # 解析走法
        parsed_moves = [(move_str, parse_move(move_str)[0]) for move_str in legal_moves]
        move_to_str = {m: s for s, m in parsed_moves}
        jieqi_moves = [m for _, m in parsed_moves]

        # 迭代加深，收集所有走法的评分
        all_scores: dict[JieqiMove, float] = {}

        for depth in range(1, self.max_depth + 1):
            if time.time() - self._start_time > self.time_limit * 0.8:
                break

            try:
                scores = self._search_root_all(sim_board, jieqi_moves, depth, my_color)
                all_scores = scores  # 用最深层的评分覆盖
            except TimeoutError:
                break

        # 转换为字符串格式并排序
        str_scores: dict[str, float] = {}
        for move, score in all_scores.items():
            move_str = move_to_str.get(move)
            if move_str:
                str_scores[move_str] = score

        sorted_results = sorted(str_scores.items(), key=lambda x: -x[1])

        # 处理同分情况
        result: list[tuple[str, float]] = []
        i = 0
        items = sorted_results
        while i < len(items) and len(result) < n:
            current_score = items[i][1]
            same_score_moves = []
            while i < len(items) and items[i][1] == current_score:
                same_score_moves.append(items[i])
                i += 1
            self._rng.shuffle(same_score_moves)
            for move in same_score_moves:
                if len(result) < n:
                    result.append(move)

        return result

    def _search_root_all(
        self,
        board: SimulationBoard,
        legal_moves: list[JieqiMove],
        depth: int,
        color: Color,
    ) -> dict[JieqiMove, float]:
        """根节点搜索，返回所有走法的评分"""
        position_hash = board.get_position_hash()
        tt_entry = self._tt.get(position_hash)
        sorted_moves = self._order_moves(board, legal_moves, color, 0, tt_entry)

        scores: dict[JieqiMove, float] = {}
        alpha = float("-inf")
        beta = float("inf")

        for move in sorted_moves:
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                scores[move] = 100000
                continue

            score = -self._alpha_beta(board, depth - 1, -beta, -alpha, color.opposite, 1)
            board.undo_move(move, captured, was_hidden)

            scores[move] = score
            alpha = max(alpha, score)

        return scores

    def _alpha_beta(
        self,
        board: SimulationBoard,
        depth: int,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
    ) -> float:
        """Alpha-Beta with Transposition Table"""
        # 时间检查（每1000节点检查一次）
        self._nodes_evaluated += 1
        if self._nodes_evaluated % 1000 == 0:
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

        alpha_orig = alpha
        position_hash = board.get_position_hash()

        # TT 查找
        tt_entry = self._tt.get(position_hash)
        if tt_entry is not None and tt_entry.depth >= depth:
            if tt_entry.flag == TTFlag.EXACT:
                return tt_entry.score
            elif tt_entry.flag == TTFlag.LOWERBOUND:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == TTFlag.UPPERBOUND:
                beta = min(beta, tt_entry.score)

            if alpha >= beta:
                return tt_entry.score

        # 检查是否无将
        if board.find_king(color) is None:
            return -100000 + ply
        if board.find_king(color.opposite) is None:
            return 100000 - ply

        # 叶子节点
        if depth <= 0:
            return self._quiesce(board, alpha, beta, color, ply)

        # 获取走法
        legal_moves = board.get_legal_moves(color)
        if not legal_moves:
            if board.is_in_check(color):
                return -100000 + ply
            return 0

        # 排序走法
        sorted_moves = self._order_moves(board, legal_moves, color, ply, tt_entry)

        best_score = float("-inf")
        best_move = None

        for move in sorted_moves:
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return 100000 - ply

            score = -self._alpha_beta(board, depth - 1, -beta, -alpha, color.opposite, ply + 1)

            board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, score)

            if alpha >= beta:
                if captured is None:
                    self._update_killers(move, ply)
                    self._update_history(move, depth)
                break

        # Store TT
        if best_score <= alpha_orig:
            flag = TTFlag.UPPERBOUND
        elif best_score >= beta:
            flag = TTFlag.LOWERBOUND
        else:
            flag = TTFlag.EXACT

        self._tt.store(position_hash, depth, best_score, flag, best_move)

        return best_score

    def _quiesce(
        self,
        board: SimulationBoard,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
    ) -> float:
        """静态搜索 - 只搜索吃子走法直到局面稳定"""
        stand_pat = self._evaluate(board, color)

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        # 只搜索吃子走法
        captures = self._get_captures(board, color)

        for move in captures:
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return 100000 - ply

            score = -self._quiesce(board, -beta, -alpha, color.opposite, ply + 1)

            board.undo_move(move, captured, was_hidden)

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def _get_captures(self, board: SimulationBoard, color: Color) -> list[JieqiMove]:
        """只获取吃子走法"""
        captures = []
        for piece in board.get_all_pieces(color):
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden

            for to_pos in board.get_potential_moves(piece):
                target = board.get_piece(to_pos)
                if target is None or target.color == color:
                    continue  # 不是吃子

                move = JieqiMove(action_type, piece.position, to_pos)
                captured = board.make_move(move)
                in_check = board.is_in_check(color)
                board.undo_move(move, captured, was_hidden)
                if not in_check:
                    captures.append(move)

        return captures

    def _order_moves(
        self,
        board: SimulationBoard,
        moves: list[JieqiMove],
        color: Color,
        ply: int,
        tt_entry: TTEntry | None = None,
    ) -> list[JieqiMove]:
        """走法排序"""
        scored_moves: list[tuple[float, JieqiMove]] = []
        tt_best = tt_entry.best_move if tt_entry else None

        for move in moves:
            score = 0.0

            if tt_best and move == tt_best:
                score += 10000000

            target = board.get_piece(move.to_pos)

            if target is not None and target.color != color:
                victim_value = get_piece_value(target)
                piece = board.get_piece(move.from_pos)
                attacker_value = get_piece_value(piece) if piece else 0
                score += 1000000 + victim_value * 10 - attacker_value

            if ply < len(self._killers):
                if move in self._killers[ply]:
                    score += 500000

            history_key = (move.from_pos, move.to_pos)
            score += self._history.get(history_key, 0)

            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 100

            scored_moves.append((score, move))

        scored_moves.sort(key=lambda x: -x[0])
        return [m for _, m in scored_moves]

    def _update_killers(self, move: JieqiMove, ply: int) -> None:
        if ply >= len(self._killers):
            return
        killers = self._killers[ply]
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def _update_history(self, move: JieqiMove, depth: int) -> None:
        key = (move.from_pos, move.to_pos)
        self._history[key] = self._history.get(key, 0) + depth * depth

    def _evaluate(self, board: SimulationBoard, color: Color) -> float:
        """评估当前局面"""
        score = 0.0

        # 子力价值 + 位置价值
        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        # 预计算敌方攻击范围
        enemy_attacks: set[Position] = set()
        for enemy in enemy_pieces:
            for pos in board.get_potential_moves(enemy):
                enemy_attacks.add(pos)

        # 预计算己方防守范围
        my_defense: set[Position] = set()
        for ally in my_pieces:
            for pos in board.get_potential_moves(ally):
                my_defense.add(pos)

        for piece in my_pieces:
            piece_score = get_piece_value(piece) + get_position_value(piece)
            score += piece_score

            # 机动性加分（明子可移动位置数）
            if not piece.is_hidden:
                mobility = len(board.get_potential_moves(piece))
                score += mobility * 5

                # 安全性评估：被攻击但未被保护的棋子扣分
                if piece.position in enemy_attacks:
                    if piece.position not in my_defense:
                        score -= get_piece_value(piece) * 0.3

        for piece in enemy_pieces:
            piece_score = get_piece_value(piece) + get_position_value(piece)
            score -= piece_score

            if not piece.is_hidden:
                mobility = len(board.get_potential_moves(piece))
                score -= mobility * 5

        # 将军
        if board.is_in_check(color.opposite):
            score += 500
        if board.is_in_check(color):
            score -= 500

        return score
