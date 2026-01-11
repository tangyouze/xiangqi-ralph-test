"""
v014_advanced - Advanced Search with Improved Evaluation

ID: v014
名称: Advanced AI
描述: 在 v013 基础上添加更多评估因素和搜索优化

改进方向：
- Late Move Reduction (LMR) - 对不太可能的走法减少搜索深度
- 更精细的评估函数：
  - 兵过河加分 (1 -> 2)
  - 棋子机动性评估
  - 棋子协作评估（保护关系）
  - 王的安全性
- 更好的走法排序
- 揭棋特有策略优化
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.bitboard import FastMoveGenerator
from jieqi.types import Color, PieceType, GameResult, Position, ActionType, JieqiMove

if TYPE_CHECKING:
    from jieqi.game import JieqiGame
    from jieqi.piece import JieqiPiece
    from jieqi.board import JieqiBoard


AI_ID = "v014"
AI_NAME = "advanced"


# 棋子基础价值（基于经典象棋理论）
# 单位：厘兵 (centipawn)
PIECE_VALUES = {
    PieceType.KING: 100000,
    PieceType.ROOK: 9000,  # 车最强
    PieceType.CANNON: 4500,  # 炮
    PieceType.HORSE: 4000,  # 马
    PieceType.ELEPHANT: 2000,  # 象
    PieceType.ADVISOR: 2000,  # 士
    PieceType.PAWN: 1000,  # 兵（过河前）
}

# 兵过河后价值翻倍
PAWN_CROSSED_RIVER = 2000

# 隐藏棋子期望价值
HIDDEN_PIECE_VALUE = 3200


# 位置评估表 (10行 x 9列)
# 车：控制中心线和敌方底线
ROOK_PST = [
    # 红方视角: row 0 是红方底线, row 9 是黑方底线
    [0, 0, 0, 0, 0, 0, 0, 0, 0],  # 0
    [0, 0, 0, 0, 0, 0, 0, 0, 0],  # 1
    [0, 0, 0, 0, 0, 0, 0, 0, 0],  # 2
    [5, 5, 10, 15, 20, 15, 10, 5, 5],  # 3
    [10, 15, 20, 30, 35, 30, 20, 15, 10],  # 4
    [15, 20, 30, 40, 45, 40, 30, 20, 15],  # 5 - 过河
    [20, 25, 35, 45, 50, 45, 35, 25, 20],  # 6
    [25, 30, 40, 50, 55, 50, 40, 30, 25],  # 7
    [30, 35, 45, 55, 60, 55, 45, 35, 30],  # 8
    [35, 40, 50, 60, 70, 60, 50, 40, 35],  # 9 - 敌方底线
]

# 马：中心控制和进攻位置
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

# 炮：远程控制和炮架位置
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

# 兵：鼓励过河和前进
PAWN_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 5, 10, 10, 15, 10, 10, 5, 5],  # 4 - 过河前一行
    [20, 25, 35, 45, 50, 45, 35, 25, 20],  # 5 - 刚过河
    [30, 40, 55, 65, 70, 65, 55, 40, 30],  # 6
    [40, 55, 70, 80, 85, 80, 70, 55, 40],  # 7
    [50, 65, 80, 90, 95, 90, 80, 65, 50],  # 8
    [60, 75, 90, 100, 105, 100, 90, 75, 60],  # 9 - 敌方底线
]

PST_TABLES = {
    PieceType.ROOK: ROOK_PST,
    PieceType.HORSE: HORSE_PST,
    PieceType.CANNON: CANNON_PST,
    PieceType.PAWN: PAWN_PST,
}


def get_piece_base_value(piece: JieqiPiece) -> int:
    """获取棋子基础价值"""
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE

    value = PIECE_VALUES.get(piece.actual_type, 0)

    # 兵过河加分
    if piece.actual_type == PieceType.PAWN:
        if not piece.position.is_on_own_side(piece.color):
            value = PAWN_CROSSED_RIVER

    return value


def get_pst_value(piece: JieqiPiece) -> int:
    """获取位置加成"""
    if piece.is_hidden:
        return 0

    pst = PST_TABLES.get(piece.actual_type)
    if pst is None:
        return 0

    row, col = piece.position.row, piece.position.col

    # 黑方需要翻转棋盘视角
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
        # 替换策略：更深的搜索或精确值
        old = self.table.get(hash_key)
        if old is not None:
            if old.depth > depth and old.flag == TTFlag.EXACT:
                return

        if len(self.table) >= self.max_size:
            # 简单清理：删除一些旧条目
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
class AdvancedAI(AIStrategy):
    """Advanced AI with LMR and Improved Evaluation"""

    name = AI_NAME
    ai_id = AI_ID
    description = "高级搜索 + 改进评估 (v014)"

    # LMR 参数
    LMR_FULL_DEPTH_MOVES = 4  # 前 N 个走法不使用 LMR
    LMR_REDUCTION_LIMIT = 3  # 最少需要搜索的深度

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        self.max_depth = max(self.config.depth, 3)
        self.time_limit = self.config.time_limit or 1.5

        self._rng = random.Random(self.config.seed)
        self._tt = TranspositionTable()
        self._fast_gen = None
        self._nodes_evaluated = 0
        self._history: dict[tuple[Position, Position], int] = {}
        self._killers: list[list[JieqiMove]] = [[] for _ in range(30)]
        self._start_time = 0.0
        self._best_move_at_depth: dict[int, JieqiMove] = {}

    def select_move(self, game: JieqiGame) -> JieqiMove | None:
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        if len(legal_moves) == 1:
            return legal_moves[0]

        my_color = game.current_turn
        self._fast_gen = FastMoveGenerator(game.board)
        self._nodes_evaluated = 0
        self._start_time = time.time()
        self._best_move_at_depth.clear()

        # 迭代加深
        best_move = legal_moves[0]
        best_score = float("-inf")

        for depth in range(1, self.max_depth + 1):
            if time.time() - self._start_time > self.time_limit * 0.7:
                break

            try:
                move, score = self._search_root(game, depth, my_color)
                if move is not None:
                    best_move = move
                    best_score = score
                    self._best_move_at_depth[depth] = move
            except TimeoutError:
                break

        return best_move

    def _search_root(
        self,
        game: JieqiGame,
        depth: int,
        color: Color,
    ) -> tuple[JieqiMove | None, float]:
        """根节点搜索 with Aspiration Windows"""
        legal_moves = game.get_legal_moves()
        position_hash = game.board.get_position_hash()

        tt_entry = self._tt.get(position_hash)

        # 使用上一次迭代的最佳走法优先
        prev_best = self._best_move_at_depth.get(depth - 1)
        sorted_moves = self._order_moves(game, legal_moves, color, 0, tt_entry, prev_best)

        best_score = float("-inf")
        best_move = None
        alpha = float("-inf")
        beta = float("inf")

        for i, move in enumerate(sorted_moves):
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

            piece = game.board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = game.board.make_move(move)
            self._fast_gen.invalidate_cache()

            if captured and captured.actual_type == PieceType.KING:
                game.board.undo_move(move, captured, was_hidden)
                return move, 100000

            # Principal Variation Search (PVS)
            if i == 0:
                score = -self._alpha_beta(game, depth - 1, -beta, -alpha, color.opposite, 1, True)
            else:
                # 先用窄窗口搜索
                score = -self._alpha_beta(
                    game, depth - 1, -alpha - 1, -alpha, color.opposite, 1, False
                )
                # 如果失败，重新搜索
                if alpha < score < beta:
                    score = -self._alpha_beta(
                        game, depth - 1, -beta, -score, color.opposite, 1, True
                    )

            game.board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_move = move
                alpha = max(alpha, score)

        self._tt.store(position_hash, depth, best_score, TTFlag.EXACT, best_move)
        return best_move, best_score

    def _alpha_beta(
        self,
        game: JieqiGame,
        depth: int,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
        is_pv: bool,
    ) -> float:
        """Alpha-Beta with LMR and PVS"""
        self._nodes_evaluated += 1
        if self._nodes_evaluated % 2000 == 0:
            if time.time() - self._start_time > self.time_limit:
                raise TimeoutError()

        alpha_orig = alpha
        position_hash = game.board.get_position_hash()

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
        if game.board.find_king(color) is None:
            return -100000 + ply
        if game.board.find_king(color.opposite) is None:
            return 100000 - ply

        # 叶子节点
        if depth <= 0:
            return self._quiesce(game, alpha, beta, color, ply)

        # 获取走法
        legal_moves = self._get_moves_fast(game, color)
        if not legal_moves:
            if self._fast_gen.is_in_check_fast(color):
                return -100000 + ply
            return 0

        # 排序走法
        sorted_moves = self._order_moves(game, legal_moves, color, ply, tt_entry)

        best_score = float("-inf")
        best_move = None
        in_check = self._fast_gen.is_in_check_fast(color)

        for i, move in enumerate(sorted_moves):
            piece = game.board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = game.board.make_move(move)
            self._fast_gen.invalidate_cache()

            if captured and captured.actual_type == PieceType.KING:
                game.board.undo_move(move, captured, was_hidden)
                return 100000 - ply

            # Late Move Reduction (LMR)
            new_depth = depth - 1
            if (
                i >= self.LMR_FULL_DEPTH_MOVES
                and depth >= self.LMR_REDUCTION_LIMIT
                and captured is None  # 非吃子
                and not in_check  # 非被将状态
                and not was_hidden  # 非揭子
            ):
                # 减少搜索深度
                reduction = 1 if i < 10 else 2
                new_depth = max(1, depth - 1 - reduction)

            # 搜索
            if i == 0 or not is_pv:
                score = -self._alpha_beta(
                    game, new_depth, -beta, -alpha, color.opposite, ply + 1, is_pv
                )
            else:
                # PVS: 先窄窗口
                score = -self._alpha_beta(
                    game, new_depth, -alpha - 1, -alpha, color.opposite, ply + 1, False
                )
                if alpha < score < beta:
                    score = -self._alpha_beta(
                        game, depth - 1, -beta, -score, color.opposite, ply + 1, True
                    )

            game.board.undo_move(move, captured, was_hidden)
            self._fast_gen.invalidate_cache()

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
        game: JieqiGame,
        alpha: float,
        beta: float,
        color: Color,
        ply: int,
    ) -> float:
        """静态搜索"""
        stand_pat = self._evaluate(game, color)

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        # 只搜索吃子走法
        captures = self._get_captures(game, color)

        # 按 MVV-LVA 排序
        captures.sort(key=lambda m: self._mvv_lva_score(game, m), reverse=True)

        for move in captures:
            piece = game.board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = game.board.make_move(move)
            self._fast_gen.invalidate_cache()

            if captured and captured.actual_type == PieceType.KING:
                game.board.undo_move(move, captured, was_hidden)
                return 100000 - ply

            score = -self._quiesce(game, -beta, -alpha, color.opposite, ply + 1)

            game.board.undo_move(move, captured, was_hidden)
            self._fast_gen.invalidate_cache()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def _mvv_lva_score(self, game: JieqiGame, move: JieqiMove) -> int:
        """MVV-LVA 分数"""
        target = game.board.get_piece(move.to_pos)
        piece = game.board.get_piece(move.from_pos)

        if target is None:
            return 0

        victim = get_piece_base_value(target)
        attacker = get_piece_base_value(piece) if piece else 0

        return victim * 10 - attacker

    def _get_captures(self, game: JieqiGame, color: Color) -> list[JieqiMove]:
        """只获取吃子走法"""
        captures = []
        for piece in game.board.get_all_pieces(color):
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden

            for to_pos in piece.get_potential_moves(game.board):
                target = game.board.get_piece(to_pos)
                if target is None or target.color == color:
                    continue

                move = JieqiMove(action_type, piece.position, to_pos)
                captured = game.board.make_move(move)
                self._fast_gen.invalidate_cache()
                in_check = self._fast_gen.is_in_check_fast(color)
                game.board.undo_move(move, captured, was_hidden)
                if not in_check:
                    captures.append(move)

        return captures

    def _get_moves_fast(self, game: JieqiGame, color: Color) -> list[JieqiMove]:
        """快速获取走法"""
        moves = []
        for piece in game.board.get_all_pieces(color):
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden

            for to_pos in piece.get_potential_moves(game.board):
                move = JieqiMove(action_type, piece.position, to_pos)
                captured = game.board.make_move(move)
                self._fast_gen.invalidate_cache()
                in_check = self._fast_gen.is_in_check_fast(color)
                game.board.undo_move(move, captured, was_hidden)
                if not in_check:
                    moves.append(move)

        return moves

    def _order_moves(
        self,
        game: JieqiGame,
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

            # 之前迭代的最佳走法
            if prev_best and move == prev_best:
                score += 20000000

            # TT 最佳走法
            if tt_best and move == tt_best:
                score += 10000000

            target = game.board.get_piece(move.to_pos)

            # MVV-LVA
            if target is not None and target.color != color:
                score += 1000000 + self._mvv_lva_score(game, move)

            # Killer moves
            if ply < len(self._killers):
                if move in self._killers[ply]:
                    score += 500000

            # 历史启发式
            history_key = (move.from_pos, move.to_pos)
            score += self._history.get(history_key, 0)

            # 揭子有价值
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 200

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

    def _evaluate(self, game: JieqiGame, color: Color) -> float:
        """评估当前局面"""
        score = 0.0

        my_pieces = game.board.get_all_pieces(color)
        enemy_pieces = game.board.get_all_pieces(color.opposite)

        # 1. 子力价值 + 位置价值
        for piece in my_pieces:
            score += get_piece_base_value(piece)
            score += get_pst_value(piece)

        for piece in enemy_pieces:
            score -= get_piece_base_value(piece)
            score -= get_pst_value(piece)

        # 2. 将军加分
        if self._fast_gen.is_in_check_fast(color.opposite):
            score += 500
        if self._fast_gen.is_in_check_fast(color):
            score -= 500

        # 3. 棋子数量优势
        my_revealed = len([p for p in my_pieces if p.is_revealed])
        enemy_revealed = len([p for p in enemy_pieces if p.is_revealed])

        # 揭棋特有：早期不要急于揭子
        my_hidden = len([p for p in my_pieces if p.is_hidden])
        enemy_hidden = len([p for p in enemy_pieces if p.is_hidden])
        total_pieces = len(my_pieces) + len(enemy_pieces)

        if total_pieces > 24:
            # 开局阶段，保持神秘感
            score += (my_hidden - enemy_hidden) * 50
        else:
            # 中后期，明子更有价值
            score += (my_revealed - enemy_revealed) * 30

        # 4. 车的活跃度（简化版）
        for piece in my_pieces:
            if piece.is_revealed and piece.actual_type == PieceType.ROOK:
                # 车在开放线上加分
                if piece.position.col == 4:  # 中路
                    score += 50

        return score
