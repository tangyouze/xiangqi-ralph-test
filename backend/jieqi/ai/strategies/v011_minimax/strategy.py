"""
v011_minimax - Minimax with Alpha-Beta Pruning AI

ID: v011
名称: Minimax AI
描述: 使用 Minimax 算法和 Alpha-Beta 剪枝进行搜索

改进方向：真正的搜索算法
- Minimax 搜索到可配置的深度（默认深度2）
- Alpha-Beta 剪枝减少搜索节点
- 移动排序优化剪枝效率
- 改进的评估函数

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.simulation import SimulationBoard, SimPiece
from jieqi.types import ActionType, Color, GameResult, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    from jieqi.view import PlayerView


AI_ID = "v011"
AI_NAME = "minimax"


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

# 隐藏棋子的估计价值（因为不知道真实身份）
HIDDEN_PIECE_VALUE = 350


def get_piece_value(piece: SimPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden or piece.actual_type is None:
        return HIDDEN_PIECE_VALUE
    return PIECE_VALUES.get(piece.actual_type, 0)


# 位置价值表：鼓励棋子占据中心和活跃位置
# 索引为 row * 9 + col
POSITION_BONUS = {
    PieceType.ROOK: [
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
        5,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        5,
        10,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        10,
        10,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        10,
        5,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        5,
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
    ],
    PieceType.HORSE: [
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
        5,
        10,
        10,
        10,
        10,
        10,
        5,
        0,
        0,
        10,
        15,
        15,
        15,
        15,
        15,
        10,
        0,
        5,
        15,
        20,
        25,
        25,
        25,
        20,
        15,
        5,
        10,
        20,
        25,
        30,
        30,
        30,
        25,
        20,
        10,
        10,
        20,
        25,
        30,
        30,
        30,
        25,
        20,
        10,
        5,
        15,
        20,
        25,
        25,
        25,
        20,
        15,
        5,
        0,
        10,
        15,
        15,
        15,
        15,
        15,
        10,
        0,
        0,
        5,
        10,
        10,
        10,
        10,
        10,
        5,
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
    ],
    PieceType.CANNON: [
        0,
        5,
        10,
        10,
        15,
        10,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        5,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        5,
        10,
        15,
        20,
        25,
        30,
        25,
        20,
        15,
        10,
        10,
        15,
        20,
        25,
        30,
        25,
        20,
        15,
        10,
        5,
        10,
        15,
        20,
        25,
        20,
        15,
        10,
        5,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        15,
        20,
        15,
        10,
        5,
        0,
        0,
        5,
        10,
        10,
        15,
        10,
        10,
        5,
        0,
    ],
}


def get_position_bonus(piece: SimPiece) -> int:
    """获取位置加成"""
    if piece.is_hidden or piece.actual_type is None:
        return 0

    pos_index = piece.position.row * 9 + piece.position.col
    if piece.actual_type in POSITION_BONUS:
        bonus_table = POSITION_BONUS[piece.actual_type]
        if pos_index < len(bonus_table):
            return bonus_table[pos_index]
    return 0


@AIEngine.register(AI_NAME)
class MinimaxAI(AIStrategy):
    """Minimax with Alpha-Beta Pruning AI

    使用 Minimax 搜索算法，通过向前看多步来选择最佳走法。
    Alpha-Beta 剪枝显著减少需要评估的节点数量。
    """

    name = AI_NAME
    ai_id = AI_ID
    description = "Minimax 搜索策略 (v011)"

    def __init__(self, config: AIConfig | None = None):
        super().__init__(config)
        # 默认深度2（比较快）
        if self.config.depth == 3:  # AIConfig 默认值是 3
            self.config.depth = 2
        self._rng = random.Random(self.config.seed)
        self._nodes_evaluated = 0

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

        # 对走法排序以提高剪枝效率
        sorted_moves = self._order_moves(sim_board, view.legal_moves, my_color)

        best_score = float("-inf")
        best_moves: list[JieqiMove] = []

        alpha = float("-inf")
        beta = float("inf")

        for move in sorted_moves:
            # 执行走法
            piece = sim_board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = sim_board.make_move(move)

            # 吃将直接返回
            if captured and captured.actual_type == PieceType.KING:
                sim_board.undo_move(move, captured, was_hidden)
                return move

            # 递归搜索
            score = -self._minimax(sim_board, depth - 1, -beta, -alpha, my_color.opposite)

            sim_board.undo_move(move, captured, was_hidden)

            if score > best_score:
                best_score = score
                best_moves = [move]
                alpha = max(alpha, score)
            elif score == best_score:
                best_moves.append(move)

        # 从最佳走法中随机选择一个（添加少量随机性）
        return self._rng.choice(best_moves)

    def _minimax(
        self,
        board: SimulationBoard,
        depth: int,
        alpha: float,
        beta: float,
        color: Color,
    ) -> float:
        """Minimax with Alpha-Beta Pruning

        使用 negamax 变体简化代码。
        返回当前玩家视角的分数。
        """
        self._nodes_evaluated += 1

        # 检查是否无将（被吃掉）
        if board.find_king(color) is None:
            return -50000
        if board.find_king(color.opposite) is None:
            return 50000

        # 达到搜索深度，返回静态评估
        if depth <= 0:
            return self._evaluate_position(board, color)

        # 获取走法
        legal_moves = board.get_legal_moves(color)
        if not legal_moves:
            # 无合法走法
            if board.is_in_check(color):
                return -40000  # 被将死
            return 0  # 逼和

        # 对走法排序（只在根节点附近）
        if depth >= 2:
            sorted_moves = self._order_moves(board, legal_moves, color)
        else:
            sorted_moves = legal_moves

        best_score = float("-inf")

        for move in sorted_moves:
            piece = board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = board.make_move(move)

            # 吃将直接返回高分
            if captured and captured.actual_type == PieceType.KING:
                board.undo_move(move, captured, was_hidden)
                return 50000

            score = -self._minimax(board, depth - 1, -beta, -alpha, color.opposite)

            board.undo_move(move, captured, was_hidden)

            best_score = max(best_score, score)
            alpha = max(alpha, score)

            # Alpha-Beta 剪枝
            if alpha >= beta:
                break

        return best_score

    def _order_moves(
        self,
        board: SimulationBoard,
        moves: list[JieqiMove],
        color: Color,
    ) -> list[JieqiMove]:
        """对走法排序以提高 Alpha-Beta 剪枝效率

        优先级：
        1. 吃子走法（按价值排序）
        2. 将军走法
        3. 其他走法
        """
        scored_moves: list[tuple[float, JieqiMove]] = []

        for move in moves:
            score = 0.0
            target = board.get_piece(move.to_pos)

            # 吃子得分
            if target is not None and target.color != color:
                capture_value = get_piece_value(target)
                if target.actual_type == PieceType.KING:
                    score += 100000  # 吃将最高优先级
                else:
                    score += capture_value * 10  # 优先考虑吃子

            # 揭子有一定价值
            if move.action_type == ActionType.REVEAL_AND_MOVE:
                score += 5

            scored_moves.append((score, move))

        # 按分数降序排序
        scored_moves.sort(key=lambda x: -x[0])

        return [m for _, m in scored_moves]

    def _evaluate_position(self, board: SimulationBoard, color: Color) -> float:
        """评估当前局面

        从指定颜色的视角评估。
        """
        score = 0.0

        # 子力价值（最重要的因素）
        for piece in board.get_all_pieces():
            value = get_piece_value(piece)
            pos_bonus = get_position_bonus(piece)
            total = value + pos_bonus

            if piece.color == color:
                score += total
            else:
                score -= total

        # 将军威胁
        if board.is_in_check(color.opposite):
            score += 50
        if board.is_in_check(color):
            score -= 50

        # 控制中心区域的加分
        center_control = self._evaluate_center_control(board, color)
        score += center_control

        # 暗子数量评估
        my_hidden = len([p for p in board.get_all_pieces(color) if p.is_hidden])
        enemy_hidden = len([p for p in board.get_all_pieces(color.opposite) if p.is_hidden])

        # 游戏早期，己方暗子多是优势（保留选择权）
        total_pieces = len(board.get_all_pieces())
        if total_pieces > 24:
            score += (my_hidden - enemy_hidden) * 5
        else:
            score -= (my_hidden - enemy_hidden) * 3

        return score

    def _evaluate_center_control(self, board: SimulationBoard, color: Color) -> float:
        """评估中心控制"""
        score = 0.0

        # 定义中心区域
        center_positions = [
            Position(4, 3),
            Position(4, 4),
            Position(4, 5),
            Position(5, 3),
            Position(5, 4),
            Position(5, 5),
        ]

        for pos in center_positions:
            piece = board.get_piece(pos)
            if piece is not None:
                if piece.color == color:
                    score += 10
                else:
                    score -= 10

        return score
