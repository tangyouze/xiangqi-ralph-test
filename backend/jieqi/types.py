"""
揭棋核心类型定义

定义揭棋中所有基础数据类型
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


class PieceState(Enum):
    """棋子状态"""

    # 暗子 - 反面朝上，身份未知
    HIDDEN = "hidden"
    # 明子 - 正面朝上，身份已知
    REVEALED = "revealed"


class ActionType(Enum):
    """动作类型"""

    # 揭子并走棋
    REVEAL_AND_MOVE = "reveal_and_move"
    # 明子走棋
    MOVE = "move"


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


class JieqiMove(NamedTuple):
    """揭棋走法

    包含动作类型、起始位置和目标位置
    """

    action_type: ActionType
    from_pos: Position
    to_pos: Position

    def to_notation(self) -> str:
        """转换为标准记谱法"""
        action = "R" if self.action_type == ActionType.REVEAL_AND_MOVE else "M"
        return f"{action}:{self.from_pos.col}{self.from_pos.row}-{self.to_pos.col}{self.to_pos.row}"

    @classmethod
    def from_notation(cls, notation: str) -> "JieqiMove":
        """从记谱法解析"""
        # 格式: "R:c1r1-c2r2" 或 "M:c1r1-c2r2"
        action_str, positions = notation.split(":")
        action_type = (
            ActionType.REVEAL_AND_MOVE if action_str == "R" else ActionType.MOVE
        )
        parts = positions.split("-")
        from_col, from_row = int(parts[0][0]), int(parts[0][1])
        to_col, to_row = int(parts[1][0]), int(parts[1][1])
        return cls(action_type, Position(from_row, from_col), Position(to_row, to_col))

    @classmethod
    def reveal_move(cls, from_pos: Position, to_pos: Position) -> "JieqiMove":
        """创建揭子走法"""
        return cls(ActionType.REVEAL_AND_MOVE, from_pos, to_pos)

    @classmethod
    def regular_move(cls, from_pos: Position, to_pos: Position) -> "JieqiMove":
        """创建普通走法"""
        return cls(ActionType.MOVE, from_pos, to_pos)


class GameResult(Enum):
    """游戏结果"""

    ONGOING = "ongoing"
    RED_WIN = "red_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"


# 标准中国象棋的初始位置定义
# 用于确定暗子按什么位置的规则走子
INITIAL_POSITIONS: dict[Position, PieceType] = {
    # 红方 (下方，row 0-4)
    # 后排
    Position(0, 0): PieceType.ROOK,
    Position(0, 1): PieceType.HORSE,
    Position(0, 2): PieceType.ELEPHANT,
    Position(0, 3): PieceType.ADVISOR,
    Position(0, 4): PieceType.KING,
    Position(0, 5): PieceType.ADVISOR,
    Position(0, 6): PieceType.ELEPHANT,
    Position(0, 7): PieceType.HORSE,
    Position(0, 8): PieceType.ROOK,
    # 炮位
    Position(2, 1): PieceType.CANNON,
    Position(2, 7): PieceType.CANNON,
    # 兵位
    Position(3, 0): PieceType.PAWN,
    Position(3, 2): PieceType.PAWN,
    Position(3, 4): PieceType.PAWN,
    Position(3, 6): PieceType.PAWN,
    Position(3, 8): PieceType.PAWN,
    # 黑方 (上方，row 5-9)
    # 后排
    Position(9, 0): PieceType.ROOK,
    Position(9, 1): PieceType.HORSE,
    Position(9, 2): PieceType.ELEPHANT,
    Position(9, 3): PieceType.ADVISOR,
    Position(9, 4): PieceType.KING,
    Position(9, 5): PieceType.ADVISOR,
    Position(9, 6): PieceType.ELEPHANT,
    Position(9, 7): PieceType.HORSE,
    Position(9, 8): PieceType.ROOK,
    # 炮位
    Position(7, 1): PieceType.CANNON,
    Position(7, 7): PieceType.CANNON,
    # 卒位
    Position(6, 0): PieceType.PAWN,
    Position(6, 2): PieceType.PAWN,
    Position(6, 4): PieceType.PAWN,
    Position(6, 6): PieceType.PAWN,
    Position(6, 8): PieceType.PAWN,
}


def get_position_piece_type(pos: Position) -> PieceType | None:
    """根据位置获取该位置对应的棋子类型（走法规则）"""
    return INITIAL_POSITIONS.get(pos)


def get_piece_positions_by_type(piece_type: PieceType, color: Color) -> list[Position]:
    """获取某种棋子类型在某方的所有初始位置"""
    positions = []
    for pos, pt in INITIAL_POSITIONS.items():
        if pt != piece_type:
            continue
        # 根据颜色筛选
        if color == Color.RED and pos.row <= 4:
            positions.append(pos)
        elif color == Color.BLACK and pos.row >= 5:
            positions.append(pos)
    return positions
