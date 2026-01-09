"""
棋子类定义

每种棋子有独立的走法规则
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from xiangqi.types import Color, PieceType, Position

if TYPE_CHECKING:
    from xiangqi.board import Board


class Piece(ABC):
    """棋子基类"""

    piece_type: PieceType

    def __init__(self, color: Color, position: Position):
        self.color = color
        self.position = position

    @abstractmethod
    def get_potential_moves(self, board: "Board") -> list[Position]:
        """获取所有可能的目标位置（不考虑将军）"""
        pass

    def can_capture(self, target: "Piece | None") -> bool:
        """检查是否可以吃子"""
        if target is None:
            return True
        return target.color != self.color

    def __repr__(self) -> str:
        return f"{self.piece_type.value}({self.color.value})@{self.position}"

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "type": self.piece_type.value,
            "color": self.color.value,
            "position": {"row": self.position.row, "col": self.position.col},
        }


class King(Piece):
    """将/帅"""

    piece_type = PieceType.KING

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 上下左右移动一格，限制在九宫格内
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_pos = self.position + (dr, dc)
            if new_pos.is_valid() and new_pos.is_in_palace(self.color):
                target = board.get_piece(new_pos)
                if self.can_capture(target):
                    moves.append(new_pos)

        # 将帅对面（飞将）检查 - 如果两将对面，可以直接吃对方将
        enemy_king_pos = board.find_king(self.color.opposite)
        if enemy_king_pos and enemy_king_pos.col == self.position.col:
            # 检查中间是否有棋子
            min_row = min(self.position.row, enemy_king_pos.row)
            max_row = max(self.position.row, enemy_king_pos.row)
            has_piece_between = False
            for row in range(min_row + 1, max_row):
                if board.get_piece(Position(row, self.position.col)):
                    has_piece_between = True
                    break
            if not has_piece_between:
                moves.append(enemy_king_pos)

        return moves


class Advisor(Piece):
    """士/仕"""

    piece_type = PieceType.ADVISOR

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 斜走一格，限制在九宫格内
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            new_pos = self.position + (dr, dc)
            if new_pos.is_valid() and new_pos.is_in_palace(self.color):
                target = board.get_piece(new_pos)
                if self.can_capture(target):
                    moves.append(new_pos)
        return moves


class Elephant(Piece):
    """象/相"""

    piece_type = PieceType.ELEPHANT

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 走田字，不能过河，需检查象眼
        for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            new_pos = self.position + (dr, dc)
            # 检查是否在己方半场
            if new_pos.is_valid() and new_pos.is_on_own_side(self.color):
                # 检查象眼（田字中心）
                eye_pos = self.position + (dr // 2, dc // 2)
                if board.get_piece(eye_pos) is None:
                    target = board.get_piece(new_pos)
                    if self.can_capture(target):
                        moves.append(new_pos)
        return moves


class Horse(Piece):
    """马"""

    piece_type = PieceType.HORSE

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 马走日字，需检查马脚（蹩马腿）
        # 格式: (马脚偏移, 目标位置偏移列表)
        leg_and_moves = [
            ((-1, 0), [(-2, -1), (-2, 1)]),  # 向上的马脚
            ((1, 0), [(2, -1), (2, 1)]),  # 向下的马脚
            ((0, -1), [(-1, -2), (1, -2)]),  # 向左的马脚
            ((0, 1), [(-1, 2), (1, 2)]),  # 向右的马脚
        ]

        for leg_offset, move_offsets in leg_and_moves:
            leg_pos = self.position + leg_offset
            # 检查马脚是否被绊
            if leg_pos.is_valid() and board.get_piece(leg_pos) is None:
                for move_offset in move_offsets:
                    new_pos = self.position + move_offset
                    if new_pos.is_valid():
                        target = board.get_piece(new_pos)
                        if self.can_capture(target):
                            moves.append(new_pos)
        return moves


class Rook(Piece):
    """车"""

    piece_type = PieceType.ROOK

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 横竖直走，遇子停止
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            for step in range(1, 10):
                new_pos = self.position + (dr * step, dc * step)
                if not new_pos.is_valid():
                    break
                target = board.get_piece(new_pos)
                if target is None:
                    moves.append(new_pos)
                elif target.color != self.color:
                    moves.append(new_pos)
                    break
                else:
                    break
        return moves


class Cannon(Piece):
    """炮"""

    piece_type = PieceType.CANNON

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 横竖直走，吃子需隔一个棋子（炮架）
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            found_platform = False
            for step in range(1, 10):
                new_pos = self.position + (dr * step, dc * step)
                if not new_pos.is_valid():
                    break
                target = board.get_piece(new_pos)
                if not found_platform:
                    if target is None:
                        moves.append(new_pos)
                    else:
                        found_platform = True
                else:
                    if target is not None:
                        if target.color != self.color:
                            moves.append(new_pos)
                        break
        return moves


class Pawn(Piece):
    """卒/兵"""

    piece_type = PieceType.PAWN

    def get_potential_moves(self, board: "Board") -> list[Position]:
        moves = []
        # 前进方向
        forward = 1 if self.color == Color.RED else -1

        # 始终可以向前走
        forward_pos = self.position + (forward, 0)
        if forward_pos.is_valid():
            target = board.get_piece(forward_pos)
            if self.can_capture(target):
                moves.append(forward_pos)

        # 过河后可以左右走
        if not self.position.is_on_own_side(self.color):
            for dc in [-1, 1]:
                side_pos = self.position + (0, dc)
                if side_pos.is_valid():
                    target = board.get_piece(side_pos)
                    if self.can_capture(target):
                        moves.append(side_pos)

        return moves


def create_piece(piece_type: PieceType, color: Color, position: Position) -> Piece:
    """工厂函数：创建棋子"""
    piece_classes = {
        PieceType.KING: King,
        PieceType.ADVISOR: Advisor,
        PieceType.ELEPHANT: Elephant,
        PieceType.HORSE: Horse,
        PieceType.ROOK: Rook,
        PieceType.CANNON: Cannon,
        PieceType.PAWN: Pawn,
    }
    return piece_classes[piece_type](color, position)
