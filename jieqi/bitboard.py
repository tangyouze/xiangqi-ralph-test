"""
揭棋 Bitboard 优化模块

使用位图表示棋盘状态，加速走法生成和局面评估。

棋盘布局 (10行 x 9列 = 90位):
- 位置索引: index = row * 9 + col
- 使用 128 位整数 (Python int 自动支持大整数)

每个位置用 1 位表示是否有棋子。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jieqi.types import Color, PieceType, Position

if TYPE_CHECKING:
    from jieqi.board import JieqiBoard


# 棋子价值表（用于快速评估）
PIECE_VALUES = {
    PieceType.KING: 10000,
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
}

# 隐藏棋子的默认价值（期望值）
HIDDEN_PIECE_VALUE = 320


def pos_to_index(pos: Position) -> int:
    """位置转索引"""
    return pos.row * 9 + pos.col


def index_to_pos(index: int) -> Position:
    """索引转位置"""
    return Position(index // 9, index % 9)


def set_bit(bitmap: int, index: int) -> int:
    """设置位"""
    return bitmap | (1 << index)


def clear_bit(bitmap: int, index: int) -> int:
    """清除位"""
    return bitmap & ~(1 << index)


def test_bit(bitmap: int, index: int) -> bool:
    """测试位"""
    return bool(bitmap & (1 << index))


def popcount(bitmap: int) -> int:
    """计算 1 的数量"""
    return bin(bitmap).count("1")


def iter_bits(bitmap: int):
    """迭代所有设置的位"""
    while bitmap:
        # 找最低位的 1
        lsb = bitmap & -bitmap
        index = (lsb - 1).bit_length()
        if lsb > 0:
            index = lsb.bit_length() - 1
        yield index
        bitmap &= bitmap - 1


class BitBoard:
    """位图棋盘表示

    使用多个位图分别表示不同类型的棋子位置。
    """

    def __init__(self):
        # 按颜色分的占用位图
        self.red_pieces: int = 0
        self.black_pieces: int = 0

        # 按类型分的位图（不区分颜色）
        self.kings: int = 0
        self.advisors: int = 0
        self.elephants: int = 0
        self.horses: int = 0
        self.rooks: int = 0
        self.cannons: int = 0
        self.pawns: int = 0

        # 隐藏棋子位图
        self.hidden: int = 0

        # 实际类型映射 (index -> PieceType)
        # 用于隐藏棋子的真实身份
        self._actual_types: dict[int, PieceType] = {}

    @property
    def all_pieces(self) -> int:
        """所有棋子占用的位置"""
        return self.red_pieces | self.black_pieces

    @property
    def empty(self) -> int:
        """空位置（90位内）"""
        all_positions = (1 << 90) - 1
        return all_positions & ~self.all_pieces

    def get_type_bitmap(self, piece_type: PieceType) -> int:
        """获取某种棋子类型的位图"""
        if piece_type == PieceType.KING:
            return self.kings
        elif piece_type == PieceType.ADVISOR:
            return self.advisors
        elif piece_type == PieceType.ELEPHANT:
            return self.elephants
        elif piece_type == PieceType.HORSE:
            return self.horses
        elif piece_type == PieceType.ROOK:
            return self.rooks
        elif piece_type == PieceType.CANNON:
            return self.cannons
        elif piece_type == PieceType.PAWN:
            return self.pawns
        return 0

    def set_type_bitmap(self, piece_type: PieceType, bitmap: int) -> None:
        """设置某种棋子类型的位图"""
        if piece_type == PieceType.KING:
            self.kings = bitmap
        elif piece_type == PieceType.ADVISOR:
            self.advisors = bitmap
        elif piece_type == PieceType.ELEPHANT:
            self.elephants = bitmap
        elif piece_type == PieceType.HORSE:
            self.horses = bitmap
        elif piece_type == PieceType.ROOK:
            self.rooks = bitmap
        elif piece_type == PieceType.CANNON:
            self.cannons = bitmap
        elif piece_type == PieceType.PAWN:
            self.pawns = bitmap

    def add_piece(
        self,
        pos: Position,
        color: Color,
        actual_type: PieceType,
        is_hidden: bool = False,
    ) -> None:
        """添加棋子"""
        index = pos_to_index(pos)

        # 设置颜色位图
        if color == Color.RED:
            self.red_pieces = set_bit(self.red_pieces, index)
        else:
            self.black_pieces = set_bit(self.black_pieces, index)

        # 设置类型位图
        type_bitmap = self.get_type_bitmap(actual_type)
        self.set_type_bitmap(actual_type, set_bit(type_bitmap, index))

        # 记录实际类型
        self._actual_types[index] = actual_type

        # 设置隐藏状态
        if is_hidden:
            self.hidden = set_bit(self.hidden, index)

    def remove_piece(self, pos: Position) -> tuple[Color, PieceType, bool] | None:
        """移除棋子，返回 (颜色, 类型, 是否隐藏)"""
        index = pos_to_index(pos)

        # 确定颜色
        if test_bit(self.red_pieces, index):
            color = Color.RED
            self.red_pieces = clear_bit(self.red_pieces, index)
        elif test_bit(self.black_pieces, index):
            color = Color.BLACK
            self.black_pieces = clear_bit(self.black_pieces, index)
        else:
            return None

        # 确定类型并清除
        actual_type = self._actual_types.pop(index, None)
        if actual_type:
            type_bitmap = self.get_type_bitmap(actual_type)
            self.set_type_bitmap(actual_type, clear_bit(type_bitmap, index))

        # 检查隐藏状态
        was_hidden = test_bit(self.hidden, index)
        if was_hidden:
            self.hidden = clear_bit(self.hidden, index)

        return (color, actual_type, was_hidden) if actual_type else None

    def move_piece(self, from_pos: Position, to_pos: Position) -> tuple | None:
        """移动棋子，返回被吃的棋子信息"""
        from_index = pos_to_index(from_pos)
        to_index = pos_to_index(to_pos)

        # 获取移动棋子信息
        if test_bit(self.red_pieces, from_index):
            color = Color.RED
        elif test_bit(self.black_pieces, from_index):
            color = Color.BLACK
        else:
            return None

        actual_type = self._actual_types.get(from_index)
        if actual_type is None:
            return None

        was_hidden = test_bit(self.hidden, from_index)

        # 移除目标位置的棋子（如果有）
        captured = self.remove_piece(to_pos)

        # 移除源位置
        if color == Color.RED:
            self.red_pieces = clear_bit(self.red_pieces, from_index)
            self.red_pieces = set_bit(self.red_pieces, to_index)
        else:
            self.black_pieces = clear_bit(self.black_pieces, from_index)
            self.black_pieces = set_bit(self.black_pieces, to_index)

        # 更新类型位图
        type_bitmap = self.get_type_bitmap(actual_type)
        type_bitmap = clear_bit(type_bitmap, from_index)
        type_bitmap = set_bit(type_bitmap, to_index)
        self.set_type_bitmap(actual_type, type_bitmap)

        # 更新实际类型映射
        del self._actual_types[from_index]
        self._actual_types[to_index] = actual_type

        # 更新隐藏状态
        if was_hidden:
            self.hidden = clear_bit(self.hidden, from_index)
            # 移动后揭开
            # self.hidden = set_bit(self.hidden, to_index)  # 移动后自动揭开

        return captured

    def reveal(self, pos: Position) -> bool:
        """揭开棋子"""
        index = pos_to_index(pos)
        if test_bit(self.hidden, index):
            self.hidden = clear_bit(self.hidden, index)
            return True
        return False

    def get_piece_at(self, pos: Position) -> tuple[Color, PieceType, bool] | None:
        """获取位置上的棋子信息"""
        index = pos_to_index(pos)

        if test_bit(self.red_pieces, index):
            color = Color.RED
        elif test_bit(self.black_pieces, index):
            color = Color.BLACK
        else:
            return None

        actual_type = self._actual_types.get(index)
        if actual_type is None:
            return None

        is_hidden = test_bit(self.hidden, index)
        return (color, actual_type, is_hidden)

    @classmethod
    def from_board(cls, board: JieqiBoard) -> BitBoard:
        """从 JieqiBoard 创建 BitBoard"""
        bb = cls()
        for piece in board.get_all_pieces():
            bb.add_piece(
                piece.position,
                piece.color,
                piece.actual_type,
                piece.is_hidden,
            )
        return bb

    def copy(self) -> BitBoard:
        """复制位图棋盘"""
        new_bb = BitBoard()
        new_bb.red_pieces = self.red_pieces
        new_bb.black_pieces = self.black_pieces
        new_bb.kings = self.kings
        new_bb.advisors = self.advisors
        new_bb.elephants = self.elephants
        new_bb.horses = self.horses
        new_bb.rooks = self.rooks
        new_bb.cannons = self.cannons
        new_bb.pawns = self.pawns
        new_bb.hidden = self.hidden
        new_bb._actual_types = self._actual_types.copy()
        return new_bb


class FastEvaluator:
    """快速局面评估器

    使用位图进行快速计算。
    """

    # 位置权重表 (90个位置)
    # 中心控制、过河加分等预计算
    POSITION_WEIGHTS: list[float] = []

    @classmethod
    def _init_position_weights(cls) -> None:
        """初始化位置权重表"""
        if cls.POSITION_WEIGHTS:
            return

        cls.POSITION_WEIGHTS = [0.0] * 90
        for row in range(10):
            for col in range(9):
                index = row * 9 + col
                weight = 0.0

                # 中心控制
                if 3 <= col <= 5:
                    weight += 8
                elif 2 <= col <= 6:
                    weight += 4

                # 前进加分 (红方视角)
                weight += row * 1.5

                cls.POSITION_WEIGHTS[index] = weight

    def __init__(self, bitboard: BitBoard):
        self.bb = bitboard
        self._init_position_weights()

    def evaluate(self, color: Color) -> float:
        """评估局面（从 color 视角）

        返回值:
        - 正数: color 方优势
        - 负数: 对方优势
        - 0: 均势
        """
        score = 0.0

        # 1. 棋子价值
        score += self._material_score(color)
        score -= self._material_score(color.opposite)

        # 2. 位置分数
        score += self._position_score(color)
        score -= self._position_score(color.opposite)

        return score

    def _material_score(self, color: Color) -> float:
        """计算子力价值"""
        score = 0.0
        pieces = self.bb.red_pieces if color == Color.RED else self.bb.black_pieces

        for index in iter_bits(pieces):
            actual_type = self.bb._actual_types.get(index)
            if actual_type is None:
                continue

            is_hidden = test_bit(self.bb.hidden, index)
            if is_hidden:
                score += HIDDEN_PIECE_VALUE
            else:
                score += PIECE_VALUES.get(actual_type, 0)

        return score

    def _position_score(self, color: Color) -> float:
        """计算位置分数"""
        score = 0.0
        pieces = self.bb.red_pieces if color == Color.RED else self.bb.black_pieces

        for index in iter_bits(pieces):
            # 红方用正向权重，黑方用反向权重
            if color == Color.RED:
                score += self.POSITION_WEIGHTS[index]
            else:
                # 黑方从上往下看，row 9 变成 row 0
                row = index // 9
                col = index % 9
                flipped_index = (9 - row) * 9 + col
                score += self.POSITION_WEIGHTS[flipped_index]

        return score

    def quick_evaluate(self, color: Color) -> float:
        """快速评估（仅子力）"""
        my_material = self._material_score(color)
        enemy_material = self._material_score(color.opposite)
        return my_material - enemy_material


def evaluate_board_fast(board: JieqiBoard, color: Color) -> float:
    """快速评估棋盘（便捷函数）"""
    bb = BitBoard.from_board(board)
    evaluator = FastEvaluator(bb)
    return evaluator.evaluate(color)


def quick_material_eval(board: JieqiBoard, color: Color) -> float:
    """超快速子力评估"""
    score = 0.0
    for piece in board.get_all_pieces(color):
        if piece.is_hidden:
            score += HIDDEN_PIECE_VALUE
        else:
            score += PIECE_VALUES.get(piece.actual_type, 0)

    for piece in board.get_all_pieces(color.opposite):
        if piece.is_hidden:
            score -= HIDDEN_PIECE_VALUE
        else:
            score -= PIECE_VALUES.get(piece.actual_type, 0)

    return score


# 预计算的走法查找表
# 用于快速获取棋子的潜在目标位置

# 马的走法偏移 (腿位置, [目标位置偏移])
HORSE_MOVES = [
    ((-1, 0), [(-2, -1), (-2, 1)]),  # 上
    ((1, 0), [(2, -1), (2, 1)]),  # 下
    ((0, -1), [(-1, -2), (1, -2)]),  # 左
    ((0, 1), [(-1, 2), (1, 2)]),  # 右
]

# 象的走法偏移 (眼位置偏移, 目标位置偏移)
ELEPHANT_MOVES = [
    ((-1, -1), (-2, -2)),
    ((-1, 1), (-2, 2)),
    ((1, -1), (2, -2)),
    ((1, 1), (2, 2)),
]

# 士的走法偏移
ADVISOR_MOVES = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

# 将/帅的走法偏移
KING_MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class FastMoveGenerator:
    """快速走法生成器

    使用缓存和预计算加速走法生成。
    """

    def __init__(self, board: JieqiBoard):
        self.board = board
        # 缓存将的位置
        self._king_pos_cache: dict[Color, Position | None] = {}

    def find_king_cached(self, color: Color) -> Position | None:
        """缓存的将位置查找"""
        if color not in self._king_pos_cache:
            self._king_pos_cache[color] = self.board.find_king(color)
        return self._king_pos_cache[color]

    def invalidate_cache(self) -> None:
        """使缓存失效"""
        self._king_pos_cache.clear()

    def is_attacked_by(self, pos: Position, by_color: Color) -> bool:
        """检查位置是否被某方攻击（优化版）

        只检查能攻击到目标位置的棋子，而不是遍历所有棋子。
        """
        row, col = pos.row, pos.col

        # 1. 检查马攻击
        for leg_offset, move_offsets in HORSE_MOVES:
            for move_offset in move_offsets:
                # 反向查找：从目标位置反推马的位置
                horse_row = row - move_offset[0]
                horse_col = col - move_offset[1]
                if not (0 <= horse_row <= 9 and 0 <= horse_col <= 8):
                    continue

                horse_pos = Position(horse_row, horse_col)
                piece = self.board.get_piece(horse_pos)
                if piece is None or piece.color != by_color:
                    continue

                # 检查是否是马的走法
                movement_type = piece.get_movement_type()
                if movement_type != PieceType.HORSE:
                    continue

                # 检查马腿
                leg_row = horse_row + leg_offset[0]
                leg_col = horse_col + leg_offset[1]
                if 0 <= leg_row <= 9 and 0 <= leg_col <= 8:
                    leg_pos = Position(leg_row, leg_col)
                    if self.board.get_piece(leg_pos) is None:
                        # 马腿没被蹩，可以攻击
                        return True

        # 2. 检查车/炮攻击（直线）
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            platform_count = 0
            for step in range(1, 10):
                check_row = row + dr * step
                check_col = col + dc * step
                if not (0 <= check_row <= 9 and 0 <= check_col <= 8):
                    break

                check_pos = Position(check_row, check_col)
                piece = self.board.get_piece(check_pos)
                if piece is None:
                    continue

                if piece.color == by_color:
                    movement_type = piece.get_movement_type()
                    if movement_type == PieceType.ROOK and platform_count == 0:
                        return True
                    if movement_type == PieceType.CANNON and platform_count == 1:
                        return True
                    if movement_type == PieceType.KING and platform_count == 0:
                        # 飞将
                        return True

                platform_count += 1
                if platform_count > 1:
                    break

        # 3. 检查兵/卒攻击
        pawn_directions = (
            [(1, 0), (0, -1), (0, 1)] if by_color == Color.RED else [(-1, 0), (0, -1), (0, 1)]
        )
        for dr, dc in pawn_directions:
            pawn_row = row - dr
            pawn_col = col - dc
            if not (0 <= pawn_row <= 9 and 0 <= pawn_col <= 8):
                continue

            pawn_pos = Position(pawn_row, pawn_col)
            piece = self.board.get_piece(pawn_pos)
            if piece is None or piece.color != by_color:
                continue

            movement_type = piece.get_movement_type()
            if movement_type != PieceType.PAWN:
                continue

            # 检查兵是否过河（侧向攻击需要过河）
            if dc != 0:  # 侧向
                if pawn_pos.is_on_own_side(by_color):
                    continue

            return True

        # 4. 检查士攻击
        for dr, dc in ADVISOR_MOVES:
            adv_row = row - dr
            adv_col = col - dc
            if not (0 <= adv_row <= 9 and 0 <= adv_col <= 8):
                continue

            adv_pos = Position(adv_row, adv_col)
            piece = self.board.get_piece(adv_pos)
            if piece is None or piece.color != by_color:
                continue

            movement_type = piece.get_movement_type()
            if movement_type != PieceType.ADVISOR:
                continue

            # 暗子士限制在九宫格
            if piece.is_hidden:
                if not adv_pos.is_in_palace(by_color):
                    continue
            # 明子士可以任意位置攻击

            return True

        # 5. 检查象攻击
        for eye_offset, target_offset in ELEPHANT_MOVES:
            ele_row = row - target_offset[0]
            ele_col = col - target_offset[1]
            if not (0 <= ele_row <= 9 and 0 <= ele_col <= 8):
                continue

            ele_pos = Position(ele_row, ele_col)
            piece = self.board.get_piece(ele_pos)
            if piece is None or piece.color != by_color:
                continue

            movement_type = piece.get_movement_type()
            if movement_type != PieceType.ELEPHANT:
                continue

            # 检查象眼
            eye_row = ele_row + eye_offset[0]
            eye_col = ele_col + eye_offset[1]
            if 0 <= eye_row <= 9 and 0 <= eye_col <= 8:
                eye_pos = Position(eye_row, eye_col)
                if self.board.get_piece(eye_pos) is not None:
                    continue  # 象眼被蹩

            # 暗子象限制在己方半场
            if piece.is_hidden:
                if not pos.is_on_own_side(by_color):
                    continue

            return True

        # 6. 检查将/帅攻击（九宫格内）
        for dr, dc in KING_MOVES:
            king_row = row - dr
            king_col = col - dc
            if not (0 <= king_row <= 9 and 0 <= king_col <= 8):
                continue

            king_pos = Position(king_row, king_col)
            piece = self.board.get_piece(king_pos)
            if piece is None or piece.color != by_color:
                continue

            if piece.get_movement_type() == PieceType.KING:
                if king_pos.is_in_palace(by_color):
                    return True

        return False

    def is_in_check_fast(self, color: Color) -> bool:
        """快速检查是否被将军"""
        king_pos = self.find_king_cached(color)
        if king_pos is None:
            return True
        return self.is_attacked_by(king_pos, color.opposite)
