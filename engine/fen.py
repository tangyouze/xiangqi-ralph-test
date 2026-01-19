"""
揭棋玩家视角 FEN (JFN v2)

设计目标：
1. 输入输出都用字符串，接口干净
2. FEN 包含完整信息（棋盘 + 被吃的子）
3. 从玩家视角表示，正确处理信息不对称

## 格式

    <棋盘> <被吃子> <回合> <视角>

### 棋盘部分

从 row 9 到 row 0（黑方底线到红方底线），每行用 `/` 分隔。

符号约定：
- 红方明子：K(将) R(车) H(马) C(炮) E(象) A(士) P(兵)
- 黑方明子：k r h c e a p
- 红方暗子：X
- 黑方暗子：x
- 空格：数字 (1-9)

### 被吃子部分

格式：`红方被吃:黑方被吃`

符号规则（用大小写区分明子/暗子）：
- 大写 `R` = 明子被吃（双方都知道）
- 小写 `r` = 暗子被吃，我知道身份（我吃的）
- `?` = 暗子被吃，我不知道身份
- 空被吃用 `-`

信息规则：
- 我方暗子被吃 → 我不知道身份 → 显示 `?`
- 我方明子被吃 → 双方都知道 → 显示 `R`（大写）
- 对方暗子被我吃 → 我知道身份 → 显示 `r`（小写）
- 对方明子被我吃 → 双方都知道 → 显示 `R`（大写）

### 回合和视角

- 回合：`r`（红方走）或 `b`（黑方走）
- 视角：`r`（红方视角）或 `b`（黑方视角）

## 走法格式

- 明子走法：`a0a1`（从 a0 到 a1）
- 揭子走法：`+a0a1`（揭子并走）
- 揭子走法执行后：`+a0a1=R`（揭出了车）

## 示例

初始局面（红方视角）：
    xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r

中局（红方视角）：
    4k4/9/3R5/x1x3x1x/4X4/4x4/X1X3X1X/1C5C1/9/4K4 RP??:raHC r r

解读被吃子 `RP??:raHC`：
- 红方被吃：`R`(车明子) `P`(兵明子) `??`(两个暗子，红方不知道是什么)
- 黑方被吃：`r`(暗子车) `a`(暗子士) `H`(马明子) `C`(炮明子)
  - 小写 ra 表示红方吃的黑方暗子，红方知道身份
  - 大写 HC 表示明子被吃，双方都知道
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from engine.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    from engine.simulation import SimulationBoard
    from engine.view import CapturedPiece, PlayerView, ViewPiece


# =============================================================================
# 常量定义
# =============================================================================

# 棋子类型 -> 字符
PIECE_TO_CHAR: dict[PieceType, str] = {
    PieceType.KING: "k",
    PieceType.ROOK: "r",
    PieceType.HORSE: "h",
    PieceType.CANNON: "c",
    PieceType.ELEPHANT: "e",
    PieceType.ADVISOR: "a",
    PieceType.PAWN: "p",
}

# 字符 -> 棋子类型
CHAR_TO_PIECE: dict[str, PieceType] = {v: k for k, v in PIECE_TO_CHAR.items()}

# 列号 -> 字母
COL_TO_CHAR = "abcdefghi"
CHAR_TO_COL = {c: i for i, c in enumerate(COL_TO_CHAR)}


# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class FenPiece:
    """FEN 中的棋子（玩家视角）"""

    position: Position
    color: Color
    is_hidden: bool
    piece_type: PieceType | None  # None 表示暗子（身份未知）


@dataclass
class CapturedPieceInfo:
    """单个被吃棋子的信息"""

    piece_type: PieceType | None  # None 表示未知（暗子被吃且不是我吃的）
    was_hidden: bool  # 被吃时是否为暗子


@dataclass
class CapturedInfo:
    """被吃子信息（玩家视角）

    区分三种情况：
    1. 明子被吃：双方都知道身份，显示为 R
    2. 暗子被吃，我知道身份（我吃的）：显示为 (R)
    3. 暗子被吃，我不知道身份（对方吃的我的暗子）：显示为 ?
    """

    # 红方被吃的子
    red_captured: list[CapturedPieceInfo] = field(default_factory=list)
    # 黑方被吃的子
    black_captured: list[CapturedPieceInfo] = field(default_factory=list)


@dataclass
class FenState:
    """FEN 解析后的状态"""

    pieces: list[FenPiece]
    captured: CapturedInfo
    turn: Color
    viewer: Color


# =============================================================================
# FEN 生成
# =============================================================================


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


# =============================================================================
# FEN 解析
# =============================================================================


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


# =============================================================================
# 走法字符串
# =============================================================================


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


# =============================================================================
# 便捷函数
# =============================================================================


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


# =============================================================================
# FEN 到 SimulationBoard 转换
# =============================================================================


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


# =============================================================================
# 显示相关常量
# =============================================================================

# 符号映射（用于 markdown/网页显示）
PIECE_SYMBOLS = {
    # 红方（大写）
    "K": "♔",  # 帅
    "A": "✚",  # 仕
    "E": "♗",  # 相
    "H": "♘",  # 马
    "R": "♖",  # 车
    "C": "⊕",  # 炮
    "P": "♙",  # 兵
    "X": "▣",  # 红暗子
    # 黑方（小写）
    "k": "♚",  # 将
    "a": "✜",  # 士
    "e": "♝",  # 象
    "h": "♞",  # 马
    "r": "♜",  # 车
    "c": "⊖",  # 炮
    "p": "♟",  # 卒
    "x": "▣",  # 黑暗子
}

# 中文符号映射（用于终端显示）
PIECE_SYMBOLS_CN = {
    # 红方（大写）
    "K": "帅",
    "A": "仕",
    "E": "相",
    "H": "马",
    "R": "车",
    "C": "炮",
    "P": "兵",
    "X": "暗",
    # 黑方（小写）
    "k": "将",
    "a": "士",
    "e": "象",
    "h": "馬",
    "r": "車",
    "c": "砲",
    "p": "卒",
    "x": "闇",
}

EMPTY_SYMBOL = "·"

# 完整棋子数量
FULL_PIECE_COUNT = {
    "K": 1,
    "A": 2,
    "E": 2,
    "H": 2,
    "R": 2,
    "C": 2,
    "P": 5,
    "k": 1,
    "a": 2,
    "e": 2,
    "h": 2,
    "r": 2,
    "c": 2,
    "p": 5,
}


# =============================================================================
# FEN 验证与显示
# =============================================================================


def _parse_board_positions(board_str: str) -> dict[tuple[int, int], str]:
    """解析棋盘字符串为位置->棋子的字典

    Args:
        board_str: FEN 棋盘部分

    Returns:
        {(row, col): piece_char} 字典，row 0-9 (0是底部红方)，col 0-8
    """
    positions: dict[tuple[int, int], str] = {}
    rows = board_str.split("/")
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx  # FEN 从上到下，转为从下到上
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            else:
                positions[(row_num, col)] = char
                col += 1
    return positions


def _can_red_attack_position(
    positions: dict[tuple[int, int], str], target_row: int, target_col: int
) -> tuple[bool, str]:
    """检查红方是否能攻击到指定位置

    Args:
        positions: 棋盘位置字典
        target_row: 目标行 (0-9)
        target_col: 目标列 (0-8)

    Returns:
        (can_attack, attacker_description)
    """
    target = (target_row, target_col)

    for (row, col), piece in positions.items():
        # 只检查红方棋子（大写）
        if not piece.isupper():
            continue

        # 车 - 直线攻击
        if piece == "R":
            if row == target_row:  # 同行
                # 检查中间无子
                min_col, max_col = min(col, target_col), max(col, target_col)
                blocked = False
                for c in range(min_col + 1, max_col):
                    if (row, c) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"车({row},{col})"
            elif col == target_col:  # 同列
                min_row, max_row = min(row, target_row), max(row, target_row)
                blocked = False
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"车({row},{col})"

        # 马 - 日字跳（需检查蹩腿）
        elif piece == "H":
            # 马的 8 个可能位置及对应的蹩腿位置
            horse_moves = [
                ((2, 1), (1, 0)),  # 上右
                ((2, -1), (1, 0)),  # 上左
                ((-2, 1), (-1, 0)),  # 下右
                ((-2, -1), (-1, 0)),  # 下左
                ((1, 2), (0, 1)),  # 右上
                ((-1, 2), (0, 1)),  # 右下
                ((1, -2), (0, -1)),  # 左上
                ((-1, -2), (0, -1)),  # 左下
            ]
            for (dr, dc), (br, bc) in horse_moves:
                if (row + dr, col + dc) == target:
                    # 检查蹩腿
                    block_pos = (row + br, col + bc)
                    if block_pos not in positions:
                        return True, f"马({row},{col})"

        # 炮 - 需要一个炮架
        elif piece == "C":
            if row == target_row:  # 同行
                min_col, max_col = min(col, target_col), max(col, target_col)
                count = 0
                for c in range(min_col + 1, max_col):
                    if (row, c) in positions:
                        count += 1
                if count == 1:  # 正好一个炮架
                    return True, f"炮({row},{col})"
            elif col == target_col:  # 同列
                min_row, max_row = min(row, target_row), max(row, target_row)
                count = 0
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        count += 1
                if count == 1:
                    return True, f"炮({row},{col})"

        # 兵 - 前进或左右（过河后）
        elif piece == "P":
            # 红兵在 row 0-4 为己方，5-9 为过河
            # 红兵只能向上走 (row+1) 或过河后左右
            if row + 1 == target_row and col == target_col:
                # 向前一步
                return True, f"兵({row},{col})"
            if row >= 5:  # 过河
                if row == target_row and abs(col - target_col) == 1:
                    # 左右一步
                    return True, f"兵({row},{col})"

        # 帅 - 对面将军（已在 validate_fen 中检查，这里也加上）
        elif piece == "K":
            if col == target_col:
                min_row, max_row = min(row, target_row), max(row, target_row)
                blocked = False
                for r in range(min_row + 1, max_row):
                    if (r, col) in positions:
                        blocked = True
                        break
                if not blocked:
                    return True, f"帅({row},{col})"

    return False, ""


def validate_fen(fen: str) -> tuple[bool, str]:
    """验证 FEN 是否合法

    Args:
        fen: FEN 字符串

    Returns:
        (is_valid, error_message)
    """
    parts = fen.split()
    if len(parts) != 4:
        return False, f"FEN 格式错误：需要 4 部分，实际 {len(parts)} 部分"

    board_str, captured_str, turn_str, viewer_str = parts

    # 验证棋盘
    rows = board_str.split("/")
    if len(rows) != 10:
        return False, f"棋盘行数错误：需要 10 行，实际 {len(rows)} 行"

    piece_count: dict[str, int] = {}
    has_red_king = False
    has_black_king = False
    red_king_pos = None
    black_king_pos = None

    for row_idx, row in enumerate(rows):
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            elif char in PIECE_SYMBOLS or char in "XxKkAaEeHhRrCcPp":
                if char == "K":
                    has_red_king = True
                    red_king_pos = (9 - row_idx, col)
                elif char == "k":
                    has_black_king = True
                    black_king_pos = (9 - row_idx, col)

                piece_count[char] = piece_count.get(char, 0) + 1
                col += 1
            else:
                return False, f"非法字符：{char}"

        if col != 9:
            return False, f"第 {9 - row_idx} 行列数错误：需要 9 列，实际 {col} 列"

    # 检查帅将
    if not has_red_king:
        return False, "缺少红方帅"
    if not has_black_king:
        return False, "缺少黑方将"

    # 检查棋子数量是否超标
    for piece, max_count in FULL_PIECE_COUNT.items():
        if piece_count.get(piece, 0) > max_count:
            return False, f"{piece} 数量超标：最多 {max_count}，实际 {piece_count[piece]}"

    # 检查帅将是否对面（同列且中间无子）
    if red_king_pos and black_king_pos and red_king_pos[1] == black_king_pos[1]:
        col = red_king_pos[1]
        # 检查中间是否有棋子
        has_blocker = False
        for row_idx, row in enumerate(rows):
            row_num = 9 - row_idx
            if red_king_pos[0] < row_num < black_king_pos[0]:
                # 解析这一行，检查 col 位置
                c = 0
                for char in row:
                    if char.isdigit():
                        c += int(char)
                    else:
                        if c == col:
                            has_blocker = True
                            break
                        c += 1
                    if c > col:
                        break
        if not has_blocker:
            return False, "帅将对面（非法局面）"

    # 验证回合（必须是红方走）
    if turn_str != "r":
        return False, f"必须是红方走，当前是：{'黑方' if turn_str == 'b' else turn_str}"

    # 验证视角
    if viewer_str not in ("r", "b"):
        return False, f"视角标记错误：{viewer_str}"

    # 检查黑方是否被将军（红方能否直接吃将）
    if black_king_pos:
        positions = _parse_board_positions(board_str)
        can_attack, attacker = _can_red_attack_position(
            positions, black_king_pos[0], black_king_pos[1]
        )
        if can_attack:
            return False, f"黑方被将军（{attacker}可吃将），非法局面"

    return True, "OK"


def fen_to_ascii(fen: str) -> str:
    """将 FEN 转换为 ASCII 棋盘图（符号版，适合 markdown）

    Args:
        fen: FEN 字符串

    Returns:
        ASCII 棋盘字符串
    """
    parts = fen.split()
    if not parts:
        return "Invalid FEN"

    board_str = parts[0]
    rows = board_str.split("/")

    lines = []
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx
        line = [f"{row_num} "]
        col = 0

        for char in row:
            if char.isdigit():
                for _ in range(int(char)):
                    line.append(EMPTY_SYMBOL)
                    col += 1
            elif char in PIECE_SYMBOLS:
                line.append(PIECE_SYMBOLS[char])
                col += 1
            else:
                line.append("?")
                col += 1

        lines.append(" ".join(line))

    lines.append("   a b c d e f g h i")
    return "\n".join(lines)


def fen_to_ascii_cn(fen: str) -> str:
    """将 FEN 转换为 ASCII 棋盘图（中文版，适合终端）

    Args:
        fen: FEN 字符串

    Returns:
        ASCII 棋盘字符串
    """
    parts = fen.split()
    if not parts:
        return "Invalid FEN"

    board_str = parts[0]
    rows = board_str.split("/")

    lines = []
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx
        line = f"{row_num} "

        for char in row:
            if char.isdigit():
                line += "十 " * int(char)
            elif char in PIECE_SYMBOLS_CN:
                line += PIECE_SYMBOLS_CN[char] + " "
            else:
                line += "? "

        lines.append(line.rstrip())

    lines.append("  0  1  2  3  4  5  6  7  8")
    return "\n".join(lines)


def fen_to_canvas_html(fen: str) -> str:
    """将 FEN 转换为交互式 Canvas 棋盘的 HTML 代码

    支持点击选子和走子（纯前端交互，不验证走法合法性）。
    50% 缩放版本，适合嵌入页面。

    Args:
        fen: FEN 字符串

    Returns:
        HTML 字符串，可用于 st.components.v1.html() 渲染
    """
    board_str = fen.split()[0]

    pieces = []
    rows = board_str.split("/")
    for row_idx, row in enumerate(rows):
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            else:
                pieces.append(
                    {
                        "x": col,
                        "y": row_idx,
                        "text": PIECE_SYMBOLS_CN.get(char, char),
                        "isRed": char.isupper(),
                        "char": char,
                    }
                )
                col += 1

    pieces_json = json.dumps(pieces)

    # 50% 缩放: cellSize 40->20, margin 30->18, pieceRadius 16->8
    html = f"""
    <div style="display:flex;gap:10px;align-items:flex-start;">
        <canvas id="interactiveBoard" style="width:196px;height:216px;cursor:pointer;"></canvas>
        <div id="moveInfo" style="font-family:monospace;font-size:11px;padding:6px;background:#f0f0f0;border-radius:4px;min-width:120px;">
            <div><b>Click to select</b></div>
            <div id="selectedPiece" style="margin-top:6px;"></div>
            <div id="moveHistory" style="margin-top:6px;"></div>
        </div>
    </div>
    <script>
    (function() {{
        const canvas = document.getElementById('interactiveBoard');
        const ctx = canvas.getContext('2d');
        const cellSize = 20;
        const margin = 18;
        const pieceRadius = 8;
        let pieces = {pieces_json};
        const colLabels = 'abcdefghi';
        const rowLabels = '9876543210';

        let selectedPiece = null;
        let moveHistory = [];

        const dpr = window.devicePixelRatio || 1;
        const cssWidth = 196;
        const cssHeight = 216;
        canvas.width = cssWidth * dpr;
        canvas.height = cssHeight * dpr;
        ctx.scale(dpr, dpr);

        function draw() {{
            ctx.fillStyle = '#F5DEB3';
            ctx.fillRect(0, 0, cssWidth, cssHeight);
            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 1;
            ctx.strokeRect(margin, margin, 8 * cellSize, 9 * cellSize);

            ctx.fillStyle = '#8B4513';
            ctx.font = 'bold 8px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (let i = 0; i < 9; i++) {{
                ctx.fillText(colLabels[i], margin + i * cellSize, 7);
                ctx.fillText(colLabels[i], margin + i * cellSize, cssHeight - 5);
            }}
            for (let i = 0; i < 10; i++) {{
                ctx.fillText(rowLabels[i], 7, margin + i * cellSize);
                ctx.fillText(rowLabels[i], cssWidth - 7, margin + i * cellSize);
            }}

            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 0.5;
            for (let i = 0; i < 10; i++) {{
                ctx.beginPath();
                ctx.moveTo(margin, margin + i * cellSize);
                ctx.lineTo(margin + 8 * cellSize, margin + i * cellSize);
                ctx.stroke();
            }}
            for (let j = 0; j < 9; j++) {{
                ctx.beginPath();
                ctx.moveTo(margin + j * cellSize, margin);
                ctx.lineTo(margin + j * cellSize, margin + 4 * cellSize);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(margin + j * cellSize, margin + 5 * cellSize);
                ctx.lineTo(margin + j * cellSize, margin + 9 * cellSize);
                ctx.stroke();
            }}

            [[3,0,5,2],[5,0,3,2],[3,7,5,9],[5,7,3,9]].forEach(([x1,y1,x2,y2]) => {{
                ctx.beginPath();
                ctx.moveTo(margin + x1 * cellSize, margin + y1 * cellSize);
                ctx.lineTo(margin + x2 * cellSize, margin + y2 * cellSize);
                ctx.stroke();
            }});

            function drawStar(cx, cy) {{
                const gap = 1, size = 2;
                ctx.beginPath();
                if (cx > margin) {{
                    ctx.moveTo(cx - gap, cy - gap - size);
                    ctx.lineTo(cx - gap, cy - gap);
                    ctx.lineTo(cx - gap - size, cy - gap);
                    ctx.moveTo(cx - gap, cy + gap + size);
                    ctx.lineTo(cx - gap, cy + gap);
                    ctx.lineTo(cx - gap - size, cy + gap);
                }}
                if (cx < margin + 8 * cellSize) {{
                    ctx.moveTo(cx + gap, cy - gap - size);
                    ctx.lineTo(cx + gap, cy - gap);
                    ctx.lineTo(cx + gap + size, cy - gap);
                    ctx.moveTo(cx + gap, cy + gap + size);
                    ctx.lineTo(cx + gap, cy + gap);
                    ctx.lineTo(cx + gap + size, cy + gap);
                }}
                ctx.stroke();
            }}
            [1, 7].forEach(col => [2, 7].forEach(row => drawStar(margin + col * cellSize, margin + row * cellSize)));
            [0, 2, 4, 6, 8].forEach(col => [3, 6].forEach(row => drawStar(margin + col * cellSize, margin + row * cellSize)));

            pieces.forEach(p => {{
                const x = margin + p.x * cellSize;
                const y = margin + p.y * cellSize;
                const color = p.isRed ? '#DC143C' : '#2F4F4F';
                const isSelected = selectedPiece && selectedPiece.x === p.x && selectedPiece.y === p.y;

                if (isSelected) {{
                    ctx.beginPath();
                    ctx.arc(x, y, pieceRadius + 2, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255,215,0,0.5)';
                    ctx.fill();
                }}

                ctx.beginPath();
                ctx.arc(x + 1, y + 1, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0,0,0,0.2)';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(x, y, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = '#FFFAF0';
                ctx.fill();
                ctx.strokeStyle = isSelected ? '#FFD700' : color;
                ctx.lineWidth = isSelected ? 1.5 : 1;
                ctx.stroke();

                ctx.fillStyle = color;
                ctx.font = 'bold 7px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(p.text, x, y);
            }});
        }}

        function updateInfo() {{
            const selDiv = document.getElementById('selectedPiece');
            const histDiv = document.getElementById('moveHistory');
            if (selectedPiece) {{
                const pos = colLabels[selectedPiece.x] + rowLabels[selectedPiece.y];
                selDiv.innerHTML = '<b>Selected:</b> ' + selectedPiece.text + ' ' + pos;
            }} else {{
                selDiv.innerHTML = '';
            }}
            if (moveHistory.length > 0) {{
                histDiv.innerHTML = '<b>Moves:</b><br>' + moveHistory.slice(-5).join('<br>');
            }}
        }}

        function getClickPos(e) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = cssWidth / rect.width;
            const scaleY = cssHeight / rect.height;
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            const col = Math.round((x - margin) / cellSize);
            const row = Math.round((y - margin) / cellSize);
            if (col >= 0 && col <= 8 && row >= 0 && row <= 9) {{
                return {{ col, row }};
            }}
            return null;
        }}

        function findPiece(col, row) {{
            return pieces.find(p => p.x === col && p.y === row);
        }}

        canvas.addEventListener('click', function(e) {{
            const pos = getClickPos(e);
            if (!pos) return;
            const clickedPiece = findPiece(pos.col, pos.row);
            if (selectedPiece) {{
                if (clickedPiece === selectedPiece) {{
                    selectedPiece = null;
                }} else if (clickedPiece && clickedPiece.isRed === selectedPiece.isRed) {{
                    selectedPiece = clickedPiece;
                }} else {{
                    const fromPos = colLabels[selectedPiece.x] + rowLabels[selectedPiece.y];
                    const toPos = colLabels[pos.col] + rowLabels[pos.row];
                    const moveStr = selectedPiece.text + ' ' + fromPos + '->' + toPos;
                    if (clickedPiece) {{
                        pieces = pieces.filter(p => p !== clickedPiece);
                        moveHistory.push(moveStr + 'x' + clickedPiece.text);
                    }} else {{
                        moveHistory.push(moveStr);
                    }}
                    selectedPiece.x = pos.col;
                    selectedPiece.y = pos.row;
                    selectedPiece = null;
                }}
            }} else {{
                if (clickedPiece) {{
                    selectedPiece = clickedPiece;
                }}
            }}
            draw();
            updateInfo();
        }});

        draw();
        updateInfo();
    }})();
    </script>
    """
    return html


# =============================================================================
# FEN 走法应用
# =============================================================================


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
