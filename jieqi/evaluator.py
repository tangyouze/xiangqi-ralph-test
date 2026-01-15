"""
揭棋统一评估模块

提供标准化的局面评估函数，可被 API 和 AI 共同使用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jieqi.types import Color, PieceType

if TYPE_CHECKING:
    from jieqi.board import JieqiBoard
    from jieqi.game import JieqiGame
    from jieqi.piece import JieqiPiece


# 棋子基础价值（单位：厘兵 centipawn）
PIECE_VALUES = {
    PieceType.KING: 100000,
    PieceType.ROOK: 9000,
    PieceType.CANNON: 4500,
    PieceType.HORSE: 4000,
    PieceType.ELEPHANT: 2000,
    PieceType.ADVISOR: 2000,
    PieceType.PAWN: 1000,
}

# 兵过河后价值
PAWN_CROSSED_VALUE = 2000

# 隐藏棋子期望价值
HIDDEN_PIECE_VALUE = 3200


# 位置评估表 (10行 x 9列)
# 车的位置权重 - 鼓励占据中心和敌方阵地
ROOK_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 5, 10, 15, 20, 15, 10, 5, 5],
    [10, 15, 20, 30, 35, 30, 20, 15, 10],
    [15, 20, 30, 40, 45, 40, 30, 20, 15],
    [20, 25, 35, 45, 50, 45, 35, 25, 20],
    [25, 30, 40, 50, 55, 50, 40, 30, 25],
    [30, 35, 45, 55, 60, 55, 45, 35, 30],
    [35, 40, 50, 60, 70, 60, 50, 40, 35],
]

# 马的位置权重 - 中心控制
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

# 炮的位置权重 - 远程控制
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

# 兵的位置权重 - 鼓励过河和前进
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


def get_piece_value(piece: JieqiPiece) -> int:
    """获取棋子价值"""
    if piece.is_hidden:
        return HIDDEN_PIECE_VALUE

    value = PIECE_VALUES.get(piece.actual_type, 0)

    # 兵过河加分
    if piece.actual_type == PieceType.PAWN:
        if not piece.position.is_on_own_side(piece.color):
            value = PAWN_CROSSED_VALUE

    return value


def get_position_value(piece: JieqiPiece) -> int:
    """获取位置加成"""
    if piece.is_hidden:
        return 0

    pst = PST_TABLES.get(piece.actual_type)
    if pst is None:
        return 0

    row, col = piece.position.row, piece.position.col

    # 黑方需要翻转视角
    if piece.color == Color.BLACK:
        row = 9 - row

    if 0 <= row < 10 and 0 <= col < 9:
        return pst[row][col]
    return 0


class BoardEvaluator:
    """棋盘评估器"""

    def __init__(self, board: JieqiBoard):
        self.board = board
        self._fast_gen = None

    def _get_fast_gen(self):
        """懒加载 FastMoveGenerator"""
        if self._fast_gen is None:
            from jieqi.bitboard import FastMoveGenerator

            self._fast_gen = FastMoveGenerator(self.board)
        return self._fast_gen

    def evaluate(self, perspective: Color = Color.RED) -> dict:
        """评估局面

        Args:
            perspective: 评估视角（默认红方）

        Returns:
            评估结果字典，包含总分和各项细分
        """
        result = {
            "total": 0,
            "material": {"red": 0, "black": 0, "diff": 0},
            "position": {"red": 0, "black": 0, "diff": 0},
            "check": 0,
            "hidden": {"red": 0, "black": 0},
            "piece_count": {"red": 0, "black": 0},
        }

        # 子力价值
        for piece in self.board.get_all_pieces(Color.RED):
            result["material"]["red"] += get_piece_value(piece)
            result["position"]["red"] += get_position_value(piece)
            result["piece_count"]["red"] += 1
            if piece.is_hidden:
                result["hidden"]["red"] += 1

        for piece in self.board.get_all_pieces(Color.BLACK):
            result["material"]["black"] += get_piece_value(piece)
            result["position"]["black"] += get_position_value(piece)
            result["piece_count"]["black"] += 1
            if piece.is_hidden:
                result["hidden"]["black"] += 1

        # 计算差值
        result["material"]["diff"] = result["material"]["red"] - result["material"]["black"]
        result["position"]["diff"] = result["position"]["red"] - result["position"]["black"]

        # 将军评估
        fast_gen = self._get_fast_gen()
        if fast_gen.is_in_check_fast(Color.BLACK):
            result["check"] = 500  # 红方将黑方军
        elif fast_gen.is_in_check_fast(Color.RED):
            result["check"] = -500  # 黑方将红方军

        # 总分（红方视角）
        total = result["material"]["diff"] + result["position"]["diff"] + result["check"]

        # 如果视角是黑方，取反
        if perspective == Color.BLACK:
            total = -total

        result["total"] = total

        return result

    def get_score(self, perspective: Color = Color.RED) -> int:
        """获取简化的总分

        Args:
            perspective: 评估视角

        Returns:
            总分（厘兵单位）
        """
        return self.evaluate(perspective)["total"]

    def get_win_probability(self, perspective: Color = Color.RED) -> float:
        """估算胜率

        使用 sigmoid 函数将分数转换为胜率估计。

        Args:
            perspective: 评估视角

        Returns:
            胜率（0-1 之间）
        """
        import math

        score = self.get_score(perspective)
        # 将分数转换为胜率，假设 3000 分约等于 85% 胜率
        k = 0.0005  # 调整曲线斜率
        probability = 1 / (1 + math.exp(-k * score))
        return round(probability, 3)


def evaluate_game(game: JieqiGame, perspective: Color = Color.RED) -> dict:
    """评估游戏局面

    Args:
        game: 游戏实例
        perspective: 评估视角

    Returns:
        评估结果
    """
    evaluator = BoardEvaluator(game.board)
    result = evaluator.evaluate(perspective)
    result["win_probability"] = evaluator.get_win_probability(perspective)
    result["move_count"] = len(game.move_history)
    result["current_turn"] = game.current_turn.value
    return result


def evaluate_board(board: JieqiBoard, perspective: Color = Color.RED) -> dict:
    """评估棋盘

    Args:
        board: 棋盘实例
        perspective: 评估视角

    Returns:
        评估结果
    """
    evaluator = BoardEvaluator(board)
    result = evaluator.evaluate(perspective)
    result["win_probability"] = evaluator.get_win_probability(perspective)
    return result
