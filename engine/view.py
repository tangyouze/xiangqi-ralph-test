"""
揭棋玩家视角

PlayerView 表示某个玩家能看到的游戏状态：
- 棋盘上的暗子：actual_type = None（双方都不知道）
- 棋盘上的明子：显示真实身份
- 我吃掉的对方暗子：显示真实身份（我知道）
- 对方吃掉的我的暗子：actual_type = None（我不知道）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.types import Color, GameResult, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    pass


@dataclass
class ViewPiece:
    """玩家视角中的棋子

    actual_type 为 None 表示该棋子的身份对该玩家不可见
    """

    color: Color
    position: Position
    is_hidden: bool  # 是否为暗子（棋盘上未翻开的）
    actual_type: PieceType | None  # None 表示身份不可见

    # 用于暗子的走法类型（按位置规则）
    movement_type: PieceType | None = None


@dataclass
class CapturedPiece:
    """被吃掉的棋子信息"""

    color: Color  # 被吃棋子的颜色
    was_hidden: bool  # 被吃时是否为暗子
    actual_type: PieceType | None  # 真实身份（如果可见）
    captured_by: Color  # 被谁吃的
    move_number: int  # 第几步被吃的


@dataclass
class PlayerView:
    """玩家视角

    表示某个玩家（viewer）能看到的游戏状态
    """

    viewer: Color  # 谁在看
    current_turn: Color  # 当前该谁走
    result: GameResult  # 游戏结果
    move_count: int  # 已走步数
    is_in_check: bool  # 当前方是否被将军

    # 棋盘上的棋子（暗子的 actual_type = None）
    pieces: list[ViewPiece] = field(default_factory=list)

    # 合法走法（只有轮到自己时才有意义）
    legal_moves: list[JieqiMove] = field(default_factory=list)

    # 被吃掉的棋子
    # - 我吃的对方棋子：能看到身份
    # - 对方吃的我的棋子：看不到身份（actual_type = None）
    captured_pieces: list[CapturedPiece] = field(default_factory=list)

    # 暗子数量统计
    hidden_count: dict[str, int] = field(default_factory=dict)

    def get_piece_at(self, pos: Position) -> ViewPiece | None:
        """获取指定位置的棋子"""
        for piece in self.pieces:
            if piece.position == pos:
                return piece
        return None

    def get_my_pieces(self) -> list[ViewPiece]:
        """获取我方所有棋子"""
        return [p for p in self.pieces if p.color == self.viewer]

    def get_opponent_pieces(self) -> list[ViewPiece]:
        """获取对方所有棋子"""
        return [p for p in self.pieces if p.color != self.viewer]

    def get_my_captures(self) -> list[CapturedPiece]:
        """获取我吃掉的对方棋子（能看到身份）"""
        return [c for c in self.captured_pieces if c.captured_by == self.viewer]

    def get_opponent_captures(self) -> list[CapturedPiece]:
        """获取对方吃掉的我的棋子（看不到身份）"""
        return [c for c in self.captured_pieces if c.captured_by != self.viewer]

    def is_my_turn(self) -> bool:
        """是否轮到我走"""
        return self.current_turn == self.viewer

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "viewer": self.viewer.value,
            "current_turn": self.current_turn.value,
            "result": self.result.value,
            "move_count": self.move_count,
            "is_in_check": self.is_in_check,
            "pieces": [
                {
                    "color": p.color.value,
                    "position": {"row": p.position.row, "col": p.position.col},
                    "is_hidden": p.is_hidden,
                    "actual_type": p.actual_type.value if p.actual_type else None,
                    "movement_type": p.movement_type.value if p.movement_type else None,
                }
                for p in self.pieces
            ],
            "legal_moves": [
                {
                    "action_type": m.action_type.value,
                    "from": {"row": m.from_pos.row, "col": m.from_pos.col},
                    "to": {"row": m.to_pos.row, "col": m.to_pos.col},
                }
                for m in self.legal_moves
            ],
            "captured_pieces": [
                {
                    "color": c.color.value,
                    "was_hidden": c.was_hidden,
                    "actual_type": c.actual_type.value if c.actual_type else None,
                    "captured_by": c.captured_by.value,
                    "move_number": c.move_number,
                }
                for c in self.captured_pieces
            ],
            "hidden_count": self.hidden_count,
        }
