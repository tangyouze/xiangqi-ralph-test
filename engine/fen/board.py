"""FEN 与 SimulationBoard 转换"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.fen.parse import move_to_str, parse_fen, parse_move
from engine.fen.types import PIECE_TO_CHAR, CapturedInfo, FenPiece
from engine.types import Color, PieceType

if TYPE_CHECKING:
    from engine.simulation import SimulationBoard


def fen_from_pieces(
    pieces: list[FenPiece],
    captured: CapturedInfo | None = None,
    turn: Color = Color.RED,
    viewer: Color = Color.RED,
) -> str:
    """从棋子列表生成 FEN

    便捷函数，用于测试和调试
    """
    # 构建棋盘
    board: list[list[FenPiece | None]] = [[None] * 9 for _ in range(10)]
    for piece in pieces:
        board[piece.position.row][piece.position.col] = piece

    rows: list[str] = []
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
                    row_str += "X" if piece.color == Color.RED else "x"
                else:
                    char = PIECE_TO_CHAR[piece.piece_type]
                    row_str += char.upper() if piece.color == Color.RED else char

        if empty_count > 0:
            row_str += str(empty_count)

        rows.append(row_str)

    board_str = "/".join(rows)

    # 被吃子
    if captured is None:
        captured_str = "-:-"
    else:
        # 生成红方被吃的字符串
        red_parts: list[str] = []
        for cap in captured.red_captured:
            if cap.piece_type is None:
                # 暗子被吃，不知道身份
                red_parts.append("?")
            elif cap.was_hidden:
                # 暗子被吃，知道身份 - 小写
                red_parts.append(PIECE_TO_CHAR[cap.piece_type].lower())
            else:
                # 明子被吃 - 大写
                red_parts.append(PIECE_TO_CHAR[cap.piece_type].upper())

        # 生成黑方被吃的字符串
        black_parts: list[str] = []
        for cap in captured.black_captured:
            if cap.piece_type is None:
                # 暗子被吃，不知道身份
                black_parts.append("?")
            elif cap.was_hidden:
                # 暗子被吃，知道身份 - 小写
                black_parts.append(PIECE_TO_CHAR[cap.piece_type].lower())
            else:
                # 明子被吃 - 大写
                black_parts.append(PIECE_TO_CHAR[cap.piece_type].upper())

        red_str = "".join(red_parts) if red_parts else "-"
        black_str = "".join(black_parts) if black_parts else "-"
        captured_str = f"{red_str}:{black_str}"

    turn_str = "r" if turn == Color.RED else "b"
    viewer_str = "r" if viewer == Color.RED else "b"

    return f"{board_str} {captured_str} {turn_str} {viewer_str}"


def create_board_from_fen(fen: str) -> SimulationBoard:
    """从 FEN 字符串创建 SimulationBoard

    用于 AI 基于 FEN 进行决策。

    Args:
        fen: FEN 字符串

    Returns:
        SimulationBoard 实例
    """
    from engine.simulation import SimulationBoard
    from engine.types import GameResult, get_position_piece_type
    from engine.view import PlayerView, ViewPiece

    state = parse_fen(fen)

    # 将 FenPiece 转换为 ViewPiece
    view_pieces: list[ViewPiece] = []
    for fp in state.pieces:
        if fp.is_hidden:
            # 暗子：movement_type 由位置决定
            movement_type = get_position_piece_type(fp.position)
            view_pieces.append(
                ViewPiece(
                    color=fp.color,
                    position=fp.position,
                    is_hidden=True,
                    actual_type=None,
                    movement_type=movement_type,
                )
            )
        else:
            # 明子：actual_type 和 movement_type 相同
            view_pieces.append(
                ViewPiece(
                    color=fp.color,
                    position=fp.position,
                    is_hidden=False,
                    actual_type=fp.piece_type,
                    movement_type=fp.piece_type,
                )
            )

    # 创建 PlayerView
    view = PlayerView(
        viewer=state.viewer,
        current_turn=state.turn,
        result=GameResult.ONGOING,
        move_count=0,
        is_in_check=False,
        pieces=view_pieces,
        legal_moves=[],
        captured_pieces=[],
    )

    return SimulationBoard(view)


def get_legal_moves_from_fen(fen: str) -> list[str]:
    """从 FEN 获取所有合法走法

    Args:
        fen: FEN 字符串

    Returns:
        走法字符串列表
    """
    state = parse_fen(fen)
    board = create_board_from_fen(fen)
    legal_moves = board.get_legal_moves(state.turn)

    return [move_to_str(move) for move in legal_moves]


def simulation_board_to_fen(
    board: SimulationBoard,
    captured_fen: str = "-:-",
    viewer: Color | None = None,
) -> str:
    """从 SimulationBoard 生成 FEN 字符串

    注意：被吃子需要外部传入，因为 SimulationBoard 不跟踪被吃子历史

    Args:
        board: 模拟棋盘
        captured_fen: 被吃子 FEN 部分，默认 "-:-"
        viewer: 视角，默认使用当前回合

    Returns:
        FEN 字符串
    """
    if viewer is None:
        viewer = board.current_turn

    # 构建棋盘
    grid: list[list[str | None]] = [[None] * 9 for _ in range(10)]
    for piece in board.get_all_pieces():
        row, col = piece.position.row, piece.position.col
        if piece.is_hidden:
            grid[row][col] = "X" if piece.color == Color.RED else "x"
        else:
            # 明子
            pt = piece.actual_type or piece.movement_type
            char = PIECE_TO_CHAR.get(pt, "?")
            grid[row][col] = char.upper() if piece.color == Color.RED else char

    # 生成棋盘字符串
    rows: list[str] = []
    for row in range(9, -1, -1):
        row_str = ""
        empty_count = 0
        for col in range(9):
            cell = grid[row][col]
            if cell is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += cell
        if empty_count > 0:
            row_str += str(empty_count)
        rows.append(row_str)

    board_str = "/".join(rows)
    turn_str = "r" if board.current_turn == Color.RED else "b"
    viewer_str = "r" if viewer == Color.RED else "b"

    return f"{board_str} {captured_fen} {turn_str} {viewer_str}"


def apply_move_with_capture(fen: str, move_str: str) -> tuple[str, dict | None]:
    """应用走法到 FEN，返回新 FEN 和被吃子信息

    与 apply_move_to_fen 不同，此函数还返回被吃子信息。

    Args:
        fen: 当前 FEN
        move_str: 走法字符串（如 "a0a1", "+a0a1", "+a0a1=R"）

    Returns:
        (新 FEN, 被吃子信息)
        被吃子信息格式: {"type": str, "color": str, "was_hidden": bool} 或 None
    """
    # 解析走法和揭子类型
    move, revealed_type = parse_move(move_str)
    if move is None:
        raise ValueError(f"Invalid move: {move_str}")

    # 创建 SimulationBoard 获取被吃子信息
    board = create_board_from_fen(fen)

    # 检查被吃子
    target = board.get_piece(move.to_pos)
    captured_info = None
    if target:
        captured_info = {
            "type": (
                target.actual_type.value
                if target.actual_type
                else target.movement_type.value
                if target.movement_type
                else None
            ),
            "color": target.color.value,
            "was_hidden": target.is_hidden,
        }

    # 使用 apply_move_to_fen 生成新 FEN（它会正确处理揭子类型）
    from engine.fen.move import apply_move_to_fen

    new_fen = apply_move_to_fen(fen, move_str, revealed_type)

    return new_fen, captured_info


def _update_captured_fen(current_captured: str, captured_info: dict | None, viewer: Color) -> str:
    """更新被吃子 FEN 部分"""
    if captured_info is None:
        return current_captured

    # 解析当前被吃子
    if current_captured == "-:-":
        red_lost, black_lost = "", ""
    else:
        parts = current_captured.split(":")
        red_lost = parts[0] if parts[0] != "-" else ""
        black_lost = parts[1] if len(parts) > 1 and parts[1] != "-" else ""

    # 确定添加的字符
    pt = captured_info["type"]
    color = captured_info["color"]
    was_hidden = captured_info["was_hidden"]

    if pt:
        # 有类型信息
        char = PIECE_TO_CHAR.get(PieceType(pt), "?")
        if was_hidden:
            # 暗子被吃 - 小写表示我知道身份
            char = char.lower()
        else:
            # 明子被吃 - 大写
            char = char.upper()
    else:
        # 暗子被吃但不知道身份
        char = "?"

    # 添加到对应列表
    if color == "red":
        red_lost += char
    else:
        black_lost += char

    # 生成新的被吃子 FEN
    red_part = red_lost if red_lost else "-"
    black_part = black_lost if black_lost else "-"
    return f"{red_part}:{black_part}"
