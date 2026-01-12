"""
v012_alphabeta - Alpha-Beta with Transposition Table AI

ID: v012
名称: AlphaBeta AI
描述: 在 v011 基础上添加 Transposition Table 和改进的评估函数

改进方向：
- Transposition Table (TT) 缓存已评估的局面
- 改进的走法排序（吃子、将军优先）
- Killer Move 启发式
- 历史启发式

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    from jieqi.view import PlayerView


AI_ID = "v012"
AI_NAME = "alphabeta"


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

HIDDEN_PIECE_VALUE = 350


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


class TTFlag(IntEnum):
    """Transposition Table 节点类型"""

    EXACT = 0  # 精确值
    LOWERBOUND = 1  # 下界（beta cutoff）
    UPPERBOUND = 2  # 上界（alpha cutoff）


@dataclass
class TTEntry:
    """Transposition Table 条目"""

    hash_key: int
    depth: int
    score: float
    flag: TTFlag
    best_move: JieqiMove | None


class TranspositionTable:
    """Transposition Table 实现

    使用 hash 来快速查找已评估的局面。
    """

    def __init__(self, max_size: int = 100000):
        self.max_size = max_size
        self.table: dict[int, TTEntry] = {}

    def get(self, hash_key: int) -> TTEntry | None:
        """查找条目"""
        return self.table.get(hash_key)

    def store(
        self,
        hash_key: int,
        depth: int,
        score: float,
        flag: TTFlag,
        best_move: JieqiMove | None,
    ) -> None:
        """存储条目"""
        # 如果表满了，使用替换策略
        if len(self.table) >= self.max_size:
            # 简单策略：如果新条目深度更大，替换旧条目
            old_entry = self.table.get(hash_key)
            if old_entry is not None and old_entry.depth > depth:
                return  # 保留更深的搜索结果

        self.table[hash_key] = TTEntry(hash_key, depth, score, flag, best_move)

    def clear(self) -> None:
        """清空表"""
        self.table.clear()


@AIEngine.register(AI_NAME)
class AlphaBetaAI(AIStrategy):
    """Alpha-Beta with Transposition Table AI

    使用 TT 来避免重复评估相同局面。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "Alpha-Beta 搜索 + TT (v012)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        # 默认深度2（有TT后可以搜索更深）
        if self.config.depth == 3:
            self.config.depth = 2
        self._rng = random.Random(self.config.seed)
        self._tt = TranspositionTable()
        self._nodes_evaluated = 0
        # 历史启发式表
        self._history: dict[tuple[Position, Position], int] = {}
        # Killer moves（每层保存2个）
        self._killers: list[list[JieqiMove]] = [[] for _ in range(10)]

    def select_move(self, view: PlayerView) -> JieqiMove | None:
        """选择最佳走法"""
        if not view.legal_moves:
            return None

        if len(view.legal_moves) == 1:
            return view.legal_moves[0]

        my_color = view.viewer
        depth = self.config.depth

        # 创建模拟棋盘
        sim_board = SimulationBoard(view)
        self._nodes_evaluated = 0

        # 获取局面哈希
        position_hash = sim_board.get_position_hash()

        # 对走法排序
        sorted_moves = self._order_moves(sim_board, view.legal_moves, my_color, 0)

        best_score = float("-inf")
        best_moves: list[JieqiMove] = []

        alpha = float("-inf")
        beta = float("inf")

        for move in sorted_moves:
            piece = sim_board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = sim_board.make_move(move)

            # 吃将直接返回
            if captured and captured.actual_type == PieceType.KING:
                sim_board.undo_move(move, captured, was_hidden)
                return move

            score = -self._alpha_beta(sim_board, depth - 1, -beta, -alpha, my_color.opposite, 1)

            sim_board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_moves = [move]
                alpha = max(alpha, score)
            elif score == best_score:
                best_moves.append(move)

        return self._rng.choice(best_moves)

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
        self._nodes_evaluated += 1
        alpha_orig = alpha

        # 获取局面哈希
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
            return -50000 + ply  # 距离越近的将死越好
        if board.find_king(color.opposite) is None:
            return 50000 - ply

        # 达到搜索深度，返回静态评估
        if depth <= 0:
            score = self._evaluate(board, color)
            self._tt.store(position_hash, 0, score, TTFlag.EXACT, None)
            return score

        # 获取走法
        legal_moves = board.get_legal_moves(color)
        if not legal_moves:
            if board.is_in_check(color):
                return -40000 + ply  # 被将死
            return 0  # 逼和

        # 走法排序
        sorted_moves = self._order_moves(board, legal_moves, color, ply, tt_entry)

        best_score = float("-inf")
        best_move = None

        for move in sorted_moves:
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            # 吃将
            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return 50000 - ply

            score = -self._alpha_beta(board, depth - 1, -beta, -alpha, color.opposite, ply + 1)

            board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, score)

            # Beta cutoff
            if alpha >= beta:
                # 更新 killer moves 和历史启发式
                if captured is None:  # 非吃子走法
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

    def _order_moves(
        self,
        board: SimulationBoard,
        moves: list[JieqiMove],
        color: Color,
        ply: int,
        tt_entry: TTEntry | None = None,
    ) -> list[JieqiMove]:
        """对走法排序以提高剪枝效率

        优先级：
        1. TT 中的最佳走法
        2. 吃子走法（按 MVV-LVA 排序）
        3. Killer moves
        4. 历史启发式
        5. 其他走法
        """
        scored_moves: list[tuple[float, JieqiMove]] = []

        tt_best = tt_entry.best_move if tt_entry else None

        for move in moves:
            score = 0.0

            # TT 最佳走法最高优先级
            if tt_best and move == tt_best:
                score += 1000000

            target = board.get_piece(move.to_pos)

            # 吃子得分（MVV-LVA: Most Valuable Victim - Least Valuable Attacker）
            if target is not None and target.color != color:
                victim_value = get_piece_value(target)
                piece = board.get_piece(move.from_pos)
                attacker_value = get_piece_value(piece) if piece else 0
                # MVV-LVA: 优先用低价值棋子吃高价值棋子
                score += 100000 + victim_value * 10 - attacker_value

            # Killer move
            if ply < len(self._killers):
                if move in self._killers[ply]:
                    score += 50000

            # 历史启发式
            history_key = (move.from_pos, move.to_pos)
            score += self._history.get(history_key, 0)

            # 揭子有一定价值
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 10

            scored_moves.append((score, move))

        scored_moves.sort(key=lambda x: -x[0])
        return [m for _, m in scored_moves]

    def _update_killers(self, move: JieqiMove, ply: int) -> None:
        """更新 killer moves"""
        if ply >= len(self._killers):
            return

        killers = self._killers[ply]
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def _update_history(self, move: JieqiMove, depth: int) -> None:
        """更新历史启发式表"""
        key = (move.from_pos, move.to_pos)
        self._history[key] = self._history.get(key, 0) + depth * depth

    def _evaluate(self, board: SimulationBoard, color: Color) -> float:
        """评估当前局面"""
        score = 0.0

        # 子力价值
        for piece in board.get_all_pieces():
            value = get_piece_value(piece)

            if piece.color == color:
                score += value
            else:
                score -= value

        # 将军
        if board.is_in_check(color.opposite):
            score += 50
        if board.is_in_check(color):
            score -= 50

        return score
