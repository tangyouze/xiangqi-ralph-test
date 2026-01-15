"""
v016_muses - Muses-inspired AI Strategy

ID: v016
名称: Muses AI
描述: 参考 miaosisrai 揭棋 AI 的 PVS 搜索和评估思路

核心特性：
1. Principal Variation Search (PVS) - 主变搜索
2. 统一评分系统 (-1000 到 1000)
3. 胜率输出功能
4. 揭棋特有战术评估
5. 暗子期望价值计算
6. Quiescence Search (静态搜索) - 避免水平线效应

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.ai.evaluator import get_evaluator
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimulationBoard
from jieqi.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    from jieqi.view import PlayerView


AI_ID = "v016"
AI_NAME = "muses"


class TTFlag(IntEnum):
    """Transposition Table 节点类型"""

    EXACT = 0
    LOWERBOUND = 1
    UPPERBOUND = 2


@dataclass
class TTEntry:
    """Transposition Table 条目"""

    hash_key: int
    depth: int
    score: float
    flag: TTFlag
    best_move: JieqiMove | None


class TranspositionTable:
    """Transposition Table 实现"""

    def __init__(self, max_size: int = 500000):
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
            # 保留更深的精确值
            if old.depth > depth and old.flag == TTFlag.EXACT:
                return

        if len(self.table) >= self.max_size:
            # 清理老条目
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
class MusesAI(AIStrategy):
    """Muses AI - 参考 miaosisrai 的揭棋 AI

    使用 PVS 搜索和揭棋专用评估函数
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "Muses 风格 AI (v016) - 参考揭棋 AI 大师思路"

    # 搜索参数
    DEFAULT_DEPTH = 5
    MAX_DEPTH = 30
    QS_DEPTH_LIMIT = 4  # 静态搜索最大深度

    # LMR 参数
    LMR_FULL_DEPTH_MOVES = 4
    LMR_REDUCTION_LIMIT = 3

    # 分数常量
    MATE_SCORE = 10000

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.time_limit = self.config.time_limit or 2.0
        if self.config.time_limit:
            self.max_depth = self.MAX_DEPTH
        else:
            self.max_depth = max(self.config.depth, self.DEFAULT_DEPTH)

        self._rng = random.Random(self.config.seed)
        self._tt = TranspositionTable()
        self._evaluator = get_evaluator()
        self._nodes_evaluated = 0
        self._history: dict[tuple[Position, Position], int] = {}
        self._killers: list[list[JieqiMove]] = [[] for _ in range(50)]
        self._start_time = 0.0
        self._best_move_at_depth: dict[int, tuple[JieqiMove, float]] = {}
        self._pv_line: list[JieqiMove] = []

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

        # 解析走法
        parsed_moves = [(move_str, parse_move(move_str)[0]) for move_str in legal_moves]
        move_to_str = {m: s for s, m in parsed_moves}
        jieqi_moves = [m for _, m in parsed_moves]

        self._nodes_evaluated = 0
        self._start_time = time.time()
        self._best_move_at_depth.clear()
        self._pv_line.clear()

        all_scores: dict[JieqiMove, float] = {}

        # 迭代加深搜索
        for depth in range(1, self.max_depth + 1):
            if depth > 1 and time.time() - self._start_time > self.time_limit * 0.7:
                break

            try:
                scores = self._search_root_all(sim_board, jieqi_moves, depth, my_color)
                if scores:
                    all_scores = scores
                    best_move = max(scores, key=scores.get)  # type: ignore
                    best_score = scores[best_move]
                    self._best_move_at_depth[depth] = (best_move, best_score)
            except TimeoutError:
                break

        if not all_scores:
            shuffled = legal_moves[:]
            self._rng.shuffle(shuffled)
            return [(move, 0.0) for move in shuffled[:n]]

        # 转换为字符串格式并排序
        str_scores: dict[str, float] = {}
        for move, score in all_scores.items():
            move_str = move_to_str.get(move)
            if move_str:
                str_scores[move_str] = self._evaluator.normalize_score(score)

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

    def get_evaluation(self, view: PlayerView) -> dict:
        """获取当前局面评估

        返回包含分数和胜率的详细评估信息
        """
        sim_board = SimulationBoard(view)
        return self._evaluator.format_evaluation(sim_board, view.viewer)

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

        prev_best = None
        if depth - 1 in self._best_move_at_depth:
            prev_best = self._best_move_at_depth[depth - 1][0]

        sorted_moves = self._order_moves(board, legal_moves, color, 0, tt_entry, prev_best)

        scores: dict[JieqiMove, float] = {}
        alpha = float("-inf")
        beta = float("inf")

        for i, move in enumerate(sorted_moves):
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue

            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            # 吃将直接返回最高分
            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                scores[move] = self.MATE_SCORE
                continue

            # PVS 搜索
            if i == 0:
                score = -self._pvs(board, depth - 1, -beta, -alpha, color.opposite, 1, True)
            else:
                # 窄窗口搜索
                score = -self._pvs(board, depth - 1, -alpha - 1, -alpha, color.opposite, 1, False)
                if alpha < score < beta:
                    # 重新搜索
                    score = -self._pvs(board, depth - 1, -beta, -score, color.opposite, 1, True)

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
    ) -> float:
        """Principal Variation Search"""
        self._nodes_evaluated += 1

        if self._nodes_evaluated % 2000 == 0:
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
            return -self.MATE_SCORE + ply
        if board.find_king(color.opposite) is None:
            return self.MATE_SCORE - ply

        # 叶子节点 - 使用静态搜索
        if depth <= 0:
            return self._quiescence(board, alpha, beta, color, ply, 0)

        # 获取走法
        legal_moves = board.get_legal_moves(color)
        if not legal_moves:
            if board.is_in_check(color):
                return -self.MATE_SCORE + ply
            return 0  # 和棋

        # 走法排序
        sorted_moves = self._order_moves(board, legal_moves, color, ply, tt_entry)

        best_score = float("-inf")
        best_move = None
        in_check = board.is_in_check(color)

        for i, move in enumerate(sorted_moves):
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue

            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            # 吃将
            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return self.MATE_SCORE - ply

            # Late Move Reduction
            new_depth = depth - 1
            if (
                i >= self.LMR_FULL_DEPTH_MOVES
                and depth >= self.LMR_REDUCTION_LIMIT
                and captured is None
                and not in_check
                and not was_hidden
            ):
                reduction = 1 if i < 10 else 2
                new_depth = max(1, depth - 1 - reduction)

            # PVS 搜索
            if i == 0 or not is_pv:
                score = -self._pvs(board, new_depth, -beta, -alpha, color.opposite, ply + 1, is_pv)
            else:
                score = -self._pvs(
                    board, new_depth, -alpha - 1, -alpha, color.opposite, ply + 1, False
                )
                if alpha < score < beta:
                    score = -self._pvs(
                        board, depth - 1, -beta, -score, color.opposite, ply + 1, True
                    )

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

        # 存储 TT
        if best_score <= alpha_orig:
            flag = TTFlag.UPPERBOUND
        elif best_score >= beta:
            flag = TTFlag.LOWERBOUND
        else:
            flag = TTFlag.EXACT

        self._tt.store(position_hash, depth, best_score, flag, best_move)

        return best_score

    def _quiescence(
        self,
        board: SimulationBoard,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
        qs_depth: int,
    ) -> float:
        """静态搜索 - 避免水平线效应

        只搜索吃子走法，直到局面稳定
        """
        # 使用评估器获取评分
        stand_pat = self._evaluator.evaluate(board, color)

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        # 深度限制
        if qs_depth >= self.QS_DEPTH_LIMIT:
            return stand_pat

        # 只搜索吃子走法
        captures = self._get_captures(board, color)

        # MVV-LVA 排序
        captures.sort(key=lambda m: self._mvv_lva_score(board, m), reverse=True)

        for move in captures:
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue

            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return self.MATE_SCORE - ply

            score = -self._quiescence(board, -beta, -alpha, color.opposite, ply + 1, qs_depth + 1)

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
                    continue

                move = JieqiMove(action_type, piece.position, to_pos)
                captured = board.make_move(move)
                in_check = board.is_in_check(color)
                board.undo_move(move, captured, was_hidden)
                if not in_check:
                    captures.append(move)

        return captures

    def _mvv_lva_score(self, board: SimulationBoard, move: JieqiMove) -> int:
        """MVV-LVA 分数计算"""
        target = board.get_piece(move.to_pos)
        piece = board.get_piece(move.from_pos)

        if target is None:
            return 0

        victim_value = int(self._evaluator.get_piece_value(target))
        attacker_value = int(self._evaluator.get_piece_value(piece)) if piece else 0

        return victim_value * 10 - attacker_value

    def _order_moves(
        self,
        board: SimulationBoard,
        moves: list[JieqiMove],
        color: Color,
        ply: int,
        tt_entry: TTEntry | None = None,
        prev_best: JieqiMove | None = None,
    ) -> list[JieqiMove]:
        """走法排序"""
        scored_moves: list[tuple[float, JieqiMove]] = []
        tt_best = tt_entry.best_move if tt_entry else None

        for move in moves:
            score = 0.0

            # 上一次迭代的最佳走法
            if prev_best and move == prev_best:
                score += 20000000

            # TT 最佳走法
            if tt_best and move == tt_best:
                score += 10000000

            target = board.get_piece(move.to_pos)

            # MVV-LVA
            if target is not None and target.color != color:
                score += 1000000 + self._mvv_lva_score(board, move)

            # Killer moves
            if ply < len(self._killers):
                if move in self._killers[ply]:
                    score += 500000

            # 历史启发式
            history_key = (move.from_pos, move.to_pos)
            score += self._history.get(history_key, 0)

            # 揭子走法有价值
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                piece = board.get_piece(move.from_pos)
                if piece:
                    # 根据位置判断揭子价值
                    if not move.to_pos.is_on_own_side(color):
                        score += 300  # 过河揭子更有价值
                    else:
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
