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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jieqi.types import ActionType, Color, JieqiMove, PieceType, Position

if TYPE_CHECKING:
    from jieqi.simulation import SimulationBoard
    from jieqi.view import CapturedPiece, PlayerView, ViewPiece


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
    from jieqi.simulation import SimulationBoard
    from jieqi.types import GameResult, get_position_piece_type
    from jieqi.view import PlayerView, ViewPiece

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
            from jieqi.types import get_position_piece_type

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
