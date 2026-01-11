"""
预计算的攻击表

用于快速查找棋子的攻击范围，避免运行时计算。
"""

from jieqi.types import Position

# 棋盘大小
ROWS = 10
COLS = 9


def _init_king_attacks() -> list[list[Position]]:
    """预计算将/帅的攻击位置（九宫格内）"""
    attacks = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row <= 9 and 0 <= new_col <= 8:
                    positions.append(Position(new_row, new_col))
            attacks.append(positions)
    return attacks


def _init_advisor_attacks() -> list[list[Position]]:
    """预计算士的攻击位置"""
    attacks = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row <= 9 and 0 <= new_col <= 8:
                    positions.append(Position(new_row, new_col))
            attacks.append(positions)
    return attacks


def _init_elephant_attacks() -> list[list[tuple[Position, Position]]]:
    """预计算象的攻击位置（包含象眼位置）

    返回: [(目标位置, 象眼位置), ...]
    """
    attacks = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                new_row, new_col = row + dr, col + dc
                eye_row, eye_col = row + dr // 2, col + dc // 2
                if 0 <= new_row <= 9 and 0 <= new_col <= 8:
                    positions.append((Position(new_row, new_col), Position(eye_row, eye_col)))
            attacks.append(positions)
    return attacks


def _init_horse_attacks() -> list[list[tuple[Position, Position]]]:
    """预计算马的攻击位置（包含马腿位置）

    返回: [(目标位置, 马腿位置), ...]
    """
    attacks = []
    leg_and_moves = [
        ((-1, 0), [(-2, -1), (-2, 1)]),
        ((1, 0), [(2, -1), (2, 1)]),
        ((0, -1), [(-1, -2), (1, -2)]),
        ((0, 1), [(-1, 2), (1, 2)]),
    ]

    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for leg_offset, move_offsets in leg_and_moves:
                leg_row = row + leg_offset[0]
                leg_col = col + leg_offset[1]
                if not (0 <= leg_row <= 9 and 0 <= leg_col <= 8):
                    continue
                leg_pos = Position(leg_row, leg_col)

                for move_offset in move_offsets:
                    new_row = row + move_offset[0]
                    new_col = col + move_offset[1]
                    if 0 <= new_row <= 9 and 0 <= new_col <= 8:
                        positions.append((Position(new_row, new_col), leg_pos))
            attacks.append(positions)
    return attacks


def _init_pawn_attacks_red() -> list[list[Position]]:
    """预计算红兵的攻击位置"""
    attacks = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 向前
            if row + 1 <= 9:
                positions.append(Position(row + 1, col))
            # 过河后可以左右
            if row >= 5:  # 红方过河
                if col - 1 >= 0:
                    positions.append(Position(row, col - 1))
                if col + 1 <= 8:
                    positions.append(Position(row, col + 1))
            attacks.append(positions)
    return attacks


def _init_pawn_attacks_black() -> list[list[Position]]:
    """预计算黑卒的攻击位置"""
    attacks = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 向前（黑方向下）
            if row - 1 >= 0:
                positions.append(Position(row - 1, col))
            # 过河后可以左右
            if row <= 4:  # 黑方过河
                if col - 1 >= 0:
                    positions.append(Position(row, col - 1))
                if col + 1 <= 8:
                    positions.append(Position(row, col + 1))
            attacks.append(positions)
    return attacks


def _init_line_attacks() -> list[list[list[Position]]]:
    """预计算直线攻击（车/炮用）

    对于每个位置，预计算四个方向上的所有位置
    返回: [位置索引][方向][步数] = Position
    方向: 0=上, 1=下, 2=左, 3=右
    """
    attacks = []
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for row in range(ROWS):
        for col in range(COLS):
            dir_attacks = []
            for dr, dc in directions:
                line = []
                for step in range(1, 10):
                    new_row = row + dr * step
                    new_col = col + dc * step
                    if not (0 <= new_row <= 9 and 0 <= new_col <= 8):
                        break
                    line.append(Position(new_row, new_col))
                dir_attacks.append(line)
            attacks.append(dir_attacks)
    return attacks


# 预计算的攻击表
KING_ATTACKS = _init_king_attacks()
ADVISOR_ATTACKS = _init_advisor_attacks()
ELEPHANT_ATTACKS = _init_elephant_attacks()
HORSE_ATTACKS = _init_horse_attacks()
PAWN_ATTACKS_RED = _init_pawn_attacks_red()
PAWN_ATTACKS_BLACK = _init_pawn_attacks_black()
LINE_ATTACKS = _init_line_attacks()


def pos_to_index(pos: Position) -> int:
    """位置转索引"""
    return pos.row * 9 + pos.col


def get_king_attacks(pos: Position) -> list[Position]:
    """获取将/帅的攻击位置"""
    return KING_ATTACKS[pos_to_index(pos)]


def get_advisor_attacks(pos: Position) -> list[Position]:
    """获取士的攻击位置"""
    return ADVISOR_ATTACKS[pos_to_index(pos)]


def get_elephant_attacks(pos: Position) -> list[tuple[Position, Position]]:
    """获取象的攻击位置（包含象眼）"""
    return ELEPHANT_ATTACKS[pos_to_index(pos)]


def get_horse_attacks(pos: Position) -> list[tuple[Position, Position]]:
    """获取马的攻击位置（包含马腿）"""
    return HORSE_ATTACKS[pos_to_index(pos)]


def get_pawn_attacks(pos: Position, is_red: bool) -> list[Position]:
    """获取兵/卒的攻击位置"""
    if is_red:
        return PAWN_ATTACKS_RED[pos_to_index(pos)]
    return PAWN_ATTACKS_BLACK[pos_to_index(pos)]


def get_line_attacks(pos: Position, direction: int) -> list[Position]:
    """获取直线攻击位置

    direction: 0=上, 1=下, 2=左, 3=右
    """
    return LINE_ATTACKS[pos_to_index(pos)][direction]
