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

迭代记录：
- v1: 初始版本
- v2: 优化评估函数，增加安全性评估和机动性评估

注意：AI 使用 PlayerView，无法看到暗子的真实身份！
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from jieqi.ai.base import AIConfig, AIEngine, AIStrategy
from jieqi.fen import create_board_from_fen, get_legal_moves_from_fen, parse_fen, parse_move
from jieqi.simulation import SimPiece, SimulationBoard
from jieqi.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    pass


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
        # 深度2，搜索更快
        self.config.depth = 2
        self._rng = random.Random(self.config.seed)
        self._nodes_evaluated = 0

    def select_moves_fen(self, fen: str, n: int = 10) -> list[tuple[str, float]]:
        """选择得分最高的 n 个走法"""
        legal_moves = get_legal_moves_from_fen(fen)
        if not legal_moves:
            return []

        if len(legal_moves) == 1:
            return [(legal_moves[0], 0.0)]

        state = parse_fen(fen)
        my_color = state.turn
        depth = self.config.depth

        # 创建模拟棋盘
        sim_board = create_board_from_fen(fen)
        self._nodes_evaluated = 0

        # 解析走法
        parsed_moves = [(move_str, parse_move(move_str)[0]) for move_str in legal_moves]

        # 对走法排序以提高剪枝效率
        sorted_moves = self._order_moves(sim_board, [m for _, m in parsed_moves], my_color)

        # 建立映射
        move_to_str = {m: s for s, m in parsed_moves}

        scores: dict[str, float] = {}
        alpha = float("-inf")
        beta = float("inf")

        for move in sorted_moves:
            move_str = move_to_str.get(move)
            if move_str is None:
                continue

            piece = sim_board.get_piece(move.from_pos)
            if piece is None:
                continue
            was_hidden = piece.is_hidden
            captured = sim_board.make_move(move)

            # 吃将直接高分
            if captured and captured.actual_type == PieceType.KING:
                sim_board.undo_move(move, captured, was_hidden)
                scores[move_str] = 50000
                continue

            score = -self._minimax(sim_board, depth - 1, -beta, -alpha, my_color.opposite)
            sim_board.undo_move(move, captured, was_hidden)

            scores[move_str] = score
            alpha = max(alpha, score)

        # 按分数降序排列，取前 N 个
        sorted_results = sorted(scores.items(), key=lambda x: -x[1])

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

        从指定颜色的视角评估。简化版评估，让搜索更快。
        """
        score = 0.0

        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        # 1. 子力价值 + 位置加成（简化版，更快）
        for piece in my_pieces:
            value = get_piece_value(piece)
            pos_bonus = get_position_bonus(piece)
            score += value + pos_bonus

            # 简化位置评估
            if not piece.is_hidden:
                if not piece.position.is_on_own_side(color):
                    score += 15  # 过河加分
                if 3 <= piece.position.col <= 5:
                    score += 8  # 中心控制

        for piece in enemy_pieces:
            value = get_piece_value(piece)
            pos_bonus = get_position_bonus(piece)
            score -= value + pos_bonus

        # 2. 将军威胁
        if board.is_in_check(color.opposite):
            score += 60
        if board.is_in_check(color):
            score -= 60

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
