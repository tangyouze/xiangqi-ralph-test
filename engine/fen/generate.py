"""FEN 生成函数"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.fen.types import PIECE_TO_CHAR
from engine.types import Color

if TYPE_CHECKING:
    from engine.view import CapturedPiece, PlayerView, ViewPiece


def to_fen(view: PlayerView) -> str:
    """从 PlayerView 生成 FEN 字符串

    Args:
        view: 玩家视角

    Returns:
        FEN 字符串
    """
    # 1. 生成棋盘部分
    board_str = _board_to_fen(view.pieces)

    # 2. 生成被吃子部分
    captured_str = _captured_to_fen(view.captured_pieces, view.viewer)

    # 3. 回合和视角
    turn_str = "r" if view.current_turn == Color.RED else "b"
    viewer_str = "r" if view.viewer == Color.RED else "b"

    return f"{board_str} {captured_str} {turn_str} {viewer_str}"


def _board_to_fen(pieces: list[ViewPiece]) -> str:
    """棋盘转 FEN 字符串"""
    # 构建 10x9 的棋盘
    board: list[list[ViewPiece | None]] = [[None] * 9 for _ in range(10)]
    for piece in pieces:
        board[piece.position.row][piece.position.col] = piece

    rows: list[str] = []

    # 从 row 9 到 row 0（FEN 从上往下）
    for row in range(9, -1, -1):
        row_str = ""
        empty_count = 0

        for col in range(9):
            piece = board[row][col]
            if piece is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0

                if piece.is_hidden:
                    # 暗子：X（红）或 x（黑）
                    row_str += "X" if piece.color == Color.RED else "x"
                else:
                    # 明子：显示身份
                    char = PIECE_TO_CHAR[piece.actual_type]
                    row_str += char.upper() if piece.color == Color.RED else char

        if empty_count > 0:
            row_str += str(empty_count)

        rows.append(row_str)

    return "/".join(rows)


def _captured_to_fen(captured_pieces: list[CapturedPiece], viewer: Color) -> str:
    """被吃子转 FEN 字符串

    规则（用大小写区分明子/暗子）：
    - 大写 = 明子被吃（双方都知道）
    - 小写 = 暗子被吃，我知道身份（我吃的）
    - ? = 暗子被吃，我不知道身份
    """
    red_captured: list[str] = []  # 红方被吃的
    black_captured: list[str] = []  # 黑方被吃的

    for cap in captured_pieces:
        # 确定这个被吃的子，从 viewer 视角能看到什么
        is_my_piece = cap.color == viewer

        if cap.color == Color.RED:
            # 红方棋子被吃
            if is_my_piece and viewer == Color.RED:
                # 我（红方）的棋子被对方（黑方）吃了
                if cap.was_hidden:
                    # 暗子被吃，我不知道是什么
                    red_captured.append("?")
                else:
                    # 明子被吃，我知道 - 大写
                    char = PIECE_TO_CHAR[cap.actual_type].upper()
                    red_captured.append(char)
            else:
                # 对方（红方）的棋子被我（黑方）吃了
                if cap.was_hidden:
                    # 暗子被我吃，我知道身份 - 小写
                    char = PIECE_TO_CHAR[cap.actual_type].lower()
                    red_captured.append(char)
                else:
                    # 明子被吃 - 大写
                    char = PIECE_TO_CHAR[cap.actual_type].upper()
                    red_captured.append(char)
        else:
            # 黑方棋子被吃
            if is_my_piece and viewer == Color.BLACK:
                # 我（黑方）的棋子被对方（红方）吃了
                if cap.was_hidden:
                    # 暗子被吃，我不知道是什么
                    black_captured.append("?")
                else:
                    # 明子被吃，我知道 - 大写
                    char = PIECE_TO_CHAR[cap.actual_type].upper()
                    black_captured.append(char)
            else:
                # 对方（黑方）的棋子被我（红方）吃了
                if cap.was_hidden:
                    # 暗子被我吃，我知道身份 - 小写
                    char = PIECE_TO_CHAR[cap.actual_type].lower()
                    black_captured.append(char)
                else:
                    # 明子被吃 - 大写
                    char = PIECE_TO_CHAR[cap.actual_type].upper()
                    black_captured.append(char)

    red_str = "".join(red_captured) if red_captured else "-"
    black_str = "".join(black_captured) if black_captured else "-"

    return f"{red_str}:{black_str}"
