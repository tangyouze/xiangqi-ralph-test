"""FEN 解析和走法字符串处理"""

from __future__ import annotations

from engine.fen.types import (
    CHAR_TO_COL,
    CHAR_TO_PIECE,
    COL_TO_CHAR,
    PIECE_TO_CHAR,
    CapturedInfo,
    CapturedPieceInfo,
    FenPiece,
    FenState,
)
from engine.types import ActionType, Color, JieqiMove, PieceType, Position


def parse_fen(fen: str) -> FenState:
    """解析 FEN 字符串

    Args:
        fen: FEN 字符串

    Returns:
        FenState

    Raises:
        ValueError: 格式错误
    """
    parts = fen.strip().split()
    if len(parts) != 4:
        raise ValueError(
            f"Invalid FEN format: expected '<board> <captured> <turn> <viewer>', got: {fen}"
        )

    board_str, captured_str, turn_str, viewer_str = parts

    # 解析各部分
    pieces = _parse_board(board_str)
    captured = _parse_captured(captured_str)
    turn = Color.RED if turn_str.lower() == "r" else Color.BLACK
    viewer = Color.RED if viewer_str.lower() == "r" else Color.BLACK

    return FenState(pieces=pieces, captured=captured, turn=turn, viewer=viewer)


def _parse_board(board_str: str) -> list[FenPiece]:
    """解析棋盘字符串"""
    rows = board_str.split("/")
    if len(rows) != 10:
        raise ValueError(f"Invalid board: expected 10 rows, got {len(rows)}")

    pieces: list[FenPiece] = []

    for row_idx, row_str in enumerate(rows):
        # FEN 从上往下是 row 9 到 row 0
        row = 9 - row_idx
        col = 0

        for ch in row_str:
            if col >= 9:
                break

            if ch.isdigit():
                col += int(ch)
            elif ch == "X":
                # 红方暗子
                pieces.append(
                    FenPiece(
                        position=Position(row, col),
                        color=Color.RED,
                        is_hidden=True,
                        piece_type=None,
                    )
                )
                col += 1
            elif ch == "x":
                # 黑方暗子
                pieces.append(
                    FenPiece(
                        position=Position(row, col),
                        color=Color.BLACK,
                        is_hidden=True,
                        piece_type=None,
                    )
                )
                col += 1
            elif ch.isalpha():
                # 明子
                piece_type = CHAR_TO_PIECE.get(ch.lower())
                if piece_type is None:
                    raise ValueError(f"Invalid piece char: {ch}")
                color = Color.RED if ch.isupper() else Color.BLACK
                pieces.append(
                    FenPiece(
                        position=Position(row, col),
                        color=color,
                        is_hidden=False,
                        piece_type=piece_type,
                    )
                )
                col += 1
            else:
                raise ValueError(f"Invalid character in board: {ch}")

        if col != 9:
            raise ValueError(f"Row {row} has {col} columns, expected 9")

    return pieces


def _parse_captured(captured_str: str) -> CapturedInfo:
    """解析被吃子字符串

    格式：
    - 大写 = 明子被吃
    - 小写 = 暗子被吃（我知道身份）
    - ? = 暗子被吃（我不知道身份）
    """
    parts = captured_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid captured format: {captured_str}")

    red_str, black_str = parts
    info = CapturedInfo()

    # 解析红方被吃
    if red_str != "-":
        for ch in red_str:
            if ch == "?":
                # 暗子被吃，不知道身份
                info.red_captured.append(CapturedPieceInfo(piece_type=None, was_hidden=True))
            else:
                piece_type = CHAR_TO_PIECE.get(ch.lower())
                if piece_type is None:
                    raise ValueError(f"Invalid captured piece: {ch}")
                # 大写 = 明子，小写 = 暗子
                was_hidden = ch.islower()
                info.red_captured.append(
                    CapturedPieceInfo(piece_type=piece_type, was_hidden=was_hidden)
                )

    # 解析黑方被吃
    if black_str != "-":
        for ch in black_str:
            if ch == "?":
                # 暗子被吃，不知道身份
                info.black_captured.append(CapturedPieceInfo(piece_type=None, was_hidden=True))
            else:
                piece_type = CHAR_TO_PIECE.get(ch.lower())
                if piece_type is None:
                    raise ValueError(f"Invalid captured piece: {ch}")
                # 大写 = 明子，小写 = 暗子
                was_hidden = ch.islower()
                info.black_captured.append(
                    CapturedPieceInfo(piece_type=piece_type, was_hidden=was_hidden)
                )

    return info


def move_to_str(move: JieqiMove, revealed_type: PieceType | None = None) -> str:
    """走法转字符串

    Args:
        move: 走法
        revealed_type: 揭子后的类型（仅用于 REVEAL_AND_MOVE 执行后）

    Returns:
        走法字符串

    Examples:
        >>> move_to_str(JieqiMove.regular_move(Position(0, 0), Position(1, 0)))
        'a0a1'
        >>> move_to_str(JieqiMove.reveal_move(Position(0, 0), Position(1, 0)))
        '+a0a1'
        >>> move_to_str(JieqiMove.reveal_move(Position(0, 0), Position(1, 0)), PieceType.ROOK)
        '+a0a1=R'
    """
    from_str = f"{COL_TO_CHAR[move.from_pos.col]}{move.from_pos.row}"
    to_str = f"{COL_TO_CHAR[move.to_pos.col]}{move.to_pos.row}"

    if move.action_type == ActionType.REVEAL_AND_MOVE:
        prefix = "+"
        if revealed_type is not None:
            suffix = f"={PIECE_TO_CHAR[revealed_type].upper()}"
        else:
            suffix = ""
        return f"{prefix}{from_str}{to_str}{suffix}"
    else:
        return f"{from_str}{to_str}"


def parse_move(move_str: str) -> tuple[JieqiMove, PieceType | None]:
    """解析走法字符串

    Args:
        move_str: 走法字符串

    Returns:
        (走法, 揭示的棋子类型)

    Examples:
        >>> parse_move('a0a1')
        (JieqiMove(MOVE, (0,0), (1,0)), None)
        >>> parse_move('+a0a1')
        (JieqiMove(REVEAL_AND_MOVE, (0,0), (1,0)), None)
        >>> parse_move('+a0a1=R')
        (JieqiMove(REVEAL_AND_MOVE, (0,0), (1,0)), ROOK)
    """
    revealed_type: PieceType | None = None

    # 检查是否有揭示结果
    if "=" in move_str:
        move_str, revealed_char = move_str.split("=")
        revealed_type = CHAR_TO_PIECE.get(revealed_char.lower())
        if revealed_type is None:
            raise ValueError(f"Invalid revealed type: {revealed_char}")

    # 检查是否是揭子走法
    if move_str.startswith("+"):
        action_type = ActionType.REVEAL_AND_MOVE
        move_str = move_str[1:]
    else:
        action_type = ActionType.MOVE

    # 解析坐标：a0a1 格式
    if len(move_str) != 4:
        raise ValueError(f"Invalid move format: {move_str}")

    from_col = CHAR_TO_COL.get(move_str[0])
    from_row = int(move_str[1]) if move_str[1].isdigit() else None
    to_col = CHAR_TO_COL.get(move_str[2])
    to_row = int(move_str[3]) if move_str[3].isdigit() else None

    if None in (from_col, from_row, to_col, to_row):
        raise ValueError(f"Invalid move coordinates: {move_str}")

    move = JieqiMove(
        action_type=action_type,
        from_pos=Position(from_row, from_col),
        to_pos=Position(to_row, to_col),
    )

    return move, revealed_type
