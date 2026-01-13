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


# ============ 反向攻击表（用于快速检测将是否被攻击）============


def _init_horse_reverse_attacks() -> list[list[tuple[Position, Position]]]:
    """预计算能攻击到每个位置的马的位置

    给定目标位置，返回所有可能攻击到该位置的马的位置及其马腿
    返回: [(马的位置, 马腿位置), ...]

    马腿位置是从马的位置出发，向目标方向走一步的位置。
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 马从8个方向攻击，每个方向包含马相对于目标的偏移
            # 马腿在马向目标方向"先直走一步"的位置
            horse_offsets = [
                # (马相对于目标的偏移, 马腿相对于马的偏移)
                ((-2, -1), (1, 0)),   # 马在上方偏左，马腿在马下方（马先向下走）
                ((-2, 1), (1, 0)),    # 马在上方偏右，马腿在马下方
                ((2, -1), (-1, 0)),   # 马在下方偏左，马腿在马上方
                ((2, 1), (-1, 0)),    # 马在下方偏右，马腿在马上方
                ((-1, -2), (0, 1)),   # 马在左上，马腿在马右边
                ((1, -2), (0, 1)),    # 马在左下，马腿在马右边
                ((-1, 2), (0, -1)),   # 马在右上，马腿在马左边
                ((1, 2), (0, -1)),    # 马在右下，马腿在马左边
            ]
            for horse_offset, leg_offset_from_horse in horse_offsets:
                horse_row = row + horse_offset[0]
                horse_col = col + horse_offset[1]
                # 马腿是从马的位置出发计算的
                leg_row = horse_row + leg_offset_from_horse[0]
                leg_col = horse_col + leg_offset_from_horse[1]
                if (0 <= horse_row <= 9 and 0 <= horse_col <= 8 and
                    0 <= leg_row <= 9 and 0 <= leg_col <= 8):
                    positions.append((Position(horse_row, horse_col), Position(leg_row, leg_col)))
            reverse.append(positions)
    return reverse


def _init_pawn_reverse_attacks_red() -> list[list[Position]]:
    """预计算能攻击到每个位置的红兵的位置

    红兵向上攻击，所以能攻击到 (row, col) 的红兵在:
    - (row-1, col) - 正下方的兵向上攻击
    - (row, col-1) 或 (row, col+1) - 左右的兵横向攻击（需要过河）
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 正下方的红兵（向上攻击）
            if row - 1 >= 0:
                positions.append(Position(row - 1, col))
            # 左边的红兵（横向攻击，需要过河 row >= 5）
            if col - 1 >= 0 and row >= 5:
                positions.append(Position(row, col - 1))
            # 右边的红兵
            if col + 1 <= 8 and row >= 5:
                positions.append(Position(row, col + 1))
            reverse.append(positions)
    return reverse


def _init_pawn_reverse_attacks_black() -> list[list[Position]]:
    """预计算能攻击到每个位置的黑卒的位置

    黑卒向下攻击，所以能攻击到 (row, col) 的黑卒在:
    - (row+1, col) - 正上方的卒向下攻击
    - (row, col-1) 或 (row, col+1) - 左右的卒横向攻击（需要过河）
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 正上方的黑卒（向下攻击）
            if row + 1 <= 9:
                positions.append(Position(row + 1, col))
            # 左边的黑卒（横向攻击，需要过河 row <= 4）
            if col - 1 >= 0 and row <= 4:
                positions.append(Position(row, col - 1))
            # 右边的黑卒
            if col + 1 <= 8 and row <= 4:
                positions.append(Position(row, col + 1))
            reverse.append(positions)
    return reverse


# 预计算的反向攻击表
HORSE_REVERSE_ATTACKS = _init_horse_reverse_attacks()
PAWN_REVERSE_ATTACKS_RED = _init_pawn_reverse_attacks_red()
PAWN_REVERSE_ATTACKS_BLACK = _init_pawn_reverse_attacks_black()


def get_horse_reverse_attacks(pos: Position) -> list[tuple[Position, Position]]:
    """获取能攻击到该位置的马的位置"""
    return HORSE_REVERSE_ATTACKS[pos_to_index(pos)]


def get_pawn_reverse_attacks(pos: Position, attacker_is_red: bool) -> list[Position]:
    """获取能攻击到该位置的兵/卒的位置"""
    if attacker_is_red:
        return PAWN_REVERSE_ATTACKS_RED[pos_to_index(pos)]
    return PAWN_REVERSE_ATTACKS_BLACK[pos_to_index(pos)]


def _init_elephant_reverse_attacks() -> list[list[tuple[Position, Position]]]:
    """预计算能攻击到每个位置的象的位置

    象走田字，从 (row, col) 可以被 4 个方向的象攻击
    返回: [(象的位置, 象眼位置), ...]
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            # 象从4个方向攻击
            for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                elephant_row = row + dr
                elephant_col = col + dc
                eye_row = row + dr // 2
                eye_col = col + dc // 2
                if (0 <= elephant_row <= 9 and 0 <= elephant_col <= 8 and
                    0 <= eye_row <= 9 and 0 <= eye_col <= 8):
                    positions.append((Position(elephant_row, elephant_col), Position(eye_row, eye_col)))
            reverse.append(positions)
    return reverse


def _init_advisor_reverse_attacks() -> list[list[Position]]:
    """预计算能攻击到每个位置的士的位置

    士走斜线一格，从 (row, col) 可以被 4 个斜方向的士攻击
    返回: [士的位置, ...]
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                advisor_row = row + dr
                advisor_col = col + dc
                if 0 <= advisor_row <= 9 and 0 <= advisor_col <= 8:
                    positions.append(Position(advisor_row, advisor_col))
            reverse.append(positions)
    return reverse


def _init_king_reverse_attacks() -> list[list[Position]]:
    """预计算能攻击到每个位置的将/帅的位置

    将走直线一格，从 (row, col) 可以被 4 个方向的将攻击
    返回: [将的位置, ...]
    """
    reverse = []
    for row in range(ROWS):
        for col in range(COLS):
            positions = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                king_row = row + dr
                king_col = col + dc
                if 0 <= king_row <= 9 and 0 <= king_col <= 8:
                    positions.append(Position(king_row, king_col))
            reverse.append(positions)
    return reverse


ELEPHANT_REVERSE_ATTACKS = _init_elephant_reverse_attacks()
ADVISOR_REVERSE_ATTACKS = _init_advisor_reverse_attacks()
KING_REVERSE_ATTACKS = _init_king_reverse_attacks()


def get_elephant_reverse_attacks(pos: Position) -> list[tuple[Position, Position]]:
    """获取能攻击到该位置的象的位置"""
    return ELEPHANT_REVERSE_ATTACKS[pos_to_index(pos)]


def get_advisor_reverse_attacks(pos: Position) -> list[Position]:
    """获取能攻击到该位置的士的位置"""
    return ADVISOR_REVERSE_ATTACKS[pos_to_index(pos)]


def get_king_reverse_attacks(pos: Position) -> list[Position]:
    """获取能攻击到该位置的将的位置"""
    return KING_REVERSE_ATTACKS[pos_to_index(pos)]
