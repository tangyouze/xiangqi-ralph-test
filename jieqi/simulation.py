"""
揭棋模拟棋盘

SimulationBoard 用于 AI 进行走棋模拟，而不暴露暗子的真实身份。
暗子在模拟中保持 actual_type = None，评估时使用期望值。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jieqi.attack_tables import (
    get_advisor_attacks,
    get_advisor_reverse_attacks,
    get_elephant_attacks,
    get_elephant_reverse_attacks,
    get_horse_attacks,
    get_horse_reverse_attacks,
    get_king_attacks,
    get_king_reverse_attacks,
    get_line_attacks,
    get_pawn_attacks,
    get_pawn_reverse_attacks,
)
from jieqi.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceType,
    Position,
)

if TYPE_CHECKING:
    from jieqi.view import PlayerView


@dataclass(slots=True)
class SimPiece:
    """模拟棋子

    暗子的 actual_type = None，只有 movement_type
    """

    color: Color
    position: Position
    is_hidden: bool
    actual_type: PieceType | None  # 暗子时为 None
    movement_type: PieceType | None  # 暗子的走法类型

    def get_movement_type(self) -> PieceType:
        """获取走法类型"""
        if self.is_hidden and self.movement_type:
            return self.movement_type
        elif self.actual_type:
            return self.actual_type
        else:
            raise ValueError("Piece has no movement type")

    def copy(self) -> SimPiece:
        return SimPiece(
            color=self.color,
            position=self.position,
            is_hidden=self.is_hidden,
            actual_type=self.actual_type,
            movement_type=self.movement_type,
        )


class SimulationBoard:
    """模拟棋盘

    从 PlayerView 创建，用于 AI 进行走棋模拟。
    暗子的 actual_type 保持为 None。
    """

    def __init__(self, view: PlayerView):
        self._pieces: dict[Position, SimPiece] = {}
        self._viewer = view.viewer
        self._current_turn = view.current_turn

        # 从 PlayerView 初始化棋子
        for vp in view.pieces:
            pos = vp.position
            self._pieces[pos] = SimPiece(
                color=vp.color,
                position=pos,
                is_hidden=vp.is_hidden,
                actual_type=vp.actual_type,
                movement_type=vp.movement_type,
            )

    @property
    def current_turn(self) -> Color:
        return self._current_turn

    def get_piece(self, pos: Position) -> SimPiece | None:
        return self._pieces.get(pos)

    def get_all_pieces(self, color: Color | None = None) -> list[SimPiece]:
        if color is None:
            return list(self._pieces.values())
        return [p for p in self._pieces.values() if p.color == color]

    def find_king(self, color: Color) -> Position | None:
        """找到将的位置

        优先使用 actual_type（明子）
        如果是暗子，使用 movement_type（按位置规则判断）
        """
        for piece in self._pieces.values():
            if piece.color != color:
                continue
            # 明子：使用 actual_type
            if piece.actual_type == PieceType.KING:
                return piece.position
            # 暗子：使用 movement_type（在将的初始位置）
            if piece.is_hidden and piece.movement_type == PieceType.KING:
                return piece.position
        return None

    def make_move(self, move: JieqiMove) -> SimPiece | None:
        """执行走棋，返回被吃的棋子"""
        piece = self._pieces.get(move.from_pos)
        if piece is None:
            raise ValueError(f"No piece at {move.from_pos}")

        # 揭子走法：标记为明子
        if move.action_type == ActionType.REVEAL_AND_MOVE:
            piece.is_hidden = False
            # 注意：actual_type 仍然是 None，因为 AI 不知道真实身份
            # 但走法类型会从 movement_type 变为 movement_type（保持不变）
            piece.actual_type = piece.movement_type  # 使用位置类型作为"已知"类型

        # 移动棋子
        self._pieces.pop(move.from_pos)
        captured = self._pieces.pop(move.to_pos, None)
        piece.position = move.to_pos
        self._pieces[move.to_pos] = piece

        # 切换回合
        self._current_turn = self._current_turn.opposite

        return captured

    def undo_move(self, move: JieqiMove, captured: SimPiece | None, was_hidden: bool) -> None:
        """撤销走棋"""
        piece = self._pieces.pop(move.to_pos, None)
        if piece is None:
            raise ValueError(f"No piece at {move.to_pos}")

        piece.position = move.from_pos
        self._pieces[move.from_pos] = piece

        # 恢复暗子状态
        if was_hidden:
            piece.is_hidden = True
            piece.actual_type = None

        if captured is not None:
            captured.position = move.to_pos
            self._pieces[move.to_pos] = captured

        # 恢复回合
        self._current_turn = self._current_turn.opposite

    def get_potential_moves(self, piece: SimPiece) -> list[Position]:
        """获取棋子的所有可能目标位置"""
        movement_type = piece.get_movement_type()

        if movement_type == PieceType.KING:
            return self._get_king_moves(piece)
        elif movement_type == PieceType.ADVISOR:
            return self._get_advisor_moves(piece)
        elif movement_type == PieceType.ELEPHANT:
            return self._get_elephant_moves(piece)
        elif movement_type == PieceType.HORSE:
            return self._get_horse_moves(piece)
        elif movement_type == PieceType.ROOK:
            return self._get_rook_moves(piece)
        elif movement_type == PieceType.CANNON:
            return self._get_cannon_moves(piece)
        elif movement_type == PieceType.PAWN:
            return self._get_pawn_moves(piece)
        return []

    def _can_move_to(self, piece: SimPiece, pos: Position) -> bool:
        target = self.get_piece(pos)
        if target is None:
            return True
        return target.color != piece.color

    def _get_king_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        for pos in get_king_attacks(piece.position):
            if pos.is_in_palace(piece.color) and self._can_move_to(piece, pos):
                moves.append(pos)

        # 飞将
        enemy_king_pos = self.find_king(piece.color.opposite)
        if enemy_king_pos and enemy_king_pos.col == piece.position.col:
            min_row = min(piece.position.row, enemy_king_pos.row)
            max_row = max(piece.position.row, enemy_king_pos.row)
            has_piece = False
            for row in range(min_row + 1, max_row):
                if self.get_piece(Position(row, piece.position.col)):
                    has_piece = True
                    break
            if not has_piece:
                moves.append(enemy_king_pos)

        return moves

    def _get_advisor_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        for pos in get_advisor_attacks(piece.position):
            if piece.is_hidden:
                if not pos.is_in_palace(piece.color):
                    continue
            if self._can_move_to(piece, pos):
                moves.append(pos)
        return moves

    def _get_elephant_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        for new_pos, eye_pos in get_elephant_attacks(piece.position):
            if piece.is_hidden:
                if not new_pos.is_on_own_side(piece.color):
                    continue
            if self.get_piece(eye_pos) is not None:
                continue
            if self._can_move_to(piece, new_pos):
                moves.append(new_pos)
        return moves

    def _get_horse_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        pieces = self._pieces
        piece_color = piece.color
        for new_pos, leg_pos in get_horse_attacks(piece.position):
            if pieces.get(leg_pos) is not None:
                continue
            target = pieces.get(new_pos)
            if target is None or target.color != piece_color:
                moves.append(new_pos)
        return moves

    def _get_rook_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        pieces = self._pieces
        piece_color = piece.color
        for direction in range(4):
            for pos in get_line_attacks(piece.position, direction):
                target = pieces.get(pos)
                if target is None:
                    moves.append(pos)
                elif target.color != piece_color:
                    moves.append(pos)
                    break
                else:
                    break
        return moves

    def _get_cannon_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        pieces = self._pieces  # 局部变量加速访问
        piece_color = piece.color
        for direction in range(4):
            found_platform = False
            for pos in get_line_attacks(piece.position, direction):
                target = pieces.get(pos)
                if not found_platform:
                    if target is None:
                        moves.append(pos)
                    else:
                        found_platform = True
                else:
                    if target is not None:
                        if target.color != piece_color:
                            moves.append(pos)
                        break
        return moves

    def _get_pawn_moves(self, piece: SimPiece) -> list[Position]:
        moves = []
        is_red = piece.color == Color.RED
        for pos in get_pawn_attacks(piece.position, is_red):
            if self._can_move_to(piece, pos):
                moves.append(pos)
        return moves

    def is_in_check(self, color: Color) -> bool:
        """检查是否被将军"""
        king_pos = self.find_king(color)
        if king_pos is None:
            return True
        return self.is_king_attacked(king_pos, color)

    def is_king_attacked(self, king_pos: Position, king_color: Color) -> bool:
        """快速检测将是否被攻击（使用反向攻击表）"""
        pieces = self._pieces
        enemy_color = king_color.opposite
        enemy_is_red = enemy_color == Color.RED

        # 1. 检查马的攻击（使用反向攻击表）
        for horse_pos, leg_pos in get_horse_reverse_attacks(king_pos):
            piece = pieces.get(horse_pos)
            if piece and piece.color == enemy_color:
                movement = piece.get_movement_type()
                if movement == PieceType.HORSE:
                    # 检查马腿
                    if pieces.get(leg_pos) is None:
                        return True

        # 2. 检查兵/卒的攻击（使用反向攻击表）
        for pawn_pos in get_pawn_reverse_attacks(king_pos, enemy_is_red):
            piece = pieces.get(pawn_pos)
            if piece and piece.color == enemy_color:
                movement = piece.get_movement_type()
                if movement == PieceType.PAWN:
                    return True

        # 3. 检查车/炮的攻击（同行或同列）
        for direction in range(4):
            first_piece = None
            for pos in get_line_attacks(king_pos, direction):
                piece = pieces.get(pos)
                if piece:
                    if first_piece is None:
                        # 第一个棋子
                        if piece.color == enemy_color:
                            movement = piece.get_movement_type()
                            if movement == PieceType.ROOK:
                                return True
                        first_piece = piece
                    else:
                        # 第二个棋子（炮架）
                        if piece.color == enemy_color:
                            movement = piece.get_movement_type()
                            if movement == PieceType.CANNON:
                                return True
                        break

        # 4. 检查象的攻击（使用反向攻击表）
        for elephant_pos, eye_pos in get_elephant_reverse_attacks(king_pos):
            piece = pieces.get(elephant_pos)
            if piece and piece.color == enemy_color:
                movement = piece.get_movement_type()
                if movement == PieceType.ELEPHANT:
                    # 检查象眼
                    if pieces.get(eye_pos) is None:
                        return True

        # 5. 检查士的攻击（使用反向攻击表）
        for advisor_pos in get_advisor_reverse_attacks(king_pos):
            piece = pieces.get(advisor_pos)
            if piece and piece.color == enemy_color:
                movement = piece.get_movement_type()
                if movement == PieceType.ADVISOR:
                    return True

        # 6. 检查敌方将的直接攻击（相邻格）
        for king_attack_pos in get_king_reverse_attacks(king_pos):
            piece = pieces.get(king_attack_pos)
            if piece and piece.color == enemy_color:
                movement = piece.get_movement_type()
                if movement == PieceType.KING:
                    return True

        # 7. 检查飞将（敌方将在同一列）
        enemy_king_pos = self.find_king(enemy_color)
        if enemy_king_pos and enemy_king_pos.col == king_pos.col:
            min_row = min(king_pos.row, enemy_king_pos.row)
            max_row = max(king_pos.row, enemy_king_pos.row)
            has_piece = False
            for row in range(min_row + 1, max_row):
                if pieces.get(Position(row, king_pos.col)):
                    has_piece = True
                    break
            if not has_piece:
                return True

        return False

    def get_legal_moves(self, color: Color) -> list[JieqiMove]:
        """获取所有合法走法"""
        moves = []
        king_pos = self.find_king(color)
        if king_pos is None:
            return moves

        # 获取所有己方棋子和潜在走法（内联优化）
        pieces = self._pieces
        my_pieces = [p for p in pieces.values() if p.color == color]
        get_moves = self.get_potential_moves
        is_attacked = self.is_king_attacked

        for piece in my_pieces:
            action_type = ActionType.REVEAL_AND_MOVE if piece.is_hidden else ActionType.MOVE
            was_hidden = piece.is_hidden
            from_pos = piece.position
            is_king = piece.get_movement_type() == PieceType.KING

            for to_pos in get_moves(piece):
                move = JieqiMove(action_type, from_pos, to_pos)
                captured = self.make_move(move)

                # 如果是将移动，更新将的位置
                check_king_pos = to_pos if is_king else king_pos

                # 使用快速攻击检测
                in_check = is_attacked(check_king_pos, color)

                self.undo_move(move, captured, was_hidden)

                if not in_check:
                    moves.append(move)

        return moves

    def get_game_result(
        self, current_turn: Color, legal_moves: list[JieqiMove] | None = None
    ) -> GameResult:
        """判断游戏结果

        Args:
            current_turn: 当前回合的颜色
            legal_moves: 预先计算的合法走法（可选，避免重复计算）
        """
        red_king = self.find_king(Color.RED)
        black_king = self.find_king(Color.BLACK)

        if red_king is None:
            return GameResult.BLACK_WIN
        if black_king is None:
            return GameResult.RED_WIN

        # 使用预计算的走法或重新计算
        moves = legal_moves if legal_moves is not None else self.get_legal_moves(current_turn)
        if not moves:
            if self.is_in_check(current_turn):
                return GameResult.RED_WIN if current_turn == Color.BLACK else GameResult.BLACK_WIN
            return GameResult.DRAW

        return GameResult.ONGOING

    def copy(self) -> SimulationBoard:
        """创建副本"""
        new_board = SimulationBoard.__new__(SimulationBoard)
        new_board._pieces = {pos: piece.copy() for pos, piece in self._pieces.items()}
        new_board._viewer = self._viewer
        new_board._current_turn = self._current_turn
        return new_board

    # 棋子类型到整数的映射（用于哈希）
    _PIECE_TYPE_INDEX = {
        PieceType.KING: 0,
        PieceType.ADVISOR: 1,
        PieceType.ELEPHANT: 2,
        PieceType.HORSE: 3,
        PieceType.ROOK: 4,
        PieceType.CANNON: 5,
        PieceType.PAWN: 6,
    }

    def get_position_hash(self) -> int:
        """获取局面哈希值

        用于 Transposition Table 缓存
        """
        # 使用简单的多项式哈希
        h = 0
        for pos, piece in sorted(self._pieces.items(), key=lambda x: (x[0].row, x[0].col)):
            # 位置编码
            pos_val = pos.row * 9 + pos.col
            # 颜色编码
            color_val = 0 if piece.color == Color.RED else 1
            # 类型编码（使用 movement_type 作为暗子的类型）
            movement_type = (
                piece.get_movement_type() if piece.actual_type or piece.movement_type else None
            )
            type_val = self._PIECE_TYPE_INDEX.get(movement_type, 7) if movement_type else 7
            # 暗子标记
            hidden_val = 1 if piece.is_hidden else 0

            # 组合成一个值
            piece_hash = (pos_val << 8) | (color_val << 7) | (type_val << 3) | (hidden_val << 2)
            h = (h * 31 + piece_hash) & 0xFFFFFFFFFFFFFFFF

        # 加入当前回合
        h = (h * 2 + (0 if self._current_turn == Color.RED else 1)) & 0xFFFFFFFFFFFFFFFF
        return h
