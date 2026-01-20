"""FEN 走法应用"""

from __future__ import annotations

from engine.fen.board import fen_from_pieces
from engine.fen.parse import parse_fen, parse_move
from engine.fen.types import CapturedInfo, CapturedPieceInfo, FenPiece
from engine.types import ActionType, Color, PieceType


def apply_move_to_fen(fen: str, move_str: str, revealed_type: PieceType | None = None) -> str:
    """在 FEN 上执行走法，返回新的 FEN

    Args:
        fen: 当前 FEN
        move_str: 走法字符串（如 "a0a1" 或 "+a0a1"）
        revealed_type: 揭子后的真实类型（如果是揭子走法）

    Returns:
        执行走法后的新 FEN
    """
    state = parse_fen(fen)
    move, _ = parse_move(move_str)

    # 更新棋盘
    new_pieces: list[FenPiece] = []
    moved_piece: FenPiece | None = None
    captured_piece: FenPiece | None = None

    for fp in state.pieces:
        if fp.position == move.from_pos:
            moved_piece = fp
        elif fp.position == move.to_pos:
            captured_piece = fp
        else:
            new_pieces.append(fp)

    if moved_piece is None:
        raise ValueError(f"No piece at {move.from_pos}")

    # 处理揭子
    if move.action_type == ActionType.REVEAL_AND_MOVE:
        # 揭子后变成明子
        if revealed_type is not None:
            moved_piece = FenPiece(
                position=move.to_pos,
                color=moved_piece.color,
                is_hidden=False,
                piece_type=revealed_type,
            )
        else:
            # 如果没有提供 revealed_type，使用位置类型
            from engine.types import get_position_piece_type

            pos_type = get_position_piece_type(move.from_pos)
            moved_piece = FenPiece(
                position=move.to_pos,
                color=moved_piece.color,
                is_hidden=False,
                piece_type=pos_type,
            )
    else:
        # 普通走法
        moved_piece = FenPiece(
            position=move.to_pos,
            color=moved_piece.color,
            is_hidden=moved_piece.is_hidden,
            piece_type=moved_piece.piece_type,
        )

    new_pieces.append(moved_piece)

    # 更新被吃子信息
    new_captured = CapturedInfo(
        red_captured=list(state.captured.red_captured),
        black_captured=list(state.captured.black_captured),
    )

    if captured_piece is not None:
        # 添加到被吃子列表
        cap_info = CapturedPieceInfo(
            piece_type=captured_piece.piece_type,
            was_hidden=captured_piece.is_hidden,
        )
        if captured_piece.color == Color.RED:
            new_captured.red_captured.append(cap_info)
        else:
            new_captured.black_captured.append(cap_info)

    # 切换回合
    new_turn = state.turn.opposite

    return fen_from_pieces(new_pieces, new_captured, new_turn, state.viewer)
