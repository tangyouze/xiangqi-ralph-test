"""
棋盘类定义

管理棋盘状态、走棋逻辑和游戏规则
"""

from copy import deepcopy
from typing import Iterator

from xiangqi.piece import Piece, create_piece
from xiangqi.types import Color, GameResult, Move, PieceType, Position


class Board:
    """象棋棋盘

    坐标系统：
    - row 0-9: 0 是红方底线，9 是黑方底线
    - col 0-8: 从左到右
    """

    def __init__(self):
        self._pieces: dict[Position, Piece] = {}
        self._setup_initial_position()

    def _setup_initial_position(self) -> None:
        """初始化棋盘布局"""
        # 红方（下方，row 0-4）
        self._place_pieces_for_color(Color.RED, base_row=0, pawn_row=3)
        # 黑方（上方，row 5-9）
        self._place_pieces_for_color(Color.BLACK, base_row=9, pawn_row=6)

    def _place_pieces_for_color(self, color: Color, base_row: int, pawn_row: int) -> None:
        """为一方放置所有棋子"""
        # 后排棋子
        back_row = [
            (0, PieceType.ROOK),
            (1, PieceType.HORSE),
            (2, PieceType.ELEPHANT),
            (3, PieceType.ADVISOR),
            (4, PieceType.KING),
            (5, PieceType.ADVISOR),
            (6, PieceType.ELEPHANT),
            (7, PieceType.HORSE),
            (8, PieceType.ROOK),
        ]
        for col, piece_type in back_row:
            pos = Position(base_row, col)
            self._pieces[pos] = create_piece(piece_type, color, pos)

        # 炮的位置（第二行）
        cannon_row = base_row + (2 if color == Color.RED else -2)
        for col in [1, 7]:
            pos = Position(cannon_row, col)
            self._pieces[pos] = create_piece(PieceType.CANNON, color, pos)

        # 兵/卒的位置
        for col in [0, 2, 4, 6, 8]:
            pos = Position(pawn_row, col)
            self._pieces[pos] = create_piece(PieceType.PAWN, color, pos)

    def get_piece(self, pos: Position) -> Piece | None:
        """获取指定位置的棋子"""
        return self._pieces.get(pos)

    def set_piece(self, pos: Position, piece: Piece | None) -> None:
        """设置指定位置的棋子"""
        if piece is None:
            self._pieces.pop(pos, None)
        else:
            piece.position = pos
            self._pieces[pos] = piece

    def remove_piece(self, pos: Position) -> Piece | None:
        """移除并返回指定位置的棋子"""
        return self._pieces.pop(pos, None)

    def get_all_pieces(self, color: Color | None = None) -> list[Piece]:
        """获取所有棋子，可按颜色过滤"""
        if color is None:
            return list(self._pieces.values())
        return [p for p in self._pieces.values() if p.color == color]

    def find_king(self, color: Color) -> Position | None:
        """找到指定颜色的将/帅位置"""
        for piece in self._pieces.values():
            if piece.piece_type == PieceType.KING and piece.color == color:
                return piece.position
        return None

    def is_in_check(self, color: Color) -> bool:
        """检查指定颜色的将/帅是否被将军"""
        king_pos = self.find_king(color)
        if king_pos is None:
            return True  # 没有将，认为被将军

        # 检查对方所有棋子是否能攻击到将
        for piece in self.get_all_pieces(color.opposite):
            if king_pos in piece.get_potential_moves(self):
                return True
        return False

    def make_move(self, move: Move) -> Piece | None:
        """执行走棋，返回被吃的棋子（如果有）"""
        piece = self._pieces.pop(move.from_pos, None)
        if piece is None:
            raise ValueError(f"No piece at position {move.from_pos}")

        captured = self._pieces.pop(move.to_pos, None)
        piece.position = move.to_pos
        self._pieces[move.to_pos] = piece
        return captured

    def undo_move(self, move: Move, captured: Piece | None) -> None:
        """撤销走棋"""
        piece = self._pieces.pop(move.to_pos, None)
        if piece is None:
            raise ValueError(f"No piece at position {move.to_pos}")

        piece.position = move.from_pos
        self._pieces[move.from_pos] = piece

        if captured is not None:
            captured.position = move.to_pos
            self._pieces[move.to_pos] = captured

    def is_valid_move(self, move: Move, color: Color) -> bool:
        """检查走棋是否合法"""
        piece = self.get_piece(move.from_pos)
        if piece is None or piece.color != color:
            return False

        # 检查目标位置是否在可能的移动列表中
        if move.to_pos not in piece.get_potential_moves(self):
            return False

        # 检查走完后是否会导致自己被将军
        captured = self.make_move(move)
        in_check = self.is_in_check(color)
        self.undo_move(move, captured)

        return not in_check

    def get_legal_moves(self, color: Color) -> list[Move]:
        """获取指定颜色的所有合法走法"""
        moves = []
        for piece in self.get_all_pieces(color):
            for to_pos in piece.get_potential_moves(self):
                move = Move(piece.position, to_pos)
                if self.is_valid_move(move, color):
                    moves.append(move)
        return moves

    def get_game_result(self, current_turn: Color) -> GameResult:
        """判断游戏结果"""
        # 检查当前方是否有合法走法
        legal_moves = self.get_legal_moves(current_turn)

        if not legal_moves:
            # 没有合法走法
            if self.is_in_check(current_turn):
                # 被将死
                return GameResult.RED_WIN if current_turn == Color.BLACK else GameResult.BLACK_WIN
            else:
                # 逼和
                return GameResult.DRAW

        return GameResult.ONGOING

    def copy(self) -> "Board":
        """创建棋盘的深拷贝"""
        new_board = Board.__new__(Board)
        new_board._pieces = {}
        for pos, piece in self._pieces.items():
            new_piece = create_piece(piece.piece_type, piece.color, pos)
            new_board._pieces[pos] = new_piece
        return new_board

    def to_fen(self) -> str:
        """转换为 FEN 格式（简化版）"""
        rows = []
        for row in range(9, -1, -1):
            row_str = ""
            empty_count = 0
            for col in range(9):
                piece = self.get_piece(Position(row, col))
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += self._piece_to_fen_char(piece)
            if empty_count > 0:
                row_str += str(empty_count)
            rows.append(row_str)
        return "/".join(rows)

    def _piece_to_fen_char(self, piece: Piece) -> str:
        """棋子转 FEN 字符"""
        char_map = {
            PieceType.KING: "k",
            PieceType.ADVISOR: "a",
            PieceType.ELEPHANT: "e",
            PieceType.HORSE: "h",
            PieceType.ROOK: "r",
            PieceType.CANNON: "c",
            PieceType.PAWN: "p",
        }
        char = char_map[piece.piece_type]
        return char.upper() if piece.color == Color.RED else char

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {"pieces": [piece.to_dict() for piece in self._pieces.values()]}

    def __iter__(self) -> Iterator[Piece]:
        return iter(self._pieces.values())

    def __repr__(self) -> str:
        return f"Board({len(self._pieces)} pieces)"

    def display(self) -> str:
        """返回棋盘的文本表示"""
        char_map = {
            (PieceType.KING, Color.RED): "帅",
            (PieceType.KING, Color.BLACK): "将",
            (PieceType.ADVISOR, Color.RED): "仕",
            (PieceType.ADVISOR, Color.BLACK): "士",
            (PieceType.ELEPHANT, Color.RED): "相",
            (PieceType.ELEPHANT, Color.BLACK): "象",
            (PieceType.HORSE, Color.RED): "马",
            (PieceType.HORSE, Color.BLACK): "马",
            (PieceType.ROOK, Color.RED): "车",
            (PieceType.ROOK, Color.BLACK): "车",
            (PieceType.CANNON, Color.RED): "炮",
            (PieceType.CANNON, Color.BLACK): "炮",
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
                    char = char_map[(piece.piece_type, piece.color)]
                    line += char + " "
            lines.append(line)
        lines.append("  0  1  2  3  4  5  6  7  8")
        return "\n".join(lines)
