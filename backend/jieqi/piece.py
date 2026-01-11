"""
揭棋棋子类定义

揭棋棋子分为暗子和明子：
- 暗子：反面朝上，真实身份未知，按所在位置对应的棋子类型走法走子
- 明子：正面朝上，按真实身份走子（象、士可以过河）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jieqi.types import (
    Color,
    PieceState,
    PieceType,
    Position,
    get_position_piece_type,
)

# 导入预计算的攻击表
from jieqi.attack_tables import (
    get_king_attacks,
    get_advisor_attacks,
    get_elephant_attacks,
    get_horse_attacks,
    get_pawn_attacks,
    get_line_attacks,
)

if TYPE_CHECKING:
    from jieqi.board import JieqiBoard


class JieqiPiece:
    """揭棋棋子

    揭棋棋子有两种状态：
    - HIDDEN: 暗子，真实身份隐藏，按位置规则走子
    - REVEALED: 明子，真实身份已知，按明棋规则走子
    """

    def __init__(
        self,
        color: Color,
        actual_type: PieceType,
        position: Position,
        state: PieceState = PieceState.HIDDEN,
    ):
        self.color = color
        # 真实身份（将/帅开局就是明子）
        self.actual_type = actual_type
        self.position = position
        self.state = state

    @property
    def is_hidden(self) -> bool:
        """是否为暗子"""
        return self.state == PieceState.HIDDEN

    @property
    def is_revealed(self) -> bool:
        """是否为明子"""
        return self.state == PieceState.REVEALED

    def reveal(self) -> None:
        """揭开暗子，变成明子"""
        self.state = PieceState.REVEALED

    def get_movement_type(self) -> PieceType:
        """获取走法对应的棋子类型

        暗子按位置对应的棋子类型走法；明子按真实身份走法
        """
        if self.is_hidden:
            # 暗子按位置规则走
            pos_type = get_position_piece_type(self.position)
            if pos_type is None:
                # 不在标准位置上，无法走动（不应该发生）
                raise ValueError(f"Hidden piece at {self.position} is not on a standard position")
            return pos_type
        else:
            # 明子按真实身份走
            return self.actual_type

    def get_potential_moves(self, board: JieqiBoard) -> list[Position]:
        """获取所有可能的目标位置（不考虑将军）

        根据棋子状态返回不同的走法：
        - 暗子：按位置对应的棋子类型走法
        - 明子：按真实身份走法（象、士可以过河）
        """
        movement_type = self.get_movement_type()
        return self._get_moves_for_type(board, movement_type)

    def _get_moves_for_type(self, board: JieqiBoard, piece_type: PieceType) -> list[Position]:
        """根据指定的棋子类型获取走法"""
        if piece_type == PieceType.KING:
            return self._get_king_moves(board)
        elif piece_type == PieceType.ADVISOR:
            return self._get_advisor_moves(board)
        elif piece_type == PieceType.ELEPHANT:
            return self._get_elephant_moves(board)
        elif piece_type == PieceType.HORSE:
            return self._get_horse_moves(board)
        elif piece_type == PieceType.ROOK:
            return self._get_rook_moves(board)
        elif piece_type == PieceType.CANNON:
            return self._get_cannon_moves(board)
        elif piece_type == PieceType.PAWN:
            return self._get_pawn_moves(board)
        else:
            return []

    def _get_king_moves(self, board: JieqiBoard) -> list[Position]:
        """将/帅走法：九宫格内四向移动一格（使用预计算表）"""
        moves = []
        for new_pos in get_king_attacks(self.position):
            if new_pos.is_in_palace(self.color) and self._can_move_to(board, new_pos):
                moves.append(new_pos)

        # 飞将检查
        enemy_king_pos = board.find_king(self.color.opposite)
        if enemy_king_pos and enemy_king_pos.col == self.position.col:
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

    def _get_advisor_moves(self, board: JieqiBoard) -> list[Position]:
        """士/仕走法（使用预计算表）：

        - 暗子：九宫格内斜走一格
        - 明子：可以过河，斜走一格（无九宫格限制）
        """
        moves = []
        for new_pos in get_advisor_attacks(self.position):
            # 揭棋规则：明子的士可以过河
            if self.is_hidden:
                # 暗子仍限制在九宫格内
                if not new_pos.is_in_palace(self.color):
                    continue

            if self._can_move_to(board, new_pos):
                moves.append(new_pos)
        return moves

    def _get_elephant_moves(self, board: JieqiBoard) -> list[Position]:
        """象/相走法（使用预计算表）：

        - 暗子：己方半场走田字，需检查象眼
        - 明子：可以过河，走田字，需检查象眼
        """
        moves = []
        for new_pos, eye_pos in get_elephant_attacks(self.position):
            # 揭棋规则：明子的象可以过河
            if self.is_hidden:
                # 暗子仍限制在己方半场
                if not new_pos.is_on_own_side(self.color):
                    continue

            # 检查象眼
            if board.get_piece(eye_pos) is not None:
                continue

            if self._can_move_to(board, new_pos):
                moves.append(new_pos)
        return moves

    def _get_horse_moves(self, board: JieqiBoard) -> list[Position]:
        """马走法（使用预计算表）：日字走法，需检查蹩马腿"""
        moves = []
        for new_pos, leg_pos in get_horse_attacks(self.position):
            # 检查马腿是否被蹩
            if board.get_piece(leg_pos) is not None:
                continue
            if self._can_move_to(board, new_pos):
                moves.append(new_pos)
        return moves

    def _get_rook_moves(self, board: JieqiBoard) -> list[Position]:
        """车走法（使用预计算表）：横竖直走，遇子停止"""
        moves = []
        for direction in range(4):
            for new_pos in get_line_attacks(self.position, direction):
                target = board.get_piece(new_pos)
                if target is None:
                    moves.append(new_pos)
                elif target.color != self.color:
                    moves.append(new_pos)
                    break
                else:
                    break
        return moves

    def _get_cannon_moves(self, board: JieqiBoard) -> list[Position]:
        """炮走法（使用预计算表）：横竖直走，吃子需隔一个棋子（炮架）"""
        moves = []
        for direction in range(4):
            found_platform = False
            for new_pos in get_line_attacks(self.position, direction):
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

    def _get_pawn_moves(self, board: JieqiBoard) -> list[Position]:
        """卒/兵走法（使用预计算表）：

        - 未过河：只能向前一格
        - 过河后：可以向前、左、右各一格
        """
        moves = []
        is_red = self.color == Color.RED

        for new_pos in get_pawn_attacks(self.position, is_red):
            if self._can_move_to(board, new_pos):
                moves.append(new_pos)

        return moves

    def _can_move_to(self, board: JieqiBoard, pos: Position) -> bool:
        """检查是否可以移动到指定位置（空位或对方棋子）"""
        target = board.get_piece(pos)
        if target is None:
            return True
        return target.color != self.color

    def can_capture(self, target: JieqiPiece | None) -> bool:
        """检查是否可以吃子"""
        if target is None:
            return True
        return target.color != self.color

    def copy(self) -> JieqiPiece:
        """创建棋子副本"""
        return JieqiPiece(
            color=self.color,
            actual_type=self.actual_type,
            position=self.position,
            state=self.state,
        )

    def to_dict(self) -> dict:
        """序列化为字典"""
        result = {
            "color": self.color.value,
            "position": {"row": self.position.row, "col": self.position.col},
            "state": self.state.value,
        }
        # 只有明子才显示真实身份
        if self.is_revealed:
            result["type"] = self.actual_type.value
        return result

    def to_full_dict(self) -> dict:
        """序列化为完整字典（包含隐藏信息，用于调试）"""
        return {
            "color": self.color.value,
            "actual_type": self.actual_type.value,
            "position": {"row": self.position.row, "col": self.position.col},
            "state": self.state.value,
            "movement_type": (self.get_movement_type().value if self.is_hidden else None),
        }

    def __repr__(self) -> str:
        state_str = "?" if self.is_hidden else self.actual_type.value
        return f"JieqiPiece({self.color.value}, {state_str})@{self.position}"


def create_jieqi_piece(
    color: Color,
    actual_type: PieceType,
    position: Position,
    revealed: bool = False,
) -> JieqiPiece:
    """工厂函数：创建揭棋棋子"""
    state = PieceState.REVEALED if revealed else PieceState.HIDDEN
    return JieqiPiece(color, actual_type, position, state)
