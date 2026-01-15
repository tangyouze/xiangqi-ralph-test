"""
揭棋 AI 评估器

参考 miaosisrai 的设计思路，提供统一的评分系统:
- 分数范围: -1000 到 1000
- 正分表示当前玩家优势，负分表示劣势
- 可以转换为胜率 (win rate)

核心思路:
1. Position Score Table (PST): 每个棋子在每个位置的价值
2. 暗子期望价值: 根据剩余可能棋子计算期望值
3. 揭棋特有战术评估: 空头炮、沉底炮、肋道车等
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jieqi.types import Color, PieceType, Position

if TYPE_CHECKING:
    from jieqi.simulation import SimPiece, SimulationBoard


# ============================================================================
# 棋子基础价值 (参考 miaosisrai 的设定)
# ============================================================================
# 这些值经过调整，使得最终评分在合理范围内

PIECE_BASE_VALUES = {
    PieceType.KING: 2500,  # 将/帅 - 无价
    PieceType.ROOK: 233,  # 车 - 最强
    PieceType.CANNON: 101,  # 炮
    PieceType.HORSE: 108,  # 马
    PieceType.ELEPHANT: 23,  # 象
    PieceType.ADVISOR: 23,  # 士
    PieceType.PAWN: 44,  # 兵/卒
}

# 兵过河后价值提升
PAWN_CROSSED_RIVER_BONUS = 30

# 暗子折扣因子 (参考 miaosisrai: discount_factor = 1.6)
# 暗子期望价值 = 加权平均价值 / HIDDEN_DISCOUNT_FACTOR
HIDDEN_DISCOUNT_FACTOR = 1.6

# 特殊位置加分 (参考 miaosisrai 的 Key "0" 表)
# 底线 A/I 列 (1路、9路) 威胁对方暗子
BOTTOM_THREAT_BONUS = 100
# 翻动暗兵加分
REVEAL_PAWN_BONUS = 30
# 本方底线 A/I 列防守压力
BOTTOM_DEFENSE_PENALTY = -80


# ============================================================================
# 位置价值表 (PST - Position Score Tables)
# 参考 miaosisrai 的 common.py，适配我们的 10x9 棋盘
# ============================================================================

# 兵/卒位置表 (红方视角，row 0-9，col 0-8)
PST_PAWN = [
    # row 0 (红方底线)
    [2, 2, 3, -9, -12, -9, 3, 2, 2],
    [4, 4, 5, -6, -10, -6, 5, 4, 4],
    [5, 5, 6, 4, 5, 4, 6, 5, 5],
    [13, 13, 14, 14, 15, 14, 14, 13, 13],
    [24, 35, 20, 27, 29, 27, 20, 35, 24],  # row 4
    # row 5 (过河线)
    [34, 55, 37, 37, 39, 37, 37, 55, 34],
    [47, 57, 47, 49, 60, 49, 47, 57, 47],
    [60, 74, 74, 79, 97, 79, 74, 74, 60],
    [75, 84, 89, 101, 113, 101, 89, 84, 75],
    [75, 84, 85, 87, 87, 87, 85, 84, 75],  # row 9 (黑方底线)
]

# 相/象位置表
PST_ELEPHANT = [
    [35, 16, 40, 16, 20, 16, 40, 16, 35],  # row 0
    [55, 27, 6, 27, 30, 27, 6, 27, 55],
    [35, 30, 49, 30, 43, 30, 49, 30, 35],
    [10, 35, 65, 35, 10, 35, 65, 35, 10],
    [60, 30, 31, 30, 65, 30, 31, 30, 60],  # row 4
    [65, 35, 12, 35, 70, 35, 12, 35, 65],
    [27, 31, 70, 30, 25, 30, 70, 31, 27],
    [12, 41, 75, 41, 6, 41, 75, 41, 12],
    [65, 55, 15, 20, 68, 20, 15, 55, 65],
    [70, 39, 12, 35, 72, 35, 12, 39, 70],  # row 9
]

# 士/仕位置表
PST_ADVISOR = [
    [65, 92, 57, 104, 55, 104, 57, 92, 65],  # row 0
    [65, 57, 95, 69, 105, 69, 95, 57, 65],
    [69, 90, 65, 100, 61, 100, 65, 90, 69],
    [82, 69, 89, 69, 93, 69, 89, 69, 82],
    [73, 85, 75, 85, 75, 85, 75, 85, 73],  # row 4
    [81, 82, 85, 82, 85, 82, 85, 82, 81],
    [83, 85, 88, 86, 88, 86, 88, 85, 83],
    [85, 109, 88, 91, 88, 91, 88, 109, 85],
    [88, 88, 99, 109, 106, 109, 99, 88, 88],
    [88, 103, 92, 115, 100, 115, 92, 103, 88],  # row 9
]

# 马位置表
PST_HORSE = [
    [85, 85, 90, 105, 95, 105, 90, 85, 85],  # row 0
    [99, 105, 99, 99, 99, 99, 99, 105, 99],
    [113, 113, 114, 115, 125, 115, 114, 113, 113],
    [112, 114, 118, 115, 118, 115, 118, 114, 112],
    [110, 118, 121, 122, 122, 122, 121, 118, 110],  # row 4
    [110, 120, 133, 133, 140, 133, 133, 120, 110],
    [113, 138, 122, 135, 120, 135, 122, 138, 113],
    [117, 113, 114, 153, 129, 153, 114, 113, 117],
    [120, 126, 153, 117, 124, 117, 153, 126, 120],
    [138, 120, 120, 126, 120, 126, 120, 120, 138],  # row 9
]

# 车位置表
PST_ROOK = [
    [274, 276, 274, 282, 250, 282, 274, 276, 274],  # row 0
    [270, 278, 276, 289, 260, 289, 276, 278, 270],
    [268, 274, 274, 289, 272, 289, 274, 274, 268],
    [274, 274, 274, 287, 284, 287, 274, 274, 274],
    [278, 272, 282, 287, 285, 287, 282, 272, 278],  # row 4
    [278, 281, 281, 287, 285, 287, 281, 281, 278],
    [280, 282, 282, 289, 286, 289, 282, 282, 280],
    [280, 282, 282, 289, 296, 289, 282, 282, 280],
    [280, 282, 282, 289, 303, 289, 282, 282, 280],
    [316, 318, 318, 326, 324, 326, 318, 318, 316],  # row 9 (底线车更强)
]

# 炮位置表
PST_CANNON = [
    [126, 126, 127, 129, 129, 129, 127, 126, 126],  # row 0
    [126, 127, 128, 128, 135, 128, 128, 127, 126],
    [127, 126, 100, 129, 140, 129, 100, 126, 127],
    [126, 126, 126, 126, 140, 126, 126, 126, 126],
    [125, 126, 129, 126, 130, 126, 129, 126, 125],  # row 4
    [126, 126, 126, 126, 130, 126, 126, 126, 126],
    [126, 129, 129, 128, 130, 128, 129, 129, 126],
    [127, 127, 126, 121, 122, 121, 126, 127, 127],
    [128, 138, 126, 122, 129, 122, 126, 138, 128],
    [195, 195, 192, 182, 170, 182, 192, 195, 195],  # row 9 (沉底炮价值)
]

# 将/帅位置表 (九宫内)
PST_KING = [
    [2460, 2500, 2460, 0, 0, 0, 0, 0, 0],  # row 0 (红方底线)
    [2420, 2460, 2420, 0, 0, 0, 0, 0, 0],
    [2380, 2420, 2380, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 2380, 2420, 2380],  # row 7 (黑方九宫开始)
    [0, 0, 0, 0, 0, 0, 2420, 2460, 2420],
    [0, 0, 0, 0, 0, 0, 2460, 2500, 2460],  # row 9 (黑方底线)
]

# PST 映射
PST_TABLES = {
    PieceType.PAWN: PST_PAWN,
    PieceType.ELEPHANT: PST_ELEPHANT,
    PieceType.ADVISOR: PST_ADVISOR,
    PieceType.HORSE: PST_HORSE,
    PieceType.ROOK: PST_ROOK,
    PieceType.CANNON: PST_CANNON,
    PieceType.KING: PST_KING,
}


# ============================================================================
# 暗子期望价值计算
# ============================================================================


@dataclass
class HiddenPieceDistribution:
    """暗子分布统计

    跟踪每种棋子还剩余多少可能是暗子的数量
    """

    # 每种棋子类型剩余可能数量
    remaining: dict[PieceType, int] = field(
        default_factory=lambda: {
            PieceType.ROOK: 2,
            PieceType.HORSE: 2,
            PieceType.ELEPHANT: 2,
            PieceType.ADVISOR: 2,
            PieceType.CANNON: 2,
            PieceType.PAWN: 5,
        }
    )

    def total_remaining(self) -> int:
        """剩余暗子总数"""
        return sum(self.remaining.values())

    def get_expected_value(self, position: Position, color: Color) -> float:
        """计算某位置暗子的期望价值

        基于剩余可能棋子的加权平均值，并应用折扣因子
        参考 miaosisrai: 使用 discount_factor = 1.6 降低暗子估值的确定性
        """
        total = self.total_remaining()
        if total == 0:
            return 0.0

        expected = 0.0
        for piece_type, count in self.remaining.items():
            if count > 0:
                prob = count / total
                # 位置价值
                pst = PST_TABLES.get(piece_type)
                if pst:
                    row, col = position.row, position.col
                    # 黑方需要翻转视角
                    if color == Color.BLACK:
                        row = 9 - row
                    if 0 <= row < 10 and 0 <= col < 9:
                        value = pst[row][col]
                    else:
                        value = PIECE_BASE_VALUES.get(piece_type, 0)
                else:
                    value = PIECE_BASE_VALUES.get(piece_type, 0)

                expected += prob * value

        # 应用折扣因子：暗子的不确定性降低其估值可信度
        return expected / HIDDEN_DISCOUNT_FACTOR

    def get_average_value(self) -> float:
        """获取暗子的平均价值（不考虑位置）"""
        total = self.total_remaining()
        if total == 0:
            return 0.0

        weighted_sum = 0.0
        for piece_type, count in self.remaining.items():
            if count > 0:
                weighted_sum += count * PIECE_BASE_VALUES.get(piece_type, 0)

        return weighted_sum / total


# ============================================================================
# 评估器主类
# ============================================================================


class JieqiEvaluator:
    """揭棋评估器

    提供统一的评分系统，分数范围 -1000 到 1000
    """

    # 用于分数归一化的缩放因子
    # 按照 miaosisrai 的设计，满子力约 2000+ 分，设置缩放因子使其映射到合理范围
    SCORE_SCALE = 500.0

    # 杀棋分数
    MATE_SCORE = 10000

    def __init__(self) -> None:
        self._red_hidden = HiddenPieceDistribution()
        self._black_hidden = HiddenPieceDistribution()

    def reset_distribution(self) -> None:
        """重置暗子分布"""
        self._red_hidden = HiddenPieceDistribution()
        self._black_hidden = HiddenPieceDistribution()

    def get_piece_value(self, piece: SimPiece) -> float:
        """获取棋子价值（包含位置评估）"""
        if piece.is_hidden:
            # 暗子使用期望价值
            dist = self._red_hidden if piece.color == Color.RED else self._black_hidden
            return dist.get_expected_value(piece.position, piece.color)

        if piece.actual_type is None:
            # 未知类型（不应该发生）
            return 100.0

        # 使用 PST 获取位置价值
        pst = PST_TABLES.get(piece.actual_type)
        if pst:
            row, col = piece.position.row, piece.position.col
            # 黑方需要翻转视角
            if piece.color == Color.BLACK:
                row = 9 - row
            if 0 <= row < 10 and 0 <= col < 9:
                return float(pst[row][col])

        # 无 PST 时使用基础价值
        return float(PIECE_BASE_VALUES.get(piece.actual_type, 0))

    def evaluate(self, board: SimulationBoard, color: Color) -> float:
        """评估局面

        返回当前玩家视角的评分（正分优势，负分劣势）
        """
        score = 0.0

        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        # 检查是否有将/帅
        my_king = board.find_king(color)
        enemy_king = board.find_king(color.opposite)

        if my_king is None:
            return -self.MATE_SCORE
        if enemy_king is None:
            return self.MATE_SCORE

        # 1. 子力价值
        for piece in my_pieces:
            score += self.get_piece_value(piece)

        for piece in enemy_pieces:
            score -= self.get_piece_value(piece)

        # 2. 将军评估
        if board.is_in_check(color.opposite):
            score += 50  # 将军对方
        if board.is_in_check(color):
            score -= 50  # 被将军

        # 3. 揭棋特有评估
        score += self._evaluate_jieqi_tactics(board, color)

        # 4. 机动性评估（轻量级近似）
        my_mobility = self._estimate_mobility(board, color)
        enemy_mobility = self._estimate_mobility(board, color.opposite)
        score += (my_mobility - enemy_mobility) * 2

        return score

    def _evaluate_jieqi_tactics(self, board: SimulationBoard, color: Color) -> float:
        """评估揭棋特有战术

        参考 miaosisrai 的战术评估:
        1. 暗子数量与神秘感
        2. 空头炮
        3. 沉底炮
        4. 肋道车争夺
        5. 底线威胁
        """
        score = 0.0

        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        # 统计暗子数量
        my_hidden = sum(1 for p in my_pieces if p.is_hidden)
        enemy_hidden = sum(1 for p in enemy_pieces if p.is_hidden)

        # 开局阶段暗子多是优势（保持神秘感）
        total_pieces = len(my_pieces) + len(enemy_pieces)
        if total_pieces > 24:
            score += (my_hidden - enemy_hidden) * 5

        # 检查空头炮（炮瞄准对方将/帅，中间没有棋子）
        score += self._evaluate_kongtoupao(board, color)

        # 评估车的位置和活跃度
        score += self._evaluate_rook_position(board, color)

        # 评估沉底炮（炮进入对方底线）
        score += self._evaluate_sinking_cannon(board, color)

        # 评估底线威胁（占据对方底线 A/I 列）
        score += self._evaluate_bottom_threat(board, color)

        return score

    def _evaluate_rook_position(self, board: SimulationBoard, color: Color) -> float:
        """评估车的位置

        参考 miaosisrai: 车占据中路和肋道的价值
        """
        score = 0.0
        my_pieces = board.get_all_pieces(color)

        for piece in my_pieces:
            if not piece.is_hidden and piece.actual_type == PieceType.ROOK:
                col = piece.position.col
                row = piece.position.row

                # 车占据中路 (第5列，col=4)
                if col == 4:
                    score += 30

                # 车占据肋道（第4列或第6列，col=3 或 col=5）
                if col in [3, 5]:
                    score += 20

                # 底线车威胁：红方车在 row>=7，黑方车在 row<=2
                enemy_bottom_row = 9 if color == Color.RED else 0
                if row == enemy_bottom_row:
                    # 底线车可以横扫对方暗子
                    enemy_hidden = sum(
                        1
                        for p in board.get_all_pieces(color.opposite)
                        if p.is_hidden and p.position.row == enemy_bottom_row
                    )
                    score += 40 + enemy_hidden * 15

        return score

    def _evaluate_sinking_cannon(self, board: SimulationBoard, color: Color) -> float:
        """评估沉底炮

        参考 miaosisrai: 沉底炮（炮进入对方底线）的评估
        - 如果对方底线没有暗子，沉底炮价值降低
        - 如果有暗子可以牵制，价值提高
        """
        score = 0.0
        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        enemy_bottom_row = 9 if color == Color.RED else 0

        # 统计对方底线暗子
        enemy_bottom_hidden = sum(
            1 for p in enemy_pieces if p.is_hidden and p.position.row == enemy_bottom_row
        )

        for piece in my_pieces:
            if not piece.is_hidden and piece.actual_type == PieceType.CANNON:
                if piece.position.row == enemy_bottom_row:
                    # 沉底炮
                    if enemy_bottom_hidden > 0:
                        # 有暗子可牵制，价值提高
                        score += 25 + enemy_bottom_hidden * 10
                    else:
                        # 无暗子，价值降低（可能陷入被动）
                        score -= 30

        return score

    def _evaluate_bottom_threat(self, board: SimulationBoard, color: Color) -> float:
        """评估底线威胁

        参考 miaosisrai Key "0" 表:
        - 占据对方底线 A/I 列（1路、9路）威胁暗子: +100
        - 本方底线 A/I 列被占据有防守压力: -80
        """
        score = 0.0
        my_pieces = board.get_all_pieces(color)
        enemy_pieces = board.get_all_pieces(color.opposite)

        enemy_bottom_row = 9 if color == Color.RED else 0
        my_bottom_row = 0 if color == Color.RED else 9

        # 我方棋子占据对方底线 A/I 列
        for piece in my_pieces:
            if not piece.is_hidden:
                if piece.position.row == enemy_bottom_row and piece.position.col in [0, 8]:
                    score += 50  # 对方底线边路威胁

        # 对方棋子占据我方底线 A/I 列
        for piece in enemy_pieces:
            if not piece.is_hidden:
                if piece.position.row == my_bottom_row and piece.position.col in [0, 8]:
                    score -= 40  # 本方底线边路受威胁

        return score

    def _evaluate_kongtoupao(self, board: SimulationBoard, color: Color) -> float:
        """评估空头炮

        空头炮：炮瞄准对方将/帅，中间只有炮自己
        """
        score = 0.0

        my_pieces = board.get_all_pieces(color)
        enemy_king = board.find_king(color.opposite)

        if enemy_king is None:
            return 0.0

        for piece in my_pieces:
            if not piece.is_hidden and piece.actual_type == PieceType.CANNON:
                # 检查是否在同一列
                if piece.position.col == enemy_king.col:
                    # 检查中间是否只有己方棋子或没有棋子
                    is_kongtou = True
                    piece_count = 0
                    start_row = min(piece.position.row, enemy_king.row) + 1
                    end_row = max(piece.position.row, enemy_king.row)

                    for row in range(start_row, end_row):
                        target = board.get_piece(Position(row, piece.position.col))
                        if target is not None:
                            piece_count += 1
                            if target.color != color:
                                is_kongtou = False
                                break

                    if is_kongtou and piece_count == 0:
                        score += 70  # 空头炮价值
                        # 如果己方有车配合，价值更高
                        my_rooks = [
                            p
                            for p in my_pieces
                            if not p.is_hidden and p.actual_type == PieceType.ROOK
                        ]
                        if my_rooks:
                            score += 30

        return score

    def _estimate_mobility(self, board: SimulationBoard, color: Color) -> int:
        """估算机动性（轻量级近似）

        用棋子类型加权来近似走法数量，避免昂贵的 get_legal_moves 调用。
        每种棋子的"机动性潜力"不同：车最高，士/象最低。
        """
        # 每种棋子的机动性权重（近似平均走法数）
        MOBILITY_WEIGHTS = {
            PieceType.ROOK: 12,  # 车：横竖可走很远
            PieceType.CANNON: 10,  # 炮：类似车但需要炮架
            PieceType.HORSE: 6,  # 马：最多8个方向
            PieceType.PAWN: 2,  # 兵：1-3个方向
            PieceType.ELEPHANT: 2,  # 象：最多4个田字位
            PieceType.ADVISOR: 2,  # 士：最多4个斜向位
            PieceType.KING: 2,  # 将：九宫内移动
        }

        mobility = 0
        for piece in board.get_all_pieces(color):
            if piece.is_hidden:
                # 暗子用平均权重
                mobility += 5
            elif piece.actual_type:
                mobility += MOBILITY_WEIGHTS.get(piece.actual_type, 3)

        return mobility

    def normalize_score(self, raw_score: float) -> float:
        """将原始分数归一化到 -1000 到 1000 范围

        使用 tanh 函数平滑压缩
        """
        # 杀棋分数直接映射到边界
        if raw_score >= self.MATE_SCORE:
            return 1000.0
        if raw_score <= -self.MATE_SCORE:
            return -1000.0

        # 使用 tanh 压缩
        return math.tanh(raw_score / self.SCORE_SCALE) * 1000.0

    def score_to_win_rate(self, normalized_score: float) -> float:
        """将归一化分数转换为胜率

        胜率范围: 0.0 到 1.0
        0.5 表示均势
        """
        # 使用 sigmoid 函数
        # normalized_score 在 -1000 到 1000 之间
        # 我们希望 ±500 大约对应 75%/25% 胜率
        return 1.0 / (1.0 + math.exp(-normalized_score / 200.0))

    def win_rate_to_score(self, win_rate: float) -> float:
        """将胜率转换回归一化分数

        胜率范围: 0.0 到 1.0
        返回: -1000 到 1000
        """
        if win_rate <= 0.0:
            return -1000.0
        if win_rate >= 1.0:
            return 1000.0

        # 逆 sigmoid
        return -200.0 * math.log(1.0 / win_rate - 1.0)

    def format_evaluation(self, board: SimulationBoard, color: Color) -> dict:
        """格式化评估结果

        返回包含多种表示的评估字典
        """
        raw_score = self.evaluate(board, color)
        normalized = self.normalize_score(raw_score)
        win_rate = self.score_to_win_rate(normalized)

        return {
            "raw_score": raw_score,
            "normalized_score": round(normalized, 1),
            "win_rate": round(win_rate * 100, 1),  # 百分比
            "evaluation": self._score_to_text(normalized),
        }

    def _score_to_text(self, normalized_score: float) -> str:
        """将分数转换为文字描述"""
        if normalized_score >= 800:
            return "决定性优势"
        elif normalized_score >= 500:
            return "明显优势"
        elif normalized_score >= 200:
            return "轻微优势"
        elif normalized_score >= -200:
            return "均势"
        elif normalized_score >= -500:
            return "轻微劣势"
        elif normalized_score >= -800:
            return "明显劣势"
        else:
            return "决定性劣势"


# 全局评估器实例
_evaluator: JieqiEvaluator | None = None


def get_evaluator() -> JieqiEvaluator:
    """获取全局评估器实例"""
    global _evaluator
    if _evaluator is None:
        _evaluator = JieqiEvaluator()
    return _evaluator
