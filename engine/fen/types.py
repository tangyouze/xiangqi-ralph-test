"""FEN 类型定义和常量"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.types import Color, PieceType, Position


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

# FEN 中使用的所有棋子符号（用于验证）
PIECE_SYMBOLS = set("KAEHRCPkaehrcpXx")

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
