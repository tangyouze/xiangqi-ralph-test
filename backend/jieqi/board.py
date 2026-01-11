"""
揭棋棋盘类定义

管理揭棋棋盘状态、揭子、走棋逻辑和游戏规则
"""

from __future__ import annotations

import random
from typing import Iterator

from jieqi.piece import JieqiPiece, create_jieqi_piece
from jieqi.types import (
    ActionType,
    Color,
    GameResult,
    JieqiMove,
    PieceState,
    PieceType,
    Position,
    get_position_piece_type,
    INITIAL_POSITIONS,
)

# 使用快速将军检测（懒加载以避免循环导入）
_fast_move_generator = None


class JieqiBoard:
    """揭棋棋盘

    坐标系统：
    - row 0-9: 0 是红方底线，9 是黑方底线
    - col 0-8: 从左到右

    揭棋规则：
    - 开局时将/帅明摆，其余15个棋子背面朝上随机放在对应位置
    - 暗子按位置对应的棋子类型走法走子
    - 揭开后按真实身份走子（象、士可过河）
    """

    def __init__(self, seed: int | None = None):
        """初始化揭棋棋盘

        Args:
            seed: 随机种子，用于确定暗子的真实身份分配（可选）
        """
        self._pieces: dict[Position, JieqiPiece] = {}
        self._seed = seed
        self._setup_initial_position()

    def _setup_initial_position(self) -> None:
        """初始化揭棋棋盘布局

        - 将/帅明摆在原位
        - 其余棋子随机分配真实身份，背面朝上放在对应位置
        """
        if self._seed is not None:
            random.seed(self._seed)

        # 分别处理红方和黑方
        for color in [Color.RED, Color.BLACK]:
            self._place_pieces_for_color(color)

    def _place_pieces_for_color(self, color: Color) -> None:
        """为一方放置所有棋子（揭棋规则）"""
        # 确定基准行
        if color == Color.RED:
            base_row = 0
            cannon_row = 2
            pawn_row = 3
        else:
            base_row = 9
            cannon_row = 7
            pawn_row = 6

        # 将/帅明摆
        king_pos = Position(base_row, 4)
        self._pieces[king_pos] = create_jieqi_piece(
            color, PieceType.KING, king_pos, revealed=True
        )

        # 收集所有非将位置和对应的棋子类型
        non_king_positions: list[Position] = []
        piece_types_to_place: list[PieceType] = []

        # 后排棋子（除将/帅外）
        back_row_config = [
            (0, PieceType.ROOK),
            (1, PieceType.HORSE),
            (2, PieceType.ELEPHANT),
            (3, PieceType.ADVISOR),
            # 4 是将/帅，已处理
            (5, PieceType.ADVISOR),
            (6, PieceType.ELEPHANT),
            (7, PieceType.HORSE),
            (8, PieceType.ROOK),
        ]
        for col, piece_type in back_row_config:
            pos = Position(base_row, col)
            non_king_positions.append(pos)
            piece_types_to_place.append(piece_type)

        # 炮
        for col in [1, 7]:
            pos = Position(cannon_row, col)
            non_king_positions.append(pos)
            piece_types_to_place.append(PieceType.CANNON)

        # 兵/卒
        for col in [0, 2, 4, 6, 8]:
            pos = Position(pawn_row, col)
            non_king_positions.append(pos)
            piece_types_to_place.append(PieceType.PAWN)

        # 随机打乱真实身份
        random.shuffle(piece_types_to_place)

        # 放置暗子
        for pos, actual_type in zip(non_king_positions, piece_types_to_place):
            self._pieces[pos] = create_jieqi_piece(
                color, actual_type, pos, revealed=False
            )

    def get_piece(self, pos: Position) -> JieqiPiece | None:
        """获取指定位置的棋子"""
        return self._pieces.get(pos)

    def set_piece(self, pos: Position, piece: JieqiPiece | None) -> None:
        """设置指定位置的棋子"""
        if piece is None:
            self._pieces.pop(pos, None)
        else:
            piece.position = pos
            self._pieces[pos] = piece

    def remove_piece(self, pos: Position) -> JieqiPiece | None:
        """移除并返回指定位置的棋子"""
        return self._pieces.pop(pos, None)

    def get_all_pieces(self, color: Color | None = None) -> list[JieqiPiece]:
        """获取所有棋子，可按颜色过滤"""
        if color is None:
            return list(self._pieces.values())
        return [p for p in self._pieces.values() if p.color == color]

    def get_hidden_pieces(self, color: Color) -> list[JieqiPiece]:
        """获取某方所有暗子"""
        return [
            p
            for p in self._pieces.values()
            if p.color == color and p.state == PieceState.HIDDEN
        ]

    def get_revealed_pieces(self, color: Color) -> list[JieqiPiece]:
        """获取某方所有明子"""
        return [
            p
            for p in self._pieces.values()
            if p.color == color and p.state == PieceState.REVEALED
        ]

    def find_king(self, color: Color) -> Position | None:
        """找到指定颜色的将/帅位置"""
        for piece in self._pieces.values():
            if piece.actual_type == PieceType.KING and piece.color == color:
                return piece.position
        return None

    def is_in_check(self, color: Color) -> bool:
        """检查指定颜色的将/帅是否被将军（使用优化算法）"""
        from jieqi.bitboard import FastMoveGenerator

        fast_gen = FastMoveGenerator(self)
        return fast_gen.is_in_check_fast(color)

    def is_in_check_slow(self, color: Color) -> bool:
        """检查指定颜色的将/帅是否被将军（原始算法，用于验证）"""
        king_pos = self.find_king(color)
        if king_pos is None:
            return True  # 没有将，认为被将军

        # 检查对方所有棋子是否能攻击到将
        for piece in self.get_all_pieces(color.opposite):
            if king_pos in piece.get_potential_moves(self):
                return True
        return False

    def reveal_piece(self, pos: Position) -> bool:
        """揭开指定位置的暗子

        Returns:
            是否成功揭开
        """
        piece = self.get_piece(pos)
        if piece is None or piece.is_revealed:
            return False
        piece.reveal()
        return True

    def make_move(self, move: JieqiMove) -> JieqiPiece | None:
        """执行走棋，返回被吃的棋子（如果有）

        揭棋规则：
        - REVEAL_AND_MOVE: 先揭开暗子，再走棋
        - MOVE: 明子直接走棋
        """
        piece = self._pieces.get(move.from_pos)
        if piece is None:
            raise ValueError(f"No piece at position {move.from_pos}")

        # 如果是揭子走法，先揭开
        if move.action_type == ActionType.REVEAL_AND_MOVE:
            if piece.is_revealed:
                raise ValueError(f"Piece at {move.from_pos} is already revealed")
            piece.reveal()

        # 执行走棋
        self._pieces.pop(move.from_pos)
        captured = self._pieces.pop(move.to_pos, None)
        piece.position = move.to_pos
        self._pieces[move.to_pos] = piece

        return captured

    def undo_move(
        self,
        move: JieqiMove,
        captured: JieqiPiece | None,
        was_hidden: bool = False,
    ) -> None:
        """撤销走棋

        Args:
            move: 要撤销的走法
            captured: 被吃的棋子
            was_hidden: 走棋前是否为暗子
        """
        piece = self._pieces.pop(move.to_pos, None)
        if piece is None:
            raise ValueError(f"No piece at position {move.to_pos}")

        piece.position = move.from_pos
        self._pieces[move.from_pos] = piece

        # 如果原来是暗子，恢复为暗子状态
        if was_hidden:
            piece.state = PieceState.HIDDEN

        if captured is not None:
            captured.position = move.to_pos
            self._pieces[move.to_pos] = captured

    def is_valid_move(self, move: JieqiMove, color: Color) -> bool:
        """检查走棋是否合法

        揭棋规则：
        - 暗子按位置对应的棋子类型走法计算合法目标
        - 揭开后按真实身份走法（但揭子走法的目标是按位置类型计算的）
        """
        piece = self.get_piece(move.from_pos)
        if piece is None or piece.color != color:
            return False

        # 检查动作类型是否正确
        if move.action_type == ActionType.REVEAL_AND_MOVE:
            # 揭子走法：棋子必须是暗子
            if piece.is_revealed:
                return False
        else:
            # 普通走法：棋子必须是明子
            if piece.is_hidden:
                return False

        # 获取目标位置的合法性
        # 暗子按位置类型走法计算（不揭开）
        # 明子按真实身份走法计算
        potential_moves = piece.get_potential_moves(self)

        if move.to_pos not in potential_moves:
            return False

        # 检查走完后是否会导致自己被将军
        was_hidden = piece.is_hidden
        captured = self.make_move(move)
        in_check = self.is_in_check(color)
        self.undo_move(move, captured, was_hidden)

        return not in_check

    def get_legal_moves(self, color: Color) -> list[JieqiMove]:
        """获取指定颜色的所有合法走法

        揭棋规则：
        - 暗子只能用 REVEAL_AND_MOVE 走法，按位置类型走法计算目标
        - 明子只能用 MOVE 走法，按真实身份走法计算目标
        """
        moves = []
        for piece in self.get_all_pieces(color):
            action_type = (
                ActionType.REVEAL_AND_MOVE
                if piece.is_hidden
                else ActionType.MOVE
            )

            # 暗子按位置类型走法计算目标（不揭开）
            # 明子按真实身份走法计算目标
            for to_pos in piece.get_potential_moves(self):
                move = JieqiMove(action_type, piece.position, to_pos)
                if self.is_valid_move(move, color):
                    moves.append(move)

        return moves

    def get_game_result(self, current_turn: Color) -> GameResult:
        """判断游戏结果

        揭棋胜负规则：
        - 吃掉对方将/帅者胜
        - 无合法走法且被将军：被将死
        - 无合法走法但未被将军：逼和
        """
        # 检查将/帅是否还在
        red_king = self.find_king(Color.RED)
        black_king = self.find_king(Color.BLACK)

        if red_king is None:
            return GameResult.BLACK_WIN
        if black_king is None:
            return GameResult.RED_WIN

        # 检查当前方是否有合法走法
        legal_moves = self.get_legal_moves(current_turn)

        if not legal_moves:
            if self.is_in_check(current_turn):
                # 被将死
                return (
                    GameResult.RED_WIN
                    if current_turn == Color.BLACK
                    else GameResult.BLACK_WIN
                )
            else:
                # 逼和
                return GameResult.DRAW

        return GameResult.ONGOING

    def copy(self) -> JieqiBoard:
        """创建棋盘的深拷贝"""
        new_board = JieqiBoard.__new__(JieqiBoard)
        new_board._pieces = {}
        new_board._seed = self._seed
        for pos, piece in self._pieces.items():
            new_board._pieces[pos] = piece.copy()
        return new_board

    def to_dict(self) -> dict:
        """序列化为字典（不暴露暗子身份）"""
        return {"pieces": [piece.to_dict() for piece in self._pieces.values()]}

    def to_full_dict(self) -> dict:
        """序列化为完整字典（包含暗子身份，用于调试）"""
        return {"pieces": [piece.to_full_dict() for piece in self._pieces.values()]}

    def __iter__(self) -> Iterator[JieqiPiece]:
        return iter(self._pieces.values())

    def __repr__(self) -> str:
        hidden_count = len([p for p in self._pieces.values() if p.is_hidden])
        return f"JieqiBoard({len(self._pieces)} pieces, {hidden_count} hidden)"

    def display(self) -> str:
        """返回棋盘的文本表示"""
        # 明子显示中文名，暗子显示 "暗"
        char_map = {
            (PieceType.KING, Color.RED): "帅",
            (PieceType.KING, Color.BLACK): "将",
            (PieceType.ADVISOR, Color.RED): "仕",
            (PieceType.ADVISOR, Color.BLACK): "士",
            (PieceType.ELEPHANT, Color.RED): "相",
            (PieceType.ELEPHANT, Color.BLACK): "象",
            (PieceType.HORSE, Color.RED): "马",
            (PieceType.HORSE, Color.BLACK): "馬",
            (PieceType.ROOK, Color.RED): "车",
            (PieceType.ROOK, Color.BLACK): "車",
            (PieceType.CANNON, Color.RED): "炮",
            (PieceType.CANNON, Color.BLACK): "砲",
            (PieceType.PAWN, Color.RED): "兵",
            (PieceType.PAWN, Color.BLACK): "卒",
        }

        lines = []
        for row in range(9, -1, -1):
            line = f"{row} "
            for col in range(9):
                piece = self.get_piece(Position(row, col))
                if piece is None:
                    line += "十 "
                elif piece.is_hidden:
                    # 暗子用颜色区分
                    line += "暗" if piece.color == Color.RED else "闇"
                    line += " "
                else:
                    char = char_map[(piece.actual_type, piece.color)]
                    line += char + " "
            lines.append(line)
        lines.append("  0  1  2  3  4  5  6  7  8")
        return "\n".join(lines)

    def display_full(self) -> str:
        """返回棋盘的完整文本表示（显示暗子真实身份，用于调试）"""
        char_map = {
            (PieceType.KING, Color.RED): "帅",
            (PieceType.KING, Color.BLACK): "将",
            (PieceType.ADVISOR, Color.RED): "仕",
            (PieceType.ADVISOR, Color.BLACK): "士",
            (PieceType.ELEPHANT, Color.RED): "相",
            (PieceType.ELEPHANT, Color.BLACK): "象",
            (PieceType.HORSE, Color.RED): "马",
            (PieceType.HORSE, Color.BLACK): "馬",
            (PieceType.ROOK, Color.RED): "车",
            (PieceType.ROOK, Color.BLACK): "車",
            (PieceType.CANNON, Color.RED): "炮",
            (PieceType.CANNON, Color.BLACK): "砲",
            (PieceType.PAWN, Color.RED): "兵",
            (PieceType.PAWN, Color.BLACK): "卒",
        }

        lines = []
        for row in range(9, -1, -1):
            line = f"{row} "
            for col in range(9):
                piece = self.get_piece(Position(row, col))
                if piece is None:
                    line += "十 "
                else:
                    char = char_map[(piece.actual_type, piece.color)]
                    if piece.is_hidden:
                        # 暗子用括号标记
                        line += f"({char})"
                    else:
                        line += char + " "
            lines.append(line)
        lines.append("  0  1  2  3  4  5  6  7  8")
        return "\n".join(lines)
