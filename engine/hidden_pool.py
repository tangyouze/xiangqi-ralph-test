"""暗子池计算

用于计算某方的暗子池（剩余可揭出的棋子类型及数量）。
"""

from __future__ import annotations

import random

from engine.types import PieceType

# 初始棋子数量（不含将/帅，因为将/帅总是在初始位置明示）
INITIAL_PIECE_COUNT = {
    "A": 2,  # 士
    "E": 2,  # 象
    "H": 2,  # 马
    "R": 2,  # 车
    "C": 2,  # 炮
    "P": 5,  # 兵
}

# 棋子字符到 PieceType 的映射
CHAR_TO_PIECE_TYPE = {
    "A": PieceType.ADVISOR,
    "E": PieceType.ELEPHANT,
    "H": PieceType.HORSE,
    "R": PieceType.ROOK,
    "C": PieceType.CANNON,
    "P": PieceType.PAWN,
}


def get_hidden_pool(fen: str, color: str) -> dict[str, int]:
    """计算某方的暗子池

    Args:
        fen: 当前 FEN
        color: "red" 或 "black"

    Returns:
        暗子池 {棋子字符: 剩余数量}
    """
    board_str = fen.split()[0]

    # 统计已揭出的明子
    revealed = {k: 0 for k in INITIAL_PIECE_COUNT}
    for char in board_str:
        # 红方用大写，黑方用小写
        if color == "red" and char.isupper() and char in INITIAL_PIECE_COUNT:
            revealed[char] += 1
        elif color == "black" and char.islower() and char.upper() in INITIAL_PIECE_COUNT:
            revealed[char.upper()] += 1

    # 计算暗子池
    pool = {}
    for piece, initial in INITIAL_PIECE_COUNT.items():
        remaining = initial - revealed[piece]
        if remaining > 0:
            pool[piece] = remaining

    return pool


def random_reveal(fen: str, color: str) -> str:
    """从暗子池中随机选择一个棋子类型

    Args:
        fen: 当前 FEN
        color: "red" 或 "black"

    Returns:
        棋子字符（如 "R", "C", "P"）
    """
    pool = get_hidden_pool(fen, color)
    if not pool:
        return "P"  # fallback

    # 按数量加权随机选择
    choices = []
    weights = []
    for piece, count in pool.items():
        choices.append(piece)
        weights.append(count)

    return random.choices(choices, weights=weights, k=1)[0]
