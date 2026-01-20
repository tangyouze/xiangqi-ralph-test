"""全明子中局测试局面 - 按优势等级分类

用于评估 AI 在不同子力差距下的胜率表现。
优势以车的数量差异来衡量。

优势等级:
- 大优: 红方多两车 (+2R)
- 优势: 红方多一车 (+1R)
- 均势: 子力相同 (0)
- 劣势: 红方少一车 (-1R)
- 大劣: 红方少两车 (-2R)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from engine.fen import validate_fen
from engine.types import Color, Position


class Advantage(Enum):
    """优势等级"""

    BIG_ADVANTAGE = "big_advantage"  # 大优 +2R
    ADVANTAGE = "advantage"  # 优势 +1R
    EQUAL = "equal"  # 均势 0
    DISADVANTAGE = "disadvantage"  # 劣势 -1R
    BIG_DISADVANTAGE = "big_disadvantage"  # 大劣 -2R


@dataclass
class MidgamePosition:
    """中局测试局面"""

    id: str
    fen: str
    advantage: Advantage
    red_rooks: int
    black_rooks: int
    seed: int


# 棋盘大小
ROWS = 10
COLS = 9

# 每方初始棋子数量
INITIAL_PIECES = {
    "K": 1,
    "A": 2,
    "E": 2,
    "H": 2,
    "R": 2,
    "C": 2,
    "P": 5,
}


def _get_piece_config(advantage: Advantage) -> tuple[dict, dict]:
    """根据优势等级获取双方棋子配置

    Returns:
        (红方棋子, 黑方棋子)
    """
    # 基础配置：K + H + C + A (不含车)
    base_red = {"K": 1, "H": 1, "C": 1, "A": 1}
    base_black = {"K": 1, "H": 1, "C": 1, "A": 1}

    if advantage == Advantage.BIG_ADVANTAGE:
        # 红方 +2R
        base_red["R"] = 2
        base_black["R"] = 0
    elif advantage == Advantage.ADVANTAGE:
        # 红方 +1R
        base_red["R"] = 2
        base_black["R"] = 1
    elif advantage == Advantage.EQUAL:
        # 均势
        base_red["R"] = 1
        base_black["R"] = 1
    elif advantage == Advantage.DISADVANTAGE:
        # 红方 -1R
        base_red["R"] = 1
        base_black["R"] = 2
    else:  # BIG_DISADVANTAGE
        # 红方 -2R
        base_red["R"] = 0
        base_black["R"] = 2

    return base_red, base_black


def _calculate_captured(on_board: dict) -> str:
    """计算被吃子字符串

    Args:
        on_board: 棋盘上的棋子数量 {"K": 1, "R": 2, ...}

    Returns:
        被吃子字符串，如 "RHECCAAPPPP"
    """
    captured = []
    for piece, initial in INITIAL_PIECES.items():
        on = on_board.get(piece, 0)
        eaten = initial - on
        captured.extend([piece] * eaten)
    return "".join(captured) if captured else "-"


def _get_valid_positions(piece: str, color: Color, rng: random.Random) -> list[Position]:
    """获取棋子的有效位置列表（随机排序）

    Args:
        piece: 棋子类型 (K, R, H, C, A, E, P)
        color: 颜色
        rng: 随机数生成器

    Returns:
        有效位置列表
    """
    positions = []

    if piece == "K":
        # 帅/将在九宫
        if color == Color.RED:
            for row in range(3):
                for col in range(3, 6):
                    positions.append(Position(row, col))
        else:
            for row in range(7, 10):
                for col in range(3, 6):
                    positions.append(Position(row, col))
    elif piece == "A":
        # 士在九宫特定位置
        if color == Color.RED:
            positions = [
                Position(0, 3),
                Position(0, 5),
                Position(1, 4),
                Position(2, 3),
                Position(2, 5),
            ]
        else:
            positions = [
                Position(9, 3),
                Position(9, 5),
                Position(8, 4),
                Position(7, 3),
                Position(7, 5),
            ]
    elif piece == "E":
        # 象在己方半场特定位置
        if color == Color.RED:
            positions = [
                Position(0, 2),
                Position(0, 6),
                Position(2, 0),
                Position(2, 4),
                Position(2, 8),
                Position(4, 2),
                Position(4, 6),
            ]
        else:
            positions = [
                Position(9, 2),
                Position(9, 6),
                Position(7, 0),
                Position(7, 4),
                Position(7, 8),
                Position(5, 2),
                Position(5, 6),
            ]
    elif piece in ("R", "H", "C"):
        # 车马炮可以在任何位置
        for row in range(ROWS):
            for col in range(COLS):
                positions.append(Position(row, col))
    elif piece == "P":
        # 兵/卒在己方半场或过河
        if color == Color.RED:
            # 红兵：row 3-9
            for row in range(3, ROWS):
                for col in range(COLS):
                    positions.append(Position(row, col))
        else:
            # 黑卒：row 0-6
            for row in range(7):
                for col in range(COLS):
                    positions.append(Position(row, col))

    rng.shuffle(positions)
    return positions


def _kings_facing(red_king_pos: Position, black_king_pos: Position, board: dict) -> bool:
    """检查帅将是否对面（同列且中间无子）"""
    if red_king_pos.col != black_king_pos.col:
        return False

    col = red_king_pos.col
    min_row = min(red_king_pos.row, black_king_pos.row)
    max_row = max(red_king_pos.row, black_king_pos.row)

    for row in range(min_row + 1, max_row):
        if (row, col) in board:
            return False  # 中间有子阻挡
    return True  # 对面


def _is_in_check(king_pos: Position, king_color: Color, board: dict) -> bool:
    """简单检查将/帅是否被将军（只检查车和炮）"""
    enemy_color = Color.BLACK if king_color == Color.RED else Color.RED

    # 检查车的攻击
    for (row, col), (piece, color) in board.items():
        if color != enemy_color:
            continue

        if piece == "R":
            # 车攻击：同行或同列且中间无子
            if row == king_pos.row:
                # 同行
                min_col = min(col, king_pos.col)
                max_col = max(col, king_pos.col)
                blocked = False
                for c in range(min_col + 1, max_col):
                    if (row, c) in board:
                        blocked = True
                        break
                if not blocked:
                    return True
            elif col == king_pos.col:
                # 同列
                min_row = min(row, king_pos.row)
                max_row = max(row, king_pos.row)
                blocked = False
                for r in range(min_row + 1, max_row):
                    if (r, col) in board:
                        blocked = True
                        break
                if not blocked:
                    return True

        elif piece == "C":
            # 炮攻击：同行或同列且中间恰好一子
            if row == king_pos.row:
                min_col = min(col, king_pos.col)
                max_col = max(col, king_pos.col)
                count = 0
                for c in range(min_col + 1, max_col):
                    if (row, c) in board:
                        count += 1
                if count == 1:
                    return True
            elif col == king_pos.col:
                min_row = min(row, king_pos.row)
                max_row = max(row, king_pos.row)
                count = 0
                for r in range(min_row + 1, max_row):
                    if (r, col) in board:
                        count += 1
                if count == 1:
                    return True

    return False


def generate_position(advantage: Advantage, seed: int) -> str | None:
    """生成指定优势等级的随机局面

    Args:
        advantage: 优势等级
        seed: 随机种子

    Returns:
        FEN 字符串，如果生成失败返回 None
    """
    rng = random.Random(seed)
    red_pieces, black_pieces = _get_piece_config(advantage)

    # board: (row, col) -> (piece, color)
    board: dict[tuple[int, int], tuple[str, Color]] = {}

    # 先放帅和将
    red_king_positions = _get_valid_positions("K", Color.RED, rng)
    black_king_positions = _get_valid_positions("K", Color.BLACK, rng)

    red_king_pos = None
    black_king_pos = None

    # 尝试找到不对面的帅将位置
    for rk in red_king_positions:
        for bk in black_king_positions:
            if not _kings_facing(rk, bk, {}):
                red_king_pos = rk
                black_king_pos = bk
                break
        if red_king_pos:
            break

    if not red_king_pos or not black_king_pos:
        return None

    board[(red_king_pos.row, red_king_pos.col)] = ("K", Color.RED)
    board[(black_king_pos.row, black_king_pos.col)] = ("K", Color.BLACK)

    # 放置其他棋子
    for piece, count in red_pieces.items():
        if piece == "K" or count == 0:
            continue
        positions = _get_valid_positions(piece, Color.RED, rng)
        placed = 0
        for pos in positions:
            if (pos.row, pos.col) in board:
                continue
            board[(pos.row, pos.col)] = (piece, Color.RED)
            placed += 1
            if placed >= count:
                break

    for piece, count in black_pieces.items():
        if piece == "K" or count == 0:
            continue
        positions = _get_valid_positions(piece, Color.BLACK, rng)
        placed = 0
        for pos in positions:
            if (pos.row, pos.col) in board:
                continue
            board[(pos.row, pos.col)] = (piece, Color.BLACK)
            placed += 1
            if placed >= count:
                break

    # 检查帅将是否对面（放完所有子后再检查）
    if _kings_facing(red_king_pos, black_king_pos, board):
        return None

    # 检查黑方是否被将军（红方先走）
    if _is_in_check(black_king_pos, Color.BLACK, board):
        return None

    # 生成 FEN
    rows_str = []
    for row in range(ROWS - 1, -1, -1):
        row_str = ""
        empty = 0
        for col in range(COLS):
            if (row, col) in board:
                if empty > 0:
                    row_str += str(empty)
                    empty = 0
                piece, color = board[(row, col)]
                char = piece.upper() if color == Color.RED else piece.lower()
                row_str += char
            else:
                empty += 1
        if empty > 0:
            row_str += str(empty)
        rows_str.append(row_str)

    board_fen = "/".join(rows_str)

    # 计算被吃子
    red_captured = _calculate_captured(red_pieces)
    black_captured = _calculate_captured(black_pieces)
    captured_fen = f"{red_captured}:{black_captured}"

    fen = f"{board_fen} {captured_fen} r r"
    return fen


def generate_positions(
    advantage: Advantage, count: int = 10, start_seed: int = 1
) -> list[MidgamePosition]:
    """生成指定优势等级的多个局面

    Args:
        advantage: 优势等级
        count: 生成数量
        start_seed: 起始种子

    Returns:
        MidgamePosition 列表
    """
    positions = []
    seed = start_seed
    attempts = 0
    max_attempts = count * 100  # 最多尝试次数

    red_pieces, black_pieces = _get_piece_config(advantage)

    while len(positions) < count and attempts < max_attempts:
        fen = generate_position(advantage, seed)
        if fen:
            # 验证 FEN 有效性
            valid, _ = validate_fen(fen)
            if valid:
                # ID: MIDS=大优, MIDA=优, MIDB=均, MIDC=劣, MIDD=大劣
                suffix_map = {
                    Advantage.BIG_ADVANTAGE: "S",     # Super/Strong
                    Advantage.ADVANTAGE: "A",         # Advantage
                    Advantage.EQUAL: "B",             # Balanced
                    Advantage.DISADVANTAGE: "C",      # Challenging
                    Advantage.BIG_DISADVANTAGE: "D",  # Disadvantage
                }
                pos_id = f"MID{suffix_map[advantage]}{len(positions)+1:04d}"
                positions.append(
                    MidgamePosition(
                        id=pos_id,
                        fen=fen,
                        advantage=advantage,
                        red_rooks=red_pieces.get("R", 0),
                        black_rooks=black_pieces.get("R", 0),
                        seed=seed,
                    )
                )
        seed += 1
        attempts += 1

    return positions


# 预生成各等级局面
BIG_ADVANTAGE_POSITIONS = generate_positions(Advantage.BIG_ADVANTAGE, 10, 1)
ADVANTAGE_POSITIONS = generate_positions(Advantage.ADVANTAGE, 10, 100)
EQUAL_POSITIONS = generate_positions(Advantage.EQUAL, 10, 200)
DISADVANTAGE_POSITIONS = generate_positions(Advantage.DISADVANTAGE, 10, 300)
BIG_DISADVANTAGE_POSITIONS = generate_positions(Advantage.BIG_DISADVANTAGE, 10, 400)

# 所有局面
ALL_MIDGAME_POSITIONS = (
    BIG_ADVANTAGE_POSITIONS
    + ADVANTAGE_POSITIONS
    + EQUAL_POSITIONS
    + DISADVANTAGE_POSITIONS
    + BIG_DISADVANTAGE_POSITIONS
)


def get_position_by_id(pos_id: str) -> MidgamePosition | None:
    """按 ID 获取局面"""
    for pos in ALL_MIDGAME_POSITIONS:
        if pos.id == pos_id:
            return pos
    return None


def get_positions_by_advantage(advantage: Advantage) -> list[MidgamePosition]:
    """按优势等级获取局面"""
    return [p for p in ALL_MIDGAME_POSITIONS if p.advantage == advantage]


# 导出
__all__ = [
    "Advantage",
    "MidgamePosition",
    "generate_position",
    "generate_positions",
    "BIG_ADVANTAGE_POSITIONS",
    "ADVANTAGE_POSITIONS",
    "EQUAL_POSITIONS",
    "DISADVANTAGE_POSITIONS",
    "BIG_DISADVANTAGE_POSITIONS",
    "ALL_MIDGAME_POSITIONS",
    "get_position_by_id",
    "get_positions_by_advantage",
]
