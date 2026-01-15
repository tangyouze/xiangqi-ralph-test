"""
v021_pvs - Principal Variation Search with Advanced Pruning

ID: v021
名称: pvs
描述: 使用高级剪枝技术的 PVS 搜索引擎

改进方向：
1. Null Move Pruning (NMP) - 空着剪枝
2. Aspiration Windows - 渐进式窗口搜索
3. Futility Pruning - 无望剪枝
4. Countermove Heuristic - 反驳走法启发
5. Late Move Pruning (LMP) - 晚期走法剪枝
6. Internal Iterative Deepening (IID) - 内部迭代加深
7. Static Exchange Evaluation (SEE) - 静态交换评估

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import math
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


AI_ID = "v021"
AI_NAME = "pvs"


# 棋子基础价值
PIECE_VALUES = {
    PieceType.KING: 100000,
    PieceType.ROOK: 9000,
    PieceType.CANNON: 4500,
    PieceType.HORSE: 4000,
    PieceType.ELEPHANT: 2000,
    PieceType.ADVISOR: 2000,
    PieceType.PAWN: 1000,
}

PAWN_CROSSED_RIVER = 2000
HIDDEN_PIECE_VALUE = 3200

# 位置评估表 (10行 x 9列)
# 车
ROOK_PST = [
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [5, 5, 10, 15, 20, 15, 10, 5, 5],
    [10, 15, 20, 30, 35, 30, 20, 15, 10],
    [15, 20, 30, 40, 45, 40, 30, 20, 15],
    [20, 25, 35, 45, 50, 45, 35, 25, 20],
    [25, 30, 40, 50, 55, 50, 40, 30, 25],
    [30, 35, 45, 55, 60, 55, 45, 35, 30],
    [35, 40, 50, 60, 70, 60, 50, 40, 35],
]

# 马
HORSE_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 10, 15, 15, 15, 15, 15, 10, 0],
    [0, 15, 25, 25, 25, 25, 25, 15, 0],
    [10, 20, 30, 40, 40, 40, 30, 20, 10],
    [15, 30, 40, 50, 55, 50, 40, 30, 15],
    [20, 35, 50, 60, 65, 60, 50, 35, 20],
    [25, 40, 55, 65, 70, 65, 55, 40, 25],
    [20, 35, 50, 60, 65, 60, 50, 35, 20],
    [10, 25, 35, 45, 50, 45, 35, 25, 10],
    [0, 10, 20, 25, 30, 25, 20, 10, 0],
]

# 炮
CANNON_PST = [
    [0, 10, 15, 15, 20, 15, 15, 10, 0],
    [5, 15, 20, 25, 30, 25, 20, 15, 5],
    [5, 15, 25, 30, 35, 30, 25, 15, 5],
    [10, 20, 30, 40, 50, 40, 30, 20, 10],
    [15, 30, 45, 55, 60, 55, 45, 30, 15],
    [20, 35, 50, 60, 65, 60, 50, 35, 20],
    [15, 30, 45, 55, 60, 55, 45, 30, 15],
    [10, 25, 35, 45, 50, 45, 35, 25, 10],
    [5, 15, 25, 30, 35, 30, 25, 15, 5],
    [0, 10, 15, 20, 25, 20, 15, 10, 0],
]

# 兵
PAWN_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 5, 10, 10, 15, 10, 10, 5, 5],
    [20, 25, 35, 45, 50, 45, 35, 25, 20],
    [30, 40, 55, 65, 70, 65, 55, 40, 30],
    [40, 55, 70, 80, 85, 80, 70, 55, 40],
    [50, 65, 80, 90, 95, 90, 80, 65, 50],
    [60, 75, 90, 100, 105, 100, 90, 75, 60],
]

PST_TABLES = {
    PieceType.ROOK: ROOK_PST,
    PieceType.HORSE: HORSE_PST,
    PieceType.CANNON: CANNON_PST,
    PieceType.PAWN: PAWN_PST,
}


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE

    value = PIECE_VALUES.get(piece.actual_type, 0)
    if piece.actual_type == PieceType.PAWN:
        if not piece.position.is_on_own_side(piece.color):
            value = PAWN_CROSSED_RIVER
    return value


def get_pst_value(piece: SimPiece) -> int:
    """获取位置加成"""
    if piece.is_hidden or piece.actual_type is None:
        return 0

    pst = PST_TABLES.get(piece.actual_type)
    if pst is None:
        return 0

    row, col = piece.position.row, piece.position.col
    if piece.color == Color.BLACK:
        row = 9 - row

    if 0 <= row < 10 and 0 <= col < 9:
        return pst[row][col]
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
    """置换表"""

    def __init__(self, max_size: int = 1000000):
        self.max_size = max_size
        self.table: dict[int, TTEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, hash_key: int) -> TTEntry | None:
        entry = self.table.get(hash_key)
        if entry:
            self.hits += 1
        else:
            self.misses += 1
        return entry

    def store(
        self,
        hash_key: int,
        depth: int,
        score: float,
        flag: TTFlag,
        best_move: JieqiMove | None,
    ) -> None:
        old = self.table.get(hash_key)
        if old is not None:
            # 替换策略：更深的搜索优先
            if old.depth > depth and old.flag == TTFlag.EXACT:
                return

        if len(self.table) >= self.max_size:
            if len(self.table) > self.max_size * 0.9:
                to_delete = list(self.table.keys())[: self.max_size // 4]
                for k in to_delete:
                    del self.table[k]

        self.table[hash_key] = TTEntry(hash_key, depth, score, flag, best_move)

    def clear(self) -> None:
        self.table.clear()
        self.hits = 0
        self.misses = 0


@AIEngine.register(AI_NAME)
class PVSAI(AIStrategy):
    """Principal Variation Search with Advanced Pruning

    高级特性:
    1. Null Move Pruning - 空着剪枝
    2. Aspiration Windows - 渐进式窗口
    3. Futility Pruning - 无望剪枝
    4. Late Move Reduction (LMR)
    5. Late Move Pruning (LMP)
    6. Countermove Heuristic
    7. Internal Iterative Deepening (IID)
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "PVS高级搜索 (v021) - Null Move + Aspiration + Futility"

    # 搜索参数
    NULL_MOVE_REDUCTION = 2  # 空着减少深度
    NULL_MOVE_DEPTH_LIMIT = 3  # 最低深度才使用空着
    FUTILITY_MARGIN = 3000  # 无望剪枝边界
    FUTILITY_DEPTH = 3  # 无望剪枝最大深度
    LMR_FULL_DEPTH_MOVES = 4  # 前N个走法不使用LMR
    LMR_DEPTH_LIMIT = 3  # LMR最小深度
    LMP_DEPTH = 3  # 晚期走法剪枝深度
    LMP_MOVE_COUNT = [0, 5, 10, 15]  # 每个深度的走法数限制
    IID_DEPTH = 4  # IID 最小深度
    ASPIRATION_WINDOW = 500  # 初始渐进窗口

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.time_limit = self.config.time_limit or 2.0
        if self.config.time_limit:
            self.max_depth = 40
        else:
            self.max_depth = max(self.config.depth, 4)

        self._rng = random.Random(self.config.seed)
        self._tt = TranspositionTable()
        self._nodes_evaluated = 0
        self._start_time = 0.0

        # 启发式表
        self._history: dict[tuple[Position, Position], int] = {}
        self._killers: list[list[JieqiMove]] = [[] for _ in range(50)]
        self._countermove: dict[tuple[Position, Position], JieqiMove] = {}

        # 迭代加深状态
        self._best_move_at_depth: dict[int, JieqiMove] = {}
        self._prev_score: float = 0.0

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        if len(legal_moves) == 1:
            return [(legal_moves[0], 0.0)]

        state = parse_fen(fen)
        my_color = state.turn

        sim_board = create_board_from_fen(fen)
        self._nodes_evaluated = 0
        self._start_time = time.time()
        self._best_move_at_depth.clear()
        self._prev_score = 0.0

        # 解析走法
        parsed_moves = [(move_str, parse_move(move_str)[0]) for move_str in legal_moves]
        move_to_str = {m: s for s, m in parsed_moves}
        jieqi_moves = [m for _, m in parsed_moves]

        # 迭代加深 + Aspiration Windows
        all_scores: dict[JieqiMove, float] = {}

        for depth in range(1, self.max_depth + 1):
            if depth > 1 and time.time() - self._start_time > self.time_limit * 0.7:
                break

            try:
                if depth <= 2:
                    # 浅层不使用 aspiration
                    scores = self._search_root_all(
                        sim_board, jieqi_moves, depth, my_color, float("-inf"), float("inf")
                    )
                else:
                    # Aspiration Windows
                    alpha = self._prev_score - self.ASPIRATION_WINDOW
                    beta = self._prev_score + self.ASPIRATION_WINDOW

                    scores = self._search_root_all(
                        sim_board, jieqi_moves, depth, my_color, alpha, beta
                    )

                    # 检查是否 fail-high 或 fail-low
                    if scores:
                        best_score = max(scores.values())
                        if best_score <= alpha:
                            # Fail-low: 重新搜索
                            scores = self._search_root_all(
                                sim_board,
                                jieqi_moves,
                                depth,
                                my_color,
                                float("-inf"),
                                beta,
                            )
                        elif best_score >= beta:
                            # Fail-high: 重新搜索
                            scores = self._search_root_all(
                                sim_board,
                                jieqi_moves,
                                depth,
                                my_color,
                                alpha,
                                float("inf"),
                            )

                if scores:
                    all_scores = scores
                    best_move = max(scores, key=scores.get)
                    self._best_move_at_depth[depth] = best_move
                    self._prev_score = scores[best_move]

            except TimeoutError:
                break

        if not all_scores:
            shuffled = legal_moves[:]
            self._rng.shuffle(shuffled)
            return [(move, 0.0) for move in shuffled[:n]]

        # 转换结果
        str_scores: dict[str, float] = {}
        for move, score in all_scores.items():
            move_str = move_to_str.get(move)
            if move_str:
                str_scores[move_str] = self._normalize_score(score)

        sorted_results = sorted(str_scores.items(), key=lambda x: -x[1])

        # 处理同分
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
        alpha: float,
        beta: float,
    ) -> dict[JieqiMove, float]:
        """根节点搜索，返回所有走法的评分"""
        position_hash = board.get_position_hash()
        tt_entry = self._tt.get(position_hash)

        prev_best = self._best_move_at_depth.get(depth - 1)
        sorted_moves = self._order_moves(board, legal_moves, color, 0, tt_entry, prev_best, None)

        scores: dict[JieqiMove, float] = {}

        for i, move in enumerate(sorted_moves):
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

            # PVS
            if i == 0:
                score = -self._pvs(board, depth - 1, -beta, -alpha, color.opposite, 1, True, move)
            else:
                score = -self._pvs(
                    board, depth - 1, -alpha - 1, -alpha, color.opposite, 1, False, move
                )
                if alpha < score < beta:
                    score = -self._pvs(
                        board, depth - 1, -beta, -score, color.opposite, 1, True, move
                    )

            board.undo_move(move, captured, was_hidden)
            scores[move] = score
            alpha = max(alpha, score)

        return scores

    def _pvs(
        self,
        board: SimulationBoard,
        depth: int,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
        is_pv: bool,
        prev_move: JieqiMove | None,
    ) -> float:
        """Principal Variation Search with advanced pruning"""
        self._nodes_evaluated += 1
        if self._nodes_evaluated % 3000 == 0:
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

        alpha_orig = alpha
        position_hash = board.get_position_hash()

        # TT 查找
        tt_entry = self._tt.get(position_hash)
        if tt_entry is not None and tt_entry.depth >= depth and not is_pv:
            if tt_entry.flag == TTFlag.EXACT:
                return tt_entry.score
            elif tt_entry.flag == TTFlag.LOWERBOUND:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == TTFlag.UPPERBOUND:
                beta = min(beta, tt_entry.score)

            if alpha >= beta:
                return tt_entry.score

        # 终局检查
        if board.find_king(color) is None:
            return -100000 + ply
        if board.find_king(color.opposite) is None:
            return 100000 - ply

        in_check = board.is_in_check(color)

        # 叶子节点
        if depth <= 0:
            return self._quiesce(board, alpha, beta, color, ply)

        # Null Move Pruning (不在PV节点、被将军时、深度太浅时使用)
        if (
            not is_pv
            and not in_check
            and depth >= self.NULL_MOVE_DEPTH_LIMIT
            and self._has_non_pawn_pieces(board, color)
        ):
            # 执行空着（跳过当前方）
            board._current_turn = color.opposite

            # 用减少的深度搜索
            reduction = self.NULL_MOVE_REDUCTION + (depth // 4)
            null_score = -self._pvs(
                board,
                depth - 1 - reduction,
                -beta,
                -beta + 1,
                color.opposite,
                ply + 1,
                False,
                None,
            )

            board._current_turn = color

            if null_score >= beta:
                # 验证搜索（可选，防止 zugzwang）
                if depth >= 6:
                    verify_score = self._pvs(
                        board, depth - 5, beta - 1, beta, color, ply, False, prev_move
                    )
                    if verify_score >= beta:
                        return beta
                else:
                    return beta

        # 获取走法
        legal_moves = board.get_legal_moves(color)
        if not legal_moves:
            if in_check:
                return -100000 + ply  # 被将死
            return 0  # 和棋

        # Internal Iterative Deepening (IID)
        # 如果没有 TT 最佳走法，先做浅层搜索获取
        if tt_entry is None and depth >= self.IID_DEPTH and is_pv:
            self._pvs(board, depth - 2, alpha, beta, color, ply, True, prev_move)
            tt_entry = self._tt.get(position_hash)

        # 排序走法
        sorted_moves = self._order_moves(board, legal_moves, color, ply, tt_entry, None, prev_move)

        # 静态评估（用于剪枝）
        static_eval = self._evaluate(board, color) if not in_check else 0

        best_score = float("-inf")
        best_move = None
        moves_searched = 0

        for i, move in enumerate(sorted_moves):
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue

            target = board.get_piece(move.to_pos)
            is_capture = target is not None and target.color != color
            is_reveal = move.action_type == ActionType.REVEAL_AND_MOVE
            was_hidden = piece.is_hidden

            # Futility Pruning
            if (
                not is_pv
                and not in_check
                and depth <= self.FUTILITY_DEPTH
                and not is_capture
                and not is_reveal
                and static_eval + self.FUTILITY_MARGIN * depth < alpha
            ):
                continue

            # Late Move Pruning (LMP)
            if (
                not is_pv
                and not in_check
                and depth <= self.LMP_DEPTH
                and moves_searched >= self.LMP_MOVE_COUNT[depth]
                and not is_capture
                and not is_reveal
            ):
                continue

            captured = board.make_move(move)

            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return 100000 - ply

            gives_check = board.is_in_check(color.opposite)

            # Late Move Reduction (LMR)
            new_depth = depth - 1
            if (
                moves_searched >= self.LMR_FULL_DEPTH_MOVES
                and depth >= self.LMR_DEPTH_LIMIT
                and not is_capture
                and not in_check
                and not gives_check
                and not is_reveal
            ):
                reduction = 1 + (moves_searched // 8)
                if not is_pv:
                    reduction += 1
                new_depth = max(1, depth - 1 - reduction)

            # 搜索
            if moves_searched == 0:
                score = -self._pvs(
                    board, new_depth, -beta, -alpha, color.opposite, ply + 1, is_pv, move
                )
            else:
                # PVS: 先窄窗口
                score = -self._pvs(
                    board, new_depth, -alpha - 1, -alpha, color.opposite, ply + 1, False, move
                )
                # LMR 失败重搜
                if score > alpha and new_depth < depth - 1:
                    score = -self._pvs(
                        board, depth - 1, -alpha - 1, -alpha, color.opposite, ply + 1, False, move
                    )
                # 窄窗口失败重搜
                if alpha < score < beta:
                    score = -self._pvs(
                        board, depth - 1, -beta, -score, color.opposite, ply + 1, True, move
                    )

            board.undo_move(move, captured, was_hidden)
            moves_searched += 1

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, score)

            if alpha >= beta:
                # 更新启发式
                if not is_capture:
                    self._update_killers(move, ply)
                    self._update_history(move, depth)
                    if prev_move:
                        self._countermove[(prev_move.from_pos, prev_move.to_pos)] = move
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

    def _has_non_pawn_pieces(self, board: SimulationBoard, color: Color) -> bool:
        """检查是否有非兵棋子（用于 Null Move 安全检查）"""
        for piece in board.get_all_pieces(color):
            if piece.is_hidden:
                return True
            if piece.actual_type not in (PieceType.PAWN, PieceType.KING):
                return True
        return False

    def _quiesce(
        self,
        board: SimulationBoard,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
    ) -> float:
        """静态搜索"""
        stand_pat = self._evaluate(board, color)

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        # Delta Pruning
        DELTA = 9500  # 最大可能的吃子价值（车 + 一点余量）
        if stand_pat + DELTA < alpha:
            return alpha

        captures = self._get_captures(board, color)
        captures.sort(key=lambda m: self._mvv_lva_score(board, m), reverse=True)

        for move in captures:
            # Delta Pruning for individual captures
            target = board.get_piece(move.to_pos)
            if target and stand_pat + get_piece_value(target) + 200 < alpha:
                continue

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

    def _mvv_lva_score(self, board: SimulationBoard, move: JieqiMove) -> int:
        """MVV-LVA 分数"""
        target = board.get_piece(move.to_pos)
        piece = board.get_piece(move.from_pos)

        if target is None:
            return 0

        victim = get_piece_value(target)
        attacker = get_piece_value(piece) if piece else 0

        return victim * 10 - attacker

    def _get_captures(self, board: SimulationBoard, color: Color) -> list[JieqiMove]:
        """只获取吃子走法"""
        captures = []
        for piece in board.get_all_pieces(color):
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden

            for to_pos in board.get_potential_moves(piece):
                target = board.get_piece(to_pos)
                if target is None or target.color == color:
                    continue

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
        prev_best: JieqiMove | None = None,
        last_move: JieqiMove | None = None,
    ) -> list[JieqiMove]:
        """走法排序"""
        scored_moves: list[tuple[float, JieqiMove]] = []
        tt_best = tt_entry.best_move if tt_entry else None

        # 获取反驳走法
        countermove = None
        if last_move:
            countermove = self._countermove.get((last_move.from_pos, last_move.to_pos))

        for move in moves:
            score = 0.0

            # 上一次迭代的最佳走法
            if prev_best and move == prev_best:
                score += 30000000

            # TT 最佳走法
            if tt_best and move == tt_best:
                score += 20000000

            target = board.get_piece(move.to_pos)

            # MVV-LVA
            if target is not None and target.color != color:
                score += 10000000 + self._mvv_lva_score(board, move)

            # 反驳走法
            if countermove and move == countermove:
                score += 800000

            # Killer moves
            if ply < len(self._killers):
                if move in self._killers[ply]:
                    score += 600000

            # 历史启发式
            history_key = (move.from_pos, move.to_pos)
            score += self._history.get(history_key, 0)

            # 揭子
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 300

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
        bonus = depth * depth
        # History 衰减
        self._history[key] = self._history.get(key, 0) + bonus
        # 限制最大值
        if self._history[key] > 1000000:
            for k in self._history:
                self._history[k] //= 2

    def _evaluate(self, board: SimulationBoard, color: Color) -> float:
        """评估当前局面"""
        score = 0.0

        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        # 预计算攻击范围
        enemy_attacks: set[Position] = set()
        for enemy in enemy_pieces:
            for pos in board.get_potential_moves(enemy):
                enemy_attacks.add(pos)

        my_defense: set[Position] = set()
        for ally in my_pieces:
            for pos in board.get_potential_moves(ally):
                my_defense.add(pos)

        # 子力 + 位置价值
        for piece in my_pieces:
            score += get_piece_value(piece)
            score += get_pst_value(piece)

            # 安全性
            if not piece.is_hidden and piece.position in enemy_attacks:
                if piece.position not in my_defense:
                    score -= get_piece_value(piece) * 0.25

        for piece in enemy_pieces:
            score -= get_piece_value(piece)
            score -= get_pst_value(piece)

        # 将军
        if board.is_in_check(color.opposite):
            score += 500
        if board.is_in_check(color):
            score -= 500

        # 机动性
        my_mobility = sum(len(board.get_potential_moves(p)) for p in my_pieces if not p.is_hidden)
        enemy_mobility = sum(
            len(board.get_potential_moves(p)) for p in enemy_pieces if not p.is_hidden
        )
        score += (my_mobility - enemy_mobility) * 3

        # 揭棋特有：暗子价值
        total_pieces = len(my_pieces) + len(enemy_pieces)
        my_hidden = len([p for p in my_pieces if p.is_hidden])
        enemy_hidden = len([p for p in enemy_pieces if p.is_hidden])

        if total_pieces > 24:
            score += (my_hidden - enemy_hidden) * 50
        else:
            my_revealed = len(my_pieces) - my_hidden
            enemy_revealed = len(enemy_pieces) - enemy_hidden
            score += (my_revealed - enemy_revealed) * 30

        return score

    def _normalize_score(self, score: float) -> float:
        """归一化分数到 -1000 到 1000"""
        SCALE_FACTOR = 20000.0
        return math.tanh(score / SCALE_FACTOR) * 1000.0
