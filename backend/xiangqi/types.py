"""
核心类型定义

定义象棋中所有基础数据类型
"""

from enum import Enum
from typing import NamedTuple


class Color(Enum):
    """棋子颜色/阵营"""

    RED = "red"
    BLACK = "black"

    @property
    def opposite(self) -> "Color":
        """获取对方阵营"""
        return Color.BLACK if self == Color.RED else Color.RED


class PieceType(Enum):
    """棋子类型"""

    # 将/帅
    KING = "king"
    # 士/仕
    ADVISOR = "advisor"
    # 象/相
    ELEPHANT = "elephant"
    # 马
    HORSE = "horse"
    # 车
    ROOK = "rook"
    # 炮
    CANNON = "cannon"
    # 卒/兵
    PAWN = "pawn"


class Position(NamedTuple):
    """棋盘位置 (row, col)

    row: 0-9 (0 是红方底线，9 是黑方底线)
    col: 0-8 (从左到右)
    """

    row: int
    col: int

    def is_valid(self) -> bool:
        """检查位置是否在棋盘范围内"""
        return 0 <= self.row <= 9 and 0 <= self.col <= 8

    def is_in_palace(self, color: Color) -> bool:
        """检查位置是否在九宫格内"""
        if not (3 <= self.col <= 5):
            return False
        if color == Color.RED:
            return 0 <= self.row <= 2
        else:
            return 7 <= self.row <= 9

    def is_on_own_side(self, color: Color) -> bool:
        """检查位置是否在己方半场"""
        if color == Color.RED:
            return 0 <= self.row <= 4
        else:
            return 5 <= self.row <= 9

    def __add__(self, other: tuple[int, int]) -> "Position":
        """位置加偏移量"""
        return Position(self.row + other[0], self.col + other[1])


class Move(NamedTuple):
    """走棋动作"""

    from_pos: Position
    to_pos: Position

    def to_notation(self) -> str:
        """转换为标准记谱法 (简化版)"""
        return f"{self.from_pos.col}{self.from_pos.row}-{self.to_pos.col}{self.to_pos.row}"

    @classmethod
    def from_notation(cls, notation: str) -> "Move":
        """从记谱法解析"""
        # 格式: "c1r1-c2r2" 例如 "45-55"
        parts = notation.split("-")
        from_col, from_row = int(parts[0][0]), int(parts[0][1])
        to_col, to_row = int(parts[1][0]), int(parts[1][1])
        return cls(Position(from_row, from_col), Position(to_row, to_col))


class GameResult(Enum):
    """游戏结果"""

    ONGOING = "ongoing"
    RED_WIN = "red_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"
